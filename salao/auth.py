from __future__ import annotations

import hashlib
import hmac
import os
from dataclasses import dataclass

from .database import Database

PROFILES = ("Administrador", "Recepcao", "Profissional", "Financeiro")


@dataclass
class SystemUser:
    name: str
    username: str
    profile: str
    active: bool = True
    professional_id: int | None = None
    user_id: int | None = None


class PermissionService:
    PERMISSIONS = {
        "Administrador": {
            "view_dashboard",
            "view_agenda",
            "view_clients",
            "view_services",
            "view_professionals",
            "view_finance",
            "view_users",
            "view_settings",
            "manage_clients",
            "manage_services",
            "manage_professionals",
            "manage_appointments",
            "complete_appointments",
            "receive_payments",
            "manage_finance",
            "manage_users",
        },
        "Recepcao": {
            "view_dashboard",
            "view_agenda",
            "view_clients",
            "view_services",
            "view_professionals",
            "manage_clients",
            "manage_services",
            "manage_professionals",
            "manage_appointments",
            "receive_payments",
        },
        "Profissional": {
            "view_dashboard",
            "view_agenda",
            "view_clients",
            "complete_appointments",
        },
        "Financeiro": {
            "view_dashboard",
            "view_finance",
            "receive_payments",
            "manage_finance",
        },
    }

    def has_permission(self, user: SystemUser, permission: str) -> bool:
        return permission in self.PERMISSIONS.get(user.profile, set())


class AuditService:
    def __init__(self, database: Database):
        self.database = database

    def log(self, username: str, action: str, entity_type: str, entity_id: int = 0, description: str = "") -> None:
        self.database.execute(
            """
            INSERT INTO audit_log (username, action, entity_type, entity_id, description)
            VALUES (?, ?, ?, ?, ?)
            """,
            (username, action, entity_type, int(entity_id), description.strip()),
        )

    def list_entries(self) -> list[dict[str, object]]:
        rows = self.database.fetchall("SELECT * FROM audit_log ORDER BY id DESC LIMIT 200")
        return [
            {
                "username": str(row["username"]),
                "action": str(row["action"]),
                "entity_type": str(row["entity_type"]),
                "entity_id": int(row["entity_id"]),
                "description": str(row["description"]),
                "created_at": str(row["created_at"]),
            }
            for row in rows
        ]


class AuthService:
    def __init__(self, database: Database):
        self.database = database
        self.permission_service = PermissionService()
        self._ensure_default_admin()

    def _ensure_default_admin(self) -> None:
        row = self.database.fetchone("SELECT id FROM users LIMIT 1")
        if row is not None:
            return
        self.create_user("Administrador", "admin", "admin123", "Administrador", None, True)

    def create_user(
        self,
        name: str,
        username: str,
        password: str,
        profile: str,
        professional_id: int | None = None,
        active: bool = True,
    ) -> SystemUser:
        if not name.strip():
            raise ValueError("user name cannot be empty")
        if not username.strip():
            raise ValueError("username cannot be empty")
        if len(password) < 4:
            raise ValueError("password too short")
        if profile not in PROFILES:
            raise ValueError("invalid profile")
        existing = self.database.fetchone("SELECT id FROM users WHERE username = ?", (username.strip().lower(),))
        if existing is not None:
            raise ValueError("username already exists")
        salt = os.urandom(16).hex()
        password_hash = self._hash_password(password, salt)
        cursor = self.database.execute(
            """
            INSERT INTO users (name, username, password_hash, password_salt, profile, professional_id, active)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (name.strip(), username.strip().lower(), password_hash, salt, profile, professional_id, 1 if active else 0),
        )
        return self.get_user(int(cursor.lastrowid))

    def authenticate(self, username: str, password: str) -> SystemUser:
        row = self.database.fetchone("SELECT * FROM users WHERE username = ?", (username.strip().lower(),))
        if row is None:
            raise ValueError("usuario ou senha incorretos")
        if int(row["active"]) != 1:
            raise ValueError("usuario inativo")
        expected_hash = str(row["password_hash"])
        provided_hash = self._hash_password(password, str(row["password_salt"]))
        if not hmac.compare_digest(expected_hash, provided_hash):
            raise ValueError("usuario ou senha incorretos")
        return self._row_to_user(row)

    def list_users(self) -> list[SystemUser]:
        rows = self.database.fetchall("SELECT * FROM users ORDER BY name")
        return [self._row_to_user(row) for row in rows]

    def get_user(self, user_id: int) -> SystemUser:
        row = self.database.fetchone("SELECT * FROM users WHERE id = ?", (int(user_id),))
        if row is None:
            raise ValueError("user id not found")
        return self._row_to_user(row)

    def remember_username(self, username: str) -> None:
        self.database.execute(
            """
            INSERT INTO app_settings (setting_key, setting_value)
            VALUES ('remembered_username', ?)
            ON CONFLICT(setting_key) DO UPDATE SET setting_value = excluded.setting_value
            """,
            (username.strip().lower(),),
        )

    def clear_remembered_username(self) -> None:
        self.database.execute(
            """
            INSERT INTO app_settings (setting_key, setting_value)
            VALUES ('remembered_username', '')
            ON CONFLICT(setting_key) DO UPDATE SET setting_value = ''
            """
        )

    def get_remembered_username(self) -> str:
        row = self.database.fetchone("SELECT setting_value FROM app_settings WHERE setting_key = 'remembered_username'")
        return str(row["setting_value"]) if row else ""

    def _hash_password(self, password: str, salt: str) -> str:
        return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), 120000).hex()

    def _row_to_user(self, row) -> SystemUser:
        return SystemUser(
            name=str(row["name"]),
            username=str(row["username"]),
            profile=str(row["profile"]),
            active=int(row["active"]) == 1,
            professional_id=int(row["professional_id"]) if row["professional_id"] is not None else None,
            user_id=int(row["id"]),
        )
