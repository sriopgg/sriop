
from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramAPIError
import os
import logging
import tempfile
from pathlib import Path

import db
import sign
from keyboards import confirm_sign_keyboard, back_to_main_menu
from config import TEMP_DIR, SIGNED_DIR

router = Router()
logger = logging.getLogger(__name__)

class SignAPKStates(StatesGroup):
    waiting_for_apk = State()
    confirming_sign = State()

@router.message(lambda message: message.text == "امضای APK 📱")
async def request_apk_file(message: types.Message, state: FSMContext):
    """Request APK file from user"""
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
        
        # Get current sign price from database
        sign_price = float(db.get_setting('sign_price_trx', '3.0'))
        user_balance = db.get_user_balance(user_id)
        
        # Check user balance
        if user_balance < sign_price:
            await message.answer(
                f"❌ **موجودی ناکافی!**\n\n"
                f"💰 موجودی فعلی: {user_balance:.2f} TRX\n"
                f"💳 هزینه امضا: {sign_price:.2f} TRX\n"
                f"📉 کمبود: {sign_price - user_balance:.2f} TRX\n\n"
                "لطفا ابتدا موجودی خود را افزایش دهید.",
                reply_markup=back_to_main_menu(),
                parse_mode="Markdown"
            )
            return
        
        instructions = (
            "📱 **امضای فایل APK**\n\n"
            f"💰 هزینه امضا: **{sign_price:.2f} TRX**\n"
            f"💳 موجودی شما: **{user_balance:.2f} TRX**\n\n"
            "📋 **دستورالعمل:**\n"
            "1️⃣ فایل APK خود را ارسال کنید\n"
            "2️⃣ منتظر تأیید نهایی بمانید\n"
            "3️⃣ فایل امضا شده را دریافت کنید\n\n"
            "⚠️ **نکات مهم:**\n"
            "• حداکثر حجم فایل: 50MB\n"
            "• فقط فایل‌های APK پذیرفته می‌شوند\n"
            "• فرایند امضا چند ثانیه طول می‌کشد\n\n"
            "لطفا فایل APK خود را ارسال کنید:"
        )
        
        await message.answer(
            instructions,
            reply_markup=back_to_main_menu(),
            parse_mode="Markdown"
        )
        
        await state.set_state(SignAPKStates.waiting_for_apk)
        
    except Exception as e:
        logger.error(f"Error in request_apk_file: {e}")
        await message.answer(
            "❌ خطا در شروع فرایند امضا. لطفا مجددا تلاش کنید.",
            reply_markup=back_to_main_menu()
        )

@router.message(SignAPKStates.waiting_for_apk, F.document)
async def handle_apk_file(message: types.Message, state: FSMContext, bot: Bot):
    """Handle uploaded APK file"""
    try:
        user_id = message.from_user.id
        document = message.document
        
        # Validate file
        if not document.file_name or not document.file_name.lower().endswith('.apk'):
            await message.answer(
                "❌ لطفا فقط فایل‌های APK ارسال کنید.",
                reply_markup=back_to_main_menu()
            )
            return
        
        if document.file_size > sign.MAX_FILE_SIZE:
            await message.answer(
                f"❌ حجم فایل بیش از حد مجاز است.\n"
                f"حداکثر مجاز: {sign.MAX_FILE_SIZE // (1024*1024)}MB\n"
                f"حجم فایل شما: {document.file_size // (1024*1024)}MB",
                reply_markup=back_to_main_menu()
            )
            return
        
        # Show processing message
        processing_msg = await message.answer("⏳ در حال پردازش فایل...")
        
        # Download file
        file_info = await bot.get_file(document.file_id)
        temp_path = os.path.join(TEMP_DIR, f"{user_id}_{document.file_name}")
        
        await bot.download_file(file_info.file_path, temp_path)
        
        try:
            # Validate APK
            apk_info = sign.get_apk_info(temp_path)
            if not apk_info['valid']:
                await processing_msg.edit_text(
                    "❌ فایل APK معتبر نیست. لطفا فایل صحیح ارسال کنید.",
                    reply_markup=back_to_main_menu()
                )
                sign.cleanup_temp_files(temp_path)
                return
            
            # Store file info in state
            await state.update_data({
                'file_path': temp_path,
                'file_name': document.file_name,
                'file_id': document.file_id,
                'file_size': document.file_size,
                'apk_info': apk_info
            })
            
            # Get sign price
            sign_price = float(db.get_setting('sign_price_trx', '3.0'))
            
            confirmation_text = (
                "✅ **فایل APK دریافت شد**\n\n"
                f"📄 نام فایل: `{document.file_name}`\n"
                f"📊 حجم: {document.file_size / (1024*1024):.1f} MB\n"
                f"📦 پکیج: {apk_info['package_name']}\n"
                f"🔢 نسخه: {apk_info['version']}\n\n"
                f"💰 **هزینه امضا: {sign_price:.2f} TRX**\n\n"
                "آیا مایل به ادامه فرایند امضا هستید؟"
            )
            
            await processing_msg.edit_text(
                confirmation_text,
                reply_markup=confirm_sign_keyboard(),
                parse_mode="Markdown"
            )
            
            await state.set_state(SignAPKStates.confirming_sign)
            
        except sign.APKSigningError as e:
            await processing_msg.edit_text(
                f"❌ خطا در پردازش APK: {str(e)}",
                reply_markup=back_to_main_menu()
            )
            sign.cleanup_temp_files(temp_path)
            await state.clear()
            
    except Exception as e:
        logger.error(f"Error handling APK file: {e}")
        await message.answer(
            "❌ خطا در پردازش فایل. لطفا مجددا تلاش کنید.",
            reply_markup=back_to_main_menu()
        )
        await state.clear()

