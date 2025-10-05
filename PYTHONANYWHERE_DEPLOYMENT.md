# 🚀 PythonAnywhere Deployment Guide

## Complete Step-by-Step Deployment Instructions

This guide will help you deploy your Flask app with SQLite database to PythonAnywhere.

---

## 📋 Pre-Deployment Checklist

### ✅ What You Already Have
- [x] Flask application (`app.py`)
- [x] SQLite database system (`db_cache.py`)
- [x] Requirements file (`requirements.txt`)
- [x] Static files (CSS, JS)
- [x] Templates (HTML)
- [x] Environment variables (`.env`)

### ✅ What's New (Improvements Made)
- [x] Done button feature with database persistence
- [x] Mobile-responsive UI
- [x] Task completion tracking
- [x] Improved button styling (Yellow/Green)

---

## 🔧 Step 1: Prepare Your Files

### 1.1 Verify Requirements
```bash
# Make sure requirements.txt is complete
pip freeze > requirements_full.txt
# Compare with your requirements.txt
```

Your `requirements.txt` should include:
```
Flask==3.1.0
flask-cors==5.0.1
python-dotenv==1.0.1
pytz==2025.1
requests==2.32.3
google-generativeai==0.8.4
youtube-transcript-api==1.0.3
APScheduler==3.11.0
```

### 1.2 Check Environment Variables
Create `.env` file with your credentials:
```env
web_app=YOUR_GOOGLE_SHEETS_URL
GEMINI_API=YOUR_GEMINI_API_KEY
APP_ACCESS_CODE=YOUR_ACCESS_CODE
ADMIN_TOKEN=YOUR_ADMIN_TOKEN
```

⚠️ **Important**: Keep `.env` secure and don't commit to Git!

---

## 🌐 Step 2: Upload Files to PythonAnywhere

### Option A: Upload via Web Interface
1. Go to **Files** tab in PythonAnywhere
2. Navigate to `/home/yourusername/`
3. Create folder: `pythonAPIapp`
4. Upload all files:
   - `app.py`
   - `db_cache.py`
   - `requirements.txt`
   - `refresh_cache.py`
   - `.env` (create manually for security)
   - `static/` folder (all files)
   - `templates/` folder (all files)

### Option B: Upload via Git (Recommended)
```bash
# On PythonAnywhere console
cd ~
git clone https://github.com/GitKaran4723/pythonAPIapp.git
cd pythonAPIapp

# Create .env file manually
nano .env
# Paste your environment variables
# Press Ctrl+X, then Y, then Enter to save
```

---

## 📦 Step 3: Install Dependencies

### 3.1 Open PythonAnywhere Bash Console
1. Go to **Consoles** tab
2. Start a new **Bash** console

### 3.2 Create Virtual Environment
```bash
cd ~/pythonAPIapp
python3.10 -m venv venv
source venv/bin/activate
```

### 3.3 Install Requirements
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3.4 Verify Installation
```bash
pip list
# Should show all packages from requirements.txt
```

---

## 🗄️ Step 4: Initialize Database

### 4.1 Create data_cache Directory
```bash
cd ~/pythonAPIapp
mkdir -p data_cache
```

### 4.2 Test Database Initialization
```bash
python3 -c "import db_cache; db_cache.init_db(); print('✅ Database initialized!')"
```

### 4.3 Initial Cache Refresh (Optional)
```bash
# If you want to populate from Google Sheets immediately
python3 refresh_cache.py
```

### 4.4 Verify Database
```bash
python3 test_db.py
# Should show tables and row counts
```

---

## ⚙️ Step 5: Configure Web App

### 5.1 Create/Edit Web App
1. Go to **Web** tab in PythonAnywhere
2. Click **Add a new web app**
3. Choose **Manual configuration**
4. Select **Python 3.10**

### 5.2 Configure WSGI File
1. Click on **WSGI configuration file** link
2. Replace entire content with:

