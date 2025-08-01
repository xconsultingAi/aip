from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, and_, update, delete
from sqlalchemy.orm import selectinload
from app.db.models.chat import ChatMessage
from app.db.models.chat import Conversation
from fastapi import HTTPException
from app.services.dashboard_ws import trigger_conversation_update

#SH: Create conversation
async def create_conversation(db: AsyncSession, conversation_data: dict):
    db_conv = Conversation(**conversation_data)
    db.add(db_conv)
    await db.commit()
    await db.refresh(db_conv)
    
    # Calculate new conversation count
    count = await get_user_conversation_count(db, db_conv.user_id)
    await trigger_conversation_update(count, db_conv.user_id, db_conv.organization_id)
    
    return db_conv

#SH: Update conversation title
async def update_conversation_title(db: AsyncSession, conversation_id: int, new_title: str):
    result = await db.execute(
        update(Conversation)
        .where(Conversation.id == conversation_id)
        .values(title=new_title)
    )
    await db.commit()
    return result.rowcount

#SH: Delete conversation
async def delete_conversation(db: AsyncSession, conversation_id: int):
    # Get conversation before deletion
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    db_conv = result.scalars().first()
    
    if db_conv:
        # Delete messages first
        await db.execute(
            delete(ChatMessage)
            .where(ChatMessage.conversation_id == conversation_id)
        )
        # Then delete conversation
        await db.execute(
            delete(Conversation)
            .where(Conversation.id == conversation_id)
        )
        await db.commit()
        
        # Calculate new conversation count
        count = await get_user_conversation_count(db, db_conv.user_id)
        await trigger_conversation_update(count, db_conv.user_id, db_conv.organization_id)
        
        return 1
    return 0

#SH: Create chat message
async def create_chat_message(db: AsyncSession, message_data: dict):
    try:
        # Add conversation_id validation
        if "conversation_id" not in message_data:
            raise ValueError("conversation_id is required")
        
        #SH: Validate required keys exist in the input dictionary
        if not all(key in message_data for key in ["content", "sender", "user_id", "agent_id"]):
            raise ValueError("Invalid message format")
        
        #SH: Ensure the sender is either 'user' or 'agent'
        if message_data["sender"] not in ["user", "agent"]:
            raise ValueError("Invalid sender type")
        
        #SH: Clean and limit the content to 1000 characters
        message_data["content"] = message_data["content"].strip()[:1000]

        #SH: Check if sequence_id is present, if not calculate it
        if "sequence_id" not in message_data:
            result = await db.execute(
                select(func.max(ChatMessage.sequence_id))
                .where(
                    and_(
                        ChatMessage.user_id == message_data["user_id"],
                        ChatMessage.agent_id == message_data["agent_id"],
                        ChatMessage.conversation_id == message_data["conversation_id"]
                    )
                )
            )
            max_sequence = result.scalar() or 0
            message_data["sequence_id"] = max_sequence + 1
        #SH: Create a new ChatMessage object and add it to the session
        db_message = ChatMessage(**message_data)
        db.add(db_message)
        
        #SH: Commit the transaction and refresh the object to return updated data
        await db.commit()
        await db.refresh(db_message)
        return db_message
    except Exception as e:
        #SH: Rollback on failure and raise an HTTPException
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

#SH: Retrieve the latest chat history for a specific user-agent pair
async def fetch_chat_history(
    db: AsyncSession, 
    user_id: str, 
    agent_id: int, 
    conversation_id: int,
    page: int = 1, 
    page_size: int = 50
):
    offset = (page - 1) * page_size
    result = await db.execute(
        select(ChatMessage)
        .where(
            and_(
                ChatMessage.user_id == user_id,
                ChatMessage.agent_id == agent_id,
                ChatMessage.conversation_id == conversation_id
            )
        )
        .order_by(ChatMessage.timestamp.asc())
        .offset(offset)
        .limit(page_size)
    )
    #SH: Return the list of ChatMessage objects
    return result.scalars().all()

#SH: Get conversation by id
async def get_conversation_by_id(
    db: AsyncSession, 
    conversation_id: int,
    user_id: str
) -> Conversation | None:
    #SH: Get single conversation with messages
    result = await db.execute(
        select(Conversation)
        .where(
            (Conversation.id == conversation_id) &
            (Conversation.user_id == user_id)
        )
        .options(selectinload(Conversation.messages))
    )
    return result.scalars().first()

#SH: Update conversation title
async def update_conversation_title(db: AsyncSession, conversation_id: int, new_title: str):
    new_title = new_title.strip() or "New Chat"
    result = await db.execute(
        update(Conversation)
        .where(Conversation.id == conversation_id)
        .values(title=new_title)
    )
    await db.commit()
    return result.rowcount

#SH: Get user conversation count
async def get_user_conversation_count(
    db: AsyncSession, 
    user_id: str  # Expects string user_id
) -> int:
    #SH: Get total count of conversations for a user
    result = await db.execute(
        select(func.count(Conversation.id))
        .where(Conversation.user_id == user_id)
    )
    return result.scalar() or 0

#SH: Get conversation
async def get_conversation(
    db: AsyncSession,
    user_id: str,
    agent_id: int
) -> list[Conversation]:
    #SH: Get all conversations for a user-agent pair
    result = await db.execute(
        select(Conversation)
        .where(
            (Conversation.user_id == user_id) &
            (Conversation.agent_id == agent_id)
        )
        .order_by(Conversation.updated_at.desc())
    )
    return result.scalars().all()

#SH: Get all conversations for a user across all agents
async def get_all_user_conversations(
    db: AsyncSession, 
    user_id: str
) -> list[Conversation]:
    #SH: Get all conversations for a user across all agents
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
    )
    return result.scalars().all()
