from __future__ import annotations

from decimal import Decimal

from salao.auth import AuthService
from salao.client_profile import ClientProfileService
from salao.database import Database
from salao.finance import FinanceService
from salao.salon import SalonService


def build_services(tmp_path):
    database = Database(tmp_path / "salon.db")
    salon = SalonService(database)
    finance = FinanceService(database)
    profile = ClientProfileService(database)
    auth = AuthService(database)
    return database, salon, finance, profile, auth


def test_client_profile_summary_and_metrics(tmp_path) -> None:
    _database, salon, finance, profile, _auth = build_services(tmp_path)
    maria = salon.add_client("Maria", "11999990000", "11999990000", "maria@email.com", "1995-08-18", "")
    ana = salon.add_professional("Ana", "11888880000", "Coloracao", True)
    bia = salon.add_professional("Bia", "11777770000", "Escova", True)
    coloracao = salon.add_service("Coloracao", "Cabelo", 120, 100.0, True)
    escova = salon.add_service("Escova", "Cabelo", 60, 150.0, True)
    premium = salon.add_service("Tratamento premium", "Tratamento", 90, 200.0, True)

    first = salon.create_appointment(maria.client_id, ana.professional_id, coloracao.service_id, "2026-08-01", "10:00", 120, 100.0, "Confirmado", "")
    second = salon.create_appointment(maria.client_id, ana.professional_id, escova.service_id, "2026-08-05", "11:00", 60, 150.0, "Confirmado", "")
    third = salon.create_appointment(maria.client_id, bia.professional_id, coloracao.service_id, "2026-08-09", "14:00", 120, 200.0, "Confirmado", "")
    future = salon.create_appointment(maria.client_id, ana.professional_id, premium.service_id, "2026-08-15", "09:30", 90, 220.0, "Agendado", "")
    finance.finalize_appointment_with_payment(first.appointment_id, "Dinheiro", Decimal("40.00"), "2026-08-01", Decimal("100.00"))
    finance.finalize_appointment_with_payment(second.appointment_id, "Pix", Decimal("40.00"), "2026-08-05", Decimal("150.00"))
    finance.finalize_appointment_with_payment(third.appointment_id, "Cartao de debito", Decimal("40.00"), "2026-08-09", Decimal("200.00"))

    avulso = finance.create_receivable(
        client_id=maria.client_id,
        description="Pagamento avulso",
        category="Avulso",
        amount=Decimal("50.00"),
        issue_date="2026-08-10",
        due_date="2026-08-10",
        payment_method="Dinheiro",
    )[0]
    finance.receive_receivable(avulso.receivable_id, Decimal("50.00"), "2026-08-10", "Dinheiro")

    result = profile.get_profile(maria.client_id)

    assert result["summary"]["total_appointments"] == 3
    assert result["summary"]["total_spent"] == Decimal("450.00")
    assert result["summary"]["average_ticket"] == Decimal("150.00")
    assert result["summary"]["last_visit"]["appointment_id"] == third.appointment_id
    assert result["summary"]["next_appointment"]["appointment_id"] == future.appointment_id
    assert result["summary"]["favorite_service"]["name"] == "Coloracao"
    assert result["summary"]["favorite_service"]["count"] == 2
    assert result["summary"]["frequent_professional"]["name"] == "Ana"
    assert result["summary"]["frequent_professional"]["count"] == 2
    assert any(item["origin"] == "Pagamento avulso" and item["amount"] == Decimal("50.00") for item in result["payments"])


def test_client_profile_notes_preferences_and_permissions_data(tmp_path) -> None:
    database, salon, finance, profile, auth = build_services(tmp_path)
    maria = salon.add_client("Maria")
    note = profile.add_note(maria.client_id, "Cliente prefere atendimento silencioso.", "admin")
    preferences = profile.save_preferences(
        maria.client_id,
        preferred_service="Coloracao",
        preferred_professional="Ana",
        service_notes="Evitar agua muito quente.",
        general_preferences="Prefere horarios da manha.",
    )
    finance.create_receivable(
        client_id=maria.client_id,
        description="Pacote especial",
        category="Pacote",
        amount=Decimal("120.00"),
        issue_date="2026-08-10",
        due_date="2026-08-12",
        payment_method="Pix",
    )

    result = profile.get_profile(maria.client_id)
    professional_user = auth.create_user("Ana", "ana", "1234", "Profissional")

    assert note["username"] == "admin"
    assert preferences["preferred_service"] == "Coloracao"
    assert result["summary"]["pending_payments"] == Decimal("120.00")
    assert result["notes"][0]["text"] == "Cliente prefere atendimento silencioso."
    assert auth.permission_service.has_permission(professional_user, "view_finance") is False
