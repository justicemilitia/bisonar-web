import requests
from saas.config import TELEGRAM_CONFIG

class TelegramService:
    @staticmethod
    def send_notification(customer_id, session_data):
        """Telegram bildirimi gönder"""
        from saas.models.customer import CustomerModel
        
        customer = CustomerModel.get_customer_by_id(customer_id)
        if not customer or not customer.get('receive_notifications'):
            return None
        
        # Sadece yüksek skorlu lead'ler için
        if session_data.get('leadScore', 0) < customer.get('min_lead_score', 50):
            return None
        
        message = TelegramService.format_message(customer, session_data)
        
        # 1. Müşteriye gönder (eğer telegram_id varsa)
        if customer.get('customer_telegram_id'):
            TelegramService.send_to_user(customer['customer_telegram_id'], message)
        
        # 2. Size gönder (merkezi monitoring)
        return TelegramService.send_to_admin(message)
    
    @staticmethod
    def format_message(customer, session):
        """Telegram mesajını formatla"""
        company = customer.get('business_name') or customer.get('name') or 'Yeni Müşteri'
        
        return f"""
🚀 **{company}** - Yeni Lead!

📞 **İletişim:**
{session.get('contactInfo', {}).get('phone') and f"Telefon: {session['contactInfo']['phone']}" or ''}
{session.get('contactInfo', {}).get('email') and f"E-posta: {session['contactInfo']['email']}" or ''}
{session.get('contactInfo', {}).get('name') and f"İsim: {session['contactInfo']['name']}" or ''}

🎯 **Lead Bilgisi:**
Skor: {session.get('leadScore', 0)}/100
Durum: {session.get('leadStatus', 'cold')}
İhtiyaçlar: {', '.join(session.get('customerNeeds', []))}

💬 **Son Mesaj:** {session.get('lastMessage', '')}

⏰ {session.get('timestamp', '')}
        """.strip()
    
    @staticmethod
    def send_to_admin(message):
        """Admin'e bildirim gönder"""
        try:
            response = requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_CONFIG['bot_token']}/sendMessage",
                json={
                    'chat_id': TELEGRAM_CONFIG['admin_chat_id'],
                    'text': message,
                    'parse_mode': 'Markdown'
                }
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Telegram error: {e}")
            return False