```python
# +++++++++++ FLASK +++++++++++
import sys
import os

# Add your project directory to the sys.path
project_home = '/home/yourusername/pythonAPIapp'
if project_home not in sys.path:
    sys.path = [project_home] + sys.path

# Load environment variables from .env file
from dotenv import load_dotenv
project_folder = os.path.expanduser(project_home)
load_dotenv(os.path.join(project_folder, '.env'))

# Import Flask app
from app import app as application

# IMPORTANT: Don't use app.run() in WSGI mode!
```

⚠️ **Replace `yourusername` with your PythonAnywhere username!**

### 5.3 Configure Virtual Environment
1. In **Web** tab, scroll to **Virtualenv** section
2. Enter: `/home/yourusername/pythonAPIapp/venv`
3. Click checkmark to save

### 5.4 Configure Static Files
1. In **Web** tab, scroll to **Static files** section
2. Add mapping:
   - **URL**: `/static/`
   - **Directory**: `/home/yourusername/pythonAPIapp/static`

---

## 🔄 Step 6: Configure Scheduled Tasks (Optional)

### 6.1 Set Up Hourly Cache Refresh
1. Go to **Tasks** tab
2. Create a **Scheduled task**
3. Enter command:
```bash
cd /home/yourusername/pythonAPIapp && source venv/bin/activate && python refresh_cache.py
```
4. Set schedule: **Hourly** or **Daily** (your choice)

### 6.2 Alternative: Manual Refresh
You can manually refresh via the admin endpoint:
```
https://yourusername.pythonanywhere.com/admin/refresh?t=YOUR_ADMIN_TOKEN
```

---

## 🚀 Step 7: Launch Your App

### 7.1 Reload Web App
1. Go to **Web** tab
2. Click green **Reload** button
3. Wait for reload to complete

### 7.2 Test Your App
Visit: `https://yourusername.pythonanywhere.com`

Should see your home page!

### 7.3 Test Routes
```
https://yourusername.pythonanywhere.com/
https://yourusername.pythonanywhere.com/schedule
https://yourusername.pythonanywhere.com/daily
https://yourusername.pythonanywhere.com/schedule.json
```

---

## 🧪 Step 8: Verify Everything Works

### 8.1 Check Logs
If something doesn't work:
1. Go to **Web** tab
2. Check **Error log** link
3. Check **Server log** link

### 8.2 Test Features
- [ ] Home page loads
- [ ] Monthly schedule shows data
- [ ] Daily schedule shows data
- [ ] Done buttons work (mark as done)
- [ ] Completed tasks show green "✓ Completed"
- [ ] Task completions persist after refresh
- [ ] Mobile view looks good

### 8.3 Test Database Persistence
1. Mark a few tasks as done
2. Reload page - should still show as done ✅
3. Run cache refresh (if scheduled or manual)
4. Tasks should STILL show as done ✅

---

## 🗄️ Database Migration (If Upgrading)

### If You Have Existing Data
If you're upgrading from a previous version with CSV files:

#### Option 1: Fresh Start
```bash
# Just initialize new database
python3 refresh_cache.py
# All data will be fresh from Google Sheets
```

#### Option 2: Preserve Old Completions
If you had the old CSV system and want to preserve completions:
```bash
# Unfortunately, old CSV system didn't track completions
# You'll need to start fresh with the new SQLite system
```

### Backup Your Database
```bash
# Create backup
cp data_cache/schedule.db data_cache/schedule.db.backup

# To restore if needed
cp data_cache/schedule.db.backup data_cache/schedule.db
```

---

## 🔐 Security Checklist

- [ ] `.env` file created with your credentials
- [ ] `.env` is NOT in Git repository
- [ ] `ADMIN_TOKEN` is set to a secure value
- [ ] `APP_ACCESS_CODE` is set
- [ ] CORS origins configured in `app.py` (update domain)

