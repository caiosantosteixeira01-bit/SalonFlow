from __future__ import annotations

import base64
from decimal import Decimal

import pytest
from pypdf import PdfReader

from salao.core.config import AppPaths
from salao.database import Database
from salao.finance import FinanceService
from salao.receipt import ReceiptService
from salao.salon import SalonService


PNG_PIXEL_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8"
    "/w8AAn8B9p4nWQAAAABJRU5ErkJggg=="
)


def build_services(tmp_path):
    database = Database(tmp_path / "salon.db")
    salon = SalonService(database)
    finance = FinanceService(database)
    paths = AppPaths(base_dir=tmp_path / "app")
    paths.base_dir.mkdir(parents=True, exist_ok=True)
    receipt_service = ReceiptService(finance, paths)
    return database, salon, finance, receipt_service, paths


def seed_paid_appointment(salon: SalonService, finance: FinanceService):
    client = salon.add_client("Maria", "11999999999", "11999999999", "maria@email.com", "1995-06-10", "")
    professional = salon.add_professional("Ana", "11888888888", "Corte", True)
    service_item = salon.add_service("Corte premium", "Cabelo", 60, 200.0, True)
    appointment = salon.create_appointment(
        client.client_id,
        professional.professional_id,
        service_item.service_id,
        "2026-08-20",
        "14:30",
        60,
        200.0,
        "Confirmado",
        "Cliente pediu finalizacao suave.",
    )
    finance.finalize_appointment_with_payment(
        appointment_id=appointment.appointment_id,
        payment_method="Pix",
        commission_percentage=Decimal("40.00"),
        payment_date="2026-08-20",
        received_amount=Decimal("180.00"),
        discount=Decimal("20.00"),
        notes="Pago com desconto promocional.",
    )
    return client, professional, service_item, appointment


def save_setting(database: Database, key: str, value: str) -> None:
    database.execute(
        """
        INSERT INTO app_settings (setting_key, setting_value)
        VALUES (?, ?)
        ON CONFLICT(setting_key) DO UPDATE SET setting_value = excluded.setting_value
        """,
        (key, value),
    )


def extract_pdf_text(pdf_path) -> str:
    reader = PdfReader(str(pdf_path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def test_receipt_generation_uses_real_paid_appointment_data(tmp_path) -> None:
    database, salon, finance, receipt_service, paths = build_services(tmp_path)
    seed_paid_appointment(salon, finance)
    save_setting(database, "salon_name", "SalonFlow Premium")
    save_setting(database, "salon_document", "12.345.678/0001-99")
    save_setting(database, "salon_phone", "(11) 3333-2222")
    save_setting(database, "salon_whatsapp", "(11) 99999-8888")
    save_setting(database, "salon_address", "Rua das Flores, 123")

    payment = finance.list_payments()[0]
    pdf_path = receipt_service.generate_receipt(payment.payment_id)

    assert pdf_path.exists()
    assert pdf_path.parent == paths.receipts_dir
    text = extract_pdf_text(pdf_path)
    assert "SalonFlow Premium" in text
    assert "Maria" in text
    assert "Ana" in text
    assert "Corte premium" in text
    assert "Servico" in text
    assert "Profissional" in text
    assert "Pix" in text
    assert "RCB-" in text
    assert "R$ 200,00" in text
    assert "R$ 20,00" in text
    assert "R$ 180,00" in text
    assert "20/08/2026" in text
    assert "14:30" in text or "2026 14:30" in text


def test_receipt_generation_supports_logo_and_custom_target_path(tmp_path) -> None:
    database, salon, finance, receipt_service, _paths = build_services(tmp_path)
    seed_paid_appointment(salon, finance)
    logo_path = tmp_path / "logo.png"
    logo_path.write_bytes(base64.b64decode(PNG_PIXEL_BASE64))
    save_setting(database, "salon_logo_path", str(logo_path))

    payment = finance.list_payments()[0]
    custom_path = tmp_path / "exports" / "recibo-personalizado.pdf"
    pdf_path = receipt_service.generate_receipt(payment.payment_id, custom_path)

    assert pdf_path == custom_path
    assert pdf_path.exists()
    assert "Maria" in extract_pdf_text(pdf_path)


def test_receipt_reprint_old_payment_and_history_listing(tmp_path) -> None:
    _database, salon, finance, receipt_service, _paths = build_services(tmp_path)
    seed_paid_appointment(salon, finance)
    second_client = salon.add_client("Julia")
    second_professional = salon.add_professional("Bia", "11777777777", "Escova", True)
    second_service = salon.add_service("Escova glow", "Cabelo", 45, 120.0, True)
    second_appointment = salon.create_appointment(
        second_client.client_id,
        second_professional.professional_id,
        second_service.service_id,
        "2026-08-21",
        "10:00",
        45,
        120.0,
        "Confirmado",
        "",
    )
    finance.finalize_appointment_with_payment(
        appointment_id=second_appointment.appointment_id,
        payment_method="Dinheiro",
        commission_percentage=Decimal("35.00"),
        payment_date="2026-08-21",
        received_amount=Decimal("120.00"),
    )

    payments = list(reversed(finance.list_payments()))
    first_payment_id = payments[0].payment_id
    pdf_path = receipt_service.generate_receipt(first_payment_id)
    receipts = receipt_service.list_receipts()

    assert pdf_path.exists()
    assert any(item.payment_id == first_payment_id for item in receipts)
    assert "Maria" in extract_pdf_text(pdf_path)


def test_receipt_rejects_nonexistent_payment(tmp_path) -> None:
    _database, _salon, _finance, receipt_service, _paths = build_services(tmp_path)
    with pytest.raises(ValueError, match="payment id not found"):
        receipt_service.generate_receipt(9999)


def test_receipt_for_avulso_uses_description_instead_of_fake_service(tmp_path) -> None:
    database, salon, finance, receipt_service, _paths = build_services(tmp_path)
    client = salon.add_client("Teste Avulso")
    receivable = finance.create_receivable(
        client_id=client.client_id,
        description="Pacote de manutencao",
        category="Avulso",
        amount=Decimal("100.00"),
        issue_date="2026-08-10",
        due_date="2026-08-10",
        payment_method="Dinheiro",
    )[0]
    finance.receive_receivable(
        receivable_id=receivable.receivable_id,
        received_amount=Decimal("100.00"),
        payment_date="2026-08-10",
        payment_method="Dinheiro",
    )

    payment = finance.list_payments()[0]
    record = finance.get_receipt_record(payment.payment_id)
    pdf_path = receipt_service.generate_receipt(payment.payment_id)
    text = extract_pdf_text(pdf_path)

    assert record.appointment_id is None
    assert record.service_label == "Descricao"
    assert record.service_name == "Pacote de manutencao"
    assert record.professional_name == "Nao se aplica"
    assert "Descricao" in text
    assert "Pacote de manutencao" in text
    assert "Profissional" not in text
