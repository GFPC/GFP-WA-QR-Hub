from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from core.config import get_settings
from storage.user_repo import UserRepository
from storage.bot_repo import WhatsAppBotRepository
import logging
from typing import Optional

logger = logging.getLogger(__name__)
settings = get_settings()
router = Router()


def is_allowed_user(user_id: int) -> bool:
    """Check if user is allowed to use the bot."""
    return user_id in settings.ALLOWED_TG_IDS


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Handle /start command."""
    if not is_allowed_user(message.from_user.id):
        await message.answer("You are not authorized to use this bot.")
        return

    await message.answer(
        "Welcome to WhatsApp QR Manager Bot!\n\n"
        "Available commands:\n"
        "/link_bot <bot_id> - Link a WhatsApp bot\n"
        "/toggle_qr - Toggle QR notifications"
    )


@router.message(Command("link_bot"))
async def cmd_link_bot(
    message: Message,
    user_repo: UserRepository,
    bot_repo: WhatsAppBotRepository
):
    """Handle /link_bot command."""
    if not is_allowed_user(message.from_user.id):
        await message.answer("You are not authorized to use this bot.")
        return

    try:
        # Extract bot_id from command
        bot_id = message.text.split()[1]
        
        # Get or create user
        user = await user_repo.get_by_telegram_id(message.from_user.id)
        if not user:
            user = await user_repo.create(User(
                telegram_id=message.from_user.id,
                username=message.from_user.username
            ))

        # Create WhatsApp bot
        bot = await bot_repo.create(WhatsAppBot(
            id=bot_id,
            user_id=user.id
        ))

        await message.answer(f"Successfully linked WhatsApp bot with ID: {bot_id}")
    except IndexError:
        await message.answer("Please provide a bot ID: /link_bot <bot_id>")
    except Exception as e:
        logger.error(f"Error linking bot: {str(e)}")
        await message.answer("An error occurred while linking the bot.")


@router.message(Command("toggle_qr"))
async def cmd_toggle_qr(
    message: Message,
    user_repo: UserRepository,
    bot_repo: WhatsAppBotRepository
):
    """Handle /toggle_qr command."""
    if not is_allowed_user(message.from_user.id):
        await message.answer("You are not authorized to use this bot.")
        return

    try:
        user = await user_repo.get_by_telegram_id(message.from_user.id)
        if not user:
            await message.answer("Please link a bot first using /link_bot")
            return

        bots = await bot_repo.get_by_user_id(user.id)
        if not bots:
            await message.answer("No bots found. Please link a bot first using /link_bot")
            return

        # Toggle QR notifications for all user's bots
        for bot in bots:
            await bot_repo.update(bot.id, is_active=not bot.is_active)

        await message.answer("QR notifications toggled successfully")
    except Exception as e:
        logger.error(f"Error toggling QR: {str(e)}")
        await message.answer("An error occurred while toggling QR notifications.") 