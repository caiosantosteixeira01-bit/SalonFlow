from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path


class Database:
    def __init__(self, db_path: Path | str = "salon.db"):
        self.db_path = Path(db_path)
        self._initialize()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                PRAGMA foreign_keys = ON;
                CREATE TABLE IF NOT EXISTS clients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    phone TEXT NOT NULL DEFAULT '',
                    whatsapp TEXT NOT NULL DEFAULT '',
                    email TEXT NOT NULL DEFAULT '',
                    birthday TEXT NOT NULL DEFAULT '',
                    notes TEXT NOT NULL DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS professionals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    phone TEXT NOT NULL DEFAULT '',
                    specialty TEXT NOT NULL DEFAULT '',
                    active INTEGER NOT NULL DEFAULT 1
                );
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    password_salt TEXT NOT NULL,
                    profile TEXT NOT NULL,
                    professional_id INTEGER,
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(professional_id) REFERENCES professionals(id)
                );
                CREATE TABLE IF NOT EXISTS app_settings (
                    setting_key TEXT PRIMARY KEY,
                    setting_value TEXT NOT NULL DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS services (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT '',
                    duration_minutes INTEGER NOT NULL,
                    price REAL NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1
                );
                CREATE TABLE IF NOT EXISTS appointments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id INTEGER NOT NULL,
                    professional_id INTEGER NOT NULL,
                    service_id INTEGER NOT NULL,
                    appointment_date TEXT NOT NULL,
                    appointment_time TEXT NOT NULL,
                    duration_minutes INTEGER NOT NULL,
                    price REAL NOT NULL,
                    status TEXT NOT NULL,
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(client_id) REFERENCES clients(id),
                    FOREIGN KEY(professional_id) REFERENCES professionals(id),
                    FOREIGN KEY(service_id) REFERENCES services(id)
                );
                CREATE TABLE IF NOT EXISTS receivable_accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    parent_id INTEGER,
                    appointment_id INTEGER,
                    client_id INTEGER NOT NULL,
                    description TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT '',
                    total_amount_cents INTEGER NOT NULL,
                    remaining_amount_cents INTEGER NOT NULL,
                    issue_date TEXT NOT NULL,
                    due_date TEXT NOT NULL,
                    payment_method TEXT NOT NULL DEFAULT '',
                    installment_label TEXT NOT NULL DEFAULT '',
                    installment_number INTEGER NOT NULL DEFAULT 1,
                    installment_count INTEGER NOT NULL DEFAULT 1,
                    notes TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'Pendente',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(parent_id) REFERENCES receivable_accounts(id),
                    FOREIGN KEY(appointment_id) REFERENCES appointments(id),
                    FOREIGN KEY(client_id) REFERENCES clients(id)
                );
                CREATE TABLE IF NOT EXISTS payable_accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    parent_id INTEGER,
                    description TEXT NOT NULL,
                    beneficiary TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT '',
                    total_amount_cents INTEGER NOT NULL,
                    remaining_amount_cents INTEGER NOT NULL,
                    issue_date TEXT NOT NULL,
                    due_date TEXT NOT NULL,
                    payment_method TEXT NOT NULL DEFAULT '',
                    installment_label TEXT NOT NULL DEFAULT '',
                    installment_number INTEGER NOT NULL DEFAULT 1,
                    installment_count INTEGER NOT NULL DEFAULT 1,
                    recurring_key TEXT NOT NULL DEFAULT '',
                    notes TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'Pendente',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(parent_id) REFERENCES payable_accounts(id)
                );
                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kind TEXT NOT NULL,
                    receivable_id INTEGER,
                    payable_id INTEGER,
                    appointment_id INTEGER,
                    client_id INTEGER,
                    description TEXT NOT NULL,
                    amount_cents INTEGER NOT NULL,
                    discount_cents INTEGER NOT NULL DEFAULT 0,
                    interest_cents INTEGER NOT NULL DEFAULT 0,
                    gross_amount_cents INTEGER NOT NULL DEFAULT 0,
                    net_amount_cents INTEGER NOT NULL DEFAULT 0,
                    payment_date TEXT NOT NULL,
                    payment_method TEXT NOT NULL DEFAULT '',
                    reference TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'Confirmado',
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(receivable_id) REFERENCES receivable_accounts(id),
                    FOREIGN KEY(payable_id) REFERENCES payable_accounts(id),
                    FOREIGN KEY(appointment_id) REFERENCES appointments(id),
                    FOREIGN KEY(client_id) REFERENCES clients(id)
                );
                CREATE TABLE IF NOT EXISTS cash_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    status TEXT NOT NULL DEFAULT 'Aberto',
                    opened_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    closed_at TEXT NOT NULL DEFAULT '',
                    opening_balance_cents INTEGER NOT NULL DEFAULT 0,
                    expected_balance_cents INTEGER NOT NULL DEFAULT 0,
                    counted_balance_cents INTEGER NOT NULL DEFAULT 0,
                    difference_cents INTEGER NOT NULL DEFAULT 0,
                    notes TEXT NOT NULL DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS cash_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER,
                    entry_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    amount_cents INTEGER NOT NULL,
                    payment_method TEXT NOT NULL DEFAULT '',
                    source TEXT NOT NULL DEFAULT '',
                    reference_type TEXT NOT NULL DEFAULT '',
                    reference_id INTEGER,
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(session_id) REFERENCES cash_sessions(id)
                );
                CREATE TABLE IF NOT EXISTS commissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    appointment_id INTEGER NOT NULL,
                    professional_id INTEGER NOT NULL,
                    service_id INTEGER NOT NULL,
                    base_amount_cents INTEGER NOT NULL,
                    percentage_basis_points INTEGER NOT NULL,
                    commission_amount_cents INTEGER NOT NULL,
                    commission_date TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'Pendente',
                    payment_reference TEXT NOT NULL DEFAULT '',
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(appointment_id) REFERENCES appointments(id),
                    FOREIGN KEY(professional_id) REFERENCES professionals(id),
                    FOREIGN KEY(service_id) REFERENCES services(id)
                );
                CREATE TABLE IF NOT EXISTS billing_charges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    receivable_id INTEGER,
                    payer_name TEXT NOT NULL,
                    document TEXT NOT NULL DEFAULT '',
                    description TEXT NOT NULL,
                    amount_cents INTEGER NOT NULL,
                    issue_date TEXT NOT NULL,
                    due_date TEXT NOT NULL,
                    document_number TEXT NOT NULL DEFAULT '',
                    digitable_line TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'Pendente',
                    paid_at TEXT NOT NULL DEFAULT '',
                    interest_cents INTEGER NOT NULL DEFAULT 0,
                    penalty_cents INTEGER NOT NULL DEFAULT 0,
                    discount_cents INTEGER NOT NULL DEFAULT 0,
                    notes TEXT NOT NULL DEFAULT '',
                    provider_name TEXT NOT NULL DEFAULT 'local-control',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(receivable_id) REFERENCES receivable_accounts(id)
                );
                CREATE TABLE IF NOT EXISTS financial_audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation_type TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    entity_id INTEGER NOT NULL,
                    previous_value TEXT NOT NULL DEFAULT '',
                    new_value TEXT NOT NULL DEFAULT '',
                    reason TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL DEFAULT '',
                    action TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    entity_id INTEGER NOT NULL DEFAULT 0,
                    description TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS client_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id INTEGER NOT NULL,
                    note_text TEXT NOT NULL,
                    username TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(client_id) REFERENCES clients(id)
                );
                CREATE TABLE IF NOT EXISTS client_preferences (
                    client_id INTEGER PRIMARY KEY,
                    preferred_service TEXT NOT NULL DEFAULT '',
                    preferred_professional TEXT NOT NULL DEFAULT '',
                    service_notes TEXT NOT NULL DEFAULT '',
                    general_preferences TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(client_id) REFERENCES clients(id)
                );
                """
            )
            self._ensure_column(conn, "clients", "created_at", "TEXT NOT NULL DEFAULT ''")
            conn.execute("UPDATE clients SET created_at = CURRENT_TIMESTAMP WHERE created_at = ''")
            conn.commit()

    def _ensure_column(self, conn, table_name: str, column_name: str, column_definition: str) -> None:
        columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()}
        if column_name in columns:
            return
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}")

    def execute(self, sql: str, params: tuple = ()):
        with self._connect() as conn:
            cursor = conn.execute(sql, params)
            conn.commit()
            return cursor

    def fetchone(self, sql: str, params: tuple = ()):
        with self._connect() as conn:
            return conn.execute(sql, params).fetchone()

    def fetchall(self, sql: str, params: tuple = ()):
        with self._connect() as conn:
            return conn.execute(sql, params).fetchall()

    @contextmanager
    def transaction(self):
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
