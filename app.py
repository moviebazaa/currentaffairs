import os
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, g
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import requests
from bs4 import BeautifulSoup
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-me')

# ----------------- DATABASE SETUP -----------------
database_url = os.environ.get('DATABASE_URL')
if database_url:
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    if 'sslmode' not in database_url:
        separator = '&' if '?' in database_url else '?'
        database_url += f'{separator}sslmode=require'
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///news.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'admin_login'

# ----------------- CONSTANTS -----------------
VALID_CATEGORIES = ['Current Affairs', 'GK News', 'PSC Updates']

# ----------------- MODELS -----------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.Text, nullable=False)

class News(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    summary = db.Column(db.Text, nullable=False)
    content = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(500), nullable=True)
    category = db.Column(db.String(50), nullable=False, default='Current Affairs')
    source_url = db.Column(db.String(500), nullable=True)
    date_posted = db.Column(db.DateTime, default=datetime.utcnow)

class PageView(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    page = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ----------------- DATABASE INITIALISATION (runs at startup) -----------------
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        hashed = generate_password_hash('admin123')   # CHANGE after first login!
        admin_user = User(username='admin', password_hash=hashed)
        db.session.add(admin_user)
        db.session.commit()

# ----------------- ANALYTICS TRACKING (non-blocking, safe) -----------------
@app.before_request
def track_page_view():
    if request.path.startswith('/admin') or request.path.startswith('/static') or request.path == '/favicon.ico':
        return
    if request.method != 'GET':
        return

    category = None
    if request.path.startswith('/news/') and request.view_args and 'news_id' in request.view_args:
        news_item = db.session.get(News, request.view_args['news_id'])
        if news_item:
            category = news_item.category

    try:
        view = PageView(page=request.path, category=category)
        db.session.add(view)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Analytics error (non-critical): {e}")

# ----------------- ROUTES – FRONTEND -----------------
@app.route('/')
def home():
    latest_news = News.query.order_by(News.date_posted.desc()).limit(6).all()
    return render_template('index.html', latest_news=latest_news)

@app.route('/news/<int:news_id>')
def news_detail(news_id):
    news_item = News.query.get_or_404(news_id)
    return render_template('news_detail.html', news=news_item)

@app.route('/current-affairs')
def current_affairs():
    news_list = News.query.filter_by(category='Current Affairs').order_by(News.date_posted.desc()).all()
    return render_template('category.html', news_list=news_list, category_name='Current Affairs')

@app.route('/gk-news')
def gk_news():
    news_list = News.query.filter_by(category='GK News').order_by(News.date_posted.desc()).all()
    return render_template('category.html', news_list=news_list, category_name='GK News')

@app.route('/psc-updates')
def psc_updates():
    news_list = News.query.filter_by(category='PSC Updates').order_by(News.date_posted.desc()).all()
    return render_template('category.html', news_list=news_list, category_name='PSC Important Updates')

# ----------------- ADMIN AUTH -----------------
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Logged in successfully.', 'success')
            return redirect(url_for('admin_dashboard'))
        flash('Invalid username or password.', 'danger')
    return render_template('admin/login.html')

@app.route('/admin/logout')
@login_required
def admin_logout():
    logout_user()
    flash('Logged out.', 'info')
    return redirect(url_for('home'))

# ----------------- ADMIN DASHBOARD -----------------
@app.route('/admin')
@login_required
def admin_dashboard():
    all_news = News.query.order_by(News.date_posted.desc()).all()
    return render_template('admin/dashboard.html', news_list=all_news)

@app.route('/admin/add', methods=['GET', 'POST'])
@login_required
def add_news():
    if request.method == 'POST':
        title = request.form['title']
        summary = request.form['summary']
        content = request.form['content']
        category = request.form.get('category', 'Current Affairs')
        image_url = request.form.get('image_url', '')
        source_url = request.form.get('source_url', '')
        news_item = News(
            title=title, summary=summary, content=content,
            category=category, image_url=image_url, source_url=source_url
        )
        db.session.add(news_item)
        db.session.commit()
        flash('News added successfully.', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('admin/add_news.html', categories=VALID_CATEGORIES)

@app.route('/admin/edit/<int:news_id>', methods=['GET', 'POST'])
@login_required
def edit_news(news_id):
    news_item = News.query.get_or_404(news_id)
    if request.method == 'POST':
        news_item.title = request.form['title']
        news_item.summary = request.form['summary']
        news_item.content = request.form['content']
        news_item.category = request.form.get('category', 'Current Affairs')
        news_item.image_url = request.form.get('image_url', '')
        news_item.source_url = request.form.get('source_url', '')
        db.session.commit()
        flash('News updated successfully.', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('admin/edit_news.html', news=news_item, categories=VALID_CATEGORIES)

@app.route('/admin/delete/<int:news_id>')
@login_required
def delete_news(news_id):
    news_item = News.query.get_or_404(news_id)
    db.session.delete(news_item)
    db.session.commit()
    flash('News deleted.', 'info')
    return redirect(url_for('admin_dashboard'))

# ----------------- ANALYTICS DASHBOARD -----------------
@app.route('/admin/analytics')
@login_required
def analytics():
    total_views = PageView.query.count()
    most_visited = db.session.query(
        PageView.page, db.func.count(PageView.id).label('count')
    ).group_by(PageView.page).order_by(db.desc('count')).limit(10).all()
    cutoff = datetime.utcnow() - timedelta(days=7)
    trending = db.session.query(
        PageView.category, db.func.count(PageView.id).label('count')
    ).filter(PageView.timestamp >= cutoff, PageView.category != None).group_by(PageView.category).order_by(db.desc('count')).all()
    recent_views = PageView.query.order_by(PageView.timestamp.desc()).limit(20).all()
    return render_template('admin/analytics.html', total_views=total_views, most_visited=most_visited, trending=trending, recent_views=recent_views)

# ----------------- SCRAPER FUNCTIONS -----------------
def save_article(title, summary, content, category, source_url, image_url=''):
    existing = News.query.filter_by(source_url=source_url).first()
    if existing:
        return
    article = News(
        title=title, summary=summary, content=content,
        category=category, source_url=source_url, image_url=image_url
    )
    db.session.add(article)
    db.session.commit()

def scrape_kerala_psc():
    try:
        url = "https://www.keralapsc.gov.in/notifications"
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        for item in soup.select('.view-notifications .views-row')[:10]:
            link_tag = item.find('a')
            if not link_tag:
                continue
            title = link_tag.get_text(strip=True)
            link = link_tag.get('href')
            if not link:
                continue
            if not link.startswith('http'):
                link = 'https://www.keralapsc.gov.in' + link
            date_tag = item.find('span', class_='date-display-single')
            summary = date_tag.get_text(strip=True) if date_tag else 'New notification from Kerala PSC'
            save_article(title, summary, summary, 'PSC Updates', link)
        print("Kerala PSC scrape completed.")
    except Exception as e:
        print(f"Error scraping Kerala PSC: {e}")

def scrape_gk_today():
    try:
        url = "https://www.gktoday.in/current-affairs/"
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        for article in soup.select('article')[:5]:
            title_tag = article.find('h2')
            link_tag = article.find('a')
            if not title_tag or not link_tag:
                continue
            title = title_tag.get_text(strip=True)
            link = link_tag.get('href')
            if not link.startswith('http'):
                link = 'https://www.gktoday.in' + link
            summary = article.find('p').get_text(strip=True) if article.find('p') else 'Current affairs update'
            save_article(title, summary, summary, 'Current Affairs', link)
        print("GK Today scrape completed.")
    except Exception as e:
        print(f"Error scraping GK Today: {e}")

def run_all_scrapers():
    with app.app_context():
        scrape_kerala_psc()
        scrape_gk_today()

# ----------------- SCHEDULER -----------------
scheduler = BackgroundScheduler()
scheduler.add_job(run_all_scrapers, 'interval', hours=6, id='scraper_job')
scheduler.start()

@app.route('/admin/scrape')
@login_required
def manual_scrape():
    run_all_scrapers()
    flash('Scraping triggered manually!', 'success')
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    app.run(debug=True)
