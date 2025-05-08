# Job Application Tracker

A full-stack application for searching, saving, and tracking job applications. The backend is built with Flask (Python), and the frontend is built with Next.js (React + Material UI).

---

## Prerequisites
- **Python 3.9** (for backend)
- **Node.js 18+** and **Yarn** or **npm** (for frontend)
- **pip** (Python package manager)

---

## Backend (Flask API)

### 1. Setup Python Environment
```bash
cd api
make setup
source venv/bin/activate
```

### 2. Install Python Dependencies
```bash
make install
```

### 3. Run the Backend Server
```bash
make run
```

### 4. To **deactivate** the virtual environment, simply run:
```bash
deactivate
```

- The backend will start on [http://localhost:5000](http://localhost:5000)
- The first run will initialize the SQLite database (`jobs.db`).

#### Notes
- If you see errors about missing NLTK or spaCy models, the app will attempt to download them automatically.
- If you change the database schema, delete `api/jobs.db` and restart.

---

## Frontend (Next.js + Material UI)

### 1. Setup Frontend
```bash
cd web
```

### 2. Install Node.js Dependencies
```bash
yarn install
```

### 3. Run the Frontend Dev Server
```bash
yarn run dev
```
- The frontend will start on [http://localhost:3000](http://localhost:3000)

#### Notes
- The frontend expects the backend to be running at `http://localhost:5000`.
- If you want to change the backend URL, set the environment variable `NEXT_PUBLIC_API_BASE_URL` in a `.env.local` file in the `web` directory.

---

## Features
- Search for jobs (aggregates from multiple sources)
- Save jobs, unsave, and apply
- Track applications
- Upload and analyze your resume
- Material UI for a modern, responsive interface
- Pagination for job and saved job lists

---

## Troubleshooting
- **CORS errors:** Make sure Flask is running with CORS enabled (already set up in `api/app.py`).
- **Port conflicts:** Ensure nothing else is running on ports 3000 (frontend) or 5000 (backend).
- **Database issues:** Delete `api/jobs.db` and restart the backend to reinitialize.
- **Missing Python packages:** Run `pip install -r requirements.txt` again (from the `api` directory).
- **Node errors:** Delete `node_modules` and `yarn.lock`/`package-lock.json`, then reinstall dependencies.

---

## License
MIT 