"""Mobile-password authentication with OTP verification."""
from urllib.parse import urlparse

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user

from extensions import db
from models import User
from services.mobile_service import normalize_mobile
from services.otp_service import GENERIC_ERROR, issue_otp, verify_otp


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def is_safe_redirect_url(target: str | None) -> bool:
    """Validate that redirect target is relative to prevent open redirects."""
    if not target:
        return False
    test_url = urlparse(target)
    return test_url.scheme == "" and test_url.netloc == "" and target.startswith("/") and not target.startswith("//")


def _start_otp(user: User, purpose: str, next_page: str | None = None, remember: bool = False):
    session["pending_user_id"] = user.id
    session["pending_otp_purpose"] = purpose
    session["pending_next"] = next_page if is_safe_redirect_url(next_page) else ""
    session["pending_remember"] = remember
    issue_otp(user.id, user.mobile, purpose, request.remote_addr or "unknown")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Create an account and require mobile OTP verification before login."""
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard" if current_user.is_admin else "store.home"))
    if request.method == "POST":
        mobile_input = request.form.get("mobile", "")
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        try:
            mobile = normalize_mobile(mobile_input)
        except ValueError:
            flash("Enter a valid mobile number.", "danger")
            return render_template("auth/register.html", mobile=mobile_input)
        if not password:
            flash("Please enter a mobile number and password.", "danger")
        elif len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
        elif password != confirm_password:
            flash("Passwords do not match. Please re-enter.", "danger")
        elif User.query.filter_by(mobile=mobile).first():
            flash("We could not create that account. Please check the details or sign in.", "warning")
        else:
            new_user = User(mobile=mobile, mobile_verified=False, is_admin=False)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            try:
                _start_otp(new_user, "register")
            except ValueError as error:
                flash(str(error), "warning")
                return render_template("auth/register.html", mobile=mobile_input)
            flash("We sent a verification code to your mobile.", "info")
            return redirect(url_for("auth.verify_otp_route"))
        return render_template("auth/register.html", mobile=mobile_input)
    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Check mobile/password, then start the required login OTP step."""
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard" if current_user.is_admin else "store.home"))
    next_page = request.args.get("next") or request.form.get("next")
    if request.method == "POST":
        try:
            mobile = normalize_mobile(request.form.get("mobile", ""))
        except ValueError:
            mobile = ""
        password = request.form.get("password", "")
        user = User.query.filter_by(mobile=mobile).first() if mobile else None
        if user and user.check_password(password):
            try:
                _start_otp(user, "login", next_page, bool(request.form.get("remember")))
            except ValueError as error:
                flash(str(error), "warning")
                return render_template("auth/login.html", next=next_page, mobile=request.form.get("mobile", ""))
            flash("We sent a verification code to your mobile.", "info")
            return redirect(url_for("auth.verify_otp_route"))
        flash("Invalid mobile number or password. Please verify your credentials and try again.", "danger")
    return render_template("auth/login.html", next=next_page, mobile=request.form.get("mobile", ""))


@auth_bp.route("/verify-otp", methods=["GET", "POST"])
def verify_otp_route():
    """Verify the pending registration, login, or password-reset OTP."""
    user_id = session.get("pending_user_id")
    purpose = session.get("pending_otp_purpose")
    user = db.session.get(User, user_id) if user_id else None
    if not user or purpose not in {"login", "register", "reset"}:
        flash(GENERIC_ERROR, "warning")
        return redirect(url_for("auth.login"))
    if request.method == "POST":
        if verify_otp(user.id, purpose, request.form.get("otp", ""), request.remote_addr or "unknown"):
            session.pop("pending_user_id", None)
            session.pop("pending_otp_purpose", None)
            if purpose == "reset":
                session["reset_user_id"] = user.id
                return redirect(url_for("auth.reset_password"))
            user.mobile_verified = True
            db.session.commit()
            login_user(user, remember=session.pop("pending_remember", False))
            next_page = session.pop("pending_next", "")
            flash("Mobile number verified. Welcome to Dharti Mushrooms!", "success")
            if is_safe_redirect_url(next_page):
                return redirect(next_page)
            return redirect(url_for("admin.dashboard" if user.is_admin else "store.home"))
        flash(GENERIC_ERROR, "danger")
    return render_template("auth/verify_otp.html", mobile=user.mobile, purpose=purpose)


@auth_bp.route("/resend-otp", methods=["POST"])
def resend_otp():
    user_id = session.get("pending_user_id")
    purpose = session.get("pending_otp_purpose")
    user = db.session.get(User, user_id) if user_id else None
    if not user or purpose not in {"login", "register", "reset"}:
        flash(GENERIC_ERROR, "warning")
        return redirect(url_for("auth.login"))
    try:
        issue_otp(user.id, user.mobile, purpose, request.remote_addr or "unknown")
    except ValueError as error:
        flash(str(error), "warning")
    else:
        flash("If the request can be completed, a new code was sent.", "info")
    return redirect(url_for("auth.verify_otp_route"))


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        try:
            mobile = normalize_mobile(request.form.get("mobile", ""))
        except ValueError:
            mobile = ""
        user = User.query.filter_by(mobile=mobile).first() if mobile else None
        if user:
            try:
                _start_otp(user, "reset")
            except ValueError:
                pass
        flash("If an account matches that mobile number, a verification code was sent.", "info")
        return redirect(url_for("auth.verify_otp_route") if user else url_for("auth.forgot_password"))
    return render_template("auth/forgot_password.html")


@auth_bp.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    user_id = session.get("reset_user_id")
    user = db.session.get(User, user_id) if user_id else None
    if not user:
        return redirect(url_for("auth.forgot_password"))
    if request.method == "POST":
        password = request.form.get("password", "")
        if len(password) < 6 or password != request.form.get("confirm_password", ""):
            flash("Enter matching passwords of at least 6 characters.", "danger")
        else:
            user.set_password(password)
            db.session.commit()
            session.pop("reset_user_id", None)
            flash("Password updated. You can now sign in.", "success")
            return redirect(url_for("auth.login"))
    return render_template("auth/reset_password.html")


@auth_bp.route("/logout", methods=["GET", "POST"])
@login_required
def logout():
    logout_user()
    flash("You have been signed out successfully.", "success")
    return redirect(url_for("store.home"))
