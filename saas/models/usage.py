import psycopg2
from saas.config import DATABASE_CONFIG

class UsageModel:
    @staticmethod
    def record_openai_usage(customer_id, session_id, usage_data, model, cost):
        """OpenAI token kullanımını kaydet"""
        conn = psycopg2.connect(**DATABASE_CONFIG)
        try:
            with conn.cursor() as cur:
                cur.execute('''
                    INSERT INTO openai_usage 
                    (customer_id, session_id, prompt_tokens, completion_tokens, total_tokens, model, cost)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                ''', (customer_id, session_id, usage_data.get('prompt_tokens', 0),
                      usage_data.get('completion_tokens', 0), usage_data.get('total_tokens', 0),
                      model, cost))
                conn.commit()
        finally:
            conn.close()

    @staticmethod
    def save_chat_session(customer_id, session_data):
        """Chat session'ını kaydet"""
        conn = psycopg2.connect(**DATABASE_CONFIG)
        try:
            with conn.cursor() as cur:
                cur.execute('''
                    INSERT INTO chat_sessions 
                    (id, customer_id, session_data, lead_score, lead_status, customer_name, customer_email, customer_phone)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) 
                    DO UPDATE SET 
                        session_data = EXCLUDED.session_data,
                        lead_score = EXCLUDED.lead_score,
                        lead_status = EXCLUDED.lead_status,
                        customer_name = EXCLUDED.customer_name,
                        customer_email = EXCLUDED.customer_email,
                        customer_phone = EXCLUDED.customer_phone
                ''', (session_data['sessionId'], customer_id, session_data, 
                      session_data.get('leadScore', 0), session_data.get('leadStatus', 'cold'),
                      session_data.get('contactInfo', {}).get('name'),
                      session_data.get('contactInfo', {}).get('email'),
                      session_data.get('contactInfo', {}).get('phone')))
                conn.commit()
        finally:
            conn.close()