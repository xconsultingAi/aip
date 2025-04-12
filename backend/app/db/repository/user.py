import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.models.user import User

logging.basicConfig(level=logging.INFO)

# MJ: This file will contain all the database operations related to the User model
async def get_user(db: AsyncSession, user_id: str) -> User | None:
    logging.info(f"Attempting to fetch user with user_id: {user_id}")
    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalars().first()
    if user:
        logging.info(f"User found: {user}")
    else:
        logging.info(f"No user found with user_id: {user_id}")
    return user

async def create_user(db: AsyncSession, user_id: str, name: str = None,
                      email: str = None,organization_id: int = None) -> User:
    logging.info(f"Creating user with user_id: {user_id}, name: {name}, org_id: {organization_id}")
    user = User(user_id=user_id, name=name,email=email,organization_id=organization_id 
    )
 #SH: parameter types and add email   
    db.add(user)
    try:
        await db.commit()
        await db.refresh(user)
        logging.info(f"User created successfully: {user}")
    except Exception as e:
        await db.rollback()
        logging.error(f"Error creating user {user_id}: {str(e)}")
        raise
    return user
