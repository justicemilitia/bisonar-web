from flask import Flask, render_template, session, jsonify, request, redirect, url_for, flash, Response
import json
import requests
import sqlite3
import os
from datetime import datetime
from markdown import markdown
from functools import wraps  # Bu satırı ekleyin
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

# Normal Routes
@app.route('/')
def index():
    template_data = get_template_data()
    
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
    
    # Convert to list of dicts
    blog_posts = [dict(post) for post in posts]
    
    return render_template('index.html', **template_data, blog_posts=blog_posts)

@app.route('/blog')
def blog_list():
    """Blog list page"""
    template_data = get_template_data()
    
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
    # Convert markdown to HTML
    post_dict['content_html'] = markdown(post_dict['content'])
    
    return render_template('blog_detail.html', **template_data, post=post_dict)

# API endpoints for blog management
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

# API for admin blog management
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