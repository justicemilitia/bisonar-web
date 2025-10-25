import os

# Database Configuration
DATABASE_CONFIG = {
    'host': 'superapp-dev-rds-postgres.cna2w8equl8b.eu-central-1.rds.amazonaws.com',
    'port': 5432,
    'dbname': 'ai-chatbot-test-db', 
    'user': 'postgres',
    'password': 'SuperApp_2025'
}

# Google OAuth Configuration
GOOGLE_OAUTH_CONFIG = {
    'client_id': os.getenv('GOOGLE_CLIENT_ID'),
    'client_secret': os.getenv('GOOGLE_CLIENT_SECRET'),
    'redirect_uri': os.getenv('GOOGLE_REDIRECT_URI', 'https://yourdomain.com/oauth/google/callback')
}

# Telegram Configuration
TELEGRAM_CONFIG = {
    'bot_token': os.getenv('TELEGRAM_BOT_TOKEN'),
    'admin_chat_id': os.getenv('TELEGRAM_ADMIN_CHAT_ID')
}

# OpenAI Configuration
OPENAI_CONFIG = {
    'api_key': os.getenv('OPENAI_API_KEY')  # SİZİN key'iniz
}

# API Security
API_CONFIG = {
    'secret_key': os.getenv('API_SECRET_KEY', 'your-secret-key-here')
}