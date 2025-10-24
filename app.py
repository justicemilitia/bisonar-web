from flask import Flask, render_template, session, jsonify, request, redirect, url_for, flash, Response, send_from_directory, g
import json
import requests
import sqlite3
import os
from datetime import datetime
from markdown import markdown
from functools import wraps
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'bisonar-test'
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# Database configuration
app.config['DATABASE'] = 'blog.db'

# Admin configuration
app.config['ADMIN_USERNAME'] = 'admin'
app.config['ADMIN_PASSWORD'] = 'bisonar2024'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

# Upload klasörünü oluştur
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

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
        """Hreflang URL'lerini oluştur - HASH'SİZ"""
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
    current_lang = session.get('language', 'en')
    t_data = TRANSLATIONS.get(current_lang, TRANSLATIONS['en'])
    return {
        't': t_data,
        'current_lang': current_lang
    }

# Initialize database on startup
init_db()

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

# Normal Routes
@app.route('/')
def index():
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

# Hash route'ları - BUNLARI EKLEYELİM
@app.route('/#about')
def about_section():
    """About section için canonical ana sayfa olmalı"""
    return redirect(url_for('index'))

@app.route('/#services')
def services_section():
    """Services section için canonical ana sayfa olmalı"""
    return redirect(url_for('index'))

@app.route('/#success')
def success_section():
    """Success section için canonical ana sayfa olmalı"""
    return redirect(url_for('index'))

@app.route('/#industries')
def industries_section():
    """Industries section için canonical ana sayfa olmalı"""
    return redirect(url_for('index'))

@app.route('/#contact')
def contact_section():
    """Contact section için canonical ana sayfa olmalı"""
    return redirect(url_for('index'))

@app.route('/blog')
def blog_list():
    """Blog list page"""
    template_data = get_template_data()
    
    # Blog listesi için meta bilgilerini güncelle
    g.meta_title = 'Blog - AI Automation Insights | Bisonar'
    g.meta_description = 'Latest insights on AI automation, n8n workflows, and business technology'
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
def blog_detail(slug):
    """Blog detail page"""
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
    g.canonical_url = f"{g.base_url}/blog/{slug}"
    g.og_type = 'article'
    g.og_image = post_dict['image_url']
    
    return render_template('blog_detail.html', **template_data, post=post_dict)

# Diğer route'lar aynı kalacak...
# (admin routes, API endpoints, sitemap, robots.txt, set-language)

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
        
        # SPA sections - TÜM önemli sayfalarınız
        spa_sections = [
            {'loc': '', 'priority': '1.0', 'changefreq': 'weekly'},
            {'loc': '#about', 'priority': '0.8', 'changefreq': 'monthly'},
            {'loc': '#services', 'priority': '0.9', 'changefreq': 'monthly'},
            {'loc': '#contact', 'priority': '0.7', 'changefreq': 'monthly'},
        ]
        
        response = render_template(
            'sitemap.xml', 
            base_url=base_url,
            spa_sections=spa_sections,  # ← BU EKLENDİ
            blog_posts=blog_posts,      # ← BU ZATEN VAR
            lastmod=datetime.now().strftime('%Y-%m-%d')
        )
        
        return Response(response, mimetype='application/xml')
    
    except Exception as e:
        print(f"Sitemap error: {e}")
        return "Sitemap generation error", 500


@app.route('/robots.txt')
def robots():
    return send_from_directory(app.static_folder, 'robots.txt')

@app.route('/set-language/<lang>')
def set_language(lang):
    if lang in ['en', 'tr']:
        session['language'] = lang
    return jsonify({'success': True, 'language': lang})

# Admin Routes - BUNLARI EKLE
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


#Ai blog page

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

if __name__ == '__main__':
    import jinja2
    jinja2.clear_caches()
    app.run(debug=True, port=8000)