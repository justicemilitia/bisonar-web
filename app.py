from flask import Flask, render_template, session,jsonify
import json

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