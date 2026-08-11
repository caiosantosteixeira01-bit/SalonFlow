import pytest

from salao.database import Database
from salao.salon import SalonService
from salao.whatsapp import WhatsAppConfirmationService


def build_context(tmp_path):
    database = Database(tmp_path / "salon.db")
    service = SalonService(database)
    whatsapp = WhatsAppConfirmationService(database)
    professional = service.add_professional("Ana", "41999990000", "Corte", True)
    service_item = service.add_service("Corte", "Cabelo", 60, 80.0, True)
    client = service.add_client("Maria", phone="(41) 99999-9999", whatsapp="(41) 99999-9999")
    appointment = service.create_appointment(
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
    database.execute(
        """
        INSERT INTO app_settings (setting_key, setting_value)
        VALUES ('salon_name', 'SalonFlow Premium')
        ON CONFLICT(setting_key) DO UPDATE SET setting_value = excluded.setting_value
        """
    )
    return database, service, whatsapp, appointment


def test_normalize_phone_with_mask(tmp_path) -> None:
    _, _, whatsapp, _ = build_context(tmp_path)
    assert whatsapp.normalize_brazil_phone("(41) 99999-9999") == "5541999999999"


def test_normalize_phone_without_mask(tmp_path) -> None:
    _, _, whatsapp, _ = build_context(tmp_path)
    assert whatsapp.normalize_brazil_phone("41999999999") == "5541999999999"


def test_normalize_phone_with_existing_country_code(tmp_path) -> None:
    _, _, whatsapp, _ = build_context(tmp_path)
    assert whatsapp.normalize_brazil_phone("5541999999999") == "5541999999999"


def test_missing_phone_raises_error(tmp_path) -> None:
    database = Database(tmp_path / "salon.db")
    whatsapp = WhatsAppConfirmationService(database)
    with pytest.raises(ValueError, match="cliente sem telefone"):
        whatsapp.normalize_brazil_phone("")


def test_build_confirmation_message_uses_real_data(tmp_path) -> None:
    _, service, whatsapp, appointment = build_context(tmp_path)
    context = service.get_appointment_context(appointment.appointment_id)
    message = whatsapp.build_confirmation_message(context)
    assert "Maria" in message
    assert "20/08/2026" in message
    assert "14:00" in message
    assert "Corte" in message
    assert "Ana" in message
    assert "SalonFlow Premium" in message


def test_build_whatsapp_url_encodes_message(tmp_path) -> None:
    _, service, whatsapp, appointment = build_context(tmp_path)
    context = service.get_appointment_context(appointment.appointment_id)
    url = whatsapp.build_whatsapp_url(context)
    assert url.startswith("https://wa.me/5541999999999?text=")
    assert "Maria" not in url
    assert "%0A" in url


def test_context_prefers_whatsapp_field(tmp_path) -> None:
    _, service, whatsapp, appointment = build_context(tmp_path)
    context = service.get_appointment_context(appointment.appointment_id)
    assert whatsapp.get_contact_phone(context) == "5541999999999"
