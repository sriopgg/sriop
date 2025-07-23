import logging
from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import ADMINS
import db
from keyboards import back_to_main_menu, admin_panel_keyboard

router = Router()
logger = logging.getLogger(__name__)

class AdminStates(StatesGroup):
    waiting_user_id = State()
    waiting_amount = State()
    waiting_balance_adjustment = State()
    waiting_broadcast = State()
    waiting_new_price = State()
    waiting_block_user = State()

async def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    return user_id in ADMINS

@router.message(Command("admin"))
async def admin_panel_command(message: types.Message):
    """Show admin panel for admin users"""
    if not await is_admin(message.from_user.id):
        await message.answer("❌ دسترسی محدود!")
        return

    await message.answer(
        "👨‍💻 پنل مدیریت ربات\n\nیک گزینه را انتخاب کنید:",
        reply_markup=admin_panel_keyboard()
    )

@router.message(lambda message: message.text == "پنل مدیریت 👨‍💼")
async def admin_panel_text(message: types.Message):
    """Handle admin panel text button"""
    if not await is_admin(message.from_user.id):
        await message.answer("❌ دسترسی محدود!")
        return

    await message.answer(
        "👨‍💻 پنل مدیریت ربات\n\nیک گزینه را انتخاب کنید:",
        reply_markup=admin_panel_keyboard()
    )

