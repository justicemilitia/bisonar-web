from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
import json
from datetime import datetime, timedelta
import psycopg2
from flask import current_app

customer_bp = Blueprint('customer', __name__, template_folder='templates')

def get_pg_connection():
    """Get PostgreSQL database connection"""
    return psycopg2.connect(**current_app.config['DATABASE_CONFIG'])

@customer_bp.route('/dashboard')
def dashboard():
    if 'customer_id' not in session:
        return redirect(url_for('auth.login'))
    
    conn = get_pg_connection()
    try:
        with conn.cursor() as cur:
            cur.execute('''
                SELECT c.id, c.name, c.email, c.plan_type, c.api_key, c.trial_ends_at,
                       tp.business_name, tp.business_type, tp.services,
                       tw.position, tw.theme, tw.primary_color
                FROM customers c
                LEFT JOIN tenant_prompts tp ON c.id = tp.customer_id
                LEFT JOIN tenant_widget_configs tw ON c.id = tw.customer_id
                WHERE c.id = %s
            ''', (session['customer_id'],))
            
            customer_data = cur.fetchone()
            if customer_data:
                columns = [desc[0] for desc in cur.description]
                customer = dict(zip(columns, customer_data))
                
                cur.execute('''
                    SELECT COUNT(*) as total_sessions, 
                           COALESCE(SUM(message_count), 0) as total_messages
                    FROM chat_sessions 
                    WHERE customer_id = %s
                ''', (session['customer_id'],))
                
                usage = cur.fetchone()
                return render_template('customer/dashboard.html', 
                                    customer=customer, 
                                    usage=usage)
            else:
                flash('Müşteri bilgileri bulunamadı.', 'error')
                return redirect(url_for('auth.login'))
            
    except Exception as e:
        flash('Dashboard yüklenirken bir hata oluştu.', 'error')
        return redirect(url_for('auth.login'))
    finally:
        conn.close()

@customer_bp.route('/conversations')
def conversations():
    if 'customer_id' not in session:
        return jsonify({'success': False, 'message': 'Oturum bulunamadı'})
    
    sample_conversations = {
        'new_conversations': [
            {
                'id': 1,
                'customer_name': 'Ahmet Yılmaz',
                'lead_score': 85,
                'last_activity': '2 dk önce',
                'last_message': 'Merhaba, fiyat bilgisi almak istiyorum.',
                'channel': 'whatsapp',
                'priority': 'urgent'
            }
        ],
        'active_conversations': [
            {
                'id': 3,
                'customer_name': 'Elif Demir',
                'lead_score': 92,
                'last_activity': '5 saat önce',
                'last_message': 'Acil teknik destek gerekiyor!',
                'channel': 'whatsapp',
                'priority': 'urgent'
            }
        ],
        'completed_conversations': [
            {
                'id': 4,
                'customer_name': 'Selin Yıldız',
                'lead_score': 35,
                'last_activity': '2 gün önce',
                'last_message': 'Teşekkürler, bilgiler için.',
                'channel': 'telegram',
                'priority': 'info'
            }
        ]
    }
    
    return render_template('customer/conversations.html', **sample_conversations)

@customer_bp.route('/ai-settings')
def ai_settings():
    if 'customer_id' not in session:
        return redirect(url_for('auth.login'))
    
    conn = get_pg_connection()
    try:
        with conn.cursor() as cur:
            cur.execute('''
                SELECT c.id, c.name, c.email,
                       tp.business_name, tp.business_type, tp.services,
                       tp.custom_prompt, tp.welcome_message, tp.contact_required,
                       tp.ai_model, tp.temperature
                FROM customers c
                LEFT JOIN tenant_prompts tp ON c.id = tp.customer_id
                WHERE c.id = %s
            ''', (session['customer_id'],))
            
            customer_data = cur.fetchone()
            if customer_data:
                columns = [desc[0] for desc in cur.description]
                customer = dict(zip(columns, customer_data))
                return render_template('customer/ai_settings.html', customer=customer)
            else:
                return render_template('customer/ai_settings.html', customer={})
    except Exception as e:
        return render_template('customer/ai_settings.html', customer={})
    finally:
        conn.close()

