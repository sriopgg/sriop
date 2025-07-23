
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def main_menu() -> ReplyKeyboardMarkup:
    """Main menu keyboard with four primary functions"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="امضای APK 📱")],
            [
                KeyboardButton(text="حساب کاربری 🧾"),
                KeyboardButton(text="افزایش موجودی 💰"),
            ],
            [KeyboardButton(text="پشتیبانی 🆘")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="یک گزینه را انتخاب کنید..."
    )
    return keyboard

def admin_menu() -> ReplyKeyboardMarkup:
    """Admin menu keyboard"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="پنل مدیریت 👨‍💼")],
            [KeyboardButton(text="امضای APK 📱")],
            [
                KeyboardButton(text="حساب کاربری 🧾"),
                KeyboardButton(text="افزایش موجودی 💰"),
            ],
            [KeyboardButton(text="پشتیبانی 🆘")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="یک گزینه را انتخاب کنید..."
    )
    return keyboard

def confirm_sign_keyboard() -> InlineKeyboardMarkup:
    """Confirmation keyboard for APK signing"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="تایید امضا ✅", callback_data="confirm_sign"),
                InlineKeyboardButton(text="لغو ❌", callback_data="cancel_sign"),
            ]
        ]
    )
    return keyboard

def back_to_main_menu() -> InlineKeyboardMarkup:
    """Back to main menu button"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="back_to_main")]
        ]
    )
    return keyboard

def admin_panel_keyboard() -> InlineKeyboardMarkup:
    """Admin panel main dashboard"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 آمار کلی", callback_data="admin_stats"),
                InlineKeyboardButton(text="👤 جستجوی کاربر", callback_data="admin_search_user"),
            ],
            [
                InlineKeyboardButton(text="💰 مدیریت موجودی", callback_data="admin_balance"),
                InlineKeyboardButton(text="🚫 مسدود/رفع مسدودی", callback_data="admin_block"),
            ],
            [
                InlineKeyboardButton(text="📢 اطلاع‌رسانی", callback_data="admin_broadcast"),
                InlineKeyboardButton(text="⚙️ تنظیمات قیمت", callback_data="admin_price"),
            ],
            [
                InlineKeyboardButton(text="💬 پیام‌های پشتیبانی", callback_data="admin_support"),
            ],
            [
                InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main"),
            ]
        ]
    )
    return keyboard

def admin_user_actions_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """User-specific admin actions"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💰 افزایش موجودی", callback_data=f"admin_credit_{user_id}"),
                InlineKeyboardButton(text="💸 کسر موجودی", callback_data=f"admin_debit_{user_id}"),
            ],
            [
                InlineKeyboardButton(text="🚫 مسدود کردن", callback_data=f"admin_block_user_{user_id}"),
                InlineKeyboardButton(text="✅ رفع مسدودی", callback_data=f"admin_unblock_user_{user_id}"),
            ],
            [
                InlineKeyboardButton(text="🔙 بازگشت به پنل", callback_data="admin_panel"),
            ]
        ]
    )
    return keyboard

def payment_method_keyboard() -> InlineKeyboardMarkup:
    """Payment method selection"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💳 TRX (TRON)", callback_data="payment_trx"),
            ],
            [
                InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main"),
            ]
        ]
    )
    return keyboard

def cancel_keyboard() -> InlineKeyboardMarkup:
    """Cancel operation keyboard"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ لغو", callback_data="cancel_operation")]
        ]
    )
    return keyboard
