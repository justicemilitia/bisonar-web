import psycopg2
from datetime import datetime
from saas.config import DATABASE_CONFIG

class CustomerModel:
    @staticmethod
    def get_customer_by_id(customer_id):
        """Müşteri bilgilerini getir"""
        conn = psycopg2.connect(**DATABASE_CONFIG)
        try:
            with conn.cursor() as cur:
                cur.execute('''
                    SELECT 
                        c.*,
                        tp.business_name, tp.business_type, tp.services, tp.custom_prompt,
                        tp.ai_model, tp.temperature, tp.max_tokens,
                        tw.position, tw.theme, tw.primary_color, tw.language,
                        tt.receive_notifications, tt.customer_telegram_id, tt.min_lead_score,
                        tc.auto_create_events, tc.event_duration_minutes,
                        cot.access_token, cot.expiry_date, cot.google_email
                    FROM customers c
                    LEFT JOIN tenant_prompts tp ON c.id = tp.customer_id
                    LEFT JOIN tenant_widget_configs tw ON c.id = tw.customer_id
                    LEFT JOIN tenant_telegram_preferences tt ON c.id = tt.customer_id
                    LEFT JOIN tenant_calendar_preferences tc ON c.id = tc.customer_id
                    LEFT JOIN customer_oauth_tokens cot ON c.id = cot.customer_id 
                        AND cot.provider = 'google_calendar'
                    WHERE c.id = %s AND c.is_active = true
                ''', (customer_id,))
                
                result = cur.fetchone()
                if result:
                    columns = [desc[0] for desc in cur.description]
                    return dict(zip(columns, result))
                return None
        finally:
            conn.close()

    @staticmethod
    def validate_api_key(customer_id, api_key):
        """API key doğrulama"""
        conn = psycopg2.connect(**DATABASE_CONFIG)
        try:
            with conn.cursor() as cur:
                cur.execute('''
                    SELECT id FROM customers 
                    WHERE id = %s AND api_key = %s AND is_active = true
                ''', (customer_id, api_key))
                return cur.fetchone() is not None
        finally:
            conn.close()

    @staticmethod
    def check_usage_quota(customer_id):
        """Aylık kullanım kotasını kontrol et"""
        conn = psycopg2.connect(**DATABASE_CONFIG)
        try:
            with conn.cursor() as cur:
                # Mevcut ayın kullanımını getir
                cur.execute('''
                    SELECT SUM(message_count) as total_messages,
                           c.plan_type
                    FROM usage_stats us
                    JOIN customers c ON us.customer_id = c.id
                    WHERE us.customer_id = %s 
                    AND us.date >= date_trunc('month', CURRENT_DATE)
                    GROUP BY c.plan_type
                ''', (customer_id,))
                
                result = cur.fetchone()
                if result:
                    total_messages, plan_type = result
                    
                    # Plan limitleri
                    limits = {
                        'trial': 100,
                        'starter': 1000,
                        'pro': 5000,
                        'business': 20000
                    }
                    
                    limit = limits.get(plan_type, 100)
                    return {
                        'allowed': total_messages < limit,
                        'used': total_messages or 0,
                        'limit': limit,
                        'remaining': limit - (total_messages or 0)
                    }
                
                return {'allowed': True, 'used': 0, 'limit': 100, 'remaining': 100}
        finally:
            conn.close()

    @staticmethod
    def increment_usage(customer_id, message_count=1, session_count=0):
        """Kullanım istatistiklerini güncelle"""
        conn = psycopg2.connect(**DATABASE_CONFIG)
        try:
            with conn.cursor() as cur:
                cur.execute('''
                    INSERT INTO usage_stats (customer_id, session_count, message_count, api_calls_count)
                    VALUES (%s, %s, %s, 1)
                    ON CONFLICT (customer_id, date) 
                    DO UPDATE SET 
                        session_count = usage_stats.session_count + %s,
                        message_count = usage_stats.message_count + %s,
                        api_calls_count = usage_stats.api_calls_count + 1
                ''', (customer_id, session_count, message_count, session_count, message_count))
                conn.commit()
        finally:
            conn.close()