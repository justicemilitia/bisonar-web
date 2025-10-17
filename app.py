from flask import Flask, render_template, session, jsonify, request
import json
import requests  # Bu eksikti

app = Flask(__name__)
app.secret_key = 'bisonar-test'
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Cache'i devre dışı bırak

# Debug için translations.json'u kontrol edelim
try:
    with open('locales/translations.json', 'r', encoding='utf-8') as f:
        TRANSLATIONS = json.load(f)
    print("✅ translations.json loaded successfully")
    
    # DEBUG: Tüm services verisini kontrol edelim
    print("🔍 Full services data:", TRANSLATIONS['en']['services'])
    print("📋 Services items type:", type(TRANSLATIONS['en']['services']['items']))
    print("🔢 Services items length:", len(TRANSLATIONS['en']['services']['items']))
    
except Exception as e:
    print(f"❌ Error loading translations: {e}")
    exit(1)

def get_template_data():
    current_lang = session.get('language', 'en')
    t_data = TRANSLATIONS.get(current_lang, TRANSLATIONS['en'])
    
    # DEBUG: Template'e gönderilen veriyi kontrol edelim
    print(f"🚀 Sending to template - services.items type: {type(t_data['services']['items'])}")
    
    return {
        't': t_data,
        'current_lang': current_lang
    }

@app.route('/')
def index():
    template_data = get_template_data()
    return render_template('index.html', **template_data)

@app.route('/api/chatbot', methods=['POST'])
def chatbot_proxy():
    try:
        data = request.get_json()
        message = data.get('message', '')
        session_id = data.get('sessionId', '')
        user_id = data.get('userId', '')

        # External API'ye istek yap
        response = requests.post(
            'https://g30rnaqf.rpcld.co/webhook/019d8437-e138-4003-a77f-c59b5b8429b2',
            json={
                'message': message,
                'sessionId': session_id,
                'userId': user_id
            },
            headers={
                'Content-Type': 'application/json'
            },
            timeout=30  # 30 saniye timeout
        )

        if response.status_code == 200:
            return jsonify(response.json()), 200
        else:
            return jsonify({
                'response': 'Üzgünüm, şu anda teknik bir sorun yaşıyorum. Lütfen daha sonra tekrar deneyin.',
                'quickReplies': ['n8n Otomasyonu', 'AI İş Akışları', 'Danışmanlık', 'Fiyat Bilgisi']
            }), 200

    except requests.exceptions.Timeout:
        return jsonify({
            'response': 'İstek zaman aşımına uğradı. Lütfen tekrar deneyin.',
            'quickReplies': ['n8n Otomasyonu', 'AI İş Akışları', 'Danışmanlık', 'Fiyat Bilgisi']
        }), 200
    except Exception as e:
        print(f"Chatbot error: {str(e)}")
        return jsonify({
            'response': 'Teknik bir hata oluştu. Lütfen daha sonra tekrar deneyin.',
            'quickReplies': ['n8n Otomasyonu', 'AI İş Akışları', 'Danışmanlık', 'Fiyat Bilgisi']
        }), 200

@app.route('/set-language/<lang>')
def set_language(lang):
    if lang in ['en', 'tr']:
        session['language'] = lang
    return jsonify({'success': True, 'language': lang})

if __name__ == '__main__':
    # Template cache'i temizle
    import jinja2
    jinja2.clear_caches()
    
    app.run(debug=True, port=8000)