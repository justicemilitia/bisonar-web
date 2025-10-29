# blog.py
import sqlite3
from datetime import datetime
from markdown import markdown

# Database configuration
DATABASE = 'blog.db'

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_blog_db():
    """Initialize the blog database"""
    with sqlite3.connect(DATABASE) as conn:
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

def get_blog_posts(limit=None):
    """Get blog posts from database"""
    conn = get_db_connection()
    
    query = '''
        SELECT id, title, slug, excerpt, author, read_time, image_url, created_at
        FROM posts 
        WHERE is_published = 1 
        ORDER BY created_at DESC
    '''
    
    if limit:
        query += ' LIMIT ?'
        posts = conn.execute(query, (limit,)).fetchall()
    else:
        posts = conn.execute(query).fetchall()
    
    conn.close()
    return [dict(post) for post in posts]

def get_blog_post_by_slug(slug):
    """Get single blog post by slug"""
    conn = get_db_connection()
    post = conn.execute('''
        SELECT id, title, slug, content, excerpt, author, read_time, image_url, created_at
        FROM posts 
        WHERE slug = ? AND is_published = 1
    ''', (slug,)).fetchone()
    conn.close()
    
    if post:
        post_dict = dict(post)
        post_dict['content_html'] = markdown(post_dict['content'])
        return post_dict
    return None

def get_all_blog_posts():
    """Get all blog posts for admin"""
    conn = get_db_connection()
    posts = conn.execute('''
        SELECT id, title, slug, excerpt, author, read_time, image_url, created_at, is_published
        FROM posts 
        ORDER BY created_at DESC
    ''').fetchall()
    conn.close()
    return [dict(post) for post in posts]

def create_blog_post(title, slug, content, excerpt, author, read_time, image_url, is_published=True):
    """Create new blog post"""
    conn = get_db_connection()
    try:
        conn.execute('''
            INSERT INTO posts (title, slug, content, excerpt, author, read_time, image_url, is_published)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (title, slug, content, excerpt, author, read_time, image_url, is_published))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def update_blog_post(post_id, title, slug, content, excerpt, author, read_time, image_url, is_published):
    """Update blog post"""
    conn = get_db_connection()
    try:
        conn.execute('''
            UPDATE posts 
            SET title=?, slug=?, content=?, excerpt=?, author=?, read_time=?, image_url=?, is_published=?, updated_at=CURRENT_TIMESTAMP
            WHERE id=?
        ''', (title, slug, content, excerpt, author, read_time, image_url, is_published, post_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def delete_blog_post(post_id):
    """Delete blog post"""
    conn = get_db_connection()
    conn.execute('DELETE FROM posts WHERE id = ?', (post_id,))
    conn.commit()
    conn.close()

def toggle_blog_post_status(post_id):
    """Toggle blog post published status"""
    conn = get_db_connection()
    post = conn.execute('SELECT is_published FROM posts WHERE id = ?', (post_id,)).fetchone()
    new_status = not post['is_published']
    conn.execute('UPDATE posts SET is_published = ? WHERE id = ?', (new_status, post_id))
    conn.commit()
    conn.close()
    return new_status

def get_blog_posts_for_sitemap():
    """Get blog posts for sitemap"""
    conn = get_db_connection()
    posts = conn.execute('''
        SELECT slug, updated_at, created_at 
        FROM posts 
        WHERE is_published = 1
        ORDER BY created_at DESC
    ''').fetchall()
    conn.close()
    return [dict(post) for post in posts]

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