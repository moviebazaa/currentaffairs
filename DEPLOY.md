# 🚀 PSC Kerala Hub — Deployment Guide
## GitHub → Koyeb (Python Flask Backend)

---

## 📁 Project Structure

```
psc-kerala-hub/
├── app.py                 ← Flask backend (API + serves frontend)
├── requirements.txt       ← Python dependencies
├── Procfile               ← Koyeb/gunicorn startup command
├── .env.example           ← Environment variable template
├── .gitignore
└── templates/
    └── index.html         ← Full PSC Hub frontend
```

---

## STEP 1 — Set Up Locally

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy env file
cp .env.example .env

# Run locally
python app.py
# Open: http://localhost:5000
```

---

## STEP 2 — Push to GitHub

```bash
# Initialize git repo
git init
git add .
git commit -m "Initial commit: PSC Kerala Hub"

# Create repo on GitHub (github.com → New repository → psc-kerala-hub)
# Then connect and push:
git remote add origin https://github.com/YOUR_USERNAME/psc-kerala-hub.git
git branch -M main
git push -u origin main
```

---

## STEP 3 — Deploy on Koyeb

1. Go to **https://app.koyeb.com** → Sign up / Log in

2. Click **"Create Service"** → Choose **"GitHub"**

3. Connect your GitHub account and select **psc-kerala-hub** repo

4. Koyeb auto-detects Python. Set these settings:
   - **Build command:** `pip install -r requirements.txt`
   - **Run command:** `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2`
   - **Port:** `8000` (Koyeb default)

5. Add **Environment Variables** in Koyeb dashboard:
   ```
   SECRET_KEY     = your-random-secret-key-here
   DATABASE_URL   = (leave empty for SQLite, or add PostgreSQL URL)
   ```

6. Click **Deploy** — Koyeb builds and deploys automatically!

7. Your site goes live at: `https://your-app-name.koyeb.app`

---

## STEP 4 — Add a PostgreSQL Database (Optional but Recommended)

SQLite works for testing. For production, use a free PostgreSQL service:

### Option A: Neon (Free Tier — Recommended)
1. Go to **https://neon.tech** → Create account
2. Create a new project → Copy the **connection string**
3. It looks like: `postgresql://user:pass@ep-xxx.us-east-2.aws.neon.tech/neondb`
4. Add it as `DATABASE_URL` in Koyeb environment variables

### Option B: Supabase (Free Tier)
1. Go to **https://supabase.com** → Create project
2. Settings → Database → Copy **Connection string (URI)**
3. Add as `DATABASE_URL` in Koyeb

---

## STEP 5 — Auto-Deploy on Git Push

Once connected, every `git push` to `main` triggers a new Koyeb deployment automatically.

```bash
# Make a change, then:
git add .
git commit -m "Added new questions"
git push
# Koyeb redeploys automatically ✅
```

---

## 🔑 API Endpoints Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/stats` | Dashboard stats |
| GET | `/api/questions?subject=&limit=` | Get quiz questions |
| POST | `/api/questions` | Add a question |
| PUT | `/api/questions/<id>` | Update a question |
| DELETE | `/api/questions/<id>` | Delete a question |
| GET | `/api/articles?category=` | Get articles |
| POST | `/api/articles` | Publish an article |
| DELETE | `/api/articles/<id>` | Delete an article |
| GET | `/api/tests` | Get mock tests |
| POST | `/api/tests` | Create a test |
| POST | `/api/tests/<id>/publish` | Publish a draft test |
| GET | `/api/users` | Get all users |
| POST | `/api/users` | Add a user |

---

## 🛠️ What to Build Next

- [ ] User login/register with JWT tokens
- [ ] Password hashing with bcrypt
- [ ] Quiz score tracking per user
- [ ] WhatsApp daily quiz bot integration
- [ ] Malayalam language support
- [ ] Admin auth middleware (protect `/api/` routes)
- [ ] PDF syllabus upload and management
- [ ] Email notifications for new tests

---

## ❓ Troubleshooting

**Port error on Koyeb?**
→ Make sure Procfile uses `$PORT` not a hardcoded port.

**Database not persisting?**
→ SQLite files reset on Koyeb redeploy. Use PostgreSQL (Neon/Supabase) for persistence.

**Static files not loading?**
→ Put CSS/JS in `static/` folder and reference with `{{ url_for('static', filename='...') }}` in Flask templates.