@router.message(SignAPKStates.waiting_for_apk)
async def invalid_file_type(message: types.Message):
    """Handle invalid file types"""
    await message.answer(
        "❌ لطفا فقط فایل‌های APK ارسال کنید.\n"
        "فایل باید پسوند .apk داشته باشد.",
        reply_markup=back_to_main_menu()
    )

@router.callback_query(lambda c: c.data == "confirm_sign", SignAPKStates.confirming_sign)
async def confirm_sign(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Confirm and process APK signing"""
    try:
        user_id = callback.from_user.id
        data = await state.get_data()
        
        if not data or 'file_path' not in data:
            await callback.answer("❌ اطلاعات فایل یافت نشد", show_alert=True)
            await state.clear()
            return
        
        file_path = data['file_path']
        file_name = data['file_name']
        file_id = data['file_id']
        file_size = data['file_size']
        
        # Get sign price and check balance again
        sign_price = float(db.get_setting('sign_price_trx', '3.0'))
        user_balance = db.get_user_balance(user_id)
        
        if user_balance < sign_price:
            await callback.message.edit_text(
                "❌ موجودی ناکافی! لطفا ابتدا حساب خود را شارژ کنید.",
                reply_markup=back_to_main_menu()
            )
            sign.cleanup_temp_files(file_path)
            await state.clear()
            return
        
        # Show signing progress
        await callback.message.edit_text("⏳ در حال امضای APK...")
        
        # Generate signed file path
        signed_filename = sign.generate_signed_filename(file_name)
        signed_path = os.path.join(SIGNED_DIR, f"{user_id}_{signed_filename}")
        
        try:
            # Sign the APK
            success = sign.sign_apk(file_path, signed_path)
            
            if not success:
                raise sign.APKSigningError("Signing process failed")
            
            # Upload signed file
            with open(signed_path, 'rb') as signed_file:
                signed_doc = await bot.send_document(
                    chat_id=callback.message.chat.id,
                    document=types.FSInputFile(signed_path, filename=signed_filename),
                    caption=(
                        f"✅ **امضا با موفقیت انجام شد**\n\n"
                        f"📄 فایل اصلی: `{file_name}`\n"
                        f"📄 فایل امضا شده: `{signed_filename}`\n"
                        f"💰 هزینه: {sign_price:.2f} TRX\n\n"
                        f"🎉 فایل APK شما آماده استفاده است!"
                    ),
                    parse_mode="Markdown",
                    reply_markup=back_to_main_menu()
                )
            
            # Deduct balance and record transaction
            db.update_balance(user_id, -sign_price, 'sign_fee', f'امضای {file_name}')
            
            # Record signed APK
            signed_size = os.path.getsize(signed_path)
            db.add_signed_apk(user_id, file_name, signed_doc.document.file_id, file_size, signed_size)
            
            # Success message
            await callback.message.edit_text(
                f"✅ **امضا تکمیل شد!**\n\n"
                f"💰 موجودی جدید: {user_balance - sign_price:.2f} TRX"
            )
            
            logger.info(f"APK signed successfully for user {user_id}: {file_name}")
            
        except sign.APKSigningError as e:
            await callback.message.edit_text(
                f"❌ خطا در امضای فایل: {str(e)}",
                reply_markup=back_to_main_menu()
            )
            logger.error(f"APK signing failed for user {user_id}: {e}")
            
        finally:
            # Cleanup files
            sign.cleanup_temp_files(file_path)
            if os.path.exists(signed_path):
                sign.cleanup_temp_files(signed_path)
        
        await state.clear()
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in confirm_sign: {e}")
        await callback.answer("❌ خطا در امضای فایل", show_alert=True)
        await state.clear()

@router.callback_query(lambda c: c.data == "cancel_sign")
async def cancel_sign(callback: types.CallbackQuery, state: FSMContext):
    """Cancel APK signing process"""
    try:
        data = await state.get_data()
        if data and 'file_path' in data:
            sign.cleanup_temp_files(data['file_path'])
        
        await callback.message.edit_text(
            "❌ عملیات امضا لغو شد.",
            reply_markup=back_to_main_menu()
        )
        
        await state.clear()
        await callback.answer("عملیات لغو شد")
        
    except Exception as e:
        logger.error(f"Error in cancel_sign: {e}")
        await callback.answer("خطا در لغو عملیات", show_alert=True)
