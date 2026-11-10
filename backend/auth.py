from flask import Blueprint, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from database import get_connection

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        conn = get_connection()
        try:
            user = conn.execute(
                "SELECT id, username, password_hash FROM users WHERE username = ?",
                (username,),
            ).fetchone()
        finally:
            conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            next_url = request.args.get("next", "")
            if not next_url.startswith("/") or next_url.startswith("//"):
                next_url = url_for("dashboard")
            return redirect(next_url)
        error = "Wrong username or password"

    return render_template("login.html", error=error)


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))