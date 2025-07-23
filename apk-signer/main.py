import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from config import API_TOKEN
import db

# Import routers
from handlers.start import router as start_router
from handlers.sign_apk import router as sign_apk_router
from handlers.balance import router as balance_router
from handlers.payment import router as payment_router
from handlers.support import router as support_router
from handlers.admin_panel import router as admin_router


async def main() -> None:
    # Initialize database
    db.init_db()
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Create bot and dispatcher
    bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher(storage=MemoryStorage())
    
    # Include routers
    dp.include_router(start_router)
    dp.include_router(sign_apk_router)
    dp.include_router(balance_router)
    dp.include_router(payment_router)
    dp.include_router(support_router)
    dp.include_router(admin_router)
    
    # Start polling
    print("✅ Bot is running...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())