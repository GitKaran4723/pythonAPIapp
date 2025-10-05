# 📚 Three-Stage Task Completion Feature

## 🎯 Overview

This feature replaces the single "Mark as Done" button for daily tasks with **three separate tracking buttons**:

1. **First Read** - Initial reading/understanding of the material
2. **Notes** - Taking notes or creating summaries
3. **Revision** - Reviewing and reinforcing the content

Each task now tracks **3 independent stages** instead of a single completion state.

---

## ✨ Key Features

### 📊 Progress Calculation
- **Old system**: Progress = (completed_tasks / total_tasks) × 100
- **New system**: Progress = (completed_stages / total_stages) × 100
  - Where `total_stages = num_tasks × 3`
  - Example: 10 tasks = 30 total stages

### 🎨 Visual Indicators
- **Pending Stage**: Yellow button - "First Read" / "Notes" / "Revision"
- **Completed Stage**: Green button with ✓ - "✓ First Read" / "✓ Notes" / "✓ Revision"
- **All Stages Done**: Task title gets strikethrough + opacity 0.7

### 📱 Responsive Design
- **Mobile**: Three buttons stack vertically, full width
- **Desktop**: Three buttons displayed horizontally, side by side

---

## 🗄️ Database Schema

### Updated `task_completions` Table

```sql
CREATE TABLE task_completions (
    task_id TEXT PRIMARY KEY,
    task_type TEXT NOT NULL,
    completed INTEGER NOT NULL DEFAULT 0,     -- For monthly tasks
    first_read INTEGER NOT NULL DEFAULT 0,    -- NEW: Stage 1
    notes INTEGER NOT NULL DEFAULT 0,         -- NEW: Stage 2
    revision INTEGER NOT NULL DEFAULT 0,      -- NEW: Stage 3
    completed_at TEXT,
    month_year TEXT
)
```

### Migration
- Existing daily tasks marked "done" are automatically migrated to have all 3 stages complete
- Monthly tasks continue using the single `completed` field
- Backup created before migration: `schedule.db.backup_YYYYMMDD_HHMMSS`

---

## 🔌 API Endpoints

### 1. Mark Stage Complete (NEW)

**Endpoint**: `POST /api/task/stage`

**Request Body**:
```json
{
  "task_id": "123",
  "task_type": "daily",
  "stage": "first_read",  // or "notes" or "revision"
  "completed": true,       // or false to unmark
  "month_year": "oct_2025"
}
```

**Response**:
```json
{
  "success": true,
  "task_id": "123",
  "stage": "first_read",
  "completed": true
}
```

### 2. Get Task Progress (NEW)

**Endpoint**: `GET /api/task/progress?date=2025-10-05`

**Response**:
```json
{
  "total_tasks": 10,
  "total_stages": 30,
  "completed_stages": 18,
  "percentage": 60.0
}
```

### 3. Mark Task Complete (Monthly - Unchanged)

**Endpoint**: `POST /api/task/complete`

Still works for monthly tasks with single completion state.

---

## 🎨 Frontend Implementation

### JavaScript (daily.js)

#### Data Structure
```javascript
{
  id: "task_123",
  task_name: "Learn Python",
  first_read: true,    // 1 or 0 from database
  notes: false,        // 1 or 0 from database
  revision: false      // 1 or 0 from database
}
```

#### Button Creation
```javascript
function createStageButton(stage, isCompleted, taskId, label) {
  const btn = document.createElement("button");
  
  if (isCompleted) {
    btn.className = "stage-btn completed ...";
    btn.innerHTML = `<span class="text-sm">✓</span> ${label}`;
  } else {
    btn.className = "stage-btn pending ...";
    btn.textContent = label;
  }
  
  btn.onclick = () => toggleTaskStage(taskId, stage, isCompleted);
  return btn;
}
```

