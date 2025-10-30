import json
import psycopg2
from datetime import datetime

# JSON dosyasını oku
with open('tum_sablonlar_otomatik_verileri.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# PostgreSQL bağlantısı
conn = psycopg2.connect(
    dbname="ai-chatbot-test-db",
    user="doadmin",
    password="AVNS_vd8YhqgeY5UjRAIp71P",
    host="db-bisonar-do-user-4230972-0.d.db.ondigitalocean.com",
    port="25060"
)


cursor = conn.cursor()

# Dil ID'sini al (Türkçe için)
LANGUAGE_ID = 1  # Türkçe dil ID'si

try:
    # Her template için verileri insert et
    for template_key, template_data in data.items():
        print(f"Processing: {template_key}")
        
        # 1. Ana template tablosuna insert
        cursor.execute("""
            INSERT INTO templates (template_key, is_active, created_at, updated_at)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (template_key) DO UPDATE SET
            updated_at = %s
            RETURNING id
        """, (template_key, True, datetime.now(), datetime.now(), datetime.now()))
        
        template_id = cursor.fetchone()[0]
        
        # 2. Template çevirilerini insert et
        cursor.execute("""
            INSERT INTO template_translations (template_id, language_id, template_name, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (template_id, language_id) DO UPDATE SET
            template_name = %s, updated_at = %s
        """, (
            template_id, LANGUAGE_ID, 
            template_data.get('sablon_adi', template_key),
            datetime.now(), datetime.now(),
            template_data.get('sablon_adi', template_key),
            datetime.now()
        ))
        
        # 3. Kişilik özelliklerini insert et
        personality = template_data.get('kisilik', {})
        cursor.execute("""
            INSERT INTO personality_translations 
            (template_id, language_id, role_and_personality, tone_of_voice, 
             response_length, response_language, delay_seconds, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (template_id, language_id) DO UPDATE SET
            role_and_personality = %s, tone_of_voice = %s, response_length = %s,
            response_language = %s, delay_seconds = %s, updated_at = %s
        """, (
            template_id, LANGUAGE_ID,
            personality.get('rol_ve_kisilik', ''),
            personality.get('ses_tonu', ''),
            personality.get('cevaplarin_uzunlugu', ''),
            personality.get('cevap_dili', ''),
            personality.get('gecikme_suresi_saniye', 3),
            datetime.now(), datetime.now(),
            personality.get('rol_ve_kisilik', ''),
            personality.get('ses_tonu', ''),
            personality.get('cevaplarin_uzunlugu', ''),
            personality.get('cevap_dili', ''),
            personality.get('gecikme_suresi_saniye', 3),
            datetime.now()
        ))
        
        # 4. Aksiyonları insert et
        actions = template_data.get('aksiyonlar', [])
        for index, action in enumerate(actions):
            cursor.execute("""
                INSERT INTO action_translations 
                (template_id, language_id, trigger_condition, action_text, action_order, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                template_id, LANGUAGE_ID,
                action.get('zaman', ''),
                action.get('yap', ''),
                index,
                datetime.now(), datetime.now()
            ))
        
        # 5. Kılavuzları insert et
        guides = personality.get('kilavuzlar', [])
        for index, guide in enumerate(guides):
            cursor.execute("""
                INSERT INTO guideline_translations 
                (template_id, language_id, guideline_text, guideline_order, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                template_id, LANGUAGE_ID,
                guide,
                index,
                datetime.now(), datetime.now()
            ))
        
        print(f"✓ Completed: {template_key}")
    
    # Değişiklikleri kaydet
    conn.commit()
    print("✓ All data inserted successfully!")
    
except Exception as e:
    print(f"✗ Error: {e}")
    conn.rollback()
finally:
    cursor.close()
    conn.close()