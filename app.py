import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, g
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

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

# ----------------- MODELS -----------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    # Text – no length limit, works with all hash lengths
    password_hash = db.Column(db.Text, nullable=False)

class News(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    summary = db.Column(db.Text, nullable=False)
    content = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(500), nullable=True)
    date_posted = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ----------------- ROUTES (unchanged) -----------------
@app.route('/')
def home():
    news_list = News.query.order_by(News.date_posted.desc()).all()
    return render_template('index.html', news_list=news_list)

@app.route('/news/<int:news_id>')
def news_detail(news_id):
    news_item = News.query.get_or_404(news_id)
    return render_template('news_detail.html', news=news_item)

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
        image_url = request.form.get('image_url', '')
        news_item = News(title=title, summary=summary, content=content, image_url=image_url)
        db.session.add(news_item)
        db.session.commit()
        flash('News added successfully.', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('admin/add_news.html')

@app.route('/admin/edit/<int:news_id>', methods=['GET', 'POST'])
@login_required
def edit_news(news_id):
    news_item = News.query.get_or_404(news_id)
    if request.method == 'POST':
        news_item.title = request.form['title']
        news_item.summary = request.form['summary']
        news_item.content = request.form['content']
        news_item.image_url = request.form.get('image_url', '')
        db.session.commit()
        flash('News updated successfully.', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('admin/edit_news.html', news=news_item)

@app.route('/admin/delete/<int:news_id>')
@login_required
def delete_news(news_id):
    news_item = News.query.get_or_404(news_id)
    db.session.delete(news_item)
    db.session.commit()
    flash('News deleted.', 'info')
    return redirect(url_for('admin_dashboard'))

# ----------------- DATABASE INITIALIZATION (safe) -----------------
@app.before_request
def initialize():
    if not getattr(g, '_db_initialized', False):
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            hashed = generate_password_hash('admin123')   # change after first login!
            admin_user = User(username='admin', password_hash=hashed)
            db.session.add(admin_user)
            db.session.commit()
        g._db_initialized = True

if __name__ == '__main__':
    app.run(debug=True)