#### Progress Calculation
```javascript
function renderStats(source) {
  const totalStages = source.length * 3;
  
  let completedStages = 0;
  source.forEach(it => {
    if (it.first_read) completedStages++;
    if (it.notes) completedStages++;
    if (it.revision) completedStages++;
  });
  
  const percentage = Math.round((completedStages / totalStages) * 100);
}
```

### CSS (daily.css)

#### Mobile Layout (< 768px)
```css
.stage-buttons {
  flex-direction: column;  /* Stack vertically */
  gap: 8px;
}

.stage-btn {
  width: 100%;              /* Full width */
  padding: 12px 16px;
}
```

#### Desktop Layout (≥ 768px)
```css
.stage-buttons {
  flex-direction: row;      /* Side by side */
  gap: 6px;
}

.stage-btn {
  width: auto;              /* Fit content */
  padding: 6px 12px;
}
```

---

## 🧪 Testing

### Run Tests
```bash
python test_three_stage_feature.py
```

### Tests Cover:
1. ✅ Database schema validation
2. ✅ Marking individual stages
3. ✅ Progress percentage calculation
4. ✅ Merging completion status with sheet data

### Expected Output:
```
============================================================
TEST SUMMARY
============================================================
Total tests: 4
Passed: 4 ✅
Failed: 0 ✗

🎉 ALL TESTS PASSED! 🎉
```

---

## 📈 Example Progress Calculation

### Scenario: 5 Daily Tasks

| Task | First Read | Notes | Revision | Total Stages |
|------|-----------|-------|----------|--------------|
| Task 1 | ✓ | ✓ | ✓ | 3/3 |
| Task 2 | ✓ | ✓ | ✗ | 2/3 |
| Task 3 | ✓ | ✗ | ✗ | 1/3 |
| Task 4 | ✗ | ✗ | ✗ | 0/3 |
| Task 5 | ✓ | ✓ | ✓ | 3/3 |

**Calculation**:
- Total Tasks: 5
- Total Stages: 5 × 3 = **15 stages**
- Completed Stages: 3 + 2 + 1 + 0 + 3 = **9 stages**
- **Progress: (9 / 15) × 100 = 60%**

### Display:
- **Total**: 5 tasks
- **Done**: 2 tasks (only Task 1 and Task 5 have all 3 stages)
- **Pending**: 3 tasks
- **Progress**: 60% (based on stages, not tasks)

---

## 🎯 User Workflow

### Typical Study Flow

1. **First Read** 📖
   - Click "First Read" button (yellow)
   - Button turns green: "✓ First Read"
   - Progress increases by ~33% for that task

2. **Notes** ✍️
   - Click "Notes" button (yellow)
   - Button turns green: "✓ Notes"
   - Progress increases by another ~33%

3. **Revision** 🔄
   - Click "Revision" button (yellow)
   - Button turns green: "✓ Revision"
   - All three stages complete!
   - Task title gets strikethrough
   - Status badge changes to "All Done"
   - Progress reaches 100% for that task

### Undo a Stage
- Click any green button to unmark that stage
- Button turns back to yellow
- Progress decreases accordingly

---

## 🔄 Migration Guide

### First Time Setup
```bash
# 1. Run migration
python migrate_to_three_stage.py

# 2. Verify migration
python test_three_stage_feature.py

# 3. Start application
python app.py
```

### What Gets Migrated
- **Daily tasks** previously marked "done" → All 3 stages set to complete
- **Monthly tasks** → Unchanged (still use single completion field)
- **Database backup** → Automatically created before migration

### Rollback (if needed)
```bash
# Copy backup file
cp data_cache/schedule.db.backup_YYYYMMDD_HHMMSS data_cache/schedule.db
```

---

## 📱 Screenshots

### Mobile View
```
┌─────────────────────────────────┐
│ Learn Python Basics             │
│ 2/3 stages • Week 1 • Goal: M1  │
├─────────────────────────────────┤
│ [✓ First Read      ] (Green)    │
│ [✓ Notes           ] (Green)    │
│ [Revision          ] (Yellow)   │
└─────────────────────────────────┘
```

