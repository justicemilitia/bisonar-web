import os

# Database Configuration
DATABASE_CONFIG = {
    'host': 'db-bisonar-do-user-4230972-0.d.db.ondigitalocean.com',
    'port': 25060,
    'dbname': 'ai-chatbot-test-db', 
    'user': 'doadmin',
    'password': 'AVNS_vd8YhqgeY5UjRAIp71P',
    'sslmode':'require'
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