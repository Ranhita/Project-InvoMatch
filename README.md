# 🚀 InvoMatch - AI-Assisted Invoice Reconciliation & Anomaly Detection

## 📖 Overview

**InvoMatch** is an AI-powered invoice reconciliation system that automates the Accounts Payable (AP) process by matching vendor invoices with Purchase Orders (POs), identifying anomalies, and assisting finance teams in making accurate payment decisions.

The system combines business rules, fuzzy matching, and machine learning techniques to reduce manual effort, improve accuracy, and minimize payment fraud.

---

# ✨ Features

- 🔐 User Authentication (Register/Login using JWT)
- 📄 Upload Vendor Invoices
- 📑 Upload Purchase Orders
- 🤖 AI-Based Invoice Matching
- 🔍 Fuzzy Vendor & Product Matching
- ⚠️ Price & Quantity Anomaly Detection
- 📊 Dashboard for Invoice Review
- 📈 Match Confidence Scoring
- 📝 Audit Logging
- 📋 Report Generation

---

# 🏗️ System Architecture

```
                React Frontend
                      │
               REST API Requests
                      │
                FastAPI Backend
                      │
 ┌────────────────────────────────────┐
 │ Invoice Upload                     │
 │ Data Parsing                       │
 │ Data Cleaning                      │
 │ Feature Engineering                │
 │ Matching Engine                    │
 │ Anomaly Detection                  │
 │ Report Generation                  │
 └────────────────────────────────────┘
                      │
              PostgreSQL Database
```

---

# 🧠 AI Workflow

```
Invoice Upload
       │
       ▼
Data Parsing
       │
       ▼
Data Cleaning
       │
       ▼
Feature Engineering
       │
       ▼
Invoice Matching
       │
       ▼
Anomaly Detection
       │
       ▼
Dashboard & Reports
```

---

# 🛠️ Tech Stack

## Frontend

- React.js
- Vite
- Tailwind CSS
- Axios

## Backend

- Python
- FastAPI
- SQLAlchemy
- JWT Authentication

## Database

- PostgreSQL

## Machine Learning

- LightGBM
- Scikit-learn
- Isolation Forest
- RapidFuzz
- SHAP
- Pandas
- NumPy

---

# 📂 Project Structure

```
InvoMatch/

│── backend/
│   ├── app/
│   ├── requirements.txt
│   ├── verify_backend.py
│
│── frontend/
│   ├── src/
│   │   ├── context/
│   │   ├── pages/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css
│   ├── package.json
│   ├── vite.config.js
│   └── tailwind.config.js
│
│── database/
│
│── uploads/
│
│── test_uploads/
│
│── test_files/
│
│── logs/
│
│── README.md
│── .gitignore
│── test_app.py
│── start_production.ps1
```

---

# 🚀 Getting Started

## 1. Clone the Repository

```bash
git clone https://github.com/<username>/InvoMatch.git

cd InvoMatch
```

---

## 2. Backend Setup

```bash
cd backend

python -m venv venv
```

### Windows

```bash
venv\Scripts\activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Configure Environment Variables

Create a `.env` file inside the `backend` folder.

Example:

```env
DATABASE_URL=postgresql://username:password@localhost/invomatch

JWT_SECRET_KEY=your_secret_key
```

### Run Backend

```bash
uvicorn app.main:app --reload
```

Backend:

```
http://localhost:8000
```

Swagger Documentation:

```
http://localhost:8000/docs
```

---

## 3. Frontend Setup

```bash
cd frontend

npm install

npm run dev
```

Frontend:

```
http://localhost:5173
```

---

# 📋 Application Modules

### Authentication

- User Registration
- User Login
- JWT Authentication

### Invoice Upload

- Upload Vendor Invoices
- Upload Purchase Orders

### Data Processing

- Data Parsing
- Data Cleaning
- Feature Engineering

### AI Matching

- Exact Matching
- Fuzzy Matching
- Machine Learning Ranking

### Anomaly Detection

- Price Deviations
- Quantity Mismatches
- Duplicate Detection

### Dashboard

- Invoice Summary
- Pending Reviews
- Match Statistics
- Reports

---

# 📊 Future Enhancements

- OCR Support for Scanned PDFs
- Email Notifications
- Vendor Performance Analytics
- Multi-Currency Support
- Multi-Tenant Architecture
- Cloud Deployment
- ERP Integration (SAP, Oracle, QuickBooks)

---

# 👥 Team Members

- **Ranhita B**
- **Keerthana S**

---

# 🎯 Project Objectives

- Reduce manual invoice reconciliation time.
- Improve invoice matching accuracy.
- Detect fraudulent or duplicate invoices.
- Assist finance teams with faster decision-making.
- Automate Accounts Payable workflows.

---

# 📄 License

This project was developed as an academic Final Year Project for learning and demonstration purposes.

---

## ⭐ Support

If you found this project useful, consider giving it a ⭐ on GitHub!
