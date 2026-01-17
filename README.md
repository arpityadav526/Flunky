# FLUNKY - Task Management CLI

A beautiful command-line task manager with FastAPI backend.

## Features
- 🔐 Secure authentication (JWT)
- 📝 Create, update, delete tasks
- 📊 Beautiful terminal tables
- 💾 Persistent login
- 🎨 Rich terminal UI

## Installation

1. Clone the repo
2. Install: `pip install -e .`
3. Start backend: `uvicorn backend.main:app --reload`
4. Use CLI: `flunky --help`

## Quick Start

\`\`\`bash
# Register
flunky register

# Login
flunky login

# Create a task
flunky task create -t "Learn Python" -d "Complete tutorial"

# List tasks
flunky task list

# Mark complete
flunky task complete 1
\`\`\`

## Tech Stack
- **Backend:** FastAPI, SQLAlchemy, JWT
- **CLI:** Typer, Rich, HTTPX
- **Database:** SQLite
```

---

### **Step 14: Testing & Bug Fixes** ⏱️ ~15-20 mins

**Full test flow:**

1. ✅ Register new user
2. ✅ Login
3. ✅ Create 3-5 tasks
4. ✅ List all tasks
5. ✅ Show one task
6. ✅ Update task (both modes)
7. ✅ Complete a task
8. ✅ Filter by completed
9. ✅ Delete a task
10. ✅ Logout
11. ✅ Try task command (should fail - not logged in)
12. ✅ Login again (token should load)

**Edge cases to test:**
- Try to access non-existent task ID
- Try to access another user's task (register 2nd user)
- Try empty title/description
- Try special characters in inputs
- Stop backend mid-operation

---

## 🎁 Optional Enhancements (If You Want to Go Further):

### **Nice-to-Have Features:**

1. **Task Priorities** 
   - Add priority field (High/Medium/Low)
   - Color code in table

2. **Due Dates**
   - Add deadline field
   - Show overdue tasks in red

3. **Task Search**
   - `flunky task search "keyword"`

4. **Export Tasks**
   - `flunky task export tasks.json`

5. **Task Statistics**
   - `flunky stats` - Show completion rate, total tasks, etc.

6. **Spinner/Progress Indicators**
   - Show loading spinner during API calls

7. **Config Commands**
   - `flunky config show` - Show current settings
   - `flunky config set-backend <url>` - Change backend URL

---

## 📊 Current Project Status:
```
✅ Backend API          - COMPLETE
✅ Authentication       - COMPLETE
✅ Token Storage        - COMPLETE  
✅ CLI Commands         - COMPLETE
⚠️  Error Handling      - NEEDS POLISH
⚠️  Installation Setup  - NEEDS SETUP.PY
⚠️  Documentation       - NEEDS README
⚠️  Full Testing        - NEEDS TESTING
