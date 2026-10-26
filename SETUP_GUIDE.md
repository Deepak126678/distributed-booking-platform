# 🛠️ Distributed Booking Platform — Local Setup & Onboarding Guide

Welcome to the team! This guide walks through setting up the **FastAPI Booking Microservice** locally from scratch so both engineers can test, run, and develop seamlessly.

---

## 📌 Prerequisites

Before running the commands, ensure you have:
1. **Git** installed ([Download Git](https://git-scm.com/))
2. **Python 3.10+** (Python 3.12 recommended) ([Download Python](https://www.python.org/downloads/))
3. **Docker Desktop** (For multi-container orchestration) ([Download Docker](https://www.docker.com/products/docker-desktop/))

---

## 🚀 Step-by-Step Setup (Run Locally in 2 Minutes)

Open your terminal (**PowerShell** on Windows or **Terminal** on macOS/Linux) and follow these exact steps:

### 1. Clone the Repository
```bash
git clone https://github.com/Deepak126678/distributed-booking-platform.git
cd distributed-booking-platform
```

### 2. Navigate to the Booking Application
```bash
cd upstream/booking-app
```

### 3. Create a Python Virtual Environment (`.venv`)
```bash
python -m venv .venv
```

### 4. Activate the Virtual Environment

* **On Windows (PowerShell):**
  ```powershell
  .\.venv\Scripts\Activate.ps1
  ```
  *(💡 Note: If PowerShell shows a red security error saying "running scripts is disabled", run this first: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned`, then run the activate command again).*

* **On Windows (Command Prompt `cmd`):**
  ```cmd
  .venv\Scripts\activate.bat
  ```

* **On macOS / Linux:**
  ```bash
  source .venv/bin/activate
  ```

*You should now see `(.venv)` at the beginning of your terminal prompt.*

---

### 5. Install the Required Dependencies
Run:
```bash
pip install fastapi uvicorn sqlalchemy redis celery aiosmtplib jinja2 prometheus-client python-dotenv httpx
```

---

### 6. Set Local SQLite Database (For Instant Standalone Testing)
By default, the app looks for PostgreSQL on port 5432. For testing without starting Docker, point it to an in-memory SQLite database:

* **On Windows (PowerShell):**
  ```powershell
  $env:DATABASE_URL="sqlite:///./test.db"
  ```

* **On Windows (Command Prompt `cmd`):**
  ```cmd
  set DATABASE_URL=sqlite:///./test.db
  ```

* **On macOS / Linux:**
  ```bash
  export DATABASE_URL="sqlite:///./test.db"
  ```

---

### 7. Start the FastAPI Server!
```bash
uvicorn app.main:app --reload --port 8000
```

You should see:
```text
Database tables created successfully
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

---

## 🌐 Verifying Your Setup (Interactive Swagger UI)

Keep your terminal running and open your web browser to:  
👉 **`http://localhost:8000/docs`**

You will see FastAPI's Swagger UI dashboard. You can test these live routes:

1. **`GET /api/v1/units/`** — Search hotel room inventory.
2. **`POST /api/v1/units/`** — Add a new room:
   ```json
   {
     "name": "Deluxe Suite 101",
     "description": "King bed, city view, high-speed WiFi",
     "capacity": 2,
     "is_available": true
   }
   ```
3. **`POST /api/v1/guests/`** — Add a guest:
   ```json
   {
     "name": "Vishal Nishad",
     "email": "vishal@example.com",
     "phone": "+91-9876543211"
   }
   ```
4. **`POST /api/v1/reservations/`** — Book a room:
   ```json
   {
     "guest_id": 1,
     "unit_id": 1,
     "check_in_date": "2026-11-01",
     "check_out_date": "2026-11-05"
   }
   ```

---

## 🗄️ PostgreSQL Seed Script (`database/init.sql`)

When running with PostgreSQL and Docker, the database automatically initializes using `database/init.sql`:
* Creates tables: `guests`, `units`, and `reservations`
* Adds performance indexes on `is_available`, `email`, and reservation dates
* Seeds **5 test hotel rooms**:
  1. `Deluxe Suite 101` (Capacity: 2)
  2. `Executive Suite 102` (Capacity: 2)
  3. `Ocean View 103` (Capacity: 4)
  4. `Presidential Suite 104` (Capacity: 6)
  5. `Standard Room 105` (Capacity: 2)
* Seeds **2 test guests**: `Deepak Thakur` and `Vishal Nishad`.

---

## 👨‍💻 Engineer 2 Next Mission (Docker Multi-Container Mesh)

For **Engineer 2 (Infrastructure & Traffic Lead)**:
1. Create a new branch:
   ```bash
   git checkout -b feature/docker-mesh-topology
   ```
2. Create `docker-compose.yml` orchestrating:
   * `postgres` (:5432) with `database/init.sql` mounted to `/docker-entrypoint-initdb.d/init.sql`
   * `redis` (:6379)
   * `booking_v1` (:5001) mapped to port 8000
   * `booking_v2` (:5002) mapped to port 8000
   * Isolated Docker bridge network `booking_mesh` (`172.20.0.0/16`)
3. Test with `docker compose up -d` and push your branch for PR #2!