@customer_bp.route('/integrations')
def integrations():
    if 'customer_id' not in session:
        return redirect(url_for('auth.login'))
    
    conn = get_pg_connection()
    try:
        with conn.cursor() as cur:
            cur.execute('''
                SELECT c.id, c.name, c.webhook_secret,
                       COALESCE(ct.google_email IS NOT NULL, false) as calendar_connected
                FROM customers c
                LEFT JOIN customer_oauth_tokens ct ON c.id = ct.customer_id AND ct.provider = 'google_calendar'
                WHERE c.id = %s
            ''', (session['customer_id'],))
            
            customer_data = cur.fetchone()
            if customer_data:
                columns = [desc[0] for desc in cur.description]
                customer = dict(zip(columns, customer_data))
                
                # Telegram preferences
                cur.execute('''
                    SELECT receive_notifications, notification_types, customer_telegram_id, min_lead_score
                    FROM tenant_telegram_preferences 
                    WHERE customer_id = %s
                ''', (session['customer_id'],))
                
                telegram_data = cur.fetchone()
                if telegram_data:
                    customer['telegram_enabled'] = telegram_data[0]
                    customer['telegram_notification_types'] = telegram_data[1] or []
                    customer['telegram_chat_id'] = telegram_data[2] or ''
                    customer['min_lead_score'] = telegram_data[3] or 50
                else:
                    customer['telegram_enabled'] = False
                    customer['telegram_notification_types'] = []
                    customer['telegram_chat_id'] = ''
                    customer['min_lead_score'] = 50
                
                return render_template('customer/integrations.html', customer=customer)
            else:
                return render_template('customer/integrations.html', customer={})
    except Exception as e:
        return render_template('customer/integrations.html', customer={})
    finally:
        conn.close()

@customer_bp.route('/analytics')
def analytics():
    if 'customer_id' not in session:
        return redirect(url_for('auth.login'))
    return render_template('customer/analytics.html')

@customer_bp.route('/pricing-settings')
def pricing_settings():
    if 'customer_id' not in session:
        return redirect(url_for('auth.login'))
    return render_template('customer/pricing.html')

