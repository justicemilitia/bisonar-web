from flask import Flask, render_template, session, jsonify, request, redirect, url_for, flash, Response, send_from_directory, g
import json
import requests
import sqlite3
import os
from datetime import datetime,timedelta
from markdown import markdown
from functools import wraps
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
import psycopg2
from psycopg2 import sql
from saas import saas_bp

app = Flask(__name__)
app.secret_key = 'bisonar-test'
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

app.register_blueprint(saas_bp)

# Database configuration
app.config['DATABASE'] = 'blog.db'

# Admin configuration
app.config['ADMIN_USERNAME'] = 'admin'
app.config['ADMIN_PASSWORD'] = 'bisonar2024'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

DATABASE_CONFIG = {
    'host': 'superapp-dev-rds-postgres.cna2w8equl8b.eu-central-1.rds.amazonaws.com',
    'port': 5432,
    'dbname': 'ai-chatbot-test-db', 
    'user': 'postgres',
    'password': 'SuperApp_2025'
}

# Upload klasörünü oluştur
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def generate_csrf_token():
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_hex(16)
    return session['csrf_token']

# Template context'e ekleyin
@app.context_processor
def inject_csrf_token():
    return dict(csrf_token=generate_csrf_token)

# CSRF token doğrulama fonksiyonu
def validate_csrf_token(token):
    return token == session.get('csrf_token')

@app.before_request
def set_global_template_vars():
    """Tüm template'ler için global değişkenleri ayarla"""
    # Base URL'yi belirle
    if request.host == '127.0.0.1:8000' or request.host.startswith('localhost'):
        base_url = f'http://{request.host}'
    else:
        base_url = 'https://www.bisonar.com'
    
    # Mevcut URL - HASH'LERİ TAMAMEN KALDIR
    current_path = request.path
    # Hash içeren tüm path'ler için sadece base path'i kullan
    if '#' in current_path:
        current_path = current_path.split('#')[0]
    
    # Ana sayfa için özel kontrol
    if current_path == '/' or current_path == '':
        canonical_path = ''
    else:
        canonical_path = current_path
    
    g.current_url = f"{base_url}{current_path}"
    g.canonical_url = f"{base_url}{canonical_path}"  # Hash'siz canonical
    g.base_url = base_url
    
    # Varsayılan meta bilgileri
    g.meta_title = 'Bisonar - AI Automation Solutions'
    g.meta_description = 'Professional AI automation services with n8n workflows and ChatGPT integration'
    g.og_type = 'website'
    g.og_image = f"{base_url}/static/images/og-default.jpg"

@app.after_request
def set_security_headers(response):
    # TÜM header'ları her zaman ekle (localhost dahil)
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self' https:; script-src 'self' 'unsafe-inline' https:; style-src 'self' 'unsafe-inline' https: fonts.googleapis.com; font-src 'self' https: fonts.gstatic.com; img-src 'self' data: https:; connect-src 'self' https:; frame-src 'self' https:;"
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    return response

@app.context_processor
def utility_processor():
    def get_canonical_url():
        """Mevcut sayfa için canonical URL - HASH'SİZ"""
        current_path = request.path
        
        # Hash içeren tüm URL'ler için ana sayfayı canonical yap
        if '#' in current_path:
            current_path = ''
        
        if request.host == '127.0.0.1:8000' or request.host.startswith('localhost'):
            base_url = f'http://{request.host}'
        else:
            base_url = 'https://www.bisonar.com'
        
        # Ana sayfa için sadece base URL
        if current_path == '/' or current_path == '':
            return base_url
        
        return f"{base_url}{current_path}"
    
    def generate_hreflang():
        base_url = 'https://www.bisonar.com' if not request.host.startswith(('127.0.0.1', 'localhost')) else f'http://{request.host}'
        
        current_path = request.path
        # Hash içeren tüm URL'ler için ana sayfayı kullan
        if '#' in current_path:
            current_path = ''
        
        hreflangs = {
            'x-default': f"{base_url}{current_path}",
            'en': f"{base_url}{current_path}",
            'tr': f"{base_url}{current_path}"
        }
        
        return hreflangs
    
    def get_image_dimensions(image_url):
        """Resim boyutlarını belirle"""
        if 'unsplash' in image_url:
            return {'width': 800, 'height': 400}
        elif 'static/uploads' in image_url:
            return {'width': 400, 'height': 225}
        else:
            return {'width': 400, 'height': 225}
    
    return dict(
        get_canonical_url=get_canonical_url,
        generate_hreflang=generate_hreflang,
        get_image_dimensions=get_image_dimensions,
        meta_title=g.get('meta_title', 'Bisonar - AI Automation Solutions'),
        meta_description=g.get('meta_description', 'Professional AI automation services'),
        canonical_url=g.get('canonical_url'),
        current_url=g.get('current_url'),
        og_type=g.get('og_type', 'website'),
        og_image=g.get('og_image')
    )

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_admin_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated_function

def check_admin_auth(username, password):
    return username == app.config['ADMIN_USERNAME'] and password == app.config['ADMIN_PASSWORD']

def authenticate():
    return Response(
        'Please login with admin credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'}
    )

# Debug için translations.json'u kontrol edelim
try:
    with open('locales/translations.json', 'r', encoding='utf-8') as f:
        TRANSLATIONS = json.load(f)
    print("✅ translations.json loaded successfully")
except Exception as e:
    print(f"❌ Error loading translations: {e}")
    exit(1)

