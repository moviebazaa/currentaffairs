from flask import Flask, jsonify, request, render_template, session
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)

# ─── CONFIG ───────────────────────────────────────────────
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-change-in-prod')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL', 'sqlite:///psc_hub.db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


# ─── MODELS ───────────────────────────────────────────────

class User(db.Model):
    id        = db.Column(db.Integer, primary_key=True)
    name      = db.Column(db.String(100), nullable=False)
    email     = db.Column(db.String(120), unique=True, nullable=False)
    district  = db.Column(db.String(50))
    role      = db.Column(db.String(20), default='student')   # student | admin
    created   = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id, 'name': self.name, 'email': self.email,
            'district': self.district, 'role': self.role,
            'created': self.created.isoformat()
        }


class Question(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    text        = db.Column(db.Text, nullable=False)
    option_a    = db.Column(db.String(300), nullable=False)
    option_b    = db.Column(db.String(300), nullable=False)
    option_c    = db.Column(db.String(300), nullable=False)
    option_d    = db.Column(db.String(300), nullable=False)
    answer      = db.Column(db.String(1), nullable=False)  # A/B/C/D
    subject     = db.Column(db.String(100))
    difficulty  = db.Column(db.String(20), default='Medium')
    explanation = db.Column(db.Text)
    status      = db.Column(db.String(20), default='active')
    created     = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id, 'text': self.text,
            'option_a': self.option_a, 'option_b': self.option_b,
            'option_c': self.option_c, 'option_d': self.option_d,
            'answer': self.answer, 'subject': self.subject,
            'difficulty': self.difficulty, 'explanation': self.explanation,
            'status': self.status
        }


class Article(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    title       = db.Column(db.String(300), nullable=False)
    body        = db.Column(db.Text, nullable=False)
    category    = db.Column(db.String(50))
    tags        = db.Column(db.String(200))
    status      = db.Column(db.String(20), default='published')
    published   = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id, 'title': self.title, 'body': self.body,
            'category': self.category, 'tags': self.tags,
            'status': self.status, 'published': self.published.isoformat()
        }


class MockTest(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(200), nullable=False)
    target_post = db.Column(db.String(100))
    num_questions = db.Column(db.Integer, default=100)
    duration    = db.Column(db.Integer, default=75)  # minutes
    status      = db.Column(db.String(20), default='draft')
    attempts    = db.Column(db.Integer, default=0)
    created     = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id, 'name': self.name, 'target_post': self.target_post,
            'num_questions': self.num_questions, 'duration': self.duration,
            'status': self.status, 'attempts': self.attempts
        }


# ─── FRONTEND ROUTES ──────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


# ─── API: STATS ───────────────────────────────────────────

@app.route('/api/stats')
def stats():
    return jsonify({
        'users':     User.query.count(),
        'questions': Question.query.count(),
        'articles':  Article.query.count(),
        'tests':     MockTest.query.count(),
    })


# ─── API: QUESTIONS ───────────────────────────────────────

@app.route('/api/questions', methods=['GET'])
def get_questions():
    subject    = request.args.get('subject')
    difficulty = request.args.get('difficulty')
    limit      = int(request.args.get('limit', 10))
    q = Question.query.filter_by(status='active')
    if subject:    q = q.filter_by(subject=subject)
    if difficulty: q = q.filter_by(difficulty=difficulty)
    items = q.order_by(db.func.random()).limit(limit).all()
    return jsonify([i.to_dict() for i in items])

@app.route('/api/questions', methods=['POST'])
def add_question():
    d = request.json
    q = Question(
        text=d['text'], option_a=d['option_a'], option_b=d['option_b'],
        option_c=d['option_c'], option_d=d['option_d'], answer=d['answer'],
        subject=d.get('subject'), difficulty=d.get('difficulty', 'Medium'),
        explanation=d.get('explanation', '')
    )
    db.session.add(q); db.session.commit()
    return jsonify(q.to_dict()), 201

@app.route('/api/questions/<int:qid>', methods=['PUT'])
def update_question(qid):
    q = Question.query.get_or_404(qid)
    d = request.json
    for field in ['text','option_a','option_b','option_c','option_d',
                  'answer','subject','difficulty','explanation','status']:
        if field in d: setattr(q, field, d[field])
    db.session.commit()
    return jsonify(q.to_dict())

@app.route('/api/questions/<int:qid>', methods=['DELETE'])
def delete_question(qid):
    q = Question.query.get_or_404(qid)
    db.session.delete(q); db.session.commit()
    return jsonify({'deleted': qid})


