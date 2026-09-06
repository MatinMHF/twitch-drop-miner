# Contributing to Twitch Drop Miner

Thank you for your interest in contributing to **Twitch Drop Miner**! We welcome bug reports, feature suggestions, and pull requests.

---

## 📜 Code of Conduct

Please maintain a friendly, inclusive, and professional environment for all contributors and users.

---

## 🛠️ Development Setup

### 1. Prerequisites
- **Python 3.12+**
- **Node.js 20+** & **npm**
- **Docker** (optional for local container testing)

### 2. Backend Setup
```bash
# Navigate to backend directory
cd backend

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run backend server in debug mode
python -m uvicorn app.main:app --host 127.0.0.1 --port 8080 --reload
```

### 3. Frontend Setup
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### 4. Running Tests
```bash
# Run pytest suite from root directory
PYTHONPATH=backend pytest backend/tests
```

---

## 🛡️ Clean-Room & Security Policy

1. **Clean-Room Guarantee**: Never copy code, decompiled scripts, or UI assets from other Twitch mining tools. All logic must remain original and independently implemented.
2. **Credential Redaction**: Ensure no credentials, OAuth tokens, or passwords are ever logged in plaintext.
3. **Persisted Query Hashes**: Always add or update Twitch query hashes in `backend/app/core/twitch_constants.py` with environment variable overrides.

---

## 🚀 Pull Request Guidelines

1. Fork the repository and create a new feature branch (`git checkout -b feature/amazing-feature`).
2. Ensure all backend tests and frontend TypeScript checks pass (`pytest` and `npm run lint`).
3. Commit your changes with clear, descriptive commit messages.
4. Open a Pull Request against the `main` branch.