### Desktop View
```
┌────────────────────────────────────────────────────────────┐
│ Learn Python Basics                                        │
│ 2/3 stages • Week 1 • Goal: M1                             │
│                      [✓ First Read] [✓ Notes] [Revision]   │
│                         (Green)      (Green)   (Yellow)    │
└────────────────────────────────────────────────────────────┘
```

---

## 🎓 Benefits

### For Students
- ✅ **Better tracking** of study progress
- ✅ **More granular** completion states
- ✅ **Encourages systematic** learning approach
- ✅ **Realistic progress** percentage (not inflated)

### Example:
- **Old system**: Read 1 chapter = 100% done ❌
- **New system**: 
  - First Read = 33% ✅
  - Made Notes = 66% ✅
  - Revised = 100% ✅

---

## 🔧 Configuration

### Customize Stage Names
Edit `static/js/daily.js`:

```javascript
// Change labels here
buttonsWrapper.appendChild(createStageButton('first_read', it.first_read, it.id, 'Read'));
buttonsWrapper.appendChild(createStageButton('notes', it.notes, it.id, 'Write'));
buttonsWrapper.appendChild(createStageButton('revision', it.revision, it.id, 'Review'));
```

### Customize Colors
Edit `static/css/daily.css`:

```css
/* Pending buttons */
.stage-btn.pending {
  background: #f59e0b;  /* Change to your color */
}

/* Completed buttons */
.stage-btn.completed {
  background: #10b981;  /* Change to your color */
}
```

---

## 📝 Monthly Tasks

**Note**: Monthly tasks are **NOT affected** by this feature!

- Monthly tasks continue using single "Mark as Done" button
- Only **daily tasks** have three-stage tracking
- This is intentional - monthly goals are broader objectives

---

## 🚀 Deployment

### Local Development
```bash
python app.py
# Visit: http://localhost:5000/daily
```

### PythonAnywhere
1. Push code to GitHub (database excluded by `.gitignore`)
2. On server: `cd ~/pythonAPIapp && git pull`
3. Run migration: `python migrate_to_three_stage.py`
4. Reload web app from dashboard

**Important**: Run migration script on the server to update the database!

---

## 🐛 Troubleshooting

### Issue: "No column named first_read"
**Solution**: Run migration script
```bash
python migrate_to_three_stage.py
```

### Issue: Buttons not appearing
**Solution**: Clear browser cache and hard refresh (Ctrl+Shift+R)

### Issue: Progress stuck at 0%
**Solution**: Check browser console for JavaScript errors

### Issue: All stages auto-complete
**Solution**: Check database - old "completed" field might be set
```bash
sqlite3 data_cache/schedule.db
SELECT * FROM task_completions WHERE task_id = 'daily_XXX';
```

---

## 📚 Files Modified

### Backend
- ✅ `db_cache.py` - Added three-stage columns and functions
- ✅ `app.py` - Added `/api/task/stage` endpoint

### Frontend
- ✅ `static/js/daily.js` - Three-button rendering
- ✅ `static/css/daily.css` - Responsive button styles

### Testing
- ✅ `migrate_to_three_stage.py` - Database migration script
- ✅ `test_three_stage_feature.py` - Comprehensive test suite

### Documentation
- ✅ `THREE_STAGE_FEATURE.md` - This file!

---

## 🎉 Summary

Your daily tasks now support **three independent completion stages**:
1. **First Read** 📖
2. **Notes** ✍️
3. **Revision** 🔄

This gives you **more accurate progress tracking** and encourages a **systematic learning approach**!

**Progress = (completed_stages / total_stages) × 100**

Where each task contributes 3 stages to the total! 🚀

---

## 💡 Future Enhancements

Potential additions:
- [ ] Time tracking per stage
- [ ] Stage completion history/analytics
- [ ] Custom stage names per task
- [ ] Stage-specific notes/comments
- [ ] Reminders for incomplete stages
- [ ] Export stage completion report

---

**Happy Learning! 📚✨**
