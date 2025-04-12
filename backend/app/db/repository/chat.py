from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.models.chat import ChatMessage
from fastapi import HTTPException

# SH: TODO - Implement real-time streaming of chat messages
async def create_chat_message(db: AsyncSession, message_data: dict):
    try:
        #SH: Validate required keys exist in the input dictionary
        if not all(key in message_data for key in ["content", "sender", "user_id", "agent_id"]):
            raise ValueError("Invalid message format")
        
        #SH: Ensure the sender is either 'user' or 'agent'
        if message_data["sender"] not in ["user", "agent"]:
            raise ValueError("Invalid sender type")
        
        #SH: Clean and limit the content to 1000 characters
        message_data["content"] = message_data["content"].strip()[:1000]
        
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
async def get_chat_history(db: AsyncSession, user_id: str, agent_id: int, limit: int = 100):
    #SH: Execute a query to fetch chat messages matching user_id and agent_id
    result = await db.execute(
        select(ChatMessage)
        .where((ChatMessage.user_id == user_id) & (ChatMessage.agent_id == agent_id))
        .order_by(ChatMessage.timestamp.desc())
        .limit(limit)
    )
    #SH: Return the list of ChatMessage objects
    return result.scalars().all()
