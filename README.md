# Python E-Commerce & Delivery Tracking Web App

A modular Python e-commerce web application with an admin dashboard, carrier delivery tracking, session-based cart, and state machine workflows.

## Technology Stack

- **Backend**: Python 3.11+, Flask with Blueprints and Application Factory pattern
- **Database & Auth**: Flask-SQLAlchemy, Flask-Login, Flask-WTF, SQLite (development)
- **Frontend**: Server-rendered Jinja2 templates, standard CSS3 & Vanilla JavaScript (no framework dependencies)
- **Testing**: `pytest` with in-memory SQLite fixtures

---

## Project Structure

```
shop/
├── app.py                    # Application factory create_app(), registers all blueprints
├── config.py                 # Configuration classes: Config, DevelopmentConfig, TestingConfig, ProductionConfig
├── extensions.py             # Shared extension instances: db, login_manager
├── models.py                 # SQLAlchemy models (User, Product, Order, OrderItem, Shipment, TrackingEvent)
├── routes/
│   ├── __init__.py           # Blueprint package initialization
│   ├── auth.py               # Authentication routes (/auth/login, /auth/register, /auth/logout)
│   ├── store.py              # Catalog storefront routes (/, /products, /product/<id>, /search)
│   ├── cart.py               # Cart operations (/cart/, /cart/add, /cart/update, /cart/remove, /cart/checkout)
│   ├── tracking.py           # Shipment tracking (/track/<tracking_number>, /webhook/carrier)
│   └── admin.py              # Staff admin portal (/admin/, /products, /orders, /shipments, /users)
├── services/
│   ├── __init__.py           # Service layer package
│   ├── cart_service.py       # Session cart operations {product_id: qty}
│   ├── search_service.py     # Inverted index keyword search & prefix trie autocomplete
│   ├── order_service.py      # Checkout workflow & ORDER_STATUS_TRANSITIONS state machine
│   ├── tracking_service.py   # Carrier events & DELIVERY_STATUS_TRANSITIONS state machine
│   ├── notify_service.py     # SMS notification dispatch queue
│   └── analytics_service.py  # Min-heap best sellers, daily revenue, and shipment status metrics
├── templates/
│   ├── base.html             # Shared navigation layout and flash messages
│   ├── store/                # home.html, product.html, cart.html, checkout.html, track.html
│   ├── auth/                 # login.html, register.html
│   └── admin/                # dashboard.html, products.html, product_form.html, orders.html, shipments.html
├── static/
│   ├── css/main.css          # Modern pure CSS stylesheet
│   ├── js/main.js            # Vanilla JS for flash alerts and interactions
│   └── img/.gitkeep          # Static image asset directory
├── tests/
│   ├── __init__.py
│   ├── conftest.py           # App & test client fixtures using in-memory SQLite (:memory:)
│   ├── test_cart.py          # Cart routes and service stub tests
│   ├── test_orders.py        # Order workflow and state machine tests
│   └── test_tracking.py      # Tracking routes and delivery state machine tests
├── instance/.gitkeep         # SQLite runtime database directory
├── .env.example              # Sample environment variables
├── .gitignore                # Git exclusions (venv, __pycache__, instance/*.db, .env)
├── requirements.txt          # Minimum pinned dependency versions
└── README.md                 # Setup guide and documentation
```

---

## Architectural Rules

1. **Separation of Concerns**:
   - **Routes** (`routes/`) handle HTTP request parsing, response formatting, status codes, and template rendering only.
   - **Services** (`services/`) contain all business logic, computations, validations, and state transitions.
   - **Models** (`models.py`) define database schemas and data relationships only.
2. **Admin Authorization**:
   - The `admin` blueprint enforces administrator privileges before every route via an `@admin_bp.before_request` hook checking `current_user.is_authenticated` and `current_user.is_admin`.
