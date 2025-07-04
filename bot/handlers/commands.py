from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from db.repository import BotRepository, UserRepository
from core.logger import logger

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, db: AsyncSession):
    """Handle /start command"""
    # user_repo = UserRepository(db) # Не нужно, пользователь уже проверен мидлварью
    # await user_repo.get_or_create_user(message.from_user.id) # Удаляем автоматическую регистрацию
    
    await message.answer(
        "👋 Welcome to GFP Watcher-QR!\n\n"
        "I'll help you monitor WhatsApp QR codes for your bots.\n"
        "Use /help to see available commands."
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Handle /help command"""
    help_text = (
        "📚 Available commands:\n\n"
        "/list_bots - Show your linked bots\n"
        "/list_unlinked_bots - Show available bots to link\n"
        "/help - Show this help message\n"
        "/invite <user_id> - Add a user to the bot (Admin only)"
    )
    await message.answer(help_text)


@router.message(Command("list_bots"))
async def cmd_list_bots(message: Message, db: AsyncSession):
    """Handle /list_bots command"""
    user_repo = UserRepository(db)
    bots = await user_repo.get_user_bots(message.from_user.id)
    
    if not bots:
        await message.answer("You don't have any linked bots yet.")
        return
    
    # Send header with instructions
    header_text = (
        "📱 <b>Your Linked WhatsApp Bots</b>\n\n"
        "Here are all your connected bots. You can:\n"
        "• <b>Auth QR</b> - Get QR code for authentication\n"
        "• <b>Unlink</b> - Remove bot from your account\n\n"
        "Status indicators:\n"
        "✅ Authenticated - Bot is ready to use\n"
        "❌ Not authenticated - Needs QR code scan\n"
    )
    await message.answer(header_text, parse_mode="HTML")
    
    # Send each bot in a separate message
    for bot in bots:
        # Create message text with formatting
        status_emoji = "✅" if bot.authed else "❌"
        status_text = "Authenticated" if bot.authed else "Not authenticated"
        
        text = (
            f"🤖 <b>{bot.name}</b>\n\n"
            f"<code>ID: {bot.id}</code>\n"
            f"📝 <i>{bot.description}</i>\n\n"
            f"{status_emoji} <b>Status:</b> {status_text}"
        )
        
        # Create inline keyboard with buttons
        kb = InlineKeyboardBuilder()
        
        if not bot.authed:
            kb.button(
                text="🔐 Auth QR",
                callback_data=f"auth_qr:{bot.id}"
            )
        
        kb.button(
            text="🔗 Unlink",
            callback_data=f"unlink:{bot.id}"
        )
        
        # Send message with formatted text and buttons
        await message.answer(
            text,
            reply_markup=kb.as_markup(),
            parse_mode="HTML"
        )


@router.message(Command("list_unlinked_bots"))
async def cmd_list_unlinked_bots(message: Message, db: AsyncSession):
    """Handle /list_unlinked_bots command"""
    bot_repo = BotRepository(db)
    bots = await bot_repo.get_unlinked_bots(message.from_user.id)
    
    if not bots:
        await message.answer("No unlinked bots available.")
        return

    # Send each bot in a separate message
    for bot in bots:
        status_emoji = "✅" if bot.authed else "❌"
        status_text = "Authenticated" if bot.authed else "Not authenticated"
        # Create message text with formatting
        text = (
            f"🤖 <b>{bot.name}</b>\n\n"
            f"ID: <code> {bot.id}</code>\n"
            f"📝 <i>{bot.description}</i>\n"
            f"{status_emoji} <b>Status:</b> {status_text}"
        )
        
        # Create inline keyboard with link button
        kb = InlineKeyboardBuilder()
        kb.button(
            text=f"Link {bot.id[:6]}... ✅",
            callback_data=f"link:{bot.id}"
        )
        
        # Send message with formatted text and button
        await message.answer(
            text,
            reply_markup=kb.as_markup(),
            parse_mode="HTML"
        )


@router.message(Command("invite"))
async def cmd_invite(message: Message, db: AsyncSession):
    """Handle /invite command to add a user by tg_id"""
    user_repo = UserRepository(db)

    # Проверяем, является ли отправитель команды администратором
    if not await user_repo.is_admin(message.from_user.id):
        await message.answer("❌ You are not authorized to use this command.")
        logger.warning(f"User {message.from_user.id} tried to use /invite without admin rights.")
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].isdigit():
        await message.answer("Usage: /invite <telegram_user_id>")
        return

    invited_tg_id = int(args[1])

    try:
        invited_user = await user_repo.get_or_create_user(invited_tg_id)
        invited_user.data["is_admin"] = True
        await user_repo.update_user_data(invited_tg_id, invited_user.data)
        await message.answer(f"✅ User {invited_tg_id} has been successfully added to the bot.")
        
        # Уведомляем приглашенного пользователя
        try:
            await message.bot.send_message(
                chat_id=invited_tg_id,
                text="👋 You have been invited to GFP Watcher-QR! Use /start to begin."
            )
            logger.info(f"Sent invitation message to user {invited_tg_id}.")
        except Exception as e:
            logger.warning(f"Failed to send invitation message to user {invited_tg_id}: {e}")
            await message.answer(f"⚠️ Could not send invitation message to user {invited_tg_id}. They might have blocked the bot or not started it yet.")

    except Exception as e:
        logger.error(f"Error inviting user {invited_tg_id}: {e}")
        await message.answer(f"❌ An error occurred while inviting user {invited_tg_id}.") 