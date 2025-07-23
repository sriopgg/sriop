
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ForceReply
import logging

import trx
import db
from config import TRX_ADDRESS
from keyboards import back_to_main_menu, payment_method_keyboard, cancel_keyboard

router = Router()
logger = logging.getLogger(__name__)

class PaymentStates(StatesGroup):
    waiting_for_txid = State()

@router.message(lambda message: message.text == "افزایش موجودی 💰")
async def request_payment(message: types.Message, state: FSMContext):
    """Display payment instructions and request TX ID"""
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
        
        current_balance = db.get_user_balance(user_id)
        
        instructions = (
            "💳 **افزایش موجودی TRX**\n\n"
            f"💰 موجودی فعلی: **{current_balance:.2f} TRX**\n\n"
            "📋 **مراحل پرداخت:**\n\n"
            "1️⃣ **آدرس کیف پول:**\n"
            f"`{TRX_ADDRESS}`\n\n"
            "2️⃣ **حداقل مبلغ:** 1 TRX\n\n"
            "3️⃣ **نحوه پرداخت:**\n"
            "• مبلغ مورد نظر را به آدرس بالا ارسال کنید\n"
            "• منتظر تأیید شبکه بمانید (2-3 دقیقه)\n"
            "• شناسه تراکنش (TX ID) را در پیام بعدی ارسال کنید\n\n"
            "⚠️ **نکات مهم:**\n"
            "• فقط از شبکه TRON استفاده کنید\n"
            "• آدرس را دقیق کپی کنید\n"
            "• TX ID باید معتبر و تأیید شده باشد\n\n"
            "پس از انجام تراکنش، TX ID را ارسال کنید:"
        )
        
        await message.answer(
            instructions,
            parse_mode="Markdown",
            reply_markup=ForceReply(
                selective=True,
                input_field_placeholder="TX ID تراکنش را وارد کنید..."
            )
        )
        
        await state.set_state(PaymentStates.waiting_for_txid)
        
    except Exception as e:
        logger.error(f"Error in payment request: {e}")
        await message.answer(
            "❌ خطا در نمایش اطلاعات پرداخت.",
            reply_markup=back_to_main_menu()
        )

