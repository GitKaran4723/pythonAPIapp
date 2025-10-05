# 📋 PythonAnywhere Deployment Cheat Sheet

## 🎯 THE GOLDEN RULE

```
┌────────────────────────────────────┐
│  1st Deployment:  git clone  ✅    │
│  All Updates:     git pull   ✅    │
│  NEVER:           rm + clone ❌    │
└────────────────────────────────────┘
```

---

## 🚀 First Time Setup (Do Once)

### Local Machine:
```powershell
git add .
git commit -m "Initial commit"
git push origin main
```

### PythonAnywhere:
```bash
# Clone repo
git clone https://github.com/GitKaran4723/pythonAPIapp.git
cd pythonAPIapp

# Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Setup environment
nano .env  # Add API keys

# Initialize database
python3 -c "import db_cache; db_cache.init_db()"
python3 refresh_cache.py

# Configure WSGI on dashboard
# Reload web app
```

---

## 🔄 Update Code (Do Always)

### Local Machine:
```powershell
# Edit code
git add .
git commit -m "Update message"
git push origin main
```

### PythonAnywhere:
```bash
cd ~/pythonAPIapp
git pull origin main
# Reload web app from dashboard
```

**That's it! Database stays safe!** ✅

---

## 🛡️ Safety Checks

```bash
# Verify database exists
ls -lh data_cache/schedule.db

# Count completions
sqlite3 data_cache/schedule.db "SELECT COUNT(*) FROM task_completions;"

# Check what's tracked
git ls-files | grep data_cache  # Should be empty

# Verify gitignore
git check-ignore -v data_cache/schedule.db
```

---

## 🆘 Emergency Backup

```bash
# Before risky operations
cp data_cache/schedule.db ~/backup_$(date +%Y%m%d).db

# Restore if needed
cp ~/backup_*.db data_cache/schedule.db
```

---

## ❌ Common Mistakes

### DON'T DO THIS:
```bash
rm -rf pythonAPIapp/  # Deletes database! 💀
git clone https://...
```

### DO THIS INSTEAD:
```bash
cd pythonAPIapp  # Go inside
git pull origin main  # Update in place
```

---

## 📞 Quick Help

| Problem | Solution |
|---------|----------|
| Database missing | Restore from backup or run `refresh_cache.py` |
| Code not updating | Check you ran `git pull` and reloaded web app |
| Merge conflicts | `git stash` → `git pull` → `git stash pop` |
| Web app errors | Check error log on Web tab |

---

## 🎯 Remember

**Git pull = Safe updates**
**Git clone = First time only**
**Database = Protected by .gitignore**

---

**📚 Full guides available:**
- README_DEPLOYMENT.md (complete guide)
- GIT_CLONE_VS_PULL.md (detailed comparison)
- QUICK_GIT_GUIDE.md (visual guide)
- update_app.sh (automated script)
