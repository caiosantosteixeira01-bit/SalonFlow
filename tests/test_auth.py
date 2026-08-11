import pytest

from salao.auth import AuditService, AuthService
from salao.database import Database


def build_auth(tmp_path):
    database = Database(tmp_path / "salon.db")
    return AuthService(database), AuditService(database)


def test_default_admin_authenticates(tmp_path) -> None:
    auth, _ = build_auth(tmp_path)
    user = auth.authenticate("admin", "admin123")
    assert user.profile == "Administrador"
    assert user.active is True


def test_wrong_password_is_rejected(tmp_path) -> None:
    auth, _ = build_auth(tmp_path)
    with pytest.raises(ValueError, match="usuario ou senha incorretos"):
        auth.authenticate("admin", "senha-errada")


def test_inactive_user_cannot_login(tmp_path) -> None:
    auth, _ = build_auth(tmp_path)
    auth.create_user("Recepcao", "recepcao", "1234", "Recepcao", None, False)
    with pytest.raises(ValueError, match="usuario inativo"):
        auth.authenticate("recepcao", "1234")


def test_permission_profiles(tmp_path) -> None:
    auth, _ = build_auth(tmp_path)
    finance_user = auth.create_user("Financeiro", "financeiro", "1234", "Financeiro")
    professional_user = auth.create_user("Ana", "ana", "1234", "Profissional")
    assert auth.permission_service.has_permission(finance_user, "view_finance") is True
    assert auth.permission_service.has_permission(finance_user, "manage_users") is False
    assert auth.permission_service.has_permission(professional_user, "complete_appointments") is True
    assert auth.permission_service.has_permission(professional_user, "manage_finance") is False


def test_audit_log_records_entries(tmp_path) -> None:
    auth, audit = build_auth(tmp_path)
    user = auth.authenticate("admin", "admin123")
    audit.log(user.username, "login", "session", 0, "Inicio de sessao")
    entries = audit.list_entries()
    assert entries[0]["username"] == "admin"
    assert entries[0]["action"] == "login"