@router.callback_query(F.data == "admin_panel")
async def admin_panel_callback(callback: types.CallbackQuery):
    """Show admin panel"""
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ دسترسی محدود!", show_alert=True)
        return

    await callback.message.edit_text(
        "👨‍💻 پنل مدیریت ربات\n\nیک گزینه را انتخاب کنید:",
        reply_markup=admin_panel_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: types.CallbackQuery):
    """Show bot statistics"""
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ دسترسی محدود!", show_alert=True)
        return

    try:
        total_users = db.get_total_users()
        total_balance = db.get_total_balance()

        stats_text = (
            f"📊 **آمار کلی ربات:**\n\n"
            f"👥 تعداد کاربران: **{total_users}**\n"
            f"💰 مجموع موجودی کل: **{total_balance:.2f} TRX**"
        )

        await callback.message.edit_text(
            stats_text,
            reply_markup=admin_panel_keyboard(),
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        await callback.answer("❌ خطا در دریافت آمار", show_alert=True)

    await callback.answer()

@router.callback_query(F.data == "admin_search_user")
async def admin_search_user(callback: types.CallbackQuery, state: FSMContext):
    """Prompt for user ID to search"""
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ دسترسی محدود!", show_alert=True)
        return

    await callback.message.edit_text(
        "👤 **جستجوی کاربر**\n\nلطفا آیدی عددی کاربر را ارسال کنید:",
        reply_markup=back_to_main_menu(),
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.waiting_user_id)
    await callback.answer()

@router.callback_query(F.data == "admin_balance")
async def admin_balance_menu(callback: types.CallbackQuery, state: FSMContext):
    """Show balance adjustment menu"""
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ دسترسی محدود!", show_alert=True)
        return

    await callback.message.edit_text(
        "💰 **مدیریت موجودی**\n\n"
        "لطفا آیدی کاربر و مقدار تغییر موجودی را به صورت زیر ارسال کنید:\n\n"
        "`آیدی_کاربر مقدار`\n\n"
        "مثال: `123456789 10.5` (اضافه کردن)\n"
        "مثال: `123456789 -5.0` (کم کردن)",
        reply_markup=back_to_main_menu(),
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.waiting_balance_adjustment)
    await callback.answer()

@router.message(AdminStates.waiting_user_id)
async def handle_user_search(message: types.Message, state: FSMContext):
    """Handle user ID search"""
    try:
        user_id = int(message.text.strip())
        user = db.get_user(user_id)

        if not user:
            await message.answer(
                "❌ کاربر یافت نشد!",
                reply_markup=admin_panel_keyboard()
            )
            await state.clear()
            return

        # Get user transactions
        transactions = db.get_user_transactions(user_id, limit=5)

        user_info = (
            f"👤 **اطلاعات کاربر:**\n\n"
            f"🆔 آیدی: `{user['user_id']}`\n"
            f"👤 نام کاربری: @{user['username'] or 'تنظیم نشده'}\n"
            f"👤 نام: {user['first_name'] or ''} {user['last_name'] or ''}\n"
            f"💰 موجودی: **{user['balance']:.2f} TRX**\n"
            f"📅 تاریخ عضویت: {user['join_date'] or 'نامشخص'}\n"
            f"🚫 وضعیت: {'مسدود' if user['is_blocked'] else 'فعال'}\n\n"
        )

        if transactions:
            user_info += "📊 **آخرین تراکنش‌ها:**\n"
            for tx in transactions[:3]:
                amount_str = f"+{tx['amount']:.2f}" if tx['amount'] > 0 else f"{tx['amount']:.2f}"
                user_info += f"• {amount_str} TRX - {tx['tx_type']}\n"
        else:
            user_info += "📝 هیچ تراکنشی یافت نشد.\n"

        # Show user actions keyboard
        from keyboards import admin_user_actions_keyboard

        await message.answer(
            user_info,
            reply_markup=admin_user_actions_keyboard(user_id),
            parse_mode="Markdown"
        )

        await state.clear()

    except ValueError:
        await message.answer(
            "❌ فرمت آیدی نامعتبر! لطفا عدد وارد کنید.",
            reply_markup=admin_panel_keyboard()
        )
        await state.clear()
    except Exception as e:
        logger.error(f"Error searching user: {e}")
        await message.answer(
            "❌ خطا در جستجوی کاربر.",
            reply_markup=admin_panel_keyboard()
        )
        await state.clear()

@router.message(AdminStates.waiting_balance_adjustment)
async def handle_balance_adjustment(message: types.Message, state: FSMContext):
    """Handle balance adjustment"""
    try:
        parts = message.text.strip().split()
        if len(parts) != 2:
            await message.answer(
                "❌ فرمت ورودی نامعتبر!\n\n"
                "لطفا به فرمت صحیح ارسال کنید:\n"
                "`آیدی_کاربر مقدار`",
                reply_markup=admin_panel_keyboard(),
                parse_mode="Markdown"
            )
            await state.clear()
            return

        user_id = int(parts[0])
        amount = float(parts[1])

        # Check if user exists
        user = db.get_user(user_id)
        if not user:
            await message.answer(
                f"❌ کاربر با آیدی {user_id} یافت نشد!",
                reply_markup=admin_panel_keyboard()
            )
            await state.clear()
            return

        # Update balance
        old_balance = user['balance']
        tx_type = "admin_credit" if amount > 0 else "admin_debit"
        description = f"Admin adjustment: {amount:+.2f} TRX"

        success = db.update_balance(user_id, amount, tx_type, description)

        if success:
            new_balance = old_balance + amount

            await message.answer(
                f"✅ **موجودی به‌روزرسانی شد**\n\n"
                f"👤 کاربر: {user_id}\n"
                f"💰 موجودی قبلی: {old_balance:.2f} TRX\n"
                f"💱 تغییر: {amount:+.2f} TRX\n"
                f"💰 موجودی جدید: {new_balance:.2f} TRX",
                reply_markup=admin_panel_keyboard(),
                parse_mode="Markdown"
            )

            # Log admin action
            logger.info(f"Admin {message.from_user.id} adjusted balance for user {user_id}: {amount:+.2f} TRX")

        else:
            await message.answer(
                "❌ خطا در به‌روزرسانی موجودی!",
                reply_markup=admin_panel_keyboard()
            )

        await state.clear()

    except (ValueError, IndexError):
        await message.answer(
            "❌ فرمت ورودی نامعتبر!\n\n"
            "لطفا عدد معتبر وارد کنید.\n"
            "مثال: `123456789 10.5`",
            reply_markup=admin_panel_keyboard(),
            parse_mode="Markdown"
        )
        await state.clear()
    except Exception as e:
        logger.error(f"Error adjusting balance: {e}")
        await message.answer(
            "❌ خطا در تنظیم موجودی.",
            reply_markup=admin_panel_keyboard()
        )
        await state.clear()

@router.callback_query(F.data.startswith("admin_credit_"))
async def admin_credit_user(callback: types.CallbackQuery, state: FSMContext):
    """Credit user balance"""
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ دسترسی محدود!", show_alert=True)
        return

    user_id = int(callback.data.split("_")[-1])
    await state.update_data(target_user_id=user_id, operation="credit")

    await callback.message.edit_text(
        f"💰 **افزایش موجودی کاربر {user_id}**\n\n"
        "لطفا مقدار TRX برای افزایش موجودی ارسال کنید:",
        reply_markup=back_to_main_menu(),
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.waiting_amount)
    await callback.answer()

@router.callback_query(F.data.startswith("admin_debit_"))
async def admin_debit_user(callback: types.CallbackQuery, state: FSMContext):
    """Debit user balance"""
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ دسترسی محدود!", show_alert=True)
        return

    user_id = int(callback.data.split("_")[-1])
    await state.update_data(target_user_id=user_id, operation="debit")

    await callback.message.edit_text(
        f"💸 **کسر موجودی کاربر {user_id}**\n\n"
        "لطفا مقدار TRX برای کسر از موجودی ارسال کنید:",
        reply_markup=back_to_main_menu(),
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.waiting_amount)
    await callback.answer()

@router.message(AdminStates.waiting_amount)
async def handle_amount_adjustment(message: types.Message, state: FSMContext):
    """Handle amount for balance adjustment"""
    try:
        data = await state.get_data()
        target_user_id = data.get('target_user_id')
        operation = data.get('operation')

        if not target_user_id or not operation:
            await message.answer(
                "❌ خطا در دریافت اطلاعات عملیات.",
                reply_markup=admin_panel_keyboard()
            )
            await state.clear()
            return

        amount = float(message.text.strip())
        if amount <= 0:
            await message.answer(
                "❌ مقدار باید بزرگتر از صفر باشد!",
                reply_markup=admin_panel_keyboard()
            )
            await state.clear()
            return

        # Apply operation
        if operation == "debit":
            amount = -amount

        # Check if user exists
        user = db.get_user(target_user_id)
        if not user:
            await message.answer(
                f"❌ کاربر با آیدی {target_user_id} یافت نشد!",
                reply_markup=admin_panel_keyboard()
            )
            await state.clear()
            return

        old_balance = user['balance']
        tx_type = f"admin_{operation}"
        description = f"Admin {operation}: {abs(amount):.2f} TRX"

        success = db.update_balance(target_user_id, amount, tx_type, description)

        if success:
            new_balance = old_balance + amount
            operation_text = "افزایش" if amount > 0 else "کسر"

            await message.answer(
                f"✅ **موجودی {operation_text} یافت**\n\n"
                f"👤 کاربر: {target_user_id}\n"
                f"💰 موجودی قبلی: {old_balance:.2f} TRX\n"
                f"💱 {operation_text}: {abs(amount):.2f} TRX\n"
                f"💰 موجودی جدید: {new_balance:.2f} TRX",
                reply_markup=admin_panel_keyboard(),
                parse_mode="Markdown"
            )

            logger.info(f"Admin {message.from_user.id} {operation} {abs(amount):.2f} TRX for user {target_user_id}")
        else:
            await message.answer(
                "❌ خطا در به‌روزرسانی موجودی!",
                reply_markup=admin_panel_keyboard()
            )

        await state.clear()

    except ValueError:
        await message.answer(
            "❌ مقدار نامعتبر! لطفا عدد معتبر وارد کنید.",
            reply_markup=admin_panel_keyboard()
        )
        await state.clear()
    except Exception as e:
        logger.error(f"Error in amount adjustment: {e}")
        await message.answer(
            "❌ خطا در تنظیم موجودی.",
            reply_markup=admin_panel_keyboard()
        )
        await state.clear()