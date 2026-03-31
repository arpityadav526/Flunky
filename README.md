# FLUNKY – Full-Stack Task Management CLI

FLUNKY is a production-ready task management system built with a FastAPI backend and a powerful CLI interface. It enables developers to manage tasks efficiently directly from the terminal with secure authentication, clean UI, and automated workflows.

---

## 🚀 Features

### 🔐 Authentication

* JWT-based secure authentication
* Password hashing using bcrypt
* Persistent login via local token storage

### 📝 Task Management

* Create, update, delete tasks
* Mark tasks as complete
* Filter tasks by status
* User-specific task isolation

### 💻 CLI Experience

* Built with Typer + Rich
* Interactive prompts + command-line arguments (dual mode)
* Beautiful tables, panels, and colored output

### ⚙️ Backend (FastAPI)

* 7 REST API endpoints
* Dependency injection with `Depends`
* Pydantic validation
* SQLAlchemy ORM

### 🧪 Testing

* Pytest-based test suite
* Covers authentication and task workflows
* Includes edge cases (invalid login, unauthorized access, etc.)

### 🐳 Docker Support

* Lightweight containerized backend
* Optimized image size (~220MB)
* Ready for deployment

### 🔄 CI/CD (GitHub Actions)

* Automated testing on every push and PR
* Docker image build validation
* Ensures production stability

---

## 🏗️ Architecture

```
flunky/
├── backend/        # FastAPI backend
├── cli/            # CLI interface
├── tests/          # pytest test suite
├── Dockerfile
├── requirements.txt
└── .github/workflows/   # CI/CD pipelines
```

---

## 🛠️ Tech Stack

* **Backend:** FastAPI, SQLAlchemy, Pydantic
* **Authentication:** JWT (python-jose), bcrypt
* **CLI:** Typer, Rich, HTTPX
* **Database:** SQLite (local), PostgreSQL-ready
* **Testing:** Pytest, pytest-cov
* **DevOps:** Docker, GitHub Actions

---

## ⚡ Installation

### 1. Clone the repository

```bash
git clone https://github.com/your-username/flunky.git
cd flunky
```

### 2. Create virtual environment

```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
pip install -e .
```

---

## ▶️ Running the Application

### Start backend

```bash
uvicorn backend.main:app --reload
```

API Docs:
http://127.0.0.1:8000/docs

---

## 💻 CLI Usage

### Register

```bash
flunky register
```

### Login

```bash
flunky login
```

### Create task

```bash
flunky task create -t "Learn FastAPI" -d "Build backend project"
```

### List tasks

```bash
flunky task list
```

### Complete task

```bash
flunky task complete 1
```

### Delete task

```bash
flunky task delete 1
```

---

## 🧪 Running Tests

```bash
pytest --cov=backend --cov=cli
```

---

## 🐳 Docker

### Build image

```bash
docker build -t flunky .
```

### Run container

```bash
docker run -p 8000:8000 flunky
```

---

## 🔄 CI/CD

This project uses GitHub Actions to:

* Run automated tests on every push and pull request
* Validate Docker image builds successfully

Workflows:

* FLUNKY CI
* Docker Build Check

---

## 📊 Current Status

```
✅ Backend API          - COMPLETE
✅ Authentication       - COMPLETE
✅ CLI System           - COMPLETE
✅ Task CRUD            - COMPLETE
✅ Testing (pytest)     - COMPLETE
✅ Dockerization        - COMPLETE
✅ CI/CD (GitHub Actions) - COMPLETE
⚠️ Advanced Features    - IN PROGRESS
```

---

## 🔮 Future Improvements

* Task statistics (`flunky stats`)
* Search functionality
* Task priorities & due dates
* Export/import tasks
* Deployment to cloud (Render/Railway)

---

## 📌 Author

**Arpit Yadav**
B.Tech CSE (Data Science)

GitHub: https://github.com/arpityadav526
LinkedIn: https://www.linkedin.com/in/arpit-yadav-63b2b6293

---

## ⭐ If you like this project

Give it a star ⭐ and feel free to contribute!
