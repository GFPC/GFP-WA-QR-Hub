# GFP Watcher-QR

A Telegram bot that monitors and displays WhatsApp QR codes for multiple bots.

## Features

- Monitor multiple WhatsApp bots
- Real-time QR code updates
- User subscription system
- Secure API endpoints
- Redis caching for message IDs
- SQLite database with SQLAlchemy
- Alembic migrations
- Structured logging

## Tech Stack

- Python 3.8+
- FastAPI
- aiogram 3.x
- SQLAlchemy 2.0
- SQLite
- Redis (optional)
- Alembic
- Pydantic

## Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/gfp_watcher_qr.git
cd gfp_watcher_qr
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create `.env` file:
```env
BOT_TOKEN=your_telegram_bot_token
API_SECRET=your_api_secret_key
DATABASE_URL=sqlite+aiosqlite:///./gfp_watcher.db
REDIS_URL=redis://localhost:6379/0  # Optional
LOG_LEVEL=INFO
```

5. Initialize database:
```bash
alembic upgrade head
```

6. Run the application:
```bash
python main.py
```

## API Endpoints

### Health Check
- **GET** `/api/status` - Health check endpoint
- **Response:** `HealthCheck` model with status and version

### Bot Management
- **POST** `/api/bots` - Create a new bot
- **Request Body:** `BotCreate` model
- **Response:** `BotResponse` model with bot details

### QR Code Management
- **POST** `/api/qr_update` - Update QR code for a bot (requires API secret)
- **Request Body:** `WhatsAppQRUpdate` model
- **Headers:** Requires secret key authentication
- **Response:** Success status

### WhatsApp Bot Integration

#### Register WhatsApp Bot
- **POST** `/api/whatsapp/register` - Register a new WhatsApp bot
- **Request Body:** `WhatsAppBotRegisterRequest`
```json
{
    "bot": {
        "id": "your_bot_id_32_chars",
        "name": "Bot Name",
        "description": "Bot Description"
    }
}
```
- **Response:** `WhatsAppBotResponse` with success status and bot details

#### Check Bot Registration
- **POST** `/api/whatsapp/check_register` - Check if WhatsApp bot is registered
- **Request Body:** `WhatsAppBotCheckRegisterRequest`
```json
{
    "bot_id": "your_bot_id_32_chars"
}
```
- **Response:** `WhatsAppBotResponse` with registration status and bot info

#### Update QR Code
- **POST** `/api/whatsapp/update_qr` - Update QR code for WhatsApp bot
- **Request Body:** `WhatsAppBotUpdateQRRequest`
```json
{
    "bot_id": "your_bot_id_32_chars",
    "qr_data": "base64_encoded_qr_image_or_data"
}
```
- **Response:** `WhatsAppBotResponse` with update status

#### Update Authentication State
- **POST** `/api/whatsapp/update_auth_state` - Update authentication state for WhatsApp bot
- **Request Body:** `WhatsAppBotAuthedStateRequest`
```json
{
    "bot_id": "your_bot_id_32_chars",
    "state": "authed" 
}
```
- **Response:** `WhatsAppBotResponse` with authentication status

#### Send Custom Notification
- **POST** `/api/whatsapp/notify` - Send custom notification from WhatsApp bot to Telegram users
- **Request Body:** `CustomNotificationRequest`
```json
{
    "message": "Your custom message here",
    "sender_name": "WhatsApp Bot Name",
    "bot_id": "your_bot_id_32_chars"
}
```
- **Response:** `WhatsAppBotResponse` with notification status

## Data Models

### Request Models
- `BotCreate`: `{name: str, description: str}`
- `WhatsAppQRUpdate`: `{bot_id: str, qr_data: str, secret: str}`
- `WhatsAppBotRegisterRequest`: `{bot: WhatsAppBotData}`
- `WhatsAppBotCheckRegisterRequest`: `{bot_id: str}`
- `WhatsAppBotUpdateQRRequest`: `{bot_id: str, qr_data: str}`
- `WhatsAppBotAuthedStateRequest`: `{bot_id: str, state: str}`
- `CustomNotificationRequest`: `{message: str, sender_name: str, bot_id: str}`

### Response Models
- `BotResponse`: `{id: str, name: str, description: str, authed: bool, created_at: str}`
- `HealthCheck`: `{status: str, version: str}`
- `WhatsAppBotResponse`: `{success: bool, message: str, data: Optional[Dict]}`

## Authentication

Some endpoints require API secret authentication. Include the secret key in the request headers or body as specified in the endpoint documentation.

## Telegram Bot Commands

- `/start` - Start the bot
- `/help` - Show help message
- `/list_bots` - Show your linked bots
- `/list_unlinked_bots` - Show available bots to link

## WhatsApp Integration

The bot integrates with WhatsApp through multiple endpoints. When a WhatsApp bot needs to interact with the system, it should use the appropriate endpoint:

1. **Registration**: Use `/api/whatsapp/register` to register a new bot
2. **QR Updates**: Use `/api/whatsapp/update_qr` to update QR codes
3. **Authentication**: Use `/api/whatsapp/update_auth_state` to update auth status
4. **Notifications**: Use `/api/whatsapp/notify` to send custom messages

## Development

1. Run tests:
```bash
pytest
```

2. Create new migration:
```bash
alembic revision --autogenerate -m "description"
```

3. Apply migrations:
```bash
alembic upgrade head
```

## License

MIT License

#   G F P - W A - Q R - H u b 
 
 