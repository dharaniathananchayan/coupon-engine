# ArchintX Coupon Engine 🎫

[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-red.svg)](https://www.sqlalchemy.org/)
[![Tests](https://img.shields.io/badge/pytest-12%20passed-brightgreen.svg)](https://docs.pytest.org/)

An advanced, full-stack coupon management and validation engine built for **ArchintX**. The system allows public users to validate and redeem coupon codes against base prices with strict server-side validation rules and race-condition safety, while providing ArchintX staff with a secure management dashboard.

---

## 🌟 Key Features

- **Public Apply Coupon Portal**: Real-time coupon application with instant savings breakdown (original price, discount %, discounted price, total savings).
- **Enforced Server-Side Rule Pipeline**: All validation rules (code existence, active status, expiration timestamp, usage limits) are strictly executed on the backend in sequence.
- **Race-Condition & Concurrency Safe**: Uses atomic conditional database updates (`UPDATE coupons SET used_count = used_count + 1 WHERE ... AND used_count < usage_limit`) to guarantee usage limits hold even under high-concurrency bursts.
- **Staff Portal & Management Dashboard**:
  - Secure bcrypt password hashing and JWT / HTTP-only session cookie authentication.
  - Create new coupons with customizable discount %, UTC expiration, and usage limits.
  - View real-time coupon usage counters and instant one-click deactivation.
- **Pre-Seeded Test Data**: Comes out-of-the-box with pre-seeded staff credentials and 5 distinct coupon states for evaluation.
- **Interactive Swagger Documentation**: Built-in interactive API docs at `/docs` and ReDoc at `/redoc`.

---

## 🗄️ Database Schema & Architecture

The database requires at least 3 entities: `staff`, `coupons`, and `redemptions`.

### Entity Relationship Diagram

```mermaid
erDiagram
    STAFF {
        string id PK "UUID (String 36)"
        string email UK "Indexed, Not Null"
        string password_hash "Bcrypt Hash"
        datetime created_at "UTC Timestamp"
    }

    COUPON {
        string id PK "UUID (String 36)"
        string code UK "Indexed, Uppercase Normalized"
        float discount_percent "Check: > 0 AND <= 100"
        datetime expiry_date "UTC Timestamp"
        int usage_limit "Check: > 0"
        int used_count "Check: >= 0 AND <= usage_limit"
        boolean is_active "Default: True"
        datetime created_at "UTC Timestamp"
        datetime updated_at "UTC Timestamp"
    }

    REDEMPTION {
        string id PK "UUID (String 36)"
        string coupon_id FK "FK -> coupons.id"
        float base_price "Check: >= 0"
        float discounted_price "Check: >= 0"
        datetime redeemed_at "UTC Timestamp"
    }

    COUPON ||--o{ REDEMPTION : "tracks redemptions"
```

### Table Definitions

#### 1. `staff`
Stores authorized ArchintX staff accounts. No public registration is permitted; accounts are seeded directly.
- `id` (`VARCHAR(36)`): UUID Primary Key.
- `email` (`VARCHAR(255)`): Unique, indexed staff email.
- `password_hash` (`VARCHAR(255)`): Salted bcrypt password hash (never plain text).
- `created_at` (`DATETIME`): Account creation timestamp in UTC.

#### 2. `coupons`
Defines coupon rules, discounts, and tracking state.
- `id` (`VARCHAR(36)`): UUID Primary Key.
- `code` (`VARCHAR(50)`): Unique, indexed promo code (e.g., `MARKETINGINTX26`).
- `discount_percent` (`FLOAT`): Percentage discount between 0.1% and 100%.
- `expiry_date` (`DATETIME`): UTC expiration deadline.
- `usage_limit` (`INTEGER`): Maximum allowable redemptions across all users.
- `used_count` (`INTEGER`): Running counter of successful redemptions (`used_count <= usage_limit`).
- `is_active` (`BOOLEAN`): Administrative active status (`True` = enabled, `False` = deactivated).
- `created_at` / `updated_at` (`DATETIME`): Timestamps for audits.

#### 3. `redemptions`
Historical ledger recording every successful coupon redemption.
- `id` (`VARCHAR(36)`): UUID Primary Key.
- `coupon_id` (`VARCHAR(36)`): Foreign key referencing `coupons.id`.
- `base_price` (`FLOAT`): Original order amount.
- `discounted_price` (`FLOAT`): Final payable amount after discount.
- `redeemed_at` (`DATETIME`): UTC timestamp when the redemption transaction committed.

---

## ⚡ Concurrency Safety & Usage-Limit Protection

### The Challenge
In a naive implementation:
```python
# VULNERABLE TO RACE CONDITIONS:
coupon = db.query(Coupon).filter_by(code=code).first()
if coupon.used_count < coupon.usage_limit:
    coupon.used_count += 1
    db.commit()
```
If 10 requests hit the endpoint simultaneously when `usage_limit = 5` and `used_count = 4`, all 10 threads read `used_count == 4`, pass the check, and increment `used_count`, allowing the limit to be exceeded.

### The ArchintX Solution: Atomic Conditional SQL Updates
Our implementation performs **atomic conditional updates directly inside the database engine**:

```sql
UPDATE coupons
SET used_count = used_count + 1, updated_at = :db_now
WHERE id = :coupon_id
  AND is_active = TRUE
  AND expiry_date > :db_now
  AND used_count < usage_limit;
```

#### How this guarantees safety:
1. **Database Row Lock**: During the SQL `UPDATE`, the database engine acquires a row-level lock.
2. **Predicate Re-Evaluation**: The `WHERE used_count < usage_limit` condition is evaluated atomically at the moment the lock is held.
3. **Zero-Row Guard**: If an interleaved concurrent request consumed the last available usage slot, `rowcount` returns `0`. The transaction immediately rolls back and returns `HTTP 400 Bad Request: "Usage limit reached"`.
4. **Isolated Ledger Entry**: The `redemptions` record is only inserted if the atomic increment affected exactly 1 row, ensuring usage counters and redemption history remain in 100% sync.

This logic is verified automatically via `tests/test_concurrency.py`, which fires 25 simultaneous threads at a 5-limit coupon and verifies that exactly 5 succeed and 20 fail.

---

## 🚀 Quickstart & Setup Guide

### 1. Prerequisites
- Python 3.10+ (tested on Python 3.11, 3.12, 3.14)
- Git

### 2. Clone Repository & Setup Virtual Environment
```bash
git clone <your-repo-url>
cd coupon-engine

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.\.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Variables
Create a `.env` file from `.env.example`:
```bash
cp .env.example .env
```
Default `.env` settings:
```ini
ENVIRONMENT=development
SECRET_KEY=archintx_super_secret_jwt_key_change_in_production_2026
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
DATABASE_URL=sqlite:///./coupon_engine.db
```
*(To use PostgreSQL, simply replace `DATABASE_URL=postgresql://user:password@host:5432/dbname`)*

### 4. Database Initialization & Seeding
Run the seed script to create all database tables and populate the 5 test coupons and default staff user:
```bash
python -m scripts.seed
```

### 5. Start the Application
```bash
uvicorn app.main:app --reload --port 8000
```
Open your browser at:
- **Public Apply Page**: [http://localhost:8000/apply](http://localhost:8000/apply)
- **Staff Portal**: [http://localhost:8000/login](http://localhost:8000/login)
- **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🔑 Test Credentials & Pre-Seeded Coupons

### Staff Credentials
| Email | Password | Role |
| :--- | :--- | :--- |
| `staff@archintx.com` | `Password123!` | ArchintX Staff Administrator |

### Pre-Seeded Coupon Test Matrix
| Code | Discount | Expiry | Limit | Initial Used | State / Test Purpose |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`MARKETINGINTX26`**| 25% | +60 days | 200 | 0 | **Active & usable** (Brand showcase) |
| **`ACTIVE20`** | 20% | +30 days | 50 | 2 | **Active & usable** |
| **`EXPIRED10`** | 10% | -7 days | 100 | 5 | **Expired** (Rejection check) |
| **`MAXED50`** | 50% | +30 days | 5 | 5 | **Usage Limit Reached** (Rejection check) |
| **`DISABLED15`** | 15% | +30 days | 25 | 1 | **Deactivated** (Rejection check) |

---

## 🧪 Automated Testing

Run the full automated test suite (including unit tests, auth tests, coupon validation order, and concurrency stress testing):

```bash
pytest -v
```

Expected result:
```text
tests/test_auth.py::test_staff_login_success PASSED
tests/test_auth.py::test_staff_login_wrong_password PASSED
tests/test_auth.py::test_staff_login_nonexistent_user PASSED
tests/test_auth.py::test_protected_routes_without_auth PASSED
tests/test_concurrency.py::test_concurrent_coupon_redemptions PASSED
tests/test_coupons.py::test_create_and_list_coupons PASSED
tests/test_coupons.py::test_duplicate_coupon_creation PASSED
tests/test_coupons.py::test_deactivate_coupon PASSED
tests/test_coupons.py::test_apply_coupon_success PASSED
tests/test_coupons.py::test_apply_nonexistent_coupon PASSED
tests/test_coupons.py::test_apply_expired_coupon PASSED
tests/test_coupons.py::test_apply_maxed_coupon PASSED

======================== 12 passed in 3.11s ========================
```

---

## 🌐 API Reference

### Authentication
- `POST /auth/login`
  - Body: `{"email": "staff@archintx.com", "password": "Password123!"}`
  - Returns: `{"access_token": "...", "token_type": "bearer", "staff_email": "..."}` and sets HTTP-only cookie.
- `POST /auth/logout`
  - Clears authentication cookie.

### Coupons (Staff Only)
- `POST /coupons`
  - Headers: `Authorization: Bearer <token>`
  - Body: `{"code": "SUMMER30", "discount_percent": 30, "expiry_date": "2026-12-31T23:59:59Z", "usage_limit": 50}`
- `GET /coupons`
  - Headers: `Authorization: Bearer <token>`
  - Returns: List of all coupons with `used_count`, `usage_limit`, `is_active`, etc.
- `PATCH /coupons/{code}/deactivate`
  - Headers: `Authorization: Bearer <token>`
  - Deactivates coupon immediately.

### Coupon Application (Public)
- `POST /coupons/{code}/apply`
  - Body: `{"base_price": 100.00}`
  - Returns (200 OK):
    ```json
    {
      "valid": true,
      "code": "ACTIVE20",
      "base_price": 100.0,
      "discount_percent": 20.0,
      "discounted_price": 80.0,
      "savings": 20.0,
      "message": "Coupon 'ACTIVE20' successfully applied! You saved $20.00 (20.0% off)"
    }
    ```
  - Returns (400 / 404 on Failure):
    ```json
    {
      "detail": "Expired coupon: Code 'EXPIRED10' expired on 2026-10-28 13:01:03 UTC"
    }
    ```

---

## ☁️ Deployment Guide

### Option 1: Deploy to Render (Recommended Free Tier)
1. Push this repository to GitHub.
2. Sign in to [Render](https://render.com).
3. Click **New +** $\rightarrow$ **Blueprint** and select your GitHub repo (`render.yaml` will automatically configure a free Python Web Service and free PostgreSQL database).
4. Or create a **Web Service**:
   - Runtime: `Python`
   - Build Command: `pip install -r requirements.txt && python -m scripts.seed`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - Environment Variable: Add `DATABASE_URL` (from Neon, Supabase, or Render Postgres).

### Option 2: Deploy to Railway / Fly.io with Dockerfile
Use the included production-ready `Dockerfile`:
```bash
docker build -t coupon-engine .
docker run -p 8000:8000 -e DATABASE_URL=sqlite:///./coupon_engine.db coupon-engine
```

---

## 📷 Submission Checklist & Evidence

- [x] **Database Schema & ER Diagram** included in README.
- [x] **Atomic Concurrency Strategy** explained and verified with test suite.
- [x] **Validation Hierarchy** strictly enforced server-side (Existence $\rightarrow$ Active $\rightarrow$ Not Expired $\rightarrow$ Under Limit).
- [x] **5 Distinct Seed Coupons** + Staff Test User pre-seeded.
- [x] **Responsive Desktop & Mobile UI** for Apply, Login, and Dashboard.
- [x] **12 Automated Tests** passing with 100% success rate.
