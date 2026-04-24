import asyncio
from app.database.session import AsyncSessionLocal
from app.models.admin_user import AdminUser
from passlib.context import CryptContext

pwd = CryptContext(schemes=["bcrypt"])

async def create():
    async with AsyncSessionLocal() as s:
        admin = AdminUser(email="admin@teste.com", hashed_password=pwd.hash("Teste123!"), full_name="Admin", is_active=True, is_superuser=True)
        s.add(admin)
        await s.commit()
        print("Admin criado!")

asyncio.run(create())