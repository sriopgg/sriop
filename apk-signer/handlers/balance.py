
from aiogram import Router, types
from keyboards import back_to_main_menu
from datetime import datetime
import db
import logging

router = Router()
logger = logging.getLogger(__name__)

@router.message(lambda message: message.text == "حساب کاربری 🧾")
async def show_balance(message: types.Message):
    """Display user account information and transaction history"""
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
        
        # Get user information
        user = db.get_user(user_id)
        if not user:
            await message.answer(
                "❌ اطلاعات کاربری یافت نشد. لطفا دوباره /start کنید.",
                reply_markup=back_to_main_menu()
            )
            return
        
        # Get recent transactions
        transactions = db.get_user_transactions(user_id, limit=5)
        
        # Format user info
        join_date = datetime.fromisoformat(user['join_date']).strftime("%Y/%m/%d") if user['join_date'] else "نامشخص"
        
        user_info = (
            "👤 **اطلاعات حساب کاربری**\n\n"
            f"🆔 شناسه تلگرام: `{user_id}`\n"
            f"👤 نام کاربری: {'@' + user['username'] if user['username'] else 'تنظیم نشده'}\n"
            f"📅 تاریخ عضویت: {join_date}\n"
            f"💰 موجودی: **{user['balance']:.2f} TRX**\n\n"
        )
        
        # Add transaction history
        if transactions:
            user_info += "📊 **آخرین تراکنش‌ها:**\n\n"
            
            for i, tx in enumerate(transactions, 1):
                tx_time = datetime.fromisoformat(tx['timestamp']).strftime("%m/%d %H:%M")
                amount_str = f"+{tx['amount']:.2f}" if tx['amount'] > 0 else f"{tx['amount']:.2f}"
                
                # Transaction type icons
                type_icons = {
                    'deposit': '💳',
                    'sign_fee': '📱',
                    'admin_credit': '👨‍💼',
                    'admin_debit': '👨‍💼',
                    'refund': '↩️'
                }
                
                icon = type_icons.get(tx['tx_type'], '💰')
                status_emoji = '✅' if tx['status'] == 'completed' else '⏳'
                
                user_info += (
                    f"{i}. {icon} {amount_str} TRX {status_emoji}\n"
                    f"   📅 {tx_time}"
                )
                
                if tx['description']:
                    user_info += f" | {tx['description']}"
                
                if tx['trx_id'] and len(tx['trx_id']) > 10:
                    user_info += f"\n   🔗 TX: {tx['trx_id'][:8]}..."
                
                user_info += "\n\n"
        else:
            user_info += "📝 هیچ تراکنشی یافت نشد.\n\n"
        
        user_info += "ℹ️ برای افزایش موجودی از دکمه 'افزایش موجودی' استفاده کنید."
        
        await message.answer(
            user_info,
            reply_markup=back_to_main_menu(),
            parse_mode="Markdown"
        )
        
        logger.info(f"Balance info shown for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error showing balance for user {message.from_user.id}: {e}")
        await message.answer(
            "❌ خطا در نمایش اطلاعات حساب. لطفا مجددا تلاش کنید.",
            reply_markup=back_to_main_menu()
        )
