"""Authentication blueprint handling customer and admin registration, login, and logout."""
from urllib.parse import urlparse
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from extensions import db
from models import User

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def is_safe_redirect_url(target: str | None) -> bool:
    """Validate that redirect target is relative to prevent open-redirect vulnerabilities."""
    if not target:
        return False
    ref_url = urlparse(request.host_url)
    test_url = urlparse(target)
    # Target must be relative path without external scheme/netloc
    return test_url.scheme == "" and test_url.netloc == "" and target.startswith("/") and not target.startswith("//")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Handle new customer account registration."""
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard" if getattr(current_user, "is_admin", False) else "store.home"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not email or not password:
            flash("Please enter both an email address and a password.", "danger")
            return render_template("auth/register.html", email=email)

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template("auth/register.html", email=email)

        if password != confirm_password:
            flash("Passwords do not match. Please re-enter.", "danger")
            return render_template("auth/register.html", email=email)

        if User.query.filter_by(email=email).first():
            flash("An account with that email already exists. Please sign in.", "warning")
            return redirect(url_for("auth.login"))

        # Create new customer user
        new_user = User(email=email, is_admin=False)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        flash("Welcome to Dharti Mushrooms! Your account has been created.", "success")
        return redirect(url_for("store.home"))

    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Handle user authentication, session creation, and next-url redirect."""
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard" if getattr(current_user, "is_admin", False) else "store.home"))

    next_page = request.args.get("next") or request.form.get("next")

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember = bool(request.form.get("remember"))

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user, remember=remember)
            flash(f"Welcome back, {user.email}!", "success")

            # Redirect to safe next_page if provided
            if is_safe_redirect_url(next_page):
                return redirect(next_page)

            return redirect(url_for("admin.dashboard" if user.is_admin else "store.home"))

        flash("Invalid email or password. Please verify your credentials and try again.", "danger")

    return render_template("auth/login.html", next=next_page)


@auth_bp.route("/logout", methods=["GET", "POST"])
def logout():
    """Terminate the current authenticated user session."""
    if current_user.is_authenticated:
        logout_user()
        flash("You have been signed out successfully.", "success")
    return redirect(url_for("store.home"))
