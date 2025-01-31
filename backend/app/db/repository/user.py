from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.models.user import User

#MJ: This file will contain all the database operations related to the User model

async def get_user(db: AsyncSession, user_id: str) -> User | None:
    result = await db.execute(select(User).where(User.user_id == user_id))
    return result.scalars().first()

async def create_user(db: AsyncSession, user_id: str, name: str = None) -> User:
    try:
        user = User(user_id=user_id, name=name)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user
    except Exception as e:
        await db.rollback()
        raise RuntimeError(f"User creation failed: {str(e)}")