def init_db():
    """Initialize the database"""
    with sqlite3.connect(app.config['DATABASE']) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                slug TEXT UNIQUE NOT NULL,
                content TEXT NOT NULL,
                excerpt TEXT,
                author TEXT NOT NULL,
                read_time TEXT NOT NULL,
                image_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_published BOOLEAN DEFAULT 1
            )
        ''')
        conn.commit()

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

def get_template_data():
    # URL'den dili al (örnek: /en/blog, /tr/blog)
    path_parts = request.path.split('/')
    if len(path_parts) > 1 and path_parts[1] in ['en', 'tr']:
        lang = path_parts[1]
    else:
        # URL'de dil yoksa session'dan al veya varsayılan 'en' kullan
        lang = session.get('language', 'en')
    
    print(f"🔍 Dil seçimi - URL: {path_parts}, Seçilen: {lang}")
    
    # Dil verisini al
    t_data = TRANSLATIONS.get(lang, TRANSLATIONS['en'])
    
    # DEBUG: Hangi dil verilerinin yüklendiğini kontrol et
    if 'hero' in t_data:
        hero_data = t_data['hero']
        print(f"🎯 Hero keys in {lang}: {list(hero_data.keys())}")
        if 'features' in hero_data:
            print(f"   ✅ Features mevcut - title: {hero_data['features'].get('title', 'YOK')}")
        else:
            print("   ❌ Features EKSİK!")
    
    return {
        't': t_data,
        'current_lang': lang
    }

def get_url_for_lang(lang, endpoint=None, **values):
    """Belirtilen dil için URL oluştur"""
    if endpoint is None:
        # Mevcut endpoint'i kullan
        endpoint = request.endpoint
    
    print(f"🔍 URL Generation - Endpoint: {endpoint}, Lang: {lang}, Values: {values}")
    
    # Özel durumlar
    if endpoint == 'index':
        return f'/{lang}'
    elif endpoint == 'blog_list':
        return f'/{lang}/blog'
    elif endpoint == 'blog_detail':
        if 'slug' in values:
            return f'/{lang}/blog/{values["slug"]}'
        else:
            # Eğer slug yoksa mevcut slug'ı kullan
            if hasattr(request, 'view_args') and 'slug' in request.view_args:
                return f'/{lang}/blog/{request.view_args["slug"]}'
            return f'/{lang}/blog'
    elif endpoint == 'pricing':
        return f'/{lang}/pricing'
    
    # Mevcut path'i kullanarak URL oluştur
    current_path = request.path
    print(f"🔍 Current path: {current_path}")
    
    # Path'te dil prefix'i var mı kontrol et
    if current_path.startswith('/en/') or current_path.startswith('/tr/'):
        # Mevcut dil prefix'ini yeni dil ile değiştir
        new_path = f'/{lang}{current_path[3:]}'
        print(f"🔍 Replacing language prefix: {current_path} -> {new_path}")
    elif current_path in ['/en', '/tr']:
        # Sadece dil path'i varsa
        new_path = f'/{lang}'
        print(f"🔍 Root language path: {current_path} -> {new_path}")
    elif current_path == '/' or current_path == '':
        # Ana sayfa
        new_path = f'/{lang}'
        print(f"🔍 Home page: {current_path} -> {new_path}")
    else:
        # Dil prefix'i yoksa, mevcut path'e dil ekle
        new_path = f'/{lang}{current_path}'
        print(f"🔍 Adding language prefix: {current_path} -> {new_path}")
    
    return new_path

# Template context'e URL oluşturma fonksiyonunu ekle
@app.context_processor
def inject_url_functions():
    return dict(get_url_for_lang=get_url_for_lang)

# Initialize database on startup
init_db()

# Ana sayfa route'ları - multilingual
@app.route('/')
@app.route('/<lang>')
def index(lang=None):
    """Ana sayfa - dil desteği ile"""
    if lang and lang not in ['en', 'tr']:
        # Geçersiz dil için ana sayfaya yönlendir
        return redirect(url_for('index'))
    
    # Dil ayarla
    if lang:
        session['language'] = lang
    else:
        # Dil belirtilmemişse varsayılan 'en' kullan
        lang = session.get('language', 'en')
        if not lang:
            lang = 'en'
            session['language'] = lang
    
    template_data = get_template_data()
    
    # Ana sayfa için meta bilgilerini güncelle
    g.meta_title = 'Bisonar - AI Automation & Intelligent Workflows'
    g.meta_description = 'n8n-based AI automation systems, AI-powered workflows and digital transformation consulting. Multilingual solutions.'
    g.canonical_url = g.base_url  # Ana sayfa için sadece base URL
    
    # Get latest 3 blog posts for homepage
    conn = get_db_connection()
    posts = conn.execute('''
        SELECT id, title, slug, excerpt, author, read_time, image_url, created_at
        FROM posts 
        WHERE is_published = 1 
        ORDER BY created_at DESC 
        LIMIT 3
    ''').fetchall()
    conn.close()
    
    blog_posts = [dict(post) for post in posts]
    
    return render_template('index.html', **template_data, blog_posts=blog_posts)

# Blog route'ları - multilingual
@app.route('/blog')
@app.route('/<lang>/blog')
def blog_list(lang=None):
    """Blog list page - multilingual"""
    if lang and lang not in ['en', 'tr']:
        return redirect(url_for('blog_list'))
    
    # Dil ayarla
    if lang:
        session['language'] = lang
    
    template_data = get_template_data()
    
    # Blog listesi için meta bilgilerini güncelle
    g.meta_title = 'Blog - AI Automation Insights | Bisonar'
    g.meta_description = 'Latest insights on AI automation, n8n workflows, and business technology'
    
    # Canonical URL için doğru dil prefix'ini kullan
    if lang:
        g.canonical_url = f"{g.base_url}/{lang}/blog"
    else:
        g.canonical_url = f"{g.base_url}/blog"
    
    g.og_type = 'website'
    
    conn = get_db_connection()
    posts = conn.execute('''
        SELECT id, title, slug, excerpt, author, read_time, image_url, created_at
        FROM posts 
        WHERE is_published = 1 
        ORDER BY created_at DESC
    ''').fetchall()
    conn.close()
    
    blog_posts = [dict(post) for post in posts]
    
    return render_template('blog_list.html', **template_data, blog_posts=blog_posts)

@app.route('/blog/<slug>')
@app.route('/<lang>/blog/<slug>')
def blog_detail(slug, lang=None):
    """Blog detail page - multilingual"""
    if lang and lang not in ['en', 'tr']:
        return redirect(url_for('blog_detail', slug=slug))
    
    # Dil ayarla
    if lang:
        session['language'] = lang
    
    template_data = get_template_data()
    
    conn = get_db_connection()
    post = conn.execute('''
        SELECT id, title, slug, content, excerpt, author, read_time, image_url, created_at
        FROM posts 
        WHERE slug = ? AND is_published = 1
    ''', (slug,)).fetchone()
    conn.close()
    
    if post is None:
        return "Post not found", 404
    
    post_dict = dict(post)
    post_dict['content_html'] = markdown(post_dict['content'])
    
    # Blog detayı için meta bilgilerini güncelle
    g.meta_title = f"{post_dict['title']} | Bisonar"
    g.meta_description = post_dict['excerpt']
    
    # Canonical URL için doğru dil prefix'ini kullan
    if lang:
        g.canonical_url = f"{g.base_url}/{lang}/blog/{slug}"
    else:
        g.canonical_url = f"{g.base_url}/blog/{slug}"
    
    g.og_type = 'article'
    g.og_image = post_dict['image_url']
    
    return render_template('blog_detail.html', **template_data, post=post_dict)

# Pricing route'ları - multilingual
@app.route('/pricing')
@app.route('/<lang>/pricing')
def pricing(lang=None):
    """Fiyatlandırma sayfası - multilingual"""
    if lang and lang not in ['en', 'tr']:
        return redirect(url_for('pricing'))
    
    # Dil ayarla
    if lang:
        session['language'] = lang
    
    template_data = get_template_data()
    
    # Meta tags için context
    context = {
        'meta_title': 'Pricing Plans - Bisonar AI Assistant',
        'meta_description': 'Choose the perfect plan for your business. Start with 15-day free trial. No credit card required.',
        'og_type': 'website',
        'og_image': f"{request.host_url.rstrip('/')}/static/images/og-pricing.jpg"
    }
    
    # Canonical URL için doğru dil prefix'ini kullan
    if lang:
        context['canonical_url'] = f"{g.base_url}/{lang}/pricing"
    else:
        context['canonical_url'] = f"{g.base_url}/pricing"
    
    return render_template('pricing.html', **context, **template_data)

# Hash route'ları - BUNLARI EKLEYELİM
@app.route('/#about')
@app.route('/<lang>/#about')
def about_section(lang=None):
    """About section için canonical ana sayfa olmalı"""
    if lang and lang in ['en', 'tr']:
        return redirect(f'/{lang}')
    return redirect(url_for('index'))

@app.route('/#services')
@app.route('/<lang>/#services')
def services_section(lang=None):
    """Services section için canonical ana sayfa olmalı"""
    if lang and lang in ['en', 'tr']:
        return redirect(f'/{lang}')
    return redirect(url_for('index'))

@app.route('/#success')
@app.route('/<lang>/#success')
def success_section(lang=None):
    """Success section için canonical ana sayfa olmalı"""
    if lang and lang in ['en', 'tr']:
        return redirect(f'/{lang}')
    return redirect(url_for('index'))

@app.route('/#industries')
@app.route('/<lang>/#industries')
def industries_section(lang=None):
    """Industries section için canonical ana sayfa olmalı"""
    if lang and lang in ['en', 'tr']:
        return redirect(f'/{lang}')
    return redirect(url_for('index'))

@app.route('/#contact')
@app.route('/<lang>/#contact')
def contact_section(lang=None):
    """Contact section için canonical ana sayfa olmalı"""
    if lang and lang in ['en', 'tr']:
        return redirect(f'/{lang}')
    return redirect(url_for('index'))

# Dil değiştirme route'u
@app.route('/set-language/<lang>')
def set_language(lang):
    """Dil değiştirme - AJAX ve normal istekleri destekler"""
    print(f"🔍 Language change requested: {lang}")
    print(f"🔍 Current path: {request.path}")
    print(f"🔍 Referrer: {request.referrer}")
    print(f"🔍 AJAX request: {request.headers.get('X-Requested-With')}")
    
    if lang in ['en', 'tr']:
        session['language'] = lang
        print(f"✅ Language set in session: {lang}")
        
        # AJAX isteği mi kontrol et
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        if is_ajax:
            # REFERRER URL'sini kullanarak doğru path'i bul
            referrer = request.referrer or url_for('index')
            print(f"🔍 Using referrer for path: {referrer}")
            
            if referrer:
                from urllib.parse import urlparse
                parsed = urlparse(referrer)
                current_path = parsed.path
                
                # Referrer'daki path'i kullanarak yeni URL oluştur
                if current_path.startswith('/en/') or current_path.startswith('/tr/'):
                    new_path = f'/{lang}{current_path[3:]}'
                elif current_path in ['/en', '/tr']:
                    new_path = f'/{lang}'
                elif current_path == '/' or current_path == '':
                    new_path = f'/{lang}'
                else:
                    new_path = f'/{lang}{current_path}'
                
                print(f"🔀 Generated new path: {new_path}")
                
                response_data = {
                    'success': True, 
                    'language': lang, 
                    'message': 'Language changed successfully',
                    'new_path': new_path
                }
                print(f"📤 Sending JSON response: {response_data}")
                return jsonify(response_data)
        
        # Normal istek için redirect (mevcut kod aynı kalabilir)
        referrer = request.referrer or url_for('index')
        
        if referrer:
            from urllib.parse import urlparse, urlunparse
            parsed = urlparse(referrer)
            path = parsed.path
            
            # Path'te dil prefix'i var mı kontrol et
            if path.startswith('/en/') or path.startswith('/tr/'):
                new_path = f'/{lang}' + path[3:]
            elif path in ['/en', '/tr']:
                new_path = f'/{lang}'
            elif path == '/' or path == '':
                new_path = f'/{lang}'
            else:
                new_path = f'/{lang}{path}'
            
            new_referrer = urlunparse((
                parsed.scheme,
                parsed.netloc,
                new_path,
                parsed.params,
                parsed.query,
                parsed.fragment
            ))
            print(f"🔀 Redirecting to: {new_referrer}")
            return redirect(new_referrer)
    
    return redirect(request.referrer or url_for('index'))
    

# Diğer route'lar (admin, API, vs.) aynı kalacak...
@app.route('/billing')
def billing():
    """Ödeme sayfası"""
    if 'customer_id' not in session:
        return redirect('/customer_login')
    
    plan = request.args.get('plan', 'demo')
    
    # Customer bilgilerini al
    conn = psycopg2.connect(**DATABASE_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT id, name, email, current_plan FROM customers WHERE id = %s', (session['customer_id'],))
            customer_data = cur.fetchone()
            
            if customer_data:
                columns = [desc[0] for desc in cur.description]
                customer = dict(zip(columns, customer_data))
                customer['selected_plan'] = plan
                
                return f"Billing page for plan: {plan} - Customer: {customer['name']}"
            else:
                return redirect('/customer_login')
    except Exception as e:
        print(f"Billing error: {e}")
        return redirect('/dashboard')
    finally:
        conn.close()

# Add sample blog posts if none exist
def add_sample_posts():
    conn = get_db_connection()
    existing = conn.execute('SELECT COUNT(*) as count FROM posts').fetchone()['count']
    
    if existing == 0:
        sample_posts = [
            {
                'title': 'AI Automation: Revolutionizing Business Processes',
                'slug': 'ai-automation-revolutionizing-business-processes',
                'content': '''