@customer_bp.route('/save_telegram_settings', methods=['POST'])
def save_telegram_settings():
    """Telegram ayarlarını kaydet"""
    if 'customer_id' not in session:
        return jsonify({'success': False, 'message': 'Oturum bulunamadı'})
    
    try:
        telegram_chat_id = request.form.get('telegram_chat_id')
        min_lead_score = request.form.get('min_lead_score', 50)
        notification_types = request.form.getlist('notification_types')
        telegram_enabled = request.form.get('telegram_enabled') == 'true'
        
        conn = get_pg_connection()
        with conn.cursor() as cur:
            cur.execute('SELECT id FROM tenant_telegram_preferences WHERE customer_id = %s', (session['customer_id'],))
            existing = cur.fetchone()
            
            if existing:
                cur.execute('''
                    UPDATE tenant_telegram_preferences 
                    SET receive_notifications = %s,
                        notification_types = %s,
                        customer_telegram_id = %s,
                        min_lead_score = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE customer_id = %s
                ''', (telegram_enabled, json.dumps(notification_types), 
                      telegram_chat_id, min_lead_score, session['customer_id']))
            else:
                cur.execute('''
                    INSERT INTO tenant_telegram_preferences 
                    (customer_id, receive_notifications, notification_types, customer_telegram_id, min_lead_score)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (session['customer_id'], telegram_enabled, json.dumps(notification_types), 
                      telegram_chat_id, min_lead_score))
            
            conn.commit()
        
        return jsonify({'success': True, 'message': 'Telegram ayarları kaydedildi'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Kayıt başarısız: {str(e)}'})

@customer_bp.route('/save_calendar_settings', methods=['POST'])
def save_calendar_settings():
    """Calendar ayarlarını kaydet"""
    if 'customer_id' not in session:
        return jsonify({'success': False, 'message': 'Oturum bulunamadı'})
    
    try:
        default_event_duration = request.form.get('default_event_duration', 30)
        working_hours = request.form.get('working_hours', '9-18')
        event_types = request.form.getlist('event_types')
        calendar_enabled = request.form.get('calendar_enabled') == 'true'
        
        if working_hours and '-' in working_hours:
            try:
                start_time, end_time = working_hours.split('-')
                start_time = start_time.strip() + ':00'
                end_time = end_time.strip() + ':00'
            except Exception as e:
                start_time = '09:00:00'
                end_time = '18:00:00'
        else:
            start_time = '09:00:00'
            end_time = '18:00:00'
        
        conn = get_pg_connection()
        with conn.cursor() as cur:
            cur.execute('SELECT id FROM tenant_calendar_preferences WHERE customer_id = %s', (session['customer_id'],))
            existing = cur.fetchone()
            
            if existing:
                cur.execute('''
                    UPDATE tenant_calendar_preferences 
                    SET auto_create_events = %s,
                        event_types = %s,
                        event_duration_minutes = %s,
                        working_hours_start = %s,
                        working_hours_end = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE customer_id = %s
                ''', (calendar_enabled, json.dumps(event_types), 
                      default_event_duration, start_time, end_time, session['customer_id']))
            else:
                cur.execute('''
                    INSERT INTO tenant_calendar_preferences 
                    (customer_id, auto_create_events, event_types, event_duration_minutes, 
                     working_hours_start, working_hours_end)
                    VALUES (%s, %s, %s, %s, %s, %s)
                ''', (session['customer_id'], calendar_enabled, json.dumps(event_types), 
                      default_event_duration, start_time, end_time))
            
            conn.commit()
        
        return jsonify({'success': True, 'message': 'Calendar ayarları kaydedildi'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Kayıt başarısız: {str(e)}'})

@customer_bp.route('/save_webhook_settings', methods=['POST'])
def save_webhook_settings():
    """Webhook ayarlarını kaydet"""
    if 'customer_id' not in session:
        return jsonify({'success': False, 'message': 'Oturum bulunamadı'})
    
    try:
        webhook_url = request.form.get('webhook_url')
        webhook_secret = request.form.get('webhook_secret')
        webhook_events = request.form.getlist('webhook_events')
        webhook_enabled = request.form.get('webhook_enabled') == 'true'
        
        config = {
            'webhook_url': webhook_url,
            'webhook_secret': webhook_secret,
            'webhook_events': webhook_events
        }
        
        conn = get_pg_connection()
        with conn.cursor() as cur:
            if webhook_secret:
                cur.execute('''
                    UPDATE customers SET webhook_secret = %s WHERE id = %s
                ''', (webhook_secret, session['customer_id']))
            
            cur.execute('SELECT id FROM tenant_integrations WHERE customer_id = %s AND integration_type = %s', 
                       (session['customer_id'], 'webhook'))
            existing = cur.fetchone()
            
            if existing:
                cur.execute('''
                    UPDATE tenant_integrations 
                    SET config = %s,
                        is_active = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE customer_id = %s AND integration_type = %s
                ''', (json.dumps(config), webhook_enabled, session['customer_id'], 'webhook'))
            else:
                cur.execute('''
                    INSERT INTO tenant_integrations 
                    (customer_id, integration_type, config, is_active)
                    VALUES (%s, %s, %s, %s)
                ''', (session['customer_id'], 'webhook', json.dumps(config), webhook_enabled))
            
            conn.commit()
        
        return jsonify({'success': True, 'message': 'Webhook ayarları kaydedildi'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Kayıt başarısız: {str(e)}'})