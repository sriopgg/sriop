
from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import logging

from config import ADMINS
from keyboards import back_to_main_menu
import db

router = Router()
logger = logging.getLogger(__name__)

class SupportStates(StatesGroup):
    waiting_for_message = State()
    admin_replying = State()

@router.message(lambda message: message.text == "پشتیبانی 🆘")
async def support_menu(message: types.Message, state: FSMContext):
    """Show support options"""
    try:
        user_id = message.from_user.id
        
        # Update user activity
        db.update_user_activity(user_id)
        
        # Check if user is blocked
        if db.is_user_blocked(user_id):
            await message.answer(
                "🚫 حساب شما مسدود شده است.",
                reply_markup=back_to_main_menu()
            )
            return
        
        support_info = (
            "🆘 **مرکز پشتیبانی**\n\n"
            "💬 برای ارتباط با پشتیبانی، پیام خود را بنویسید.\n"
            "پشتیبانی ما در اسرع وقت پاسخ شما را خواهد داد.\n\n"
            "📋 **موضوعات رایج:**\n"
            "• مشکل در امضای APK\n"
            "• خطا در پرداخت\n"
            "• سوالات عمومی\n"
            "• گزارش باگ\n\n"
            "📝 پیام خود را بنویسید:"
        )
        
        await message.answer(
            support_info,
            parse_mode="Markdown",
            reply_markup=back_to_main_menu()
        )
        
        await state.set_state(SupportStates.waiting_for_message)
        
    except Exception as e:
        logger.error(f"Error in support menu: {e}")
        await message.answer(
            "❌ خطا در نمایش پشتیبانی.",
            reply_markup=back_to_main_menu()
        )

@router.message(SupportStates.waiting_for_message, F.text)
async def handle_support_message(message: types.Message, state: FSMContext, bot: Bot):
    """Handle support message from user"""
    try:
        user_id = message.from_user.id
        user_message = message.text
        
        # Save support message to database
        db.add_support_message(user_id, message.message_id, user_message)
        
        # Get user info
        user = db.get_user(user_id)
        username = f"@{user['username']}" if user and user['username'] else "بدون نام کاربری"
        full_name = f"{user['first_name'] or ''} {user['last_name'] or ''}".strip() if user else "نامشخص"
        
        # Format message for admins
        admin_message = (
            f"💬 **پیام پشتیبانی جدید**\n\n"
            f"👤 کاربر: {full_name}\n"
            f"🆔 ID: `{user_id}`\n"
            f"📝 نام کاربری: {username}\n"
            f"💰 موجودی: {user['balance']:.2f} TRX\n\n"
            f"📩 **پیام:**\n{user_message}\n\n"
            f"برای پاسخ، از دستور /reply {user_id} استفاده کنید."
        )
        
        # Send to all admins
        for admin_id in ADMINS:
            try:
                await bot.send_message(
                    chat_id=admin_id,
                    text=admin_message,
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.error(f"Failed to send support message to admin {admin_id}: {e}")
        
        # Confirm to user
        await message.answer(
            "✅ **پیام شما ارسال شد**\n\n"
            "📨 پیام شما به تیم پشتیبانی ارسال شد.\n"
            "⏰ معمولاً در کمتر از 24 ساعت پاسخ دریافت خواهید کرد.\n\n"
            "🙏 از صبر شما متشکریم.",
            parse_mode="Markdown",
            reply_markup=back_to_main_menu()
        )
        
        await state.clear()
        logger.info(f"Support message received from user {user_id}")
        
    except Exception as e:
        logger.error(f"Error handling support message: {e}")
        await message.answer(
            "❌ خطا در ارسال پیام. لطفا مجددا تلاش کنید.",
            reply_markup=back_to_main_menu()
        )
        await state.clear()

@router.message(Command("reply"))
async def admin_reply_command(message: types.Message, state: FSMContext):
    """Admin reply to support message"""
    try:
        user_id = message.from_user.id
        
        # Check if user is admin
        if user_id not in ADMINS:
            return
        
        # Parse command arguments
        args = message.text.split(' ', 2)
        if len(args) < 2:
            await message.answer(
                "❌ فرمت صحیح: /reply <user_id> [پیام]\n"
                "مثال: /reply 123456789 سلام، مشکل شما حل شد."
            )
            return
        
        try:
            target_user_id = int(args[1])
        except ValueError:
            await message.answer("❌ شناسه کاربر باید عددی باشد.")
            return
        
        # Check if target user exists
        target_user = db.get_user(target_user_id)
        if not target_user:
            await message.answer("❌ کاربر یافت نشد.")
            return
        
        if len(args) == 3:
            # Reply message provided
            reply_message = args[2]
            await send_admin_reply(message, target_user_id, reply_message, target_user)
        else:
            # Wait for reply message
            await state.update_data({'target_user_id': target_user_id})
            await state.set_state(SupportStates.admin_replying)
            
            target_name = f"{target_user['first_name'] or ''} {target_user['last_name'] or ''}".strip()
            await message.answer(
                f"📝 پاسخ به کاربر {target_name} (ID: {target_user_id}):\n\n"
                "لطفا پیام پاسخ را بنویسید:"
            )
    
    except Exception as e:
        logger.error(f"Error in admin reply command: {e}")
        await message.answer("❌ خطا در پردازش دستور.")

@router.message(SupportStates.admin_replying, F.text)
async def handle_admin_reply(message: types.Message, state: FSMContext):
    """Handle admin reply message"""
    try:
        data = await state.get_data()
        target_user_id = data.get('target_user_id')
        
        if not target_user_id:
            await message.answer("❌ خطا در دریافت اطلاعات کاربر.")
            await state.clear()
            return
        
        target_user = db.get_user(target_user_id)
        if not target_user:
            await message.answer("❌ کاربر یافت نشد.")
            await state.clear()
            return
        
        await send_admin_reply(message, target_user_id, message.text, target_user)
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error handling admin reply: {e}")
        await message.answer("❌ خطا در ارسال پاسخ.")
        await state.clear()

async def send_admin_reply(message: types.Message, target_user_id: int, reply_text: str, target_user: dict):
    """Send admin reply to user"""
    try:
        from aiogram import Bot
        bot = Bot.get_current()
        
        # Send reply to user
        user_message = (
            f"💬 **پاسخ پشتیبانی**\n\n"
            f"{reply_text}\n\n"
            f"🤝 تیم پشتیبانی"
        )
        
        await bot.send_message(
            chat_id=target_user_id,
            text=user_message,
            parse_mode="Markdown",
            reply_markup=back_to_main_menu()
        )
        
        # Confirm to admin
        target_name = f"{target_user['first_name'] or ''} {target_user['last_name'] or ''}".strip()
        await message.answer(
            f"✅ پاسخ به {target_name} (ID: {target_user_id}) ارسال شد."
        )
        
        logger.info(f"Admin {message.from_user.id} replied to user {target_user_id}")
        
    except Exception as e:
        logger.error(f"Error sending admin reply: {e}")
        await message.answer("❌ خطا در ارسال پاسخ.")

# Handle support messages for non-admin users outside of support state
@router.message(lambda message: message.text and message.from_user.id not in ADMINS and "پشتیبانی" in message.text.lower())
async def general_support_trigger(message: types.Message, state: FSMContext):
    """Trigger support for general messages containing support keywords"""
    await support_menu(message, state)