@router.message(PaymentStates.waiting_for_txid, F.text)
async def process_payment(message: types.Message, state: FSMContext):
    """Process payment verification"""
    try:
        user_id = message.from_user.id
        tx_id = message.text.strip()
        
        # Validate TX ID format
        if len(tx_id) != 64 or not all(c in '0123456789abcdefABCDEF' for c in tx_id):
            await message.answer(
                "❌ **فرمت TX ID اشتباه است**\n\n"
                "TX ID باید 64 کاراکتر هگزادسیمال باشد.\n"
                "مثال: `a1b2c3d4e5f6...`\n\n"
                "لطفا TX ID صحیح را ارسال کنید:",
                parse_mode="Markdown",
                reply_markup=cancel_keyboard()
            )
            return
        
        # Check if TX ID already used
        existing_tx = db.get_user_transactions(user_id, limit=50)
        for tx in existing_tx:
            if tx['trx_id'] == tx_id:
                await message.answer(
                    "❌ **این TX ID قبلاً استفاده شده است**\n\n"
                    "هر TX ID فقط یک بار قابل استفاده است.\n"
                    "لطفا TX ID جدید ارسال کنید:",
                    parse_mode="Markdown",
                    reply_markup=cancel_keyboard()
                )
                return
        
        # Show verification message
        verification_msg = await message.answer(
            "⏳ **در حال بررسی تراکنش...**\n\n"
            f"TX ID: `{tx_id[:16]}...`\n\n"
            "لطفا صبر کنید...",
            parse_mode="Markdown"
        )
        
        try:
            # Verify transaction on blockchain
            verification_result = trx.verify_payment(tx_id, TRX_ADDRESS, min_amount=1.0)
            
            if not verification_result['valid']:
                error_message = (
                    "❌ **تراکنش معتبر نیست**\n\n"
                    f"خطا: {verification_result['error']}\n"
                    f"مبلغ: {verification_result['amount']:.2f} TRX\n"
                    f"تأیید شده: {'بله' if verification_result['confirmed'] else 'خیر'}\n\n"
                    "لطفا موارد زیر را بررسی کنید:\n"
                    "• آدرس مقصد صحیح باشد\n"
                    "• تراکنش تأیید شده باشد\n"
                    "• مبلغ حداقل 1 TRX باشد\n\n"
                    "TX ID صحیح را ارسال کنید:"
                )
                
                await verification_msg.edit_text(
                    error_message,
                    parse_mode="Markdown",
                    reply_markup=cancel_keyboard()
                )
                return
            
            # Get transaction amount
            amount = verification_result['amount']
            
            # Credit user balance
            success = db.update_balance(
                user_id, 
                amount, 
                'deposit', 
                f'واریز TRX - TX: {tx_id[:8]}...'
            )
            
            if not success:
                await verification_msg.edit_text(
                    "❌ خطا در اعمال موجودی. لطفا با پشتیبانی تماس بگیرید.",
                    reply_markup=back_to_main_menu()
                )
                return
            
            # Add transaction record with full TX ID
            db.add_transaction(user_id, 'deposit', amount, tx_id, 'completed', 'TRX Deposit')
            
            new_balance = db.get_user_balance(user_id)
            
            success_message = (
                "✅ **پرداخت با موفقیت انجام شد!**\n\n"
                f"💰 مبلغ واریزی: **{amount:.2f} TRX**\n"
                f"💳 موجودی قبلی: {new_balance - amount:.2f} TRX\n"
                f"💎 موجودی جدید: **{new_balance:.2f} TRX**\n\n"
                f"🔗 TX ID: `{tx_id[:16]}...`\n\n"
                "🎉 حساب شما با موفقیت شارژ شد!"
            )
            
            await verification_msg.edit_text(
                success_message,
                parse_mode="Markdown",
                reply_markup=back_to_main_menu()
            )
            
            logger.info(f"Payment processed successfully for user {user_id}: {amount} TRX")
            
        except trx.TronAPIError as e:
            await verification_msg.edit_text(
                f"❌ **خطا در ارتباط با شبکه TRON**\n\n"
                f"جزئیات: {str(e)}\n\n"
                "لطفا چند دقیقه بعد دوباره تلاش کنید:",
                parse_mode="Markdown",
                reply_markup=cancel_keyboard()
            )
            
        except Exception as e:
            logger.error(f"Payment verification error: {e}")
            await verification_msg.edit_text(
                "❌ خطا در بررسی تراکنش. لطفا مجددا تلاش کنید یا با پشتیبانی تماس بگیرید.",
                reply_markup=back_to_main_menu()
            )
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error processing payment: {e}")
        await message.answer(
            "❌ خطا در پردازش پرداخت.",
            reply_markup=back_to_main_menu()
        )
        await state.clear()

@router.callback_query(lambda c: c.data == "cancel_operation")
async def cancel_payment(callback: types.CallbackQuery, state: FSMContext):
    """Cancel payment process"""
    try:
        await callback.message.edit_text(
            "❌ فرایند پرداخت لغو شد.",
            reply_markup=back_to_main_menu()
        )
        
        await state.clear()
        await callback.answer("عملیات لغو شد")
        
    except Exception as e:
        logger.error(f"Error canceling payment: {e}")
        await callback.answer("خطا در لغو عملیات", show_alert=True)

@router.message(PaymentStates.waiting_for_txid)
async def invalid_txid_format(message: types.Message):
    """Handle invalid TX ID format"""
    await message.answer(
        "❌ لطفا فقط TX ID تراکنش را ارسال کنید.\n"
        "TX ID باید 64 کاراکتر هگزادسیمال باشد.",
        reply_markup=cancel_keyboard()
    )
