#!/bin/bash
# PythonAnywhere Update Script
# Save this as: update_app.sh
# Make executable: chmod +x update_app.sh
# Run with: ./update_app.sh

echo "╔════════════════════════════════════════════════════╗"
echo "║  PythonAnywhere App Updater                        ║"
echo "║  Safe code updates without losing database         ║"
echo "╚════════════════════════════════════════════════════╝"
echo ""

# Configuration
APP_DIR="$HOME/pythonAPIapp"
BACKUP_DIR="$HOME/backups"
DB_PATH="$APP_DIR/data_cache/schedule.db"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if app directory exists
if [ ! -d "$APP_DIR" ]; then
    echo -e "${RED}❌ Error: $APP_DIR not found!${NC}"
    echo "Run this for first time setup:"
    echo "  git clone https://github.com/GitKaran4723/pythonAPIapp.git"
    exit 1
fi

# Navigate to app directory
cd "$APP_DIR" || exit 1
echo -e "${GREEN}✅ Changed to app directory${NC}"
echo "   Location: $APP_DIR"
echo ""

# Check if database exists
if [ -f "$DB_PATH" ]; then
    DB_SIZE=$(du -h "$DB_PATH" | cut -f1)
    echo -e "${GREEN}✅ Database found${NC}"
    echo "   Size: $DB_SIZE"
    
    # Count completions
    COMPLETION_COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM task_completions;" 2>/dev/null || echo "unknown")
    echo "   Completions: $COMPLETION_COUNT"
    echo ""
    
    # Create backup
    mkdir -p "$BACKUP_DIR"
    BACKUP_FILE="$BACKUP_DIR/schedule_$(date +%Y%m%d_%H%M%S).db"
    echo -e "${YELLOW}💾 Creating backup...${NC}"
    cp "$DB_PATH" "$BACKUP_FILE"
    echo "   Backup saved: $BACKUP_FILE"
    echo ""
else
    echo -e "${YELLOW}⚠️  No database found (will be created on first run)${NC}"
    echo ""
fi

# Show current status
echo -e "${YELLOW}📊 Current status:${NC}"
git log -1 --oneline
echo ""

# Pull latest code
echo -e "${YELLOW}📥 Pulling latest code from GitHub...${NC}"
git pull origin main

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Code updated successfully!${NC}"
    echo ""
    
    # Show what changed
    echo -e "${YELLOW}📋 Recent changes:${NC}"
    git log -1 --stat
    echo ""
    
    # Verify database still exists
    if [ -f "$DB_PATH" ]; then
        NEW_COMPLETION_COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM task_completions;" 2>/dev/null || echo "unknown")
        if [ "$COMPLETION_COUNT" = "$NEW_COMPLETION_COUNT" ]; then
            echo -e "${GREEN}✅ Database verified - completions intact!${NC}"
            echo "   Completions: $NEW_COMPLETION_COUNT (unchanged)"
        else
            echo -e "${YELLOW}⚠️  Completion count changed${NC}"
            echo "   Before: $COMPLETION_COUNT"
            echo "   After: $NEW_COMPLETION_COUNT"
        fi
    fi
    echo ""
    
    # Reminder
    echo -e "${YELLOW}📝 Next steps:${NC}"
    echo "   1. Go to PythonAnywhere Dashboard"
    echo "   2. Click 'Web' tab"
    echo "   3. Click 'Reload' button"
    echo ""
    echo -e "${GREEN}🎉 Update complete!${NC}"
    
else
    echo ""
    echo -e "${RED}❌ Error during git pull${NC}"
    echo "Check for conflicts or network issues"
    exit 1
fi

# Clean old backups (keep last 7 days)
echo ""
echo -e "${YELLOW}🧹 Cleaning old backups...${NC}"
find "$BACKUP_DIR" -name "schedule_*.db" -mtime +7 -delete 2>/dev/null
echo "   Kept last 7 days of backups"
echo ""

echo "═══════════════════════════════════════════════════"
echo "Update completed at: $(date)"
echo "═══════════════════════════════════════════════════"
