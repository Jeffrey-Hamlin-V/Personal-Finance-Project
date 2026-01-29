# Personal Finance Intelligence Platform

A premium AI-powered personal finance dashboard that categorizes bank transactions, detects anomalies using Machine Learning, and provides rich visual insights via D3.js.

## 🚀 Key Features
- **Smart Data Upload**: Processes bank CSV statements with automatic column mapping.
- **ML categorization**: Automatically classifies transactions into categories (Food, Bills, Shopping, etc.).
- **Anomaly Detection**: Flags unusual spending amounts, frequencies, or merchants.
- **D3 Dashboard**: High-fidelity, interactive visualizations of spending patterns.
- **Secure Authentication**: User signup/login system with local database storage.

---

## 🏗 Project Architecture & File Guide

### 📂 Backend (`/backend`)
The backend is built with **FastAPI** and handles data processing, ML inference, and database management.

| File | Description |
| :--- | :--- |
| `api/main.py` | The main entry point for the FastAPI application. Sets up middleware and includes all routers. |
| `api/routes.py` | Contains core endpoints for transaction retrieval, CSV upload, and dashboard data aggregation. |
| `api/auth_routes.py` | Handles user authentication, including signup and login logic. |
| `api/schemas.py` | Defines **Pydantic** models for request/response validation and type safety. |
| `database/models.py` | Defines the **SQLAlchemy** ORM models (`User`, `Transaction`, `Upload`, etc.). |
| `database/init_db.py` | Script to initialize the database and create tables. |
| `database/config.py` | Manages environment-specific configurations (Dev, Test, Production). |
| `database/load_data.py` | Logic for loading initial sample data or seeding the database. |
| `ml/categorizer.py` | Machine Learning module for classifying transactions into spending categories. |
| `ml/anomaly_detector.py` | Module that identifies spending outliers and unusual financial patterns. |
| `ml/insight_engine.py` | Generates textual financial insights and summaries based on user data. |
| `run_server.py` | Convenience script to launch the FastAPI server using **Uvicorn**. |

### 📂 Frontend (`/frontend`)
The frontend is a modern **React** application bundled with **Vite**, using **D3.js** for high-performance visualizations.

| File | Description |
| :--- | :--- |
| `src/main.jsx` | React entry point that renders the `App` component. |
| `src/App.jsx` | Main application component handling routing and high-level page state. |
| `src/D3Dashboard.jsx` | The core "Power BI" style dashboard. Contains D3.js visualization logic and data polling. |
| `src/DashboardHome.jsx` | The landing page after login, providing a simple overview and CSV upload options. |
| `src/LoginPage.jsx` & `SignupPage.jsx` | Clean, interactive forms for user authentication. |
| `src/api.js` | Centralized helper module for making asynchronous requests to the backend API. |
| `src/d3-dashboard.css` | Specialized styling for the dashboard cards, charts, and interactive elements. |

### 📂 Machine Learning & Scripts (`/scripts`)
Scripts used for training models and cleaning real-world data.

| File | Description |
| :--- | :--- |
| `DataCleaning.py` | Pre-processing scripts to normalize varied bank CSV formats for the ML pipeline. |
| `randomforest.py` | Training script for the Random Forest classification model. |
| `logisticregression.py` | Training script for the Logistic Regression baseline model. |

---

## ⚙️ Setup & Installation

### 1. Prerequisites
- **Python 3.9+**
- **Node.js 18+** & **npm**

### 2. Backend Setup
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # macOS/Linux:
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r ../requirements.txt
   ```
4. Initialize the database:
   ```bash
   python -m database.init_db
   ```
5. Start the server:
   ```bash
   python run_server.py
   ```
   *The API will be available at http://localhost:8000*

### 3. Frontend Setup
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the development server:
   ```bash
   npm run dev
   ```
   *The app will be available at http://localhost:3000*

---

## 🚢 Deployment Guide
### Production Configuration
1. **Environment Variables**: Create a `.env` file in the `backend` folder based on `.env.example`.
2. **Database**: Update `DATABASE_URL` to point to a PostgreSQL instance.
3. **Build Frontend**:
   ```bash
   cd frontend
   npm run build
   ```
4. **Run Backend (Gunicorn/Uvicorn)**:
   ```bash
   uvicorn api.main:app --host 0.0.0.0 --port 8000
   ```