# ─── API: ARTICLES ────────────────────────────────────────

@app.route('/api/articles', methods=['GET'])
def get_articles():
    category = request.args.get('category')
    q = Article.query.filter_by(status='published')
    if category: q = q.filter_by(category=category)
    items = q.order_by(Article.published.desc()).limit(20).all()
    return jsonify([i.to_dict() for i in items])

@app.route('/api/articles', methods=['POST'])
def add_article():
    d = request.json
    a = Article(
        title=d['title'], body=d['body'],
        category=d.get('category', 'General'),
        tags=d.get('tags', '')
    )
    db.session.add(a); db.session.commit()
    return jsonify(a.to_dict()), 201

@app.route('/api/articles/<int:aid>', methods=['DELETE'])
def delete_article(aid):
    a = Article.query.get_or_404(aid)
    db.session.delete(a); db.session.commit()
    return jsonify({'deleted': aid})


# ─── API: MOCK TESTS ─────────────────────────────────────

@app.route('/api/tests', methods=['GET'])
def get_tests():
    items = MockTest.query.order_by(MockTest.created.desc()).all()
    return jsonify([i.to_dict() for i in items])

@app.route('/api/tests', methods=['POST'])
def add_test():
    d = request.json
    t = MockTest(
        name=d['name'], target_post=d.get('target_post'),
        num_questions=d.get('num_questions', 100),
        duration=d.get('duration', 75)
    )
    db.session.add(t); db.session.commit()
    return jsonify(t.to_dict()), 201

@app.route('/api/tests/<int:tid>/publish', methods=['POST'])
def publish_test(tid):
    t = MockTest.query.get_or_404(tid)
    t.status = 'active'
    db.session.commit()
    return jsonify(t.to_dict())


# ─── API: USERS ───────────────────────────────────────────

@app.route('/api/users', methods=['GET'])
def get_users():
    items = User.query.order_by(User.created.desc()).all()
    return jsonify([i.to_dict() for i in items])

@app.route('/api/users', methods=['POST'])
def add_user():
    d = request.json
    u = User(name=d['name'], email=d['email'],
             district=d.get('district'), role=d.get('role', 'student'))
    db.session.add(u); db.session.commit()
    return jsonify(u.to_dict()), 201


# ─── SEED DATA ────────────────────────────────────────────

def seed_data():
    if Question.query.count() == 0:
        sample_questions = [
            Question(
                text="Who was the first Chief Minister of Kerala?",
                option_a="C. Achutha Menon", option_b="K. Karunakaran",
                option_c="E. M. S. Namboodiripad", option_d="Pattom Thanu Pillai",
                answer="C", subject="Kerala History", difficulty="Easy",
                explanation="EMS became the first CM after Kerala was formed on Nov 1, 1956."
            ),
            Question(
                text="Which Article of the Indian Constitution guarantees Right to Education?",
                option_a="Article 19", option_b="Article 21A",
                option_c="Article 32",  option_d="Article 44",
                answer="B", subject="Indian Polity", difficulty="Medium",
                explanation="Article 21A was inserted by the 86th Amendment Act, 2002."
            ),
            Question(
                text="Which river is known as the 'Periyar' in Kerala?",
                option_a="Bharathapuzha", option_b="Pamba",
                option_c="Chaliyar", option_d="Periyar",
                answer="D", subject="Kerala Geography", difficulty="Easy"
            ),
        ]
        db.session.add_all(sample_questions)

    if Article.query.count() == 0:
        sample_articles = [
            Article(
                title="Kerala Wins National Award for Best e-Governance Initiative 2025",
                body="The state's digital service delivery platform recognized by MeitY for citizen-centric approach.",
                category="Kerala", tags="LDC,VEO"
            ),
            Article(
                title="ISRO Successfully Launches NISAR Satellite",
                body="The joint NASA-ISRO SAR satellite aims to study Earth's surface changes.",
                category="Science & Tech", tags="All Posts"
            ),
        ]
        db.session.add_all(sample_articles)

    if MockTest.query.count() == 0:
        sample_tests = [
            MockTest(name="LDC Full Syllabus — Set A", target_post="Lower Division Clerk",
                     num_questions=100, duration=75, status='active', attempts=1204),
            MockTest(name="VEO Exam Mock — 2025", target_post="Village Extension Officer",
                     num_questions=75, duration=60, status='active', attempts=892),
        ]
        db.session.add_all(sample_tests)

    db.session.commit()


# ─── INIT ─────────────────────────────────────────────────

with app.app_context():
    db.create_all()
    seed_data()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
