import pytest
from datetime import date, timedelta

from salao.database import Database
from salao.salon import SalonService


def build_service(tmp_path):
    return SalonService(Database(tmp_path / "salon.db"))


def test_salon_core_flow_and_conflict(tmp_path) -> None:
    service = build_service(tmp_path)
    client = service.add_client("Maria", "11999999999", "11999999999", "maria@email.com", "1995-06-10", "")
    professional = service.add_professional("Ana", "11888888888", "Corte", True)
    service_item = service.add_service("Corte", "Cabelo", 60, 80.0, True)
    first = service.create_appointment(
        client.client_id,
        professional.professional_id,
        service_item.service_id,
        "2026-08-20",
        "14:00",
        60,
        80.0,
        "Agendado",
        "",
    )
    with pytest.raises(ValueError, match="appointment conflict"):
        service.create_appointment(
            client.client_id,
            professional.professional_id,
            service_item.service_id,
            "2026-08-20",
            "14:30",
            60,
            80.0,
            "Agendado",
            "",
        )
    completed = service.complete_appointment(first.appointment_id)
    assert completed.status == "Concluido"
    assert len(service.list_appointments("2026-08-20", professional.professional_id)) == 1


def test_salon_invalid_inputs(tmp_path) -> None:
    service = build_service(tmp_path)
    with pytest.raises(ValueError, match="client name cannot be empty"):
        service.add_client("   ")
    professional = service.add_professional("Ana", "11888888888", "Corte", True)
    service_item = service.add_service("Corte", "Cabelo", 60, 80.0, True)
    client = service.add_client("Maria")
    with pytest.raises(ValueError, match="invalid appointment date"):
        service.create_appointment(
            client.client_id,
            professional.professional_id,
            service_item.service_id,
            "2026-99-20",
            "14:00",
            60,
            80.0,
            "Agendado",
            "",
        )


def test_summary_includes_birthdays_and_confirmation_alerts(tmp_path) -> None:
    service = build_service(tmp_path)
    today = date.today()
    tomorrow = today + timedelta(days=1)
    week_client_birthday = (today + timedelta(days=3)).isoformat()
    today_client = service.add_client("Maria", birthday=today.isoformat())
    week_client = service.add_client("Julia", birthday=week_client_birthday)
    professional = service.add_professional("Ana", "11888888888", "Coloracao", True)
    service_item = service.add_service("Escova", "Cabelo", 45, 70.0, True)
    service.create_appointment(
        today_client.client_id,
        professional.professional_id,
        service_item.service_id,
        tomorrow.isoformat(),
        "09:00",
        45,
        70.0,
        "Agendado",
        "Confirmar pelo WhatsApp",
    )
    summary = service.summary()
    assert any(item["name"] == "Maria" for item in summary["birthdays_today"])
    assert any(item["name"] == "Julia" for item in summary["birthdays_week"])
    assert len(summary["confirmation_needed"]) == 1
    assert summary["confirmation_needed"][0]["client_name"] == "Maria"


def test_confirm_appointment_updates_summary(tmp_path) -> None:
    service = build_service(tmp_path)
    tomorrow = date.today() + timedelta(days=1)
    client = service.add_client("Paula", whatsapp="(41) 99999-1111")
    professional = service.add_professional("Ana", "11888888888", "Corte", True)
    service_item = service.add_service("Escova", "Cabelo", 45, 70.0, True)
    created = service.create_appointment(
        client.client_id,
        professional.professional_id,
        service_item.service_id,
        tomorrow.isoformat(),
        "10:00",
        45,
        70.0,
        "Agendado",
        "",
    )
    summary_before = service.summary()
    assert len(summary_before["confirmation_needed"]) == 1
    updated = service.confirm_appointment(created.appointment_id)
    assert updated.status == "Confirmado"
    summary_after = service.summary()
    assert len(summary_after["confirmation_needed"]) == 0


def test_canceled_appointment_cannot_be_confirmed(tmp_path) -> None:
    service = build_service(tmp_path)
    tomorrow = date.today() + timedelta(days=1)
    client = service.add_client("Paula")
    professional = service.add_professional("Ana", "11888888888", "Corte", True)
    service_item = service.add_service("Escova", "Cabelo", 45, 70.0, True)
    created = service.create_appointment(
        client.client_id,
        professional.professional_id,
        service_item.service_id,
        tomorrow.isoformat(),
        "10:00",
        45,
        70.0,
        "Agendado",
        "",
    )
    service.cancel_appointment(created.appointment_id)
    with pytest.raises(ValueError, match="canceled appointment cannot be confirmed"):
        service.confirm_appointment(created.appointment_id)
