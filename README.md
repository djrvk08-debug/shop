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
├── models.py                 # SQLAlchemy model stubs (User, Category, Product, Order, OrderItem, Shipment, TrackingEvent)
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
│   ├── notify_service.py     # Email/SMS notification dispatch queues
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
> **Admin Credentials**:
> - Default email: `admin@example.com` (configurable via `ADMIN_EMAIL` environment variable or `--email`)
> - Default password: `admin123` (configurable via `ADMIN_PASSWORD` environment variable or `--password`)
> - In production, always set a strong `ADMIN_PASSWORD` in your secret environment store.

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

- [ ] **Authentication**: Implement password hashing (`werkzeug.security`) and WTForms for registration and login.
- [ ] **Catalog & Database Seeding**: Build database initialization CLI command (`flask init-db`) to seed initial categories and sample products.
- [ ] **Session Cart**: Implement `services/cart_service.py` to persist items in Flask `session['cart']`.
- [ ] **Checkout & Payment**: Implement `services/order_service.checkout()` with atomic transaction rollback on inventory shortage.
- [ ] **Tracking Pipeline**: Implement `services/tracking_service.add_event()` to reject invalid state transitions and update ETA.
- [ ] **Search Index & Trie**: Implement inverted index tokenizer and trie-based prefix autocomplete in `services/search_service.py`.
- [ ] **Admin Metrics**: Implement heap-based top sellers and time-series aggregation in `services/analytics_service.py`.
