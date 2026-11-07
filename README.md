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

### Completed

- [x] **Authentication**: Registration, login, logout, and password hashing are implemented and covered by `tests/test_auth.py`.
- [x] **Application setup**: The application factory, blueprint registration, and `init-db` / `create-admin` CLI commands are implemented.
- [x] **Basic route smoke tests**: Authentication pages, the public tracking page, and the cart add endpoint have passing tests.

### Remaining

- [ ] **Catalog and search**: Add database-backed product/category listing, product detail, pagination, and initial sample-data seeding; implement indexed keyword search and trie-based autocomplete in `services/search_service.py`.
- [ ] **Cart**: Implement `services/cart_service.py` and wire cart display, update, and remove routes to session state with current stock and price validation.
- [ ] **Checkout and orders**: Implement transactional checkout, inventory updates, order status changes, and order retrieval in `services/order_service.py`.
- [ ] **Shipment tracking**: Implement shipment creation, event validation and persistence, tracking lookup, and ETA calculation in `services/tracking_service.py`.
- [ ] **Admin workflows and analytics**: Connect product, order, shipment, and user pages to database records; implement dashboard aggregations in `services/analytics_service.py`.
- [ ] **Notifications**: Implement the notification queue and delivery processing in `services/notify_service.py`.
- [ ] **Application support**: Add centralized error handlers and template context helpers; add database migrations if schema evolution is needed.
- [ ] **Behavioral coverage**: Replace tests that assert `NotImplementedError` with tests for the completed cart, order, and tracking workflows, then cover the catalog and admin flows.

**Verification note**: `pytest -q` currently passes all 18 tests in the project virtual environment. Some passing tests explicitly expect unimplemented service functions to raise `NotImplementedError`, so this is not evidence that the remaining workflows are complete.