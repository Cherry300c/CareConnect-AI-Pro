import hashlib

import streamlit as st

from database import fetch_one, insert_record


def hash_password(password):
    salt = "careconnect_static_salt_v2"
    return hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()


def register_user(name, email, phone, password, role):
    name = name.strip()
    email = email.strip().lower()
    phone = phone.strip()

    if not name or not email or not password:
        return False, "Name, email, and password are required."
    if "@" not in email or "." not in email:
        return False, "Enter a valid email address."
    if len(password) < 6:
        return False, "Password must be at least 6 characters."
    if role not in ["Patient", "Doctor"]:
        return False, "Invalid role selected."

    existing = fetch_one("SELECT id FROM users WHERE email = ?", (email,))
    if existing:
        return False, "An account already exists with this email."

    insert_record(
        "users",
        {
            "name": name,
            "email": email,
            "phone": phone,
            "password_hash": hash_password(password),
            "role": role,
            "status": "Active",
        },
    )
    return True, "Registration successful. You can now log in."


def login_user(email, password):
    email = email.strip().lower()
    if not email or not password:
        return None

    user = fetch_one(
        """
        SELECT id, name, email, phone, role, status, password_hash
        FROM users
        WHERE email = ?
        """,
        (email,),
    )
    if not user or user["status"] != "Active":
        return None
    if user["password_hash"] != hash_password(password):
        return None

    user.pop("password_hash", None)
    return user


def current_user():
    return st.session_state.get("user")


def logout_user():
    st.session_state["user"] = None


def require_role(*roles):
    user = current_user()
    if not user:
        st.warning("Please log in.")
        st.stop()
    if user["role"] not in roles:
        st.error("You do not have access to this page.")
        st.stop()
    return user