### Update CORS Settings
Edit `app.py` line 18:
```python
# Change this to your domain
CORS(app, origins=["https://yourusername.pythonanywhere.com"])
```

---

## 📱 Mobile Testing

After deployment, test on mobile:
1. Visit site on your phone
2. Check `/daily` page
3. Verify:
   - Cards are full-width ✅
   - Buttons are full-width ✅
   - Text is readable ✅
   - No horizontal scrolling ✅

---

## 🐛 Troubleshooting

### Problem: "Something went wrong :("
**Solution**: Check error log in Web tab

### Problem: "Module not found"
**Solution**: 
```bash
cd ~/pythonAPIapp
source venv/bin/activate
pip install -r requirements.txt
```

### Problem: Database not found
**Solution**:
```bash
cd ~/pythonAPIapp
mkdir -p data_cache
python3 refresh_cache.py
```

### Problem: Static files not loading
**Solution**: 
- Verify static files mapping in Web tab
- Check path: `/home/yourusername/pythonAPIapp/static`

### Problem: Done buttons not working
**Solution**:
- Check browser console for errors (F12)
- Verify `/api/task/complete` endpoint works
- Check database permissions

### Problem: Task completions not persisting
**Solution**:
```bash
# Check if database is writable
ls -la data_cache/schedule.db

# Should show rw-r--r-- permissions
# If not, fix with:
chmod 644 data_cache/schedule.db
```

---

## 🔄 Updating Your App

### When You Make Changes Locally
1. **Test locally first**
2. **Push to Git** (if using Git)
3. **Pull on PythonAnywhere**:
```bash
cd ~/pythonAPIapp
git pull origin main
```
4. **Reload web app** in Web tab

### Or Upload Changed Files
1. Go to **Files** tab
2. Navigate to changed file
3. Click edit or upload new version
4. **Reload web app** in Web tab

---

## 📊 Performance Tips

### 1. Database Optimization
```python
# Already implemented:
# - Indexed date column for fast queries
# - Separate completion table
# - Efficient merging
```

### 2. Caching
```python
# Already implemented:
# - Data cached in SQLite
# - Scheduled refresh (optional)
# - On-demand refresh via admin endpoint
```

### 3. Static Files
- Static files served directly by PythonAnywhere
- No Python overhead
- Fast delivery

---

## 🎯 Quick Reference

### Important Paths
```
App directory: /home/yourusername/pythonAPIapp
Virtual env: /home/yourusername/pythonAPIapp/venv
Database: /home/yourusername/pythonAPIapp/data_cache/schedule.db
Logs: Check Web tab → Error log, Server log
```

### Important URLs
```
Home: https://yourusername.pythonanywhere.com/
Schedule: https://yourusername.pythonanywhere.com/schedule
Daily: https://yourusername.pythonanywhere.com/daily
Admin: https://yourusername.pythonanywhere.com/admin/refresh?t=TOKEN
```

### Important Commands
```bash
# Activate venv
source ~/pythonAPIapp/venv/bin/activate

# Refresh cache
python refresh_cache.py

# Check database
python test_db.py

# View logs
tail -f /var/log/yourusername.pythonanywhere.com.error.log
```

---

## ✅ Deployment Complete!

Once everything is working:
- ✅ App is live on PythonAnywhere
- ✅ Database is persistent
- ✅ Done buttons work
- ✅ Mobile UI is responsive
- ✅ Task completions survive refreshes
- ✅ Scheduled tasks running (optional)

**Your app is now live and ready to use!** 🎉

---

## 📞 Need Help?

### PythonAnywhere Forums
- https://www.pythonanywhere.com/forums/

### Your Documentation
- `MIGRATION_SUMMARY.md` - SQLite migration
- `DONE_BUTTON_FEATURE.md` - Done button docs
- `MOBILE_UI_GUIDE.md` - Mobile improvements
- `UI_IMPROVEMENTS.md` - Button styling

**Happy deploying!** 🚀
