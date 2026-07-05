# InvoMatch - AI-Assisted Invoice Reconciliation Engine

InvoMatch is an AI-powered accounts payable invoice verification platform that automatically matches invoices with purchase orders, detects pricing/quantity discrepancies, and flags potential anomalies.

This repository contains the complete implementation for **Phase 1 (Project Setup & Auth)** and **Phase 2 (Invoice Upload Module)**.

---

## Folder Structure

```text
InvoMatch/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── auth.py         # JWT and password encryption handlers
│   │   ├── config.py       # Pydantic settings management
│   │   ├── database.py     # SQLAlchemy DB session setup
│   │   ├── main.py         # FastAPI main routing
│   │   ├── models.py       # SQL models (Users, Invoices, POs, etc.)
│   │   ├── schemas.py      # Request/Response validation schemas
│   │   └── upload.py       # Upload endpoints (duplicate checks, limits)
│   ├── .env                # App settings
│   ├── requirements.txt    # Python library requirements
│   └── venv/               # Virtual environment
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── context/
│   │   │   └── AuthContext.jsx # JWT state manager
│   │   ├── pages/
│   │   │   ├── Login.jsx       # Login layout
│   │   │   ├── Register.jsx    # Registration layout
│   │   │   └── Dashboard.jsx   # Drag & Drop uploader and upload log
│   │   ├── App.jsx             # Router and auth guards
│   │   ├── index.css           # Styling directives and background meshes
│   │   └── main.jsx
│   ├── index.html
│   ├── package.json
│   ├── postcss.config.js
│   ├── tailwind.config.js
│   └── vite.config.js
├── database/
│   ├── invomatch.db        # Auto-created local SQLite database
│   └── schema.sql          # Base database SQL scripts
├── uploads/
│   ├── invoices/           # Uploaded invoices directory
│   └── pos/                # Uploaded purchase orders directory
├── verify_backend.py       # Syntax and load sanity checker script
└── test_app.py             # Full end-to-end API test suite
```

---

## Getting Started

### 1. Backend Setup & Run

The backend is configured to use a local virtual environment and auto-create the database using SQLite on startup, meaning no separate database installation or Docker is required.

1. Navigate to the `backend/` directory:
   ```bash
   cd backend
   ```

2. Make sure you are using Python 3.10+ and start the server:
   ```bash
   .\venv\Scripts\uvicorn app.main:app --reload
   ```
   *The server will start at [http://localhost:8000](http://localhost:8000).*

3. You can access the auto-generated Swagger API documentation at:
   - Interactive docs: [http://localhost:8000/docs](http://localhost:8000/docs)
   - Alternative docs: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### 2. Run API Verification Tests

A comprehensive suite of API test cases is included in the project root:

```bash
# Run sanity checks to verify all files load cleanly
.\backend\venv\Scripts\python.exe verify_backend.py

# Run functional tests covering register, login, duplicate file checks, and size validation
.\backend\venv\Scripts\python.exe test_app.py
```

### 3. Frontend Setup & Run (Requires Node.js)

To run the React + Vite + Tailwind dashboard interface:

1. Download and install **Node.js** (LTS version recommended) from [nodejs.org](https://nodejs.org/).
2. Navigate to the `frontend/` directory:
   ```bash
   cd frontend
   ```
3. Install the dependencies:
   ```bash
   npm install
   ```
4. Run the development server:
   ```bash
   npm run dev
   ```
   *The interface will launch at [http://localhost:5173](http://localhost:5173) with requests to `/api` proxying automatically to your local backend.*

---

## Production Cloud Deployment

This project is configured as a monorepo for seamless cloud deployment. The frontend is hosted on Vercel, the backend is hosted on Render, and data is stored in a Neon serverless PostgreSQL database.

### 1. Database Setup (Neon PostgreSQL)
1. Create a free account at [Neon](https://neon.tech) and create a new PostgreSQL database.
2. In the Neon Console main dashboard, copy your database **Connection String** (URI).
3. The SQLAlchemy models will automatically migrate and initialize all tables in Neon upon backend startup.

### 2. Backend Deployment (Render)
1. Create a new **Web Service** on [Render](https://render.com).
2. Connect your GitHub repository.
3. Configure the deployment settings:
   - **Branch:** `main`
   - **Root Directory:** `backend`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Go to the **Environment Variables** tab and add:
   - `PYTHON_VERSION`: `3.10.13` (ensures pre-compiled binary packages are used)
   - `DATABASE_URL`: `[Your Neon Connection String]`
   - `JWT_SECRET_KEY`: `[Your secure 64-character random hex string]`
5. Click **Create Web Service**.

### 3. Frontend Deployment (Vercel)
1. Create a new project on [Vercel](https://vercel.com) and import your GitHub repository.
2. Configure the deployment details:
   - **Root Directory:** Select the `frontend` directory.
   - **Framework Preset:** `Vite` (automatically detected).
3. Expand the **Environment Variables** tab and add:
   - `VITE_API_URL`: `[Your Render App URL]` (e.g., `https://project-invomatch.onrender.com` - *do not include a trailing slash*).
4. Click **Deploy**.

