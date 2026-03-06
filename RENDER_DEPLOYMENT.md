# Deployment Guide for Render

## Prerequisites
- GitHub/GitLab account with your repository
- MySQL database (either local, Aiven, or another provider)
- Render account (https://render.com)

## Step-by-Step Instructions

### 1. Prepare Your Code
- ✅ `main.py` updated to use dynamic PORT
- ✅ `requirements.txt` is in place
- ✅ `.gitignore` configured
- ✅ `Procfile` created

### 2. Database Setup
Before deploying, you need a MySQL database accessible from the internet:

**Option A: Use Aiven (Free tier available)**
- Sign up at https://aiven.io
- Create a MySQL database
- Get your connection string: `mysql+pymysql://user:password@hostname:port/dbname`

**Option B: Use Railway.app or Supabase with MySQL support**

**Option C: Keep using local MySQL (NOT recommended for production)**
- Database must be publicly accessible
- Not secure for production

### 3. Push to GitHub
```powershell
git init
git add .
git commit -m "Initial deployment setup"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/vcomplaint-backend.git
git push -u origin main
```

### 4. Deploy on Render
1. Go to https://dashboard.render.com/
2. Click **"New +"** → **"Web Service"**
3. Click **"Connect a repository"** and select your backend repo
4. Configure:
   - **Name**: `complaint-backend`
   - **Environment**: `Python 3.10`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Select Free or Paid

5. Click **"Advanced"** and add Environment Variables:
   - **Key**: `DATABASE_URL`
   - **Value**: Your MySQL connection string
   - Click **"Add Environment Variable"**

6. Click **"Create Web Service"** and wait for deployment (2-5 minutes)

### 5. Important Security Fixes
Once deployed, update these in main.py for production:

**1. Remove hardcoded password from database URL:**
```python
# Current (INSECURE):
DEFAULT_DB_URL = "mysql+pymysql://root:Vikasreddy%402002@localhost:3306/complaint_db"

# Change to:
DEFAULT_DB_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")
```

**2. Change CORS settings:**
```python
# Current (INSECURE):
allow_origins=["*"]

# Change to:
allow_origins=["https://youryomain.com"]
```

**3. Add JWT authentication** (highly recommended)

### 6. View Logs
- Go to your service on Render dashboard
- Click **"Logs"** tab to see deployment and runtime logs
- Click **"Events"** to see deployment history

### 7. Your API URL
After deployment, your API will be available at:
```
https://complaint-backend.onrender.com
```

Access endpoints like:
- `https://complaint-backend.onrender.com/signup`
- `https://complaint-backend.onrender.com/login`
- `https://complaint-backend.onrender.com/admin/users`

## Troubleshooting

**Service won't start:**
- Check logs in Render dashboard
- Verify DATABASE_URL environment variable is set
- Ensure database is accessible from the internet

**Database connection errors:**
- Test connection string locally first
- Check firewall rules allow external connections
- Verify MySQL user has proper permissions

**Port binding errors:**
- Ensure you're using `$PORT` environment variable
- Check `uvicorn` is installed in requirements.txt

## Production Checklist
- [ ] Remove hardcoded database credentials
- [ ] Use environment variables for all sensitive data
- [ ] Restrict CORS origins
- [ ] Add JWT token authentication
- [ ] Enable HTTPS (Render provides this automatically)
- [ ] Set up database backups
- [ ] Monitor application logs regularly
