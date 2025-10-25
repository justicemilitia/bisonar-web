import psycopg2
from datetime import datetime, timedelta
from saas.config import DATABASE_CONFIG

class OAuthModel:
    @staticmethod
    def save_google_tokens(customer_id, tokens, google_email):
        """SADECE token'ları PostgreSQL'e kaydet"""
        conn = psycopg2.connect(**DATABASE_CONFIG)
        try:
            with conn.cursor() as cur:
                expiry_date = datetime.now() + timedelta(seconds=tokens['expires_in'])
                
                cur.execute('''
                    INSERT INTO customer_oauth_tokens 
                    (customer_id, access_token, refresh_token, expiry_date, google_email, provider)
                    VALUES (%s, %s, %s, %s, %s, 'google_calendar')
                    ON CONFLICT (customer_id, provider) 
                    DO UPDATE SET 
                        access_token = EXCLUDED.access_token,
                        refresh_token = EXCLUDED.refresh_token, 
                        expiry_date = EXCLUDED.expiry_date,
                        google_email = EXCLUDED.google_email,
                        updated_at = CURRENT_TIMESTAMP
                ''', (customer_id, tokens['access_token'], tokens.get('refresh_token'), 
                      expiry_date, google_email))
                conn.commit()
                return True
        except Exception as e:
            print(f"Token save error: {e}")
            return False
        finally:
            conn.close()

    @staticmethod
    def get_valid_google_token(customer_id):
        """SADECE token'ı PostgreSQL'den getir"""
        conn = psycopg2.connect(**DATABASE_CONFIG)
        try:
            with conn.cursor() as cur:
                cur.execute('''
                    SELECT access_token, refresh_token, expiry_date 
                    FROM customer_oauth_tokens 
                    WHERE customer_id = %s AND provider = 'google_calendar'
                ''', (customer_id,))
                
                result = cur.fetchone()
                if result:
                    access_token, refresh_token, expiry_date = result
                    # Token expired mi kontrol et
                    if expiry_date < datetime.now():
                        # Refresh logic (n8n'de handle edilebilir)
                        return None
                    return access_token
                return None
        finally:
            conn.close()