
from aiogram import Router, types
from aiogram.filters import Command
from keyboards import main_menu, admin_menu
from config import ADMINS
import db
import logging

router = Router()
logger = logging.getLogger(__name__)

@router.message(Command("start"))
async def start_command(message: types.Message):
    """Handle /start command with user registration and menu display"""
    try:
        user_id = message.from_user.id
        username = message.from_user.username
        first_name = message.from_user.first_name
        last_name = message.from_user.last_name
        
        # Register/update user in database
        db.add_user(user_id, username, first_name, last_name)
        db.update_user_activity(user_id)
        
        # Check if user is blocked
        if db.is_user_blocked(user_id):
            await message.answer(
                "🚫 حساب شما مسدود شده است.\n"
                "برای اطلاعات بیشتر با پشتیبانی تماس بگیرید."
            )
            return
        
        # Determine if user is admin
        is_admin = user_id in ADMINS
        
        welcome_message = (
            f"👋 سلام {'عزیز' if not first_name else first_name}!\n\n"
            "🔐 به ربات امضای APK خوش آمدید!\n\n"
            "✨ **امکانات ربات:**\n"
            "📱 امضای خودکار فایل‌های APK\n"
            "💰 مدیریت موجودی TRX\n"
            "🧾 مشاهده تاریخچه تراکنش‌ها\n"
            "🆘 پشتیبانی 24 ساعته\n\n"
            f"{'👨‍💼 شما به عنوان ادمین وارد شده‌اید' if is_admin else ''}\n\n"
            "لطفا از منوی زیر یک گزینه را انتخاب نمایید:"
        )
        
        # Send appropriate menu
        menu_keyboard = admin_menu() if is_admin else main_menu()
        
        await message.answer(
            text=welcome_message,
            reply_markup=menu_keyboard,
            parse_mode="Markdown"
        )
        
        logger.info(f"User {user_id} ({username}) started the bot")
        
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await message.answer(
            "❌ خطایی در راه‌اندازی رخ داد. لطفا مجددا تلاش کنید.",
            reply_markup=main_menu()
        )

@router.callback_query(lambda c: c.data == "back_to_main")
async def back_to_main_callback(callback: types.CallbackQuery):
    """Handle back to main menu callback"""
    try:
        user_id = callback.from_user.id
        is_admin = user_id in ADMINS
        
        await callback.message.delete()
        
        welcome_message = (
            "🏠 منوی اصلی\n\n"
            "یک گزینه را انتخاب کنید:"
        )
        
        menu_keyboard = admin_menu() if is_admin else main_menu()
        
        await callback.message.answer(
            text=welcome_message,
            reply_markup=menu_keyboard
        )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in back to main callback: {e}")
        await callback.answer("❌ خطا در بازگشت به منو", show_alert=True)