# AI Automation: Revolutionizing Business Processes

Artificial Intelligence is transforming how businesses operate. In this post, we explore how AI automation can streamline your workflows and boost productivity.

## Key Benefits

- **Time Savings**: Automate repetitive tasks
- **Error Reduction**: Minimize human errors
- **Scalability**: Handle increased workload effortlessly

## Real-World Applications

From customer service chatbots to data analysis, AI automation is becoming essential for modern businesses.

*Published on: {}*
                '''.format(datetime.now().strftime('%B %d, %Y')),
                'excerpt': 'Discover how AI automation can transform your business processes and increase efficiency.',
                'author': 'Bisonar Team',
                'read_time': '5 min read',
                'image_url': 'https://images.unsplash.com/photo-1516110833967-0b5716ca1387?q=80&w=800&auto=format&fit=crop'
            },
            {
                'title': 'n8n Workflows: Best Practices for 2024',
                'slug': 'n8n-workflows-best-practices-2024',
                'content': '''
# n8n Workflows: Best Practices for 2024

n8n is a powerful workflow automation tool. Here are the best practices for creating efficient and maintainable workflows.

## Planning Your Workflow

1. **Define Objectives**: What do you want to achieve?
2. **Map Dependencies**: Understand task relationships
3. **Error Handling**: Plan for failures

## Optimization Tips

- Use webhooks for real-time triggers
- Implement proper logging
- Test thoroughly before deployment

*Published on: {}*
                '''.format(datetime.now().strftime('%B %d, %Y')),
                'excerpt': 'Learn the best practices for creating efficient and scalable n8n workflows in 2024.',
                'author': 'Bisonar Team',
                'read_time': '7 min read',
                'image_url': 'https://images.unsplash.com/photo-1620712943543-26fc76334419?q=80&w=800&auto=format&fit=crop'
            },
            {
                'title': 'Integrating ChatGPT with Your Business Applications',
                'slug': 'integrating-chatgpt-business-applications',
                'content': '''
# Integrating ChatGPT with Your Business Applications

ChatGPT integration can enhance various business functions. Learn how to seamlessly integrate AI into your applications.

## Integration Methods

- **API Integration**: Direct API calls
- **Webhook Triggers**: Event-based responses
- **Custom Middleware**: Bridge between systems

## Use Cases

- Customer support automation
- Content generation
- Data analysis and reporting

*Published on: {}*
                '''.format(datetime.now().strftime('%B %d, %Y')),
                'excerpt': 'Explore different methods to integrate ChatGPT with your business applications for enhanced functionality.',
                'author': 'Bisonar Team',
                'read_time': '6 min read',
                'image_url': 'https://images.unsplash.com/photo-1634912265239-49925890ab0b?q=80&w=800&auto=format&fit=crop'
            }
        ]
        
        for post in sample_posts:
            conn.execute('''
                INSERT INTO posts (title, slug, content, excerpt, author, read_time, image_url)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (post['title'], post['slug'], post['content'], post['excerpt'], 
                  post['author'], post['read_time'], post['image_url']))
        
        conn.commit()
    conn.close()

# Add sample posts on startup
add_sample_posts()

# HTTPS yönlendirmesi
@app.before_request
def enforce_https():
    """HTTP'den HTTPS'ye yönlendir (production'da)"""
    if not request.is_secure and not request.host.startswith(('127.0.0.1', 'localhost')):
        url = request.url.replace('http://', 'https://', 1)
        return redirect(url, code=301)

@app.before_request  
def normalize_url():
    """URL'leri normalize et - çoklu slash'leri düzelt"""
    if '//' in request.path and request.path != '//':
        new_path = request.path.replace('//', '/')
        return redirect(new_path, code=301)

# API Routes - bunlar multilingual değil
@app.route('/api/blog/posts')
def api_blog_posts():
    """API endpoint to get all blog posts"""
    conn = get_db_connection()
    posts = conn.execute('''
        SELECT id, title, slug, excerpt, author, read_time, image_url, created_at
        FROM posts 
        WHERE is_published = 1 
        ORDER BY created_at DESC
    ''').fetchall()
    conn.close()
    
    return jsonify([dict(post) for post in posts])

