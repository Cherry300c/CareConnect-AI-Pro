import sqlite3
from datetime import datetime

import pandas as pd

from config import DB_PATH, DEFAULT_ADMIN_EMAIL, DEFAULT_ADMIN_PASSWORD


ALLOWED_TABLES = {
    "users",
    "assessments",
    "prescriptions",
    "appointments",
    "medicine_reminders",
    "followups",
    "feedback",
}


def now():
    return datetime.now().isoformat(timespec="seconds")


def connect():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                phone TEXT,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                status TEXT DEFAULT 'Active'
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS assessments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                patient_id INTEGER,
                patient_name TEXT,
                phone TEXT,
                age INTEGER,
                gender TEXT,
                blood_group TEXT,
                symptoms TEXT,
                disease TEXT,
                risk TEXT,
                score REAL,
                confidence REAL,
                context TEXT,
                advice TEXT,
                precautions TEXT,
                latitude REAL,
                longitude REAL,
                location_name TEXT,
                status TEXT DEFAULT 'New',
                doctor_note TEXT DEFAULT '',
                FOREIGN KEY(patient_id) REFERENCES users(id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS prescriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                patient_id INTEGER,
                patient_name TEXT,
                phone TEXT,
                file_name TEXT,
                analysis TEXT,
                FOREIGN KEY(patient_id) REFERENCES users(id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                token_id TEXT UNIQUE,
                patient_id INTEGER,
                patient_name TEXT,
                phone TEXT,
                age INTEGER,
                gender TEXT,
                blood_group TEXT,
                facility TEXT,
                facility_address TEXT,
                appointment_date TEXT,
                appointment_time TEXT,
                disease TEXT,
                risk TEXT,
                symptoms TEXT,
                status TEXT DEFAULT 'Booked',
                doctor_note TEXT DEFAULT '',
                FOREIGN KEY(patient_id) REFERENCES users(id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS medicine_reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                patient_id INTEGER,
                medicine_name TEXT,
                dosage TEXT,
                timing TEXT,
                start_date TEXT,
                end_date TEXT,
                notes TEXT,
                status TEXT DEFAULT 'Active',
                FOREIGN KEY(patient_id) REFERENCES users(id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS followups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                patient_id INTEGER,
                title TEXT,
                followup_date TEXT,
                priority TEXT,
                notes TEXT,
                status TEXT DEFAULT 'Pending',
                FOREIGN KEY(patient_id) REFERENCES users(id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                user_id INTEGER,
                name TEXT,
                role TEXT,
                rating INTEGER,
                category TEXT,
                message TEXT,
                status TEXT DEFAULT 'Open',
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)


def seed_admin():
    from auth import hash_password

    with connect() as conn:
        existing = conn.execute(
            "SELECT id FROM users WHERE email = ?",
            (DEFAULT_ADMIN_EMAIL,),
        ).fetchone()
        if existing:
            return
        conn.execute(
            """
            INSERT INTO users (created_at, name, email, phone, password_hash, role, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                now(),
                "System Admin",
                DEFAULT_ADMIN_EMAIL,
                "",
                hash_password(DEFAULT_ADMIN_PASSWORD),
                "Admin",
                "Active",
            ),
        )


def validate_table(table):
    if table not in ALLOWED_TABLES:
        raise ValueError("Unsupported table name")


def insert_record(table, data):
    validate_table(table)
    payload = dict(data)
    payload.setdefault("created_at", now())
    columns = ", ".join(payload.keys())
    placeholders = ", ".join("?" for _ in payload)
    with connect() as conn:
        cursor = conn.execute(
            f"INSERT INTO {table} ({columns}) VALUES ({placeholders})",
            list(payload.values()),
        )
        return cursor.lastrowid


def update_record(table, record_id, data):
    validate_table(table)
    payload = dict(data)
    if not payload:
        return
    assignments = ", ".join(f"{key} = ?" for key in payload)
    with connect() as conn:
        conn.execute(
            f"UPDATE {table} SET {assignments} WHERE id = ?",
            list(payload.values()) + [record_id],
        )


def fetch_one(query, params=()):
    with connect() as conn:
        row = conn.execute(query, params).fetchone()
        return dict(row) if row else None


def fetch_all(query, params=()):
    with connect() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]


def read_df(query, params=()):
    with connect() as conn:
        return pd.read_sql_query(query, conn, params=params)


def table_df(table_name):
    validate_table(table_name)
    return read_df(f"SELECT * FROM {table_name} ORDER BY created_at DESC")


def search_records(query_text):
    like = f"%{query_text.strip()}%"
    assessments = read_df(
        """
        SELECT id, created_at, patient_name, phone, disease, risk, confidence, status, symptoms, doctor_note
        FROM assessments
        WHERE patient_name LIKE ? OR phone LIKE ? OR disease LIKE ? OR symptoms LIKE ?
        ORDER BY created_at DESC
        """,
        (like, like, like, like),
    )
    appointments = read_df(
        """
        SELECT id, created_at, token_id, patient_name, phone, facility, appointment_date,
               appointment_time, risk, status, doctor_note
        FROM appointments
        WHERE patient_name LIKE ? OR phone LIKE ? OR token_id LIKE ? OR facility LIKE ?
        ORDER BY created_at DESC
        """,
        (like, like, like, like),
    )
    prescriptions = read_df(
        """
        SELECT id, created_at, patient_name, phone, file_name, analysis
        FROM prescriptions
        WHERE patient_name LIKE ? OR phone LIKE ? OR analysis LIKE ?
        ORDER BY created_at DESC
        """,
        (like, like, like),
    )
    return assessments, appointments, prescriptions


def get_patient_records(user_id):
    assessments = read_df(
        """
        SELECT id, created_at, symptoms, disease, risk, confidence, status, doctor_note
        FROM assessments
        WHERE patient_id = ?
        ORDER BY created_at DESC
        """,
        (user_id,),
    )
    appointments = read_df(
        """
        SELECT id, created_at, token_id, facility, appointment_date, appointment_time,
               status, disease, risk, doctor_note
        FROM appointments
        WHERE patient_id = ?
        ORDER BY created_at DESC
        """,
        (user_id,),
    )
    reminders = read_df(
        """
        SELECT id, medicine_name, dosage, timing, start_date, end_date, notes, status
        FROM medicine_reminders
        WHERE patient_id = ?
        ORDER BY created_at DESC
        """,
        (user_id,),
    )
    followups = read_df(
        """
        SELECT id, title, followup_date, priority, status, notes
        FROM followups
        WHERE patient_id = ?
        ORDER BY followup_date ASC
        """,
        (user_id,),
    )
    prescriptions = read_df(
        """
        SELECT id, created_at, file_name, analysis
        FROM prescriptions
        WHERE patient_id = ?
        ORDER BY created_at DESC
        """,
        (user_id,),
    )
    return assessments, appointments, reminders, followups, prescriptions


def doctor_queue():
    return read_df("""
        SELECT id, created_at, patient_name, phone, age, gender, symptoms,
               disease, risk, confidence, status, doctor_note
        FROM assessments
        WHERE risk IN ('High Risk', 'Medium Risk')
        ORDER BY
            CASE risk
                WHEN 'High Risk' THEN 1
                WHEN 'Medium Risk' THEN 2
                ELSE 3
            END,
            created_at DESC
    """)


def dashboard_stats():
    return {
        "assessments": table_df("assessments"),
        "appointments": table_df("appointments"),
        "prescriptions": table_df("prescriptions"),
        "users": table_df("users"),
        "feedback": table_df("feedback"),
        "reminders": table_df("medicine_reminders"),
        "followups": table_df("followups"),
    }