3. **Finite State Machines**:
   - Order transitions are governed by `ORDER_STATUS_TRANSITIONS` in `services/order_service.py`.
   - Delivery progression transitions are governed by `DELIVERY_STATUS_TRANSITIONS` in `services/tracking_service.py`.

---

## Setup & Running

### 1. Prerequisites
- Python 3.11 or newer (Python 3.12+ recommended)
- `python3-venv`

### 2. Create and Activate Virtual Environment
```bash
cd shop
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Environment
```bash
cp .env.example .env
```

### 5. Initialize Database & Create Admin User
```bash
flask init-db
flask create-admin
```
`flask init-db` creates the OTP tables and adds mobile columns to existing user tables. It also adds the optional `thumbnail_url` column to existing product tables. The legacy email column is retained as optional support data and is never used for login.
> **Admin Credentials**:
> - Admin mobile: `+919876543210` (configurable via `ADMIN_MOBILE` environment variable or `--mobile`)
> - Default password: `admin123` (configurable via `ADMIN_PASSWORD` environment variable or `--password`)
> - In production, always set a strong `ADMIN_PASSWORD` in your secret environment store.

For an existing account without a mobile, first back up the database, then run
`flask set-user-mobile --user-id <id> --mobile +91XXXXXXXXXX`. Do not delete
the retained email column without a separate migration decision.

### 6. Run the Application
```bash
flask --app app run
```
Open your browser and navigate to `http://127.0.0.1:5000` to view the storefront. Access `/auth/login` to log into the admin dashboard with your admin credentials.

### 7. Run Test Suite
```bash
pytest
```

---

## Implementation Roadmap (TODOs)

### Completed

- [x] **Authentication**: Mobile-number registration/login with E.164 normalization, password hashing, SMS OTP verification, reset-password OTP, resend limits, and generic errors are covered by `tests/test_auth.py`.
- [x] **Application setup**: The application factory, blueprint registration, and `init-db` / `create-admin` CLI commands are implemented.
- [x] **Basic route smoke tests**: Authentication pages, the public tracking page, and the cart add endpoint have passing tests.

### Implemented Workflows

- **Catalog and search**: Database-backed catalog with per-pack quantity/weight and price, pagination, product details, keyword search, autocomplete, and idempotent sample seeding through `flask init-db`.
- **Cart and checkout**: Session quantities are validated against current stock and current database prices; checkout records orders and decrements stock transactionally.
- **Orders and tracking**: Validated status transitions, shipment records, chronological carrier events, and ETA projection.
- **Admin and analytics**: Database-backed management pages and SQL-grouped sales, seller, and status metrics.
- **Notifications**: In-process idempotent SMS queue with retry backoff. OTP delivery uses `SMS_PROVIDER=console` in debug development or the configured Twilio provider in production.
- **Carrier updates**: Configure `CARRIER_WEBHOOK_TOKEN` and send it as the `X-Carrier-Token` header when posting carrier events.
- **Application support**: Centralized validation, 400, 404, and 500 responses plus cart-count and year template context.

Catalog indexes are declared on the models and are also ensured by `flask init-db` for existing databases. The command adds newly introduced optional product columns to existing SQLite databases.

## SMS and OTP production setup

Set `OTP_SECRET` to a long random secret and configure `SMS_PROVIDER=twilio` with
`TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`, and the
approved `SMS_TEMPLATE_ID`. The console
provider is disabled unless debug mode is enabled; OTP values are never stored
or logged outside that development-only provider. OTPs expire after five minutes,
are single-use, and are limited by mobile number and IP address.

For India, register the sender and message template with the DLT operator before
production delivery. The approved DLT template ID and sender must be supplied by
the SMS provider configuration; do not send an unregistered template.

## Database backup and migration

Before running `flask init-db` against an existing database, make a copy of
`instance/shop.db`. The command preserves existing users and the optional email
column, adds `mobile`, `mobile_verified`, and `otp_challenges`, and creates a
unique mobile index. Existing users without a mobile must be migrated with
`flask set-user-mobile`; they cannot log in until their mobile is attached.
