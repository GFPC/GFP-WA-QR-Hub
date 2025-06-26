from aiogram import Router, F
from aiogram.types import CallbackQuery, FSInputFile
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import base64
from io import BytesIO
import tempfile
import os
import qrcode
from PIL import Image

from db.repository import BotRepository, UserRepository
from core.logger import logger

router = Router()


@router.callback_query(F.data.startswith("link:"))
async def handle_link_bot(callback: CallbackQuery, db: AsyncSession):
    """Handle bot linking callback"""
    bot_id = callback.data.split(":")[1]
    bot_repo = BotRepository(db)
    
    success = await bot_repo.link_bot_to_user(callback.from_user.id, bot_id)
    
    if success:
        await callback.answer("✅ Bot linked successfully!")
        await callback.message.edit_text(
            f"✅ Bot {bot_id[:6]}... has been linked to your account."
        )
    else:
        await callback.answer("❌ Failed to link bot", show_alert=True)
        logger.error(f"Failed to link bot {bot_id} to user {callback.from_user.id}")


@router.callback_query(F.data.startswith("auth_qr:"))
async def handle_auth_qr(callback: CallbackQuery, db: AsyncSession):
    """Handle auth QR request callback"""
    bot_id = callback.data.split(":")[1]
    bot_repo = BotRepository(db)
    user_repo = UserRepository(db)
    
    bot = await bot_repo.get_bot(bot_id)
    if not bot:
        await callback.answer("❌ Bot not found", show_alert=True)
        return
    
    if not bot.current_qr:
        await callback.answer("❌ No QR code available", show_alert=True)
        return
    
    try:
        # Используем данные QR напрямую из БД, без перекодирований
        qr_data_string = bot.current_qr
        print(f"DEBUG: QR data string being used for generation: {qr_data_string}")

        last_message = await user_repo.get_qr_message(callback.from_user.id, bot_id)
        #ЗДЕСЬ Я ХОЧУ УДАЛИТЬ СООБЩЕНИЕ ПО ЕГО ID 
        if last_message:
            try:
                print("Deleting message: ", last_message, "in chat: ", callback.from_user.id)
                await callback.message.bot.delete_message(chat_id=callback.from_user.id, message_id=last_message)
            except Exception as e:
                logger.warning(f"Не удалось удалить предыдущее сообщение с QR: {e}")

        
        # Создаем QR код из данных (строки)
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data_string) # <-- Здесь передаем чистую строку из БД
        qr.make(fit=True)
        
        # Создаем изображение QR кода
        qr_image = qr.make_image(fill_color="black", back_color="white")
        
        # Сохраняем во временный файл
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
            qr_image.save(temp_file.name)
            temp_file_path = temp_file.name
        
        try:
            # Создаем FSInputFile из временного файла
            qr_file = FSInputFile(temp_file_path)
            
            # Отправляем QR код
            message = await callback.message.answer_photo(
                photo=qr_file,
                caption=f"🔐 QR Code for {bot.name}\n\nScan this QR code with WhatsApp to authenticate your bot."
            )
            print(message.json())
            # Сохраняем ID сообщения в БД
            await user_repo.set_qr_message(callback.from_user.id, bot_id, message.message_id)
            await callback.answer("✅ QR code sent!")
            
        finally:
            # Удаляем временный файл
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                logger.error(f"Error deleting temporary file: {e}")
        
    except Exception as e:
        logger.error(f"Error sending QR code: {e}")
        await callback.answer("❌ Error sending QR code", show_alert=True)


@router.callback_query(F.data.startswith("unlink:"))
async def handle_unlink_bot(callback: CallbackQuery, db: AsyncSession):
    """Handle bot unlinking callback"""
    bot_id = callback.data.split(":")[1]
    bot_repo = BotRepository(db)
    
    # Remove association between user and bot
    result = await db.execute(
        text("DELETE FROM users_bots_mul WHERE user_id = :user_id AND bot_id = :bot_id"),
        {"user_id": callback.from_user.id, "bot_id": bot_id},
    )
    await db.commit()
    
    if result.rowcount > 0:
        await callback.answer("✅ Bot unlinked successfully!")
        await callback.message.edit_text(
            f"✅ Bot {bot_id[:6]}... has been unlinked from your account."
        )
        logger.info(f"Bot {bot_id} unlinked from user {callback.from_user.id}")
    else:
        await callback.answer("❌ Failed to unlink bot", show_alert=True)
        logger.error(f"Failed to unlink bot {bot_id} to user {callback.from_user.id}") 