@app.route('/api/blog/posts/<int:post_id>')
def api_blog_post(post_id):
    """API endpoint to get specific blog post"""
    conn = get_db_connection()
    post = conn.execute('''
        SELECT id, title, slug, content, excerpt, author, read_time, image_url, created_at
        FROM posts 
        WHERE id = ? AND is_published = 1
    ''', (post_id,)).fetchone()
    conn.close()
    
    if post is None:
        return jsonify({'error': 'Post not found'}), 404
    
    return jsonify(dict(post))

@app.route('/api/admin/posts', methods=['GET'])
@admin_required
def api_admin_posts():
    conn = get_db_connection()
    posts = conn.execute('''
        SELECT id, title, slug, excerpt, author, read_time, image_url, created_at, is_published
        FROM posts 
        ORDER BY created_at DESC
    ''').fetchall()
    conn.close()
    return jsonify([dict(post) for post in posts])

@app.route('/api/chatbot', methods=['POST'])
def chatbot_proxy():
    try:
        data = request.get_json()
        message = data.get('message', '')
        session_id = data.get('sessionId', '')
        user_id = data.get('userId', '')

        response = requests.post(
            'https://g30rnaqf.rpcld.co/webhook/e1977560-4b62-48cd-bec2-530d2f3a62a4',
            json={
                'message': message,
                'sessionId': session_id,
                'userId': user_id
            },
            headers={
                'Content-Type': 'application/json'
            },
            timeout=30
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

@app.route('/sitemap.xml')
def sitemap():
    try:
        if request.host == '127.0.0.1:8000' or request.host.startswith('localhost'):
            base_url = f'http://{request.host}'
        else:
            base_url = 'https://www.bisonar.com'
        
        conn = get_db_connection()
        blog_posts = conn.execute('''
            SELECT slug, updated_at, created_at 
            FROM posts 
            WHERE is_published = 1
            ORDER BY created_at DESC
        ''').fetchall()
        conn.close()
        
        # Blog postlarını formatla - SAAT BİLGİSİNİ KALDIR
        formatted_posts = []
        for post in blog_posts:
            post_dict = dict(post)
            lastmod = post['updated_at'] or post['created_at']
            
            # Tarihi formatla - sadece YYYY-AA-GG
            if lastmod:
                if isinstance(lastmod, str):
                    # "2025-10-23 23:11:04" -> "2025-10-23"
                    post_dict['lastmod'] = lastmod.split(' ')[0]
                else:
                    # datetime objesiyse
                    post_dict['lastmod'] = lastmod.strftime('%Y-%m-%d')
            else:
                post_dict['lastmod'] = datetime.now().strftime('%Y-%m-%d')
                
            formatted_posts.append(post_dict)
        
        # Multilingual URL'ler için sitemap
        multilingual_urls = [
            {'loc': '', 'priority': '1.0', 'changefreq': 'weekly', 'lang': 'en'},
            {'loc': '/en', 'priority': '1.0', 'changefreq': 'weekly', 'lang': 'en'},
            {'loc': '/tr', 'priority': '1.0', 'changefreq': 'weekly', 'lang': 'tr'},
            {'loc': '/en/blog', 'priority': '0.8', 'changefreq': 'weekly', 'lang': 'en'},
            {'loc': '/tr/blog', 'priority': '0.8', 'changefreq': 'weekly', 'lang': 'tr'},
            {'loc': '/en/pricing', 'priority': '0.7', 'changefreq': 'monthly', 'lang': 'en'},
            {'loc': '/tr/pricing', 'priority': '0.7', 'changefreq': 'monthly', 'lang': 'tr'},
        ]
        
        # Blog postlar için multilingual URL'ler
        for post in formatted_posts:
            multilingual_urls.append({
                'loc': f'/en/blog/{post["slug"]}',
                'lastmod': post['lastmod'],
                'priority': '0.6',
                'changefreq': 'monthly',
                'lang': 'en'
            })
            multilingual_urls.append({
                'loc': f'/tr/blog/{post["slug"]}',
                'lastmod': post['lastmod'],
                'priority': '0.6',
                'changefreq': 'monthly',
                'lang': 'tr'
            })
        
        response = render_template(
            'sitemap.xml', 
            base_url=base_url,
            urls=multilingual_urls,
            lastmod=datetime.now().strftime('%Y-%m-%d')
        )
        
        return Response(response, mimetype='application/xml')
    
    except Exception as e:
        print(f"Sitemap error: {e}")
        return "Sitemap generation error", 500

@app.route('/robots.txt')
def robots():
    return send_from_directory(app.static_folder, 'robots.txt')

# Admin Routes
@app.route('/admin')
@admin_required
def admin_dashboard():
    conn = get_db_connection()
    posts = conn.execute('''
        SELECT id, title, slug, excerpt, author, read_time, image_url, created_at, is_published
        FROM posts 
        ORDER BY created_at DESC
    ''').fetchall()
    conn.close()
    
    blog_posts = [dict(post) for post in posts]
    return render_template('admin/dashboard.html', posts=blog_posts)

@app.route('/admin/posts/new', methods=['GET', 'POST'])
@admin_required
def admin_new_post():
    if request.method == 'POST':
        title = request.form['title']
        slug = request.form['slug']
        content = request.form['content']
        excerpt = request.form['excerpt']
        author = request.form['author']
        read_time = request.form['read_time']
        is_published = 'is_published' in request.form
        
        # Image upload
        image_url = ''
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                image_url = f'/static/uploads/{filename}'
        
        # Default image if none uploaded
        if not image_url:
            image_url = 'https://images.unsplash.com/photo-1486312338219-ce68d2c6f44d?q=80&w=800&auto=format&fit=crop'
        
        conn = get_db_connection()
        try:
            conn.execute('''
                INSERT INTO posts (title, slug, content, excerpt, author, read_time, image_url, is_published)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (title, slug, content, excerpt, author, read_time, image_url, is_published))
            conn.commit()
            return redirect(url_for('admin_dashboard'))
        except sqlite3.IntegrityError:
            flash('Slug already exists!', 'error')
        finally:
            conn.close()
    
    return render_template('admin/edit_post.html', post=None)

@app.route('/admin/posts/<int:post_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_post(post_id):
    conn = get_db_connection()
    
    if request.method == 'POST':
        title = request.form['title']
        slug = request.form['slug']
        content = request.form['content']
        excerpt = request.form['excerpt']
        author = request.form['author']
        read_time = request.form['read_time']
        is_published = 'is_published' in request.form
        
        # Image upload
        image_url = request.form.get('current_image', '')
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                image_url = f'/static/uploads/{filename}'
        
        try:
            conn.execute('''
                UPDATE posts 
                SET title=?, slug=?, content=?, excerpt=?, author=?, read_time=?, image_url=?, is_published=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
            ''', (title, slug, content, excerpt, author, read_time, image_url, is_published, post_id))
            conn.commit()
            return redirect(url_for('admin_dashboard'))
        except sqlite3.IntegrityError:
            flash('Slug already exists!', 'error')
    
    post = conn.execute('SELECT * FROM posts WHERE id = ?', (post_id,)).fetchone()
    conn.close()
    
    if post is None:
        return "Post not found", 404
    
    return render_template('admin/edit_post.html', post=dict(post))

@app.route('/admin/posts/<int:post_id>/delete', methods=['POST'])
@admin_required
def admin_delete_post(post_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM posts WHERE id = ?', (post_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/posts/<int:post_id>/toggle', methods=['POST'])
@admin_required
def admin_toggle_post(post_id):
    conn = get_db_connection()
    post = conn.execute('SELECT is_published FROM posts WHERE id = ?', (post_id,)).fetchone()
    new_status = not post['is_published']
    conn.execute('UPDATE posts SET is_published = ? WHERE id = ?', (new_status, post_id))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_dashboard'))

# AI Blog Generation Routes
@app.route('/admin/generate-blog', methods=['POST'])
@admin_required
def generate_blog_post():
    """Generate blog content using AI - DEBUG VERSION"""
    try:
        print("🔍 AI generation endpoint called")
        
        data = request.get_json()
        print(f"📥 Received data: {data}")
        
        topic = data.get('topic', '')
        language = data.get('language', 'en')
        
        if not topic:
            return jsonify({'error': 'Topic is required'}), 400
        
        print(f"🤖 Sending to n8n - Topic: {topic}, Language: {language}")
        
        # n8n'den yanıt al
        ai_response = generate_blog_with_ai(topic, language)
        
        print(f"📊 AI response type: {type(ai_response)}")
        print(f"📊 AI response keys: {ai_response.keys() if ai_response else 'None'}")
        
        if ai_response:
            print(f"✅ AI response received - Success: {ai_response.get('success')}")
            print(f"✅ AI response received - Content length: {len(ai_response.get('content', ''))}")
            print(f"✅ AI response received - Title: {ai_response.get('title')}")
            
            # Daha esnek kontrol
            if (ai_response.get('success') is not False and 
                ai_response.get('content') and 
                len(ai_response.get('content', '')) > 50):
                print(f"🎉 Valid AI content - returning to frontend")
                return jsonify(ai_response)
        
        print(f"❌ No valid AI response received")
        return jsonify({'error': 'AI service is currently unavailable. Please try again.'}), 503
        
    except Exception as e:
        print(f"❌ AI generation error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'AI generation failed'}), 500

def generate_blog_with_ai(topic, language='en'):
    """Generate blog content using n8n workflow - FIXED VERSION"""
    try:
        n8n_webhook_url = "https://g30rnaqf.rpcld.co/webhook/8ab73ba1-e074-4a2d-8076-91adaa0c776a"
        
        payload = {
            'topic': topic,
            'language': language,
            'timestamp': datetime.now().isoformat()
        }
        
        print(f"📡 Sending request to n8n...")
        
        response = requests.post(
            n8n_webhook_url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=45
        )
        
        print(f"📡 n8n response status: {response.status_code}")
        print(f"📡 n8n response content: {response.text}")  # DEBUG için ekledim
        
        if response.status_code == 200:
            result = response.json()
            print(f"🎯 n8n response type: {type(result)}")
            print(f"🎯 n8n response keys: {result.keys() if isinstance(result, dict) else 'Not a dict'}")
            
            # DEBUG: Tüm response'u yazdır
            print(f"🎯 Full n8n response: {result}")
            
            # EĞER result DICT ise direkt kullan, LIST ise ilk elemanı al
            if isinstance(result, dict):
                print(f"✅ Direct object response")
                return result
            elif isinstance(result, list) and len(result) > 0:
                print(f"✅ Array response, taking first item")
                return result[0]
            else:
                print(f"❌ Invalid response format: {type(result)}")
                return None
            
        else:
            print(f"❌ n8n HTTP error: {response.status_code}")
            print(f"❌ n8n error response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ n8n service error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

# ✅ YENİ: Google OAuth callback route'u
@app.route('/oauth/google/callback')
def google_oauth_callback():
    """Google OAuth callback handler"""
    try:
        from saas.models.oauth import OAuthModel
        from saas.config import GOOGLE_OAUTH_CONFIG
        
        code = request.args.get('code')
        customer_id = request.args.get('state')
        
        if not code or not customer_id:
            return "Invalid callback parameters", 400
        
        # Code'u token'a çevir
        token_response = requests.post('https://oauth2.googleapis.com/token', data={
            'client_id': GOOGLE_OAUTH_CONFIG['client_id'],
            'client_secret': GOOGLE_OAUTH_CONFIG['client_secret'],
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': GOOGLE_OAUTH_CONFIG['redirect_uri']
        })
        
        if token_response.status_code == 200:
            tokens = token_response.json()
            
            # Google user info al
            user_info = requests.get('https://www.googleapis.com/oauth2/v1/userinfo', 
                                   headers={'Authorization': f"Bearer {tokens['access_token']}"})
            
            google_email = user_info.json().get('email') if user_info.status_code == 200 else None
            
            # Token'ları kaydet
            OAuthModel.save_google_tokens(customer_id, tokens, google_email)
            
            return redirect(f'https://dashboard.bisonar.com/success?customer_id={customer_id}')
        else:
            return "Google OAuth failed", 400
            
    except Exception as e:
        print(f"OAuth callback error: {e}")
        return "Authentication failed", 400
    
@app.route('/api/saas/test')
def saas_test():
    """SaaS sisteminin çalıştığını test et"""
    return jsonify({
        'status': 'SaaS system is running',
        'endpoints': {
            'chat': '/saas/api/v1/chat/{customer_id}',
            'oauth_connect': '/saas/api/v1/oauth/google/connect/{customer_id}'
        }
    })

# Müşteri Onboarding Routes (bunlar multilingual değil)
@app.route('/signup', methods=['GET', 'POST'])
def customer_signup():
    """Müşteri kayıt sayfası"""
    if request.method == 'POST':
        try:
            # Form data'sını al
            name = request.form['company_name']
            email = request.form['email']
            password = request.form['password']
            website = request.form.get('website', '')
            
            # PostgreSQL'e kaydet
            conn = psycopg2.connect(**DATABASE_CONFIG)
            with conn.cursor() as cur:
                # Hash password ve token oluştur
                password_hash = generate_password_hash(password)
                verification_token = secrets.token_urlsafe(32)
                
                # Müşteriyi doğrudan customers tablosuna ekle (ama verified değil)
                cur.execute('''
                    INSERT INTO customers (name, email, website_url, password_hash, verification_token, is_verified, is_active)
                    VALUES (%s, %s, %s, %s, %s, false, false)
                    RETURNING id
                ''', (name, email, website, password_hash, verification_token))
                
                customer_id = cur.fetchone()[0]
                
                # Varsayılan prompt konfigürasyonu oluştur
                cur.execute('''
                    INSERT INTO tenant_prompts (customer_id, business_name, business_type, custom_prompt)
                    VALUES (%s, %s, %s, %s)
                ''', (customer_id, name, 'genel', f'Sen {name} şirketinin AI asistanısın. Profesyonel ve yardımsever ol.'))
                
                # Varsayılan widget config
                cur.execute('''
                    INSERT INTO tenant_widget_configs (customer_id, position, theme, primary_color)
                    VALUES (%s, %s, %s, %s)
                ''', (customer_id, 'bottom-right', 'light', '#007bff'))
                
                conn.commit()
                
                # Email gönder (simülasyon - gerçekte burada email API'si kullanın)
                print(f"🔐 Verification email sent to {email}")
                print(f"🔗 Verification URL: http://localhost:8000/verify/{verification_token}")
                
                flash('Kayıt başarılı! Lütfen emailinizi kontrol edin.', 'success')
                return redirect(url_for('customer_login'))
                
        except psycopg2.IntegrityError:
            flash('Bu email adresi zaten kayıtlı.', 'error')
        except Exception as e:
            flash('Kayıt sırasında bir hata oluştu.', 'error')
            print(f"Signup error: {e}")
        finally:
            conn.close()
    
    return render_template('customer/signup.html')

@app.route('/verify/<token>')
def verify_customer(token):
    """Email doğrulama"""
    conn = psycopg2.connect(**DATABASE_CONFIG)
    try:
        with conn.cursor() as cur:
            # Token'ı doğrula ve müşteriyi aktif et
            cur.execute('''
                UPDATE customers 
                SET is_verified = true, is_active = true, verification_token = NULL
                WHERE verification_token = %s AND is_verified = false
                RETURNING id, name, email
            ''', (token,))
            
            result = cur.fetchone()
            if result:
                customer_id, name, email = result
                
                # API key oluştur (eğer yoksa)
                cur.execute('''
                    UPDATE customers 
                    SET api_key = %s
                    WHERE id = %s AND api_key IS NULL
                ''', (secrets.token_urlsafe(32), customer_id))
                
                conn.commit()
                flash('Email doğrulandı! Artık giriş yapabilirsiniz.', 'success')
                print(f"✅ Customer verified: {name} ({email})")
            else:
                flash('Geçersiz veya süresi dolmuş doğrulama linki.', 'error')
                
    except Exception as e:
        flash('Doğrulama sırasında bir hata oluştu.', 'error')
        print(f"Verification error: {e}")
    finally:
        conn.close()
    
    return redirect(url_for('customer_login'))

@app.route('/login', methods=['GET', 'POST'])
def customer_login():
    """Müşteri giriş sayfası"""
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        print(f"🔐 Login attempt: {email}")  # DEBUG
        
        conn = psycopg2.connect(**DATABASE_CONFIG)
        try:
            with conn.cursor() as cur:
                cur.execute('''
                    SELECT id, name, password_hash, is_verified, api_key
                    FROM customers 
                    WHERE email = %s AND is_active = true
                ''', (email,))
                
                result = cur.fetchone()
                print(f"🔍 Database result: {result}")  # DEBUG
                
                if result:
                    customer_id, name, password_hash, is_verified, api_key = result
                    print(f"🔑 Password hash from DB: {password_hash}")  # DEBUG
                    print(f"🔑 Password check: {check_password_hash(password_hash, password)}")  # DEBUG
                    
                    if check_password_hash(password_hash, password):
                        if is_verified:
                            # Session oluştur
                            session_token = secrets.token_urlsafe(32)
                            expires_at = datetime.now() + timedelta(days=30)
                            
                            cur.execute('''
                                INSERT INTO customer_sessions (customer_id, session_token, expires_at)
                                VALUES (%s, %s, %s)
                            ''', (customer_id, session_token, expires_at))
                            
                            conn.commit()
                            
                            # Session'ı cookie'ye kaydet
                            session['customer_id'] = customer_id
                            session['customer_name'] = name
                            session['customer_token'] = session_token
                            
                            print(f"✅ Login successful for: {name}")  # DEBUG
                            flash('Giriş başarılı!', 'success')
                            return redirect(url_for('customer_dashboard'))
                        else:
                            print("❌ Email not verified")  # DEBUG
                            flash('Lütfen önce emailinizi doğrulayın.', 'error')
                    else:
                        print("❌ Password mismatch")  # DEBUG
                        flash('Geçersiz email veya şifre.', 'error')
                else:
                    print("❌ Customer not found")  # DEBUG
                    flash('Geçersiz email veya şifre.', 'error')
                    
        except Exception as e:
            print(f"🚨 Login error: {e}")  # DEBUG
            flash('Giriş sırasında bir hata oluştu.', 'error')
        finally:
            conn.close()
    
    return render_template('customer/login.html')

@app.route('/logout')
def customer_logout():
    """Müşteri çıkış"""
    session.clear()
    flash('Çıkış yapıldı.', 'success')
    return redirect(url_for('index'))

@app.route('/api/customer/update-prompt', methods=['POST'])
def update_customer_prompt():
    """Müşteri prompt ayarlarını güncelle"""
    if 'customer_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        customer_id = session['customer_id']
        
        # Services'i JSON formatına dönüştür
        services_text = data.get('services', '')
        if services_text:
            # Virgülle ayrılmış string'i listeye çevir
            services_list = [s.strip() for s in services_text.split(',') if s.strip()]
            # Listeyi JSON string'ine dönüştür
            services_json = json.dumps(services_list, ensure_ascii=False)
        else:
            services_json = json.dumps([])  # Boş array
        
        conn = psycopg2.connect(**DATABASE_CONFIG)
        with conn.cursor() as cur:
            cur.execute('''
                UPDATE tenant_prompts 
                SET business_name = %s,
                    business_type = %s,
                    services = %s::jsonb,
                    custom_prompt = %s,
                    welcome_message = %s,
                    contact_required = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE customer_id = %s
            ''', (
                data.get('business_name'),
                data.get('business_type'),
                services_json,  # JSON string olarak gönder
                data.get('custom_prompt'),
                data.get('welcome_message'),
                data.get('contact_required', True),
                customer_id
            ))
            
            conn.commit()
            return jsonify({'success': True, 'message': 'Prompt ayarları güncellendi'})
            
    except Exception as e:
        print(f"Prompt update error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Pricing Management Routes
@app.route('/pricing-settings')
def pricing_settings():
    """Fiyat listesi yönetimi"""
    if 'customer_id' not in session:
        return redirect(url_for('customer_login'))
    return render_template('customer/pricing.html')

@app.route('/api/customer/pricing', methods=['GET', 'POST'])
def customer_pricing():
    """Fiyat listesi API"""
    if 'customer_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    customer_id = session['customer_id']
    
    if request.method == 'GET':
        # Mevcut fiyatları getir (tablo yoksa boş döndür)
        conn = psycopg2.connect(**DATABASE_CONFIG)
        try:
            with conn.cursor() as cur:
                # Tablo var mı kontrol et
                cur.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'tenant_pricing'
                    );
                """)
                table_exists = cur.fetchone()[0]
                
                if not table_exists:
                    return jsonify({'prices': []})
                
                cur.execute('''
                    SELECT id, product_name, description, price, category, is_active, created_at
                    FROM tenant_pricing 
                    WHERE customer_id = %s
                    ORDER BY created_at DESC
                ''', (customer_id,))
                
                prices = []
                for row in cur.fetchall():
                    prices.append({
                        'id': row[0],
                        'product_name': row[1],
                        'description': row[2],
                        'price': float(row[3]) if row[3] else 0,
                        'category': row[4],
                        'is_active': row[5],
                        'created_at': row[6].isoformat() if row[6] else None
                    })
                
                return jsonify({'prices': prices})
        except Exception as e:
            print(f"Pricing GET error: {e}")
            return jsonify({'prices': []})
        finally:
            conn.close()
    
    elif request.method == 'POST':
        # Yeni fiyat ekle
        data = request.get_json()
        
        conn = psycopg2.connect(**DATABASE_CONFIG)
        try:
            with conn.cursor() as cur:
                # Tablo yoksa oluştur
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS tenant_pricing (
                        id SERIAL PRIMARY KEY,
                        customer_id VARCHAR(50) NOT NULL,
                        product_name VARCHAR(200) NOT NULL,
                        description TEXT,
                        price DECIMAL(10,2) NOT NULL,
                        currency VARCHAR(3) DEFAULT 'TRY',
                        category VARCHAR(50) DEFAULT 'product',
                        is_active BOOLEAN DEFAULT true,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                cur.execute('''
                    INSERT INTO tenant_pricing 
                    (customer_id, product_name, description, price, category, is_active)
                    VALUES (%s, %s, %s, %s, %s, %s)
                ''', (
                    customer_id,
                    data.get('product_name'),
                    data.get('description'),
                    data.get('price'),
                    data.get('category', 'product'),
                    data.get('is_active', True)
                ))
                
                conn.commit()
                return jsonify({'success': True, 'message': 'Fiyat eklendi'})
        except Exception as e:
            print(f"Pricing POST error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            conn.close()

@app.route('/api/customer/pricing/<int:price_id>', methods=['DELETE'])
def delete_customer_pricing(price_id):
    """Fiyat silme API"""
    if 'customer_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    customer_id = session['customer_id']
    
    conn = psycopg2.connect(**DATABASE_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute('''
                DELETE FROM tenant_pricing 
                WHERE id = %s AND customer_id = %s
            ''', (price_id, customer_id))
            
            conn.commit()
            return jsonify({'success': True, 'message': 'Fiyat silindi'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/ai-settings')
def ai_settings():
    """AI ayarları sayfası"""
    if 'customer_id' not in session:
        return redirect(url_for('customer_login'))
    
    conn = psycopg2.connect(**DATABASE_CONFIG)
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
        print(f"AI settings error: {e}")
        return render_template('customer/ai_settings.html', customer={})
    finally:
        conn.close()

# Integrations
@app.route('/integrations')
def integration_settings():
    """Entegrasyonlar sayfası"""
    if 'customer_id' not in session:
        return redirect(url_for('customer_login'))
    
    conn = psycopg2.connect(**DATABASE_CONFIG)
    try:
        with conn.cursor() as cur:
            # Customer temel bilgilerini al
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
                
                # Calendar preferences
                cur.execute('''
                    SELECT auto_create_events, event_types, event_duration_minutes, 
                           working_hours_start, working_hours_end
                    FROM tenant_calendar_preferences 
                    WHERE customer_id = %s
                ''', (session['customer_id'],))
                
                calendar_data = cur.fetchone()
                if calendar_data:
                    customer['calendar_enabled'] = calendar_data[0]
                    customer['calendar_event_types'] = calendar_data[1] or []
                    customer['default_event_duration'] = calendar_data[2] or 30
                    customer['working_hours'] = f"{calendar_data[3].strftime('%H:%M')} - {calendar_data[4].strftime('%H:%M')}"
                else:
                    customer['calendar_enabled'] = False
                    customer['calendar_event_types'] = []
                    customer['default_event_duration'] = 30
                    customer['working_hours'] = '09:00 - 18:00'
                
                # Webhook preferences
                cur.execute('''
                    SELECT config, is_active 
                    FROM tenant_integrations 
                    WHERE customer_id = %s AND integration_type = 'webhook'
                ''', (session['customer_id'],))
                
                webhook_data = cur.fetchone()
                if webhook_data:
                    config = webhook_data[0] or {}
                    customer['webhook_enabled'] = webhook_data[1]
                    customer['webhook_url'] = config.get('webhook_url', '')
                    customer['webhook_secret'] = config.get('webhook_secret', '')
                    customer['webhook_events'] = config.get('webhook_events', [])
                else:
                    customer['webhook_enabled'] = False
                    customer['webhook_url'] = ''
                    customer['webhook_secret'] = customer.get('webhook_secret', '')
                    customer['webhook_events'] = []
                
                return render_template('customer/integrations.html', customer=customer)
            else:
                return render_template('customer/integrations.html', customer={})
    except Exception as e:
        print(f"Integrations error: {e}")
        return render_template('customer/integrations.html', customer={})
    finally:
        conn.close()

@app.route('/save_telegram_settings', methods=['POST'])
def save_telegram_settings():
    """Telegram ayarlarını kaydet"""
    if 'customer_id' not in session:
        return jsonify({'success': False, 'message': 'Oturum bulunamadı'})
    
    try:
        telegram_chat_id = request.form.get('telegram_chat_id')
        min_lead_score = request.form.get('min_lead_score', 50)
        notification_types = request.form.getlist('notification_types')
        telegram_enabled = request.form.get('telegram_enabled') == 'true'
        
        conn = psycopg2.connect(**DATABASE_CONFIG)
        with conn.cursor() as cur:
            # Önce kaydın var olup olmadığını kontrol et
            cur.execute('SELECT id FROM tenant_telegram_preferences WHERE customer_id = %s', (session['customer_id'],))
            existing = cur.fetchone()
            
            if existing:
                # Varsa update et
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
                # Yoksa insert et
                cur.execute('''
                    INSERT INTO tenant_telegram_preferences 
                    (customer_id, receive_notifications, notification_types, customer_telegram_id, min_lead_score)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (session['customer_id'], telegram_enabled, json.dumps(notification_types), 
                      telegram_chat_id, min_lead_score))
            
            conn.commit()
        
        return jsonify({'success': True, 'message': 'Telegram ayarları kaydedildi'})
        
    except Exception as e:
        print(f"Save telegram settings error: {e}")
        return jsonify({'success': False, 'message': f'Kayıt başarısız: {str(e)}'})

@app.route('/save_calendar_settings', methods=['POST'])
def save_calendar_settings():
    """Calendar ayarlarını kaydet"""
    if 'customer_id' not in session:
        return jsonify({'success': False, 'message': 'Oturum bulunamadı'})
    
    try:
        default_event_duration = request.form.get('default_event_duration', 30)
        working_hours = request.form.get('working_hours', '9-18')
        event_types = request.form.getlist('event_types')
        calendar_enabled = request.form.get('calendar_enabled') == 'true'
        
        print(f"DEBUG: working_hours value: {working_hours}")
        
        # Working hours'ı parse et - daha güvenli şekilde
        if working_hours and '-' in working_hours:
            try:
                start_time, end_time = working_hours.split('-')
                # Boşlukları temizle ve formatı düzelt
                start_time = start_time.strip() + ':00'
                end_time = end_time.strip() + ':00'
                print(f"DEBUG: Parsed start_time: {start_time}, end_time: {end_time}")
            except Exception as e:
                print(f"DEBUG: Error parsing working_hours: {e}")
                # Varsayılan değerler
                start_time = '09:00:00'
                end_time = '18:00:00'
        else:
            # Varsayılan değerler
            start_time = '09:00:00'
            end_time = '18:00:00'
        
        conn = psycopg2.connect(**DATABASE_CONFIG)
        with conn.cursor() as cur:
            # Önce kaydın var olup olmadığını kontrol et
            cur.execute('SELECT id FROM tenant_calendar_preferences WHERE customer_id = %s', (session['customer_id'],))
            existing = cur.fetchone()
            
            if existing:
                # Varsa update et
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
                # Yoksa insert et
                cur.execute('''
                    INSERT INTO tenant_calendar_preferences 
                    (customer_id, auto_create_events, event_types, event_duration_minutes, 
                     working_hours_start, working_hours_end)
                    VALUES (%s, %s, %s, %s, %s, %s)
                ''', (session['customer_id'], calendar_enabled, json.dumps(event_types), 
                      default_event_duration, start_time, end_time))
            
            conn.commit()
            print("DEBUG: Calendar settings saved successfully")
        
        return jsonify({'success': True, 'message': 'Calendar ayarları kaydedildi'})
        
    except Exception as e:
        print(f"Save calendar settings error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Kayıt başarısız: {str(e)}'})

@app.route('/save_webhook_settings', methods=['POST'])
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
        
        conn = psycopg2.connect(**DATABASE_CONFIG)
        with conn.cursor() as cur:
            # Webhook secret'ı customers tablosuna da kaydet
            if webhook_secret:
                cur.execute('''
                    UPDATE customers SET webhook_secret = %s WHERE id = %s
                ''', (webhook_secret, session['customer_id']))
            
            # Önce kaydın var olup olmadığını kontrol et
            cur.execute('SELECT id FROM tenant_integrations WHERE customer_id = %s AND integration_type = %s', 
                       (session['customer_id'], 'webhook'))
            existing = cur.fetchone()
            
            if existing:
                # Varsa update et
                cur.execute('''
                    UPDATE tenant_integrations 
                    SET config = %s,
                        is_active = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE customer_id = %s AND integration_type = %s
                ''', (json.dumps(config), webhook_enabled, session['customer_id'], 'webhook'))
            else:
                # Yoksa insert et
                cur.execute('''
                    INSERT INTO tenant_integrations 
                    (customer_id, integration_type, config, is_active)
                    VALUES (%s, %s, %s, %s)
                ''', (session['customer_id'], 'webhook', json.dumps(config), webhook_enabled))
            
            conn.commit()
        
        return jsonify({'success': True, 'message': 'Webhook ayarları kaydedildi'})
        
    except Exception as e:
        print(f"Save webhook settings error: {e}")
        return jsonify({'success': False, 'message': f'Kayıt başarısız: {str(e)}'})

@app.route('/api/integrations/<integration>/toggle', methods=['POST'])
def toggle_integration(integration):
    """Entegrasyon durumunu değiştir"""
    if 'customer_id' not in session:
        return jsonify({'success': False, 'message': 'Oturum bulunamadı'})
    
    try:
        data = request.get_json()
        enabled = data.get('enabled', False)
        customer_id = session['customer_id']
        
        print(f"DEBUG: Toggling {integration} to {enabled} for customer {customer_id}")
        
        conn = psycopg2.connect(**DATABASE_CONFIG)
        with conn.cursor() as cur:
            if integration == 'telegram':
                print("DEBUG: Updating telegram preferences")
                # Önce kaydın var olup olmadığını kontrol et
                cur.execute('SELECT id FROM tenant_telegram_preferences WHERE customer_id = %s', (customer_id,))
                existing = cur.fetchone()
                
                if existing:
                    # Varsa update et
                    cur.execute('''
                        UPDATE tenant_telegram_preferences 
                        SET receive_notifications = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE customer_id = %s
                    ''', (enabled, customer_id))
                else:
                    # Yoksa insert et
                    cur.execute('''
                        INSERT INTO tenant_telegram_preferences (customer_id, receive_notifications)
                        VALUES (%s, %s)
                    ''', (customer_id, enabled))
                
            elif integration == 'calendar':
                print("DEBUG: Updating calendar preferences")
                # Önce kaydın var olup olmadığını kontrol et
                cur.execute('SELECT id FROM tenant_calendar_preferences WHERE customer_id = %s', (customer_id,))
                existing = cur.fetchone()
                
                if existing:
                    # Varsa update et
                    cur.execute('''
                        UPDATE tenant_calendar_preferences 
                        SET auto_create_events = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE customer_id = %s
                    ''', (enabled, customer_id))
                else:
                    # Yoksa insert et
                    cur.execute('''
                        INSERT INTO tenant_calendar_preferences (customer_id, auto_create_events)
                        VALUES (%s, %s)
                    ''', (customer_id, enabled))
                
            elif integration == 'webhook':
                print("DEBUG: Updating webhook integration")
                # Önce kaydın var olup olmadığını kontrol et
                cur.execute('SELECT id FROM tenant_integrations WHERE customer_id = %s AND integration_type = %s', 
                           (customer_id, 'webhook'))
                existing = cur.fetchone()
                
                if existing:
                    # Varsa update et
                    cur.execute('''
                        UPDATE tenant_integrations 
                        SET is_active = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE customer_id = %s AND integration_type = %s
                    ''', (enabled, customer_id, 'webhook'))
                else:
                    # Yoksa insert et
                    cur.execute('''
                        INSERT INTO tenant_integrations (customer_id, integration_type, is_active)
                        VALUES (%s, %s, %s)
                    ''', (customer_id, 'webhook', enabled))
            else:
                return jsonify({'success': False, 'message': f'Geçersiz entegrasyon: {integration}'})
            
            conn.commit()
            print(f"DEBUG: Successfully toggled {integration}")
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"DEBUG: Toggle integration error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'İşlem başarısız: {str(e)}'})

@app.route('/analytics')
def analytics():
    """Analitik sayfası"""
    if 'customer_id' not in session:
        return redirect(url_for('customer_login'))
    return render_template('customer/analytics.html')

# Google Calendar OAuth route'u
@app.route('/oauth/google/connect')
def google_calendar_connect():
    """Google Calendar OAuth bağlantısı"""
    if 'customer_id' not in session:
        return redirect(url_for('customer_login'))
    
    # Google OAuth URL oluştur
    from saas.config import GOOGLE_OAUTH_CONFIG
    
    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={GOOGLE_OAUTH_CONFIG['client_id']}&"
        f"redirect_uri={GOOGLE_OAUTH_CONFIG['redirect_uri']}&"
        f"response_type=code&"
        f"scope=https://www.googleapis.com/auth/calendar.events&"
        f"state={session['customer_id']}&"
        f"access_type=offline&"
        f"prompt=consent"
    )
    
    return redirect(auth_url)

# Dashboard route'unu güncelle
@app.route('/dashboard')
def customer_dashboard():
    """Müşteri dashboard'u"""
    if 'customer_id' not in session:
        return redirect(url_for('customer_login'))
    
    conn = psycopg2.connect(**DATABASE_CONFIG)
    try:
        with conn.cursor() as cur:
            # Müşteri bilgilerini getir
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
                
                # Basit usage stats
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
                return redirect(url_for('login'))
            
    except Exception as e:
        print(f"🚨 Dashboard error: {e}")
        flash('Dashboard yüklenirken bir hata oluştu.', 'error')
        return redirect(url_for('login'))
    finally:
        conn.close()

# Konuşmalar
@app.route('/customer/conversations')
def customer_conversations():
    if 'customer_id' not in session:
        return jsonify({'success': False, 'message': 'Oturum bulunamadı'})
    customer_id = session.get('customer_id')
    
    # Örnek konuşma verileri - gerçek uygulamada database'den çekilecek
    sample_conversations = {
        'new_conversations': [
            {
                'id': 1,
                'customer_name': 'Ahmet Yılmaz',
                'lead_score': 85,
                'last_activity': '2 dk önce',
                'last_message': 'Merhaba, fiyat bilgisi almak istiyorum. n8n otomasyon paketiniz ne kadar?',
                'channel': 'whatsapp',
                'priority': 'urgent'
            },
            {
                'id': 2,
                'customer_name': 'Mehmet Kaya',
                'lead_score': 62,
                'last_activity': '1 saat önce',
                'last_message': 'Demo talep ediyorum, iletişime geçebilir misiniz?',
                'channel': 'web',
                'priority': 'demo'
            }
        ],
        'active_conversations': [
            {
                'id': 3,
                'customer_name': 'Elif Demir',
                'lead_score': 92,
                'last_activity': '5 saat önce',
                'last_message': 'Acil teknik destek gerekiyor! Sistemimde sorun var.',
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
                'last_message': 'Teşekkürler, bilgiler için. İhtiyaç olursa döneceğim.',
                'channel': 'telegram',
                'priority': 'info'
            }
        ]
    }
    
    return render_template('customer/conversations.html', **sample_conversations)

@app.route('/api/conversations/<int:conversation_id>')
def get_conversation_detail(conversation_id):
    if 'customer_id' not in session:
        return jsonify({'success': False, 'message': 'Oturum bulunamadı'})
    # Örnek konuşma detayı - gerçek uygulamada database'den çekilecek
    sample_conversation = {
        'success': True,
        'conversation': {
            'id': conversation_id,
            'customer_name': 'Ahmet Yılmaz',
            'phone': '0555 123 45 67',
            'email': 'ahmet@email.com',
            'lead_score': 85,
            'messages': [
                {
                    'type': 'user',
                    'text': 'Merhaba, fiyat bilgisi almak istiyorum. n8n otomasyon paketiniz ne kadar?',
                    'timestamp': '14:30'
                },
                {
                    'type': 'ai',
                    'text': 'Merhaba Ahmet Bey! Tabii ki. Temel n8n otomasyon paketimiz 5.000 TL\'dir. Size özel teklifimiz için iletişim bilgilerinizi alabilir miyim?',
                    'timestamp': '14:31'
                },
                {
                    'type': 'user',
                    'text': 'Telefonum: 0555 123 45 67. En kısa sürede arar mısınız?',
                    'timestamp': '14:32'
                },
                {
                    'type': 'ai',
                    'text': 'Teşekkürler! Danışmanımız en kısa sürede sizi arayacaktır. İyi günler dilerim.',
                    'timestamp': '14:32'
                }
            ]
        }
    }
    
    return jsonify(sample_conversation)

if __name__ == '__main__':
    import jinja2
    jinja2.clear_caches()
    app.run(debug=True, port=8000)