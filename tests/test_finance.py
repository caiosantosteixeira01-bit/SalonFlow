import sqlite3
from decimal import Decimal
from pathlib import Path

from salao.database import Database
from salao.finance import FinanceService
from salao.salon import SalonService


def build_services(tmp_path):
    database = Database(tmp_path / "salon.db")
    return SalonService(database), FinanceService(database)


def seed_base_entities(salon: SalonService):
    client = salon.add_client("Maria", "11999999999", "11999999999", "maria@email.com", "1995-06-10", "")
    professional = salon.add_professional("Ana", "11888888888", "Coloracao", True)
    service_item = salon.add_service("Coloracao", "Cabelo", 120, 250.0, True)
    appointment = salon.create_appointment(
        client.client_id,
        professional.professional_id,
        service_item.service_id,
        "2026-08-20",
        "14:00",
        120,
        250.0,
        "Confirmado",
        "",
    )
    return client, professional, service_item, appointment


def test_financial_finalize_appointment_flow(tmp_path) -> None:
    salon, finance = build_services(tmp_path)
    _, professional, _, appointment = seed_base_entities(salon)
    result = finance.finalize_appointment_with_payment(
        appointment_id=appointment.appointment_id,
        payment_method="Pix",
        commission_percentage=Decimal("40.00"),
        payment_date="2026-08-20",
        received_amount=Decimal("250.00"),
    )
    updated = salon.get_appointment(appointment.appointment_id)
    overview = finance.financial_overview("2026-08-20")
    commissions = finance.commission_service.list_commissions()
    cash_entries = finance.cash_service.list_entries()
    assert updated.status == "Concluido"
    assert result["receivable"].status == "Pago"
    assert overview["receitas_mes"] == Decimal("250.00")
    assert commissions[0].professional_id == professional.professional_id
    assert commissions[0].commission_amount == Decimal("100.00")
    assert cash_entries[0]["amount"] == Decimal("250.00")


def test_receivable_partial_payment_flow(tmp_path) -> None:
    salon, finance = build_services(tmp_path)
    client = salon.add_client("Maria")
    receivable = finance.create_receivable(
        client_id=client.client_id,
        description="Pacote premium",
        category="Pacotes",
        amount=Decimal("500.00"),
        issue_date="2026-08-10",
        due_date="2026-08-20",
        payment_method="Pix",
    )[0]
    partial = finance.receive_receivable(
        receivable_id=receivable.receivable_id,
        received_amount=Decimal("200.00"),
        payment_date="2026-08-11",
        payment_method="Pix",
    )
    assert partial.status == "Parcial"
    assert partial.remaining_amount == Decimal("300.00")
    paid = finance.receive_receivable(
        receivable_id=receivable.receivable_id,
        received_amount=Decimal("300.00"),
        payment_date="2026-08-12",
        payment_method="Dinheiro",
    )
    assert paid.status == "Pago"
    assert paid.remaining_amount == Decimal("0.00")


def test_installment_split_matches_original_total(tmp_path) -> None:
    salon, finance = build_services(tmp_path)
    client = salon.add_client("Joana")
    installments = finance.create_receivable(
        client_id=client.client_id,
        description="Tratamento anual",
        category="Pacotes",
        amount=Decimal("1000.00"),
        issue_date="2026-08-10",
        due_date="2026-08-20",
        payment_method="Cartao de credito",
        installment_count=3,
    )
    total = sum((item.total_amount for item in installments), Decimal("0.00"))
    assert len(installments) == 3
    assert total == Decimal("1000.00")


def test_overdue_receivable_status(tmp_path) -> None:
    salon, finance = build_services(tmp_path)
    client = salon.add_client("Carla")
    receivable = finance.create_receivable(
        client_id=client.client_id,
        description="Coloracao especial",
        category="Atendimento",
        amount=Decimal("180.00"),
        issue_date="2026-07-01",
        due_date="2026-07-10",
        payment_method="Pix",
    )[0]
    refreshed = finance.get_receivable(receivable.receivable_id)
    assert refreshed.status == "Atrasado"


def test_cancelled_appointment_does_not_generate_finance(tmp_path) -> None:
    salon, finance = build_services(tmp_path)
    _, _, _, appointment = seed_base_entities(salon)
    salon.cancel_appointment(appointment.appointment_id)
    try:
        finance.finalize_appointment_with_payment(
            appointment_id=appointment.appointment_id,
            payment_method="Pix",
            commission_percentage=Decimal("40.00"),
            payment_date="2026-08-20",
            received_amount=Decimal("250.00"),
        )
    except ValueError as exc:
        assert "cancelled appointment" in str(exc)
    else:
        raise AssertionError("Expected cancelled appointment protection")


def test_financial_rollback_on_failure(tmp_path) -> None:
    salon, finance = build_services(tmp_path)
    _, _, _, appointment = seed_base_entities(salon)
    try:
        finance.finalize_appointment_with_payment(
            appointment_id=appointment.appointment_id,
            payment_method="Pix",
            commission_percentage=Decimal("40.00"),
            payment_date="2026-08-20",
            received_amount=Decimal("250.00"),
            simulate_failure_after_payment=True,
        )
    except RuntimeError:
        pass
    else:
        raise AssertionError("Expected simulated rollback")
    assert finance.list_payments() == []
    assert finance.cash_service.list_entries() == []
    assert finance.list_receivables() == []
    assert salon.get_appointment(appointment.appointment_id).status == "Confirmado"


def test_commission_payment_generates_cash_output(tmp_path) -> None:
    salon, finance = build_services(tmp_path)
    _, _, _, appointment = seed_base_entities(salon)
    finance.finalize_appointment_with_payment(
        appointment_id=appointment.appointment_id,
        payment_method="Pix",
        commission_percentage=Decimal("40.00"),
        payment_date="2026-08-20",
        received_amount=Decimal("250.00"),
    )
    commission = finance.commission_service.list_commissions()[0]
    paid = finance.pay_commission(
        commission_id=commission.commission_id,
        payment_date="2026-08-21",
        payment_method="Pix",
        notes="Repasse semanal",
    )
    assert paid.status == "Pago"
    cash_entries = finance.cash_service.list_entries()
    assert any(entry["entry_type"] == "Saida" and entry["source"] == "Comissao" for entry in cash_entries)


def test_backup_created_with_success_and_contains_data(tmp_path) -> None:
    salon, finance = build_services(tmp_path)
    seed_base_entities(salon)
    target = tmp_path / "backups" / "salonflow.db"
    backup_path = finance.create_backup(target)
    assert backup_path.exists()
    assert backup_path.suffix == ".db"
    with sqlite3.connect(backup_path) as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()}
        clients_count = conn.execute("SELECT COUNT(*) FROM clients").fetchone()[0]
    assert "appointments" in tables
    assert clients_count >= 1


def test_backup_of_empty_database_is_valid(tmp_path) -> None:
    _, finance = build_services(tmp_path)
    backup_path = finance.create_backup(tmp_path / "empty-backup.db")
    with sqlite3.connect(backup_path) as conn:
        quick_check = conn.execute("PRAGMA quick_check").fetchone()[0]
        appointments_count = conn.execute("SELECT COUNT(*) FROM appointments").fetchone()[0]
    assert str(quick_check).lower() == "ok"
    assert appointments_count == 0


def test_backup_accepts_directory_destination(tmp_path) -> None:
    _, finance = build_services(tmp_path)
    backup_dir = tmp_path / "nested" / "backup-dir"
    backup_path = finance.create_backup(backup_dir)
    assert backup_path.parent == backup_dir
    assert backup_path.exists()


def test_backup_does_not_overwrite_existing_file(tmp_path) -> None:
    _, finance = build_services(tmp_path)
    target = tmp_path / "existing-backup.db"
    target.write_text("placeholder", encoding="utf-8")
    backup_path = finance.create_backup(target)
    assert backup_path != target
    assert target.read_text(encoding="utf-8") == "placeholder"
    assert backup_path.exists()


def test_restore_rejects_invalid_file(tmp_path) -> None:
    _, finance = build_services(tmp_path)
    invalid_file = tmp_path / "invalid.db"
    invalid_file.write_text("nao e sqlite", encoding="utf-8")
    try:
        finance.restore_backup(invalid_file)
    except ValueError as exc:
        assert "not a valid sqlite database" in str(exc) or "failed integrity check" in str(exc)
    else:
        raise AssertionError("Expected invalid restore file protection")


def test_restore_rejects_missing_file(tmp_path) -> None:
    _, finance = build_services(tmp_path)
    try:
        finance.restore_backup(tmp_path / "missing.db")
    except ValueError as exc:
        assert "backup file not found" in str(exc)
    else:
        raise AssertionError("Expected missing restore file protection")


def test_restore_cycle_preserves_backup_state_and_creates_safety_copy(tmp_path) -> None:
    salon, finance = build_services(tmp_path)
    client_a = salon.add_client("Cliente A")
    backup_path = finance.create_backup(tmp_path / "restore-cycle.db")
    client_b = salon.add_client("Cliente B")
    assert any(client.name == "Cliente B" for client in salon.list_clients())
    safety_backup = finance.restore_backup(backup_path)
    restored_salon = SalonService(Database(tmp_path / "salon.db"))
    client_names = [client.name for client in restored_salon.list_clients()]
    assert "Cliente A" in client_names
    assert "Cliente B" not in client_names
    assert safety_backup.exists()
    with sqlite3.connect(safety_backup) as conn:
        names_before_restore = {row[0] for row in conn.execute("SELECT name FROM clients").fetchall()}
    assert "Cliente B" in names_before_restore


def test_concluded_appointment_cannot_be_finalized_twice(tmp_path) -> None:
    salon, finance = build_services(tmp_path)
    _, _, _, appointment = seed_base_entities(salon)
    finance.finalize_appointment_with_payment(
        appointment_id=appointment.appointment_id,
        payment_method="Pix",
        commission_percentage=Decimal("40.00"),
        payment_date="2026-08-20",
        received_amount=Decimal("250.00"),
    )
    payments_before = finance.list_payments()
    cash_before = finance.cash_service.list_entries()
    commissions_before = finance.commission_service.list_commissions()
    receipts_before = finance.list_receipt_records()
    overview_before = finance.financial_overview("2026-08-20")
    try:
        finance.finalize_appointment_with_payment(
            appointment_id=appointment.appointment_id,
            payment_method="Pix",
            commission_percentage=Decimal("40.00"),
            payment_date="2026-08-20",
            received_amount=Decimal("250.00"),
        )
    except ValueError as exc:
        assert "already finalized" in str(exc)
    else:
        raise AssertionError("Expected concluded appointment protection")
    assert len(finance.list_payments()) == len(payments_before)
    assert len(finance.cash_service.list_entries()) == len(cash_before)
    assert len(finance.commission_service.list_commissions()) == len(commissions_before)
    assert len(finance.list_receipt_records()) == len(receipts_before)
    assert finance.financial_overview("2026-08-20")["receitas_mes"] == overview_before["receitas_mes"]


def test_consecutive_finalize_calls_remain_consistent(tmp_path) -> None:
    salon, finance = build_services(tmp_path)
    _, _, _, appointment = seed_base_entities(salon)
    first = finance.finalize_appointment_with_payment(
        appointment_id=appointment.appointment_id,
        payment_method="Pix",
        commission_percentage=Decimal("40.00"),
        payment_date="2026-08-20",
        received_amount=Decimal("250.00"),
    )
    assert first["appointment"].status == "Concluido"
    try:
        finance.finalize_appointment_with_payment(
            appointment_id=appointment.appointment_id,
            payment_method="Pix",
            commission_percentage=Decimal("40.00"),
            payment_date="2026-08-20",
            received_amount=Decimal("250.00"),
        )
    except ValueError as exc:
        assert "already finalized" in str(exc)
    else:
        raise AssertionError("Expected second finalize protection")
    assert len(finance.list_payments()) == 1
    assert len(finance.cash_service.list_entries()) == 1
    assert len(finance.commission_service.list_commissions()) == 1
    assert salon.get_appointment(appointment.appointment_id).status == "Concluido"
