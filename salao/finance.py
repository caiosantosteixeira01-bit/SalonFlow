from __future__ import annotations

import json
import os
import sqlite3
from abc import ABC, abstractmethod
from dataclasses import asdict
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from .database import Database
from .models import Appointment, CommissionRecord, PayableAccount, PaymentRecord, ReceiptRecord, ReceivableAccount
from .salon import SalonService

TWOPLACES = Decimal("0.01")
PAYMENT_METHODS = ("Dinheiro", "Pix", "Cartao de debito", "Cartao de credito")
RECEIVABLE_STATUSES = ("Pendente", "Pago", "Parcial", "Atrasado", "Cancelado")
PAYABLE_STATUSES = ("Pendente", "Pago", "Atrasado", "Cancelado")
BILLING_STATUSES = ("Pendente", "Pago", "Vencido", "Cancelado")
REQUIRED_SQLITE_TABLES = {
    "clients",
    "professionals",
    "services",
    "appointments",
    "receivable_accounts",
    "payable_accounts",
    "payments",
    "cash_sessions",
    "cash_entries",
    "commissions",
    "billing_charges",
    "financial_audit_log",
    "audit_log",
    "app_settings",
}


def parse_money(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value.quantize(TWOPLACES, rounding=ROUND_HALF_UP)
    if isinstance(value, (int, float)):
        return Decimal(str(value)).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
    text = str(value).strip().replace("R$", "").replace(".", "").replace(",", ".")
    if not text:
        return Decimal("0.00")
    return Decimal(text).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def money_to_cents(value: object) -> int:
    return int((parse_money(value) * 100).to_integral_value(rounding=ROUND_HALF_UP))


def cents_to_money(value: int | str | None) -> Decimal:
    cents = int(value or 0)
    return (Decimal(cents) / Decimal("100")).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def split_amount(amount: object, parts: int) -> list[int]:
    total_cents = money_to_cents(amount)
    if parts <= 0:
        raise ValueError("installment count must be positive")
    base = total_cents // parts
    remainder = total_cents % parts
    return [base + (1 if index < remainder else 0) for index in range(parts)]


class BillingProvider(ABC):
    @abstractmethod
    def issue_charge(self, payload: dict[str, object]) -> dict[str, object]:
        raise NotImplementedError

    @abstractmethod
    def cancel_charge(self, reference: str) -> dict[str, object]:
        raise NotImplementedError

    @abstractmethod
    def query_charge(self, reference: str) -> dict[str, object]:
        raise NotImplementedError

    @abstractmethod
    def generate_pix(self, payload: dict[str, object]) -> dict[str, object]:
        raise NotImplementedError

    @abstractmethod
    def query_pix(self, reference: str) -> dict[str, object]:
        raise NotImplementedError


class LocalBillingProvider(BillingProvider):
    def issue_charge(self, payload: dict[str, object]) -> dict[str, object]:
        return {"provider": "local-control", "status": "pending", "reference": payload.get("document_number", "")}

    def cancel_charge(self, reference: str) -> dict[str, object]:
        return {"provider": "local-control", "status": "cancelled", "reference": reference}

    def query_charge(self, reference: str) -> dict[str, object]:
        return {"provider": "local-control", "status": "pending", "reference": reference}

    def generate_pix(self, payload: dict[str, object]) -> dict[str, object]:
        return {"provider": "local-control", "status": "pending", "reference": payload.get("reference", "")}

    def query_pix(self, reference: str) -> dict[str, object]:
        return {"provider": "local-control", "status": "pending", "reference": reference}


class CashService:
    def __init__(self, database: Database):
        self.database = database

    def get_open_session_id(self) -> int | None:
        row = self.database.fetchone("SELECT id FROM cash_sessions WHERE status = 'Aberto' ORDER BY id DESC LIMIT 1")
        return int(row["id"]) if row else None

    def open_cash(self, opening_balance: object = Decimal("0.00"), notes: str = "") -> int:
        open_session = self.get_open_session_id()
        if open_session is not None:
            return open_session
        cents = money_to_cents(opening_balance)
        cursor = self.database.execute(
            """
            INSERT INTO cash_sessions (status, opening_balance_cents, expected_balance_cents, notes)
            VALUES ('Aberto', ?, ?, ?)
            """,
            (cents, cents, notes.strip()),
        )
        return int(cursor.lastrowid)

    def add_entry(
        self,
        entry_type: str,
        description: str,
        amount: object,
        payment_method: str = "",
        source: str = "",
        reference_type: str = "",
        reference_id: int | None = None,
        notes: str = "",
        session_id: int | None = None,
        conn=None,
    ) -> int:
        session = session_id if session_id is not None else self.get_open_session_id()
        amount_cents = money_to_cents(amount)
        target = conn if conn is not None else self.database
        if conn is not None:
            cursor = conn.execute(
                """
                INSERT INTO cash_entries (
                    session_id, entry_type, description, amount_cents, payment_method,
                    source, reference_type, reference_id, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (session, entry_type, description.strip(), amount_cents, payment_method, source, reference_type, reference_id, notes.strip()),
            )
        else:
            cursor = target.execute(
                """
                INSERT INTO cash_entries (
                    session_id, entry_type, description, amount_cents, payment_method,
                    source, reference_type, reference_id, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (session, entry_type, description.strip(), amount_cents, payment_method, source, reference_type, reference_id, notes.strip()),
            )
        if session:
            self._refresh_session_expected(session, conn=conn)
        return int(cursor.lastrowid)

    def _refresh_session_expected(self, session_id: int, conn=None) -> None:
        source = conn if conn is not None else self.database
        fetchone = source.execute if conn is None else conn.execute
        row = (conn.execute("SELECT opening_balance_cents FROM cash_sessions WHERE id = ?", (session_id,)).fetchone()
               if conn is not None else self.database.fetchone("SELECT opening_balance_cents FROM cash_sessions WHERE id = ?", (session_id,)))
        if row is None:
            return
        entries = (conn.execute("SELECT entry_type, amount_cents FROM cash_entries WHERE session_id = ?", (session_id,)).fetchall()
                   if conn is not None else self.database.fetchall("SELECT entry_type, amount_cents FROM cash_entries WHERE session_id = ?", (session_id,)))
        expected = int(row["opening_balance_cents"])
        for entry in entries:
            if entry["entry_type"] in {"Entrada", "Suprimento"}:
                expected += int(entry["amount_cents"])
            elif entry["entry_type"] in {"Saida", "Sangria"}:
                expected -= int(entry["amount_cents"])
        if conn is not None:
            conn.execute("UPDATE cash_sessions SET expected_balance_cents = ? WHERE id = ?", (expected, session_id))
        else:
            self.database.execute("UPDATE cash_sessions SET expected_balance_cents = ? WHERE id = ?", (expected, session_id))

    def close_cash(self, counted_balance: object, notes: str = "") -> dict[str, Decimal]:
        session_id = self.get_open_session_id()
        if session_id is None:
            raise ValueError("no open cash session")
        counted_cents = money_to_cents(counted_balance)
        row = self.database.fetchone("SELECT expected_balance_cents FROM cash_sessions WHERE id = ?", (session_id,))
        expected_cents = int(row["expected_balance_cents"])
        difference_cents = counted_cents - expected_cents
        self.database.execute(
            """
            UPDATE cash_sessions
            SET status = 'Fechado', closed_at = CURRENT_TIMESTAMP, counted_balance_cents = ?,
                difference_cents = ?, notes = ?
            WHERE id = ?
            """,
            (counted_cents, difference_cents, notes.strip(), session_id),
        )
        return {
            "expected_balance": cents_to_money(expected_cents),
            "counted_balance": cents_to_money(counted_cents),
            "difference": cents_to_money(difference_cents),
        }

    def list_entries(self) -> list[dict[str, object]]:
        rows = self.database.fetchall("SELECT * FROM cash_entries ORDER BY id DESC")
        return [
            {
                "entry_id": int(row["id"]),
                "session_id": int(row["session_id"]) if row["session_id"] is not None else None,
                "entry_type": str(row["entry_type"]),
                "description": str(row["description"]),
                "amount": cents_to_money(int(row["amount_cents"])),
                "payment_method": str(row["payment_method"]),
                "source": str(row["source"]),
                "created_at": str(row["created_at"]),
            }
            for row in rows
        ]


class CommissionService:
    def __init__(self, database: Database):
        self.database = database

    def create_for_appointment(
        self,
        appointment_id: int,
        professional_id: int,
        service_id: int,
        base_amount: object,
        percentage: object,
        commission_date: str,
        notes: str = "",
        conn=None,
    ) -> CommissionRecord:
        existing = (conn.execute("SELECT * FROM commissions WHERE appointment_id = ?", (appointment_id,)).fetchone()
                    if conn is not None else self.database.fetchone("SELECT * FROM commissions WHERE appointment_id = ?", (appointment_id,)))
        if existing:
            return self._row_to_commission(existing)
        percentage_decimal = Decimal(str(percentage)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        basis_points = int((percentage_decimal * 100).to_integral_value(rounding=ROUND_HALF_UP))
        base_cents = money_to_cents(base_amount)
        commission_cents = int((Decimal(base_cents) * percentage_decimal / Decimal("100")).to_integral_value(rounding=ROUND_HALF_UP))
        if conn is not None:
            cursor = conn.execute(
                """
                INSERT INTO commissions (
                    appointment_id, professional_id, service_id, base_amount_cents,
                    percentage_basis_points, commission_amount_cents, commission_date, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (appointment_id, professional_id, service_id, base_cents, basis_points, commission_cents, commission_date, notes.strip()),
            )
            row = conn.execute("SELECT * FROM commissions WHERE id = ?", (int(cursor.lastrowid),)).fetchone()
        else:
            cursor = self.database.execute(
                """
                INSERT INTO commissions (
                    appointment_id, professional_id, service_id, base_amount_cents,
                    percentage_basis_points, commission_amount_cents, commission_date, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (appointment_id, professional_id, service_id, base_cents, basis_points, commission_cents, commission_date, notes.strip()),
            )
            row = self.database.fetchone("SELECT * FROM commissions WHERE id = ?", (int(cursor.lastrowid),))
        return self._row_to_commission(row)

    def list_commissions(self) -> list[CommissionRecord]:
        return [self._row_to_commission(row) for row in self.database.fetchall("SELECT * FROM commissions ORDER BY commission_date DESC, id DESC")]

    def mark_as_paid(self, commission_id: int, payment_reference: str = "", notes: str = "", conn=None) -> CommissionRecord:
        existing = (conn.execute("SELECT * FROM commissions WHERE id = ?", (commission_id,)).fetchone()
                    if conn is not None else self.database.fetchone("SELECT * FROM commissions WHERE id = ?", (commission_id,)))
        if existing is None:
            raise ValueError("commission id not found")
        if str(existing["status"]) == "Pago":
            return self._row_to_commission(existing)
        if conn is not None:
            conn.execute(
                """
                UPDATE commissions
                SET status = 'Pago', payment_reference = ?, notes = ?
                WHERE id = ?
                """,
                (payment_reference.strip(), notes.strip(), commission_id),
            )
            updated = conn.execute("SELECT * FROM commissions WHERE id = ?", (commission_id,)).fetchone()
        else:
            self.database.execute(
                """
                UPDATE commissions
                SET status = 'Pago', payment_reference = ?, notes = ?
                WHERE id = ?
                """,
                (payment_reference.strip(), notes.strip(), commission_id),
            )
            updated = self.database.fetchone("SELECT * FROM commissions WHERE id = ?", (commission_id,))
        return self._row_to_commission(updated)

    def _row_to_commission(self, row) -> CommissionRecord:
        return CommissionRecord(
            appointment_id=int(row["appointment_id"]),
            professional_id=int(row["professional_id"]),
            service_id=int(row["service_id"]),
            base_amount=cents_to_money(int(row["base_amount_cents"])),
            commission_amount=cents_to_money(int(row["commission_amount_cents"])),
            percentage_basis_points=int(row["percentage_basis_points"]),
            commission_date=str(row["commission_date"]),
            status=str(row["status"]),
            commission_id=int(row["id"]),
        )


class BillingService:
    def __init__(self, database: Database, provider: BillingProvider | None = None):
        self.database = database
        self.provider = provider or LocalBillingProvider()

    def create_charge(
        self,
        payer_name: str,
        description: str,
        amount: object,
        issue_date: str,
        due_date: str,
        receivable_id: int | None = None,
        document: str = "",
        document_number: str = "",
        digitable_line: str = "",
        notes: str = "",
    ) -> int:
        amount_cents = money_to_cents(amount)
        cursor = self.database.execute(
            """
            INSERT INTO billing_charges (
                receivable_id, payer_name, document, description, amount_cents, issue_date, due_date,
                document_number, digitable_line, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (receivable_id, payer_name.strip(), document.strip(), description.strip(), amount_cents, issue_date, due_date, document_number.strip(), digitable_line.strip(), notes.strip()),
        )
        return int(cursor.lastrowid)

    def list_charges(self) -> list[dict[str, object]]:
        rows = self.database.fetchall("SELECT * FROM billing_charges ORDER BY due_date, id DESC")
        today = date.today().isoformat()
        result: list[dict[str, object]] = []
        for row in rows:
            status = str(row["status"])
            if status == "Pendente" and str(row["due_date"]) < today:
                status = "Vencido"
            result.append(
                {
                    "billing_id": int(row["id"]),
                    "payer_name": str(row["payer_name"]),
                    "description": str(row["description"]),
                    "amount": cents_to_money(int(row["amount_cents"])),
                    "issue_date": str(row["issue_date"]),
                    "due_date": str(row["due_date"]),
                    "status": status,
                    "provider_name": str(row["provider_name"]),
                }
            )
        return result


class FinanceService:
    def __init__(self, database: Database):
        self.database = database
        self.cash_service = CashService(database)
        self.commission_service = CommissionService(database)
        self.billing_service = BillingService(database)

    def create_receivable(
        self,
        client_id: int,
        description: str,
        category: str,
        amount: object,
        issue_date: str,
        due_date: str,
        payment_method: str,
        installment_count: int = 1,
        notes: str = "",
        appointment_id: int | None = None,
    ) -> list[ReceivableAccount]:
        if not description.strip():
            raise ValueError("receivable description cannot be empty")
        SalonService(self.database).get_client(client_id)
        issue = self._normalize_date(issue_date)
        due = self._normalize_date(due_date)
        amounts = split_amount(amount, installment_count)
        due_base = datetime.strptime(due, "%Y-%m-%d").date()
        created: list[ReceivableAccount] = []
        parent_id: int | None = None
        for index, cents in enumerate(amounts, start=1):
            current_due = due_base + timedelta(days=(index - 1) * 30) if installment_count > 1 else due_base
            label = f"{index}/{installment_count}" if installment_count > 1 else "1/1"
            cursor = self.database.execute(
                """
                INSERT INTO receivable_accounts (
                    parent_id, appointment_id, client_id, description, category,
                    total_amount_cents, remaining_amount_cents, issue_date, due_date,
                    payment_method, installment_label, installment_number, installment_count, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    parent_id,
                    appointment_id,
                    client_id,
                    description.strip(),
                    category.strip(),
                    cents,
                    cents,
                    issue,
                    current_due.isoformat(),
                    payment_method.strip(),
                    label,
                    index,
                    installment_count,
                    notes.strip(),
                ),
            )
            current_id = int(cursor.lastrowid)
            if parent_id is None:
                parent_id = current_id
                self.database.execute("UPDATE receivable_accounts SET parent_id = ? WHERE id = ?", (parent_id, parent_id))
            row = self.database.fetchone("SELECT * FROM receivable_accounts WHERE id = ?", (current_id,))
            created.append(self._row_to_receivable(row))
        self._audit("CREATE", "receivable_accounts", created[0].receivable_id or 0, "", json.dumps({"count": len(created)}, ensure_ascii=True), "Nova conta a receber")
        return created

    def receive_receivable(
        self,
        receivable_id: int,
        received_amount: object,
        payment_date: str,
        payment_method: str,
        discount: object = Decimal("0.00"),
        interest: object = Decimal("0.00"),
        notes: str = "",
        card_fee: object = Decimal("0.00"),
    ) -> ReceivableAccount:
        row = self.database.fetchone("SELECT * FROM receivable_accounts WHERE id = ?", (receivable_id,))
        if row is None:
            raise ValueError("receivable id not found")
        payment = parse_money(received_amount)
        discount_money = parse_money(discount)
        interest_money = parse_money(interest)
        fee_money = parse_money(card_fee)
        if payment <= Decimal("0.00"):
            raise ValueError("received amount must be positive")
        current_remaining = cents_to_money(int(row["remaining_amount_cents"]))
        settlement = payment + discount_money - interest_money
        if settlement <= Decimal("0.00"):
            raise ValueError("invalid settlement amount")
        if settlement > current_remaining:
            raise ValueError("received amount exceeds remaining balance")
        normalized_date = self._normalize_date(payment_date)
        new_remaining = current_remaining - settlement
        new_status = "Pago" if new_remaining == Decimal("0.00") else "Parcial"
        gross = payment + interest_money
        net = payment - fee_money
        with self.database.transaction() as conn:
            conn.execute(
                """
                UPDATE receivable_accounts
                SET remaining_amount_cents = ?, status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (money_to_cents(new_remaining), new_status, receivable_id),
            )
            cursor = conn.execute(
                """
                INSERT INTO payments (
                    kind, receivable_id, appointment_id, client_id, description, amount_cents,
                    discount_cents, interest_cents, gross_amount_cents, net_amount_cents,
                    payment_date, payment_method, reference, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "receipt",
                    receivable_id,
                    row["appointment_id"],
                    row["client_id"],
                    row["description"],
                    money_to_cents(payment),
                    money_to_cents(discount_money),
                    money_to_cents(interest_money),
                    money_to_cents(gross),
                    money_to_cents(net),
                    normalized_date,
                    payment_method.strip(),
                    str(row["installment_label"]),
                    notes.strip(),
                ),
            )
            payment_id = int(cursor.lastrowid)
            self.cash_service.add_entry(
                entry_type="Entrada",
                description=f"Recebimento: {row['description']}",
                amount=payment,
                payment_method=payment_method,
                source="Conta a receber",
                reference_type="receivable",
                reference_id=receivable_id,
                notes=notes,
                conn=conn,
            )
            self._audit_conn(conn, "RECEIVE", "receivable_accounts", receivable_id, str(current_remaining), str(new_remaining), notes or "Recebimento")
            if payment_id <= 0:
                raise RuntimeError("payment record creation failed")
        updated = self.database.fetchone("SELECT * FROM receivable_accounts WHERE id = ?", (receivable_id,))
        return self._row_to_receivable(updated)

    def create_payable(
        self,
        description: str,
        beneficiary: str,
        category: str,
        amount: object,
        issue_date: str,
        due_date: str,
        payment_method: str,
        installment_count: int = 1,
        recurring_key: str = "",
        notes: str = "",
    ) -> list[PayableAccount]:
        if not description.strip():
            raise ValueError("payable description cannot be empty")
        if not beneficiary.strip():
            raise ValueError("beneficiary cannot be empty")
        issue = self._normalize_date(issue_date)
        due = self._normalize_date(due_date)
        amounts = split_amount(amount, installment_count)
        due_base = datetime.strptime(due, "%Y-%m-%d").date()
        created: list[PayableAccount] = []
        parent_id: int | None = None
        for index, cents in enumerate(amounts, start=1):
            current_due = due_base + timedelta(days=(index - 1) * 30) if installment_count > 1 else due_base
            label = f"{index}/{installment_count}" if installment_count > 1 else "1/1"
            cursor = self.database.execute(
                """
                INSERT INTO payable_accounts (
                    parent_id, description, beneficiary, category, total_amount_cents, remaining_amount_cents,
                    issue_date, due_date, payment_method, installment_label, installment_number,
                    installment_count, recurring_key, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    parent_id,
                    description.strip(),
                    beneficiary.strip(),
                    category.strip(),
                    cents,
                    cents,
                    issue,
                    current_due.isoformat(),
                    payment_method.strip(),
                    label,
                    index,
                    installment_count,
                    recurring_key.strip(),
                    notes.strip(),
                ),
            )
            current_id = int(cursor.lastrowid)
            if parent_id is None:
                parent_id = current_id
                self.database.execute("UPDATE payable_accounts SET parent_id = ? WHERE id = ?", (parent_id, parent_id))
            row = self.database.fetchone("SELECT * FROM payable_accounts WHERE id = ?", (current_id,))
            created.append(self._row_to_payable(row))
        self._audit("CREATE", "payable_accounts", created[0].payable_id or 0, "", json.dumps({"count": len(created)}, ensure_ascii=True), "Nova conta a pagar")
        return created

    def pay_payable(
        self,
        payable_id: int,
        paid_amount: object,
        payment_date: str,
        payment_method: str,
        notes: str = "",
    ) -> PayableAccount:
        row = self.database.fetchone("SELECT * FROM payable_accounts WHERE id = ?", (payable_id,))
        if row is None:
            raise ValueError("payable id not found")
        payment = parse_money(paid_amount)
        if payment <= Decimal("0.00"):
            raise ValueError("paid amount must be positive")
        current_remaining = cents_to_money(int(row["remaining_amount_cents"]))
        if payment > current_remaining:
            raise ValueError("paid amount exceeds remaining balance")
        normalized_date = self._normalize_date(payment_date)
        new_remaining = current_remaining - payment
        new_status = "Pago" if new_remaining == Decimal("0.00") else "Pendente"
        with self.database.transaction() as conn:
            conn.execute(
                """
                UPDATE payable_accounts
                SET remaining_amount_cents = ?, status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (money_to_cents(new_remaining), new_status, payable_id),
            )
            conn.execute(
                """
                INSERT INTO payments (
                    kind, payable_id, description, amount_cents, gross_amount_cents, net_amount_cents,
                    payment_date, payment_method, notes
                ) VALUES ('disbursement', ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payable_id,
                    row["description"],
                    money_to_cents(payment),
                    money_to_cents(payment),
                    money_to_cents(payment),
                    normalized_date,
                    payment_method.strip(),
                    notes.strip(),
                ),
            )
            self.cash_service.add_entry(
                entry_type="Saida",
                description=f"Pagamento: {row['description']}",
                amount=payment,
                payment_method=payment_method,
                source="Conta a pagar",
                reference_type="payable",
                reference_id=payable_id,
                notes=notes,
                conn=conn,
            )
            self._audit_conn(conn, "PAY", "payable_accounts", payable_id, str(current_remaining), str(new_remaining), notes or "Pagamento")
        updated = self.database.fetchone("SELECT * FROM payable_accounts WHERE id = ?", (payable_id,))
        return self._row_to_payable(updated)

    def finalize_appointment_with_payment(
        self,
        appointment_id: int,
        payment_method: str,
        commission_percentage: object,
        payment_date: str,
        received_amount: object | None = None,
        discount: object = Decimal("0.00"),
        interest: object = Decimal("0.00"),
        card_fee: object = Decimal("0.00"),
        notes: str = "",
        simulate_failure_after_payment: bool = False,
    ) -> dict[str, object]:
        appointment = SalonService(self.database).get_appointment(appointment_id)
        appointment_row = self.database.fetchone("SELECT * FROM appointments WHERE id = ?", (appointment_id,))
        if str(appointment.status) == "Cancelado":
            raise ValueError("cancelled appointment cannot generate revenue")
        if str(appointment.status) == "Concluido":
            raise ValueError("appointment already finalized")
        payment_amount = parse_money(received_amount if received_amount is not None else appointment.price)
        payment_day = self._normalize_date(payment_date)
        existing_receivable = self.database.fetchone(
            "SELECT id FROM receivable_accounts WHERE appointment_id = ? AND status != 'Cancelado' ORDER BY id LIMIT 1",
            (appointment_id,),
        )
        with self.database.transaction() as conn:
            existing_payment = conn.execute(
                "SELECT id FROM payments WHERE appointment_id = ? AND kind = 'receipt' LIMIT 1",
                (appointment_id,),
            ).fetchone()
            if existing_payment is not None:
                raise ValueError("appointment already finalized")
            if existing_receivable is None:
                cursor = conn.execute(
                    """
                    INSERT INTO receivable_accounts (
                        appointment_id, client_id, description, category, total_amount_cents,
                        remaining_amount_cents, issue_date, due_date, payment_method, installment_label,
                        installment_number, installment_count, notes, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, '1/1', 1, 1, ?, 'Pendente')
                    """,
                    (
                        appointment_id,
                        appointment.client_id,
                        f"Atendimento #{appointment_id}",
                        "Atendimento",
                        money_to_cents(appointment.price),
                        money_to_cents(appointment.price),
                        payment_day,
                        payment_day,
                        payment_method,
                        notes.strip(),
                    ),
                )
                receivable_id = int(cursor.lastrowid)
            else:
                receivable_id = int(existing_receivable["id"])
            receivable_row = conn.execute("SELECT * FROM receivable_accounts WHERE id = ?", (receivable_id,)).fetchone()
            current_remaining = cents_to_money(int(receivable_row["remaining_amount_cents"]))
            settlement = payment_amount + parse_money(discount) - parse_money(interest)
            if settlement > current_remaining:
                raise ValueError("received amount exceeds remaining balance")
            new_remaining = current_remaining - settlement
            new_status = "Pago" if new_remaining == Decimal("0.00") else "Parcial"
            conn.execute(
                """
                UPDATE receivable_accounts
                SET remaining_amount_cents = ?, status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (money_to_cents(new_remaining), new_status, receivable_id),
            )
            conn.execute(
                """
                INSERT INTO payments (
                    kind, receivable_id, appointment_id, client_id, description, amount_cents,
                    discount_cents, interest_cents, gross_amount_cents, net_amount_cents,
                    payment_date, payment_method, notes
                ) VALUES ('receipt', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    receivable_id,
                    appointment_id,
                    appointment.client_id,
                    f"Atendimento #{appointment_id}",
                    money_to_cents(payment_amount),
                    money_to_cents(discount),
                    money_to_cents(interest),
                    money_to_cents(payment_amount + parse_money(interest)),
                    money_to_cents(payment_amount - parse_money(card_fee)),
                    payment_day,
                    payment_method,
                    notes.strip(),
                ),
            )
            self.cash_service.add_entry(
                entry_type="Entrada",
                description=f"Atendimento #{appointment_id}",
                amount=payment_amount,
                payment_method=payment_method,
                source="Atendimento",
                reference_type="appointment",
                reference_id=appointment_id,
                notes=notes,
                conn=conn,
            )
            if simulate_failure_after_payment:
                raise RuntimeError("simulated rollback")
            conn.execute(
                "UPDATE appointments SET status = 'Concluido', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (appointment_id,),
            )
            commission = self.commission_service.create_for_appointment(
                appointment_id=appointment_id,
                professional_id=appointment.professional_id,
                service_id=appointment.service_id,
                base_amount=appointment.price,
                percentage=commission_percentage,
                commission_date=payment_day,
                notes="Comissao gerada no fechamento do atendimento.",
                conn=conn,
            )
            self._audit_conn(conn, "FINALIZE_APPOINTMENT", "appointments", appointment_id, appointment_row["status"], "Concluido", notes or "Pagamento integrado")
        updated_appointment = SalonService(self.database).get_appointment(appointment_id)
        return {
            "appointment": updated_appointment,
            "receivable": self.get_receivable(receivable_id),
            "commission": commission,
        }

    def get_receivable(self, receivable_id: int) -> ReceivableAccount:
        row = self.database.fetchone("SELECT * FROM receivable_accounts WHERE id = ?", (receivable_id,))
        if row is None:
            raise ValueError("receivable id not found")
        return self._row_to_receivable(row)

    def list_receivables(self) -> list[ReceivableAccount]:
        return [self._row_to_receivable(row) for row in self.database.fetchall("SELECT * FROM receivable_accounts ORDER BY due_date, id DESC")]

    def list_payables(self) -> list[PayableAccount]:
        return [self._row_to_payable(row) for row in self.database.fetchall("SELECT * FROM payable_accounts ORDER BY due_date, id DESC")]

    def list_receivables_for_appointment(self, appointment_id: int) -> list[ReceivableAccount]:
        rows = self.database.fetchall("SELECT * FROM receivable_accounts WHERE appointment_id = ? ORDER BY id", (appointment_id,))
        return [self._row_to_receivable(row) for row in rows]

    def appointment_has_financial_activity(self, appointment_id: int) -> bool:
        row = self.database.fetchone("SELECT id FROM payments WHERE appointment_id = ? LIMIT 1", (appointment_id,))
        return row is not None

    def pay_commission(
        self,
        commission_id: int,
        payment_date: str,
        payment_method: str,
        notes: str = "",
        create_cash_entry: bool = True,
    ) -> CommissionRecord:
        row = self.database.fetchone("SELECT * FROM commissions WHERE id = ?", (commission_id,))
        if row is None:
            raise ValueError("commission id not found")
        if str(row["status"]) == "Pago":
            return self.commission_service._row_to_commission(row)
        normalized_date = self._normalize_date(payment_date)
        commission_value = cents_to_money(int(row["commission_amount_cents"]))
        with self.database.transaction() as conn:
            updated = self.commission_service.mark_as_paid(
                commission_id=commission_id,
                payment_reference=normalized_date,
                notes=notes or "Pagamento de comissao.",
                conn=conn,
            )
            if create_cash_entry:
                self.cash_service.add_entry(
                    entry_type="Saida",
                    description=f"Pagamento de comissao #{commission_id}",
                    amount=commission_value,
                    payment_method=payment_method,
                    source="Comissao",
                    reference_type="commission",
                    reference_id=commission_id,
                    notes=notes,
                    conn=conn,
                )
            self._audit_conn(conn, "PAY_COMMISSION", "commissions", commission_id, "Pendente", "Pago", notes or "Pagamento de comissao")
        return updated

    def list_payments(self) -> list[PaymentRecord]:
        rows = self.database.fetchall("SELECT * FROM payments ORDER BY payment_date DESC, id DESC")
        return [
            PaymentRecord(
                kind=str(row["kind"]),
                description=str(row["description"]),
                amount=cents_to_money(int(row["amount_cents"])),
                gross_amount=cents_to_money(int(row["gross_amount_cents"])),
                net_amount=cents_to_money(int(row["net_amount_cents"])),
                payment_date=str(row["payment_date"]),
                payment_method=str(row["payment_method"]),
                status=str(row["status"]),
                notes=str(row["notes"]),
                payment_id=int(row["id"]),
            )
            for row in rows
        ]

    def get_receipt_settings(self) -> dict[str, str]:
        rows = self.database.fetchall(
            """
            SELECT setting_key, setting_value
            FROM app_settings
            WHERE setting_key IN (
                'salon_name',
                'salon_phone',
                'salon_whatsapp',
                'salon_email',
                'salon_address',
                'salon_document',
                'salon_logo_path'
            )
            """
        )
        values = {str(row["setting_key"]): str(row["setting_value"]) for row in rows}
        return {
            "salon_name": values.get("salon_name", ""),
            "salon_phone": values.get("salon_phone", ""),
            "salon_whatsapp": values.get("salon_whatsapp", ""),
            "salon_email": values.get("salon_email", ""),
            "salon_address": values.get("salon_address", ""),
            "salon_document": values.get("salon_document", ""),
            "salon_logo_path": values.get("salon_logo_path", ""),
        }

    def get_receipt_record(self, payment_id: int) -> ReceiptRecord:
        row = self.database.fetchone(
            """
            SELECT
                p.id,
                p.kind,
                p.receivable_id,
                p.appointment_id,
                p.description,
                p.amount_cents,
                p.discount_cents,
                p.gross_amount_cents,
                p.net_amount_cents,
                p.payment_date,
                p.payment_method,
                p.notes,
                p.created_at,
                c.name AS client_name,
                COALESCE(pr.name, '') AS professional_name,
                COALESCE(s.name, '') AS service_name,
                COALESCE(a.appointment_time, '') AS appointment_time,
                COALESCE(a.notes, '') AS appointment_notes,
                COALESCE(a.price, 0) AS appointment_price,
                COALESCE(r.total_amount_cents, 0) AS receivable_total_cents
            FROM payments p
            LEFT JOIN clients c ON c.id = p.client_id
            LEFT JOIN appointments a ON a.id = p.appointment_id
            LEFT JOIN professionals pr ON pr.id = a.professional_id
            LEFT JOIN services s ON s.id = a.service_id
            LEFT JOIN receivable_accounts r ON r.id = p.receivable_id
            WHERE p.id = ?
            """,
            (payment_id,),
        )
        if row is None:
            raise ValueError("payment id not found")
        if str(row["kind"]) != "receipt":
            raise ValueError("payment cannot generate receipt")
        original_amount = cents_to_money(int(row["receivable_total_cents"] or 0))
        if original_amount == Decimal("0.00"):
            original_amount = parse_money(row["appointment_price"] or 0)
        if original_amount == Decimal("0.00"):
            original_amount = cents_to_money(int(row["gross_amount_cents"] or 0))
        notes_parts = [str(row["notes"] or "").strip(), str(row["appointment_notes"] or "").strip()]
        notes = " | ".join(part for part in notes_parts if part)
        return ReceiptRecord(
            payment_id=int(row["id"]),
            receipt_number=f"RCB-{int(row['id']):06d}",
            created_at=str(row["created_at"]),
            payment_date=str(row["payment_date"]),
            appointment_time=str(row["appointment_time"] or ""),
            client_name=str(row["client_name"] or "Cliente nao identificado"),
            client_label="Cliente",
            professional_name=(
                str(row["professional_name"] or "Nao informado")
                if row["appointment_id"] is not None
                else "Nao se aplica"
            ),
            professional_label="Profissional" if row["appointment_id"] is not None else "Referencia",
            service_name=(
                str(row["service_name"] or row["description"] or "Servico")
                if row["appointment_id"] is not None
                else str(row["description"] or "Pagamento avulso")
            ),
            service_label="Servico" if row["appointment_id"] is not None else "Descricao",
            original_amount=original_amount,
            discount_amount=cents_to_money(int(row["discount_cents"] or 0)),
            paid_amount=cents_to_money(int(row["amount_cents"] or 0)),
            payment_method=str(row["payment_method"] or ""),
            notes=notes,
            appointment_id=int(row["appointment_id"]) if row["appointment_id"] is not None else None,
            receivable_id=int(row["receivable_id"]) if row["receivable_id"] is not None else None,
        )

    def list_receipt_records(self) -> list[ReceiptRecord]:
        rows = self.database.fetchall("SELECT id FROM payments WHERE kind = 'receipt' ORDER BY created_at DESC, id DESC")
        return [self.get_receipt_record(int(row["id"])) for row in rows]

    def financial_overview(self, reference_date: str | None = None) -> dict[str, object]:
        ref = datetime.strptime(reference_date, "%Y-%m-%d").date() if reference_date else date.today()
        month_start = ref.replace(day=1).isoformat()
        month_end = (ref.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        month_end_iso = month_end.isoformat()
        receivables = self.list_receivables()
        payables = self.list_payables()
        payments = self.list_payments()
        receipts_month = sum((payment.amount for payment in payments if payment.kind == "receipt" and month_start <= payment.payment_date <= month_end_iso), Decimal("0.00"))
        disbursements_month = sum((payment.amount for payment in payments if payment.kind == "disbursement" and month_start <= payment.payment_date <= month_end_iso), Decimal("0.00"))
        commissions_pending = sum((item.commission_amount for item in self.commission_service.list_commissions() if item.status == "Pendente"), Decimal("0.00"))
        a_receber = sum((item.remaining_amount for item in receivables if item.status != "Cancelado"), Decimal("0.00"))
        a_pagar = sum((item.remaining_amount for item in payables if item.status != "Cancelado"), Decimal("0.00"))
        vencidas_receber = [item for item in receivables if item.status in {"Pendente", "Parcial", "Atrasado"} and item.due_date < ref.isoformat()]
        vencidas_pagar = [item for item in payables if item.status in {"Pendente", "Atrasado"} and item.due_date < ref.isoformat()]
        week_end = (ref + timedelta(days=7)).isoformat()
        receber_semana = sum((item.remaining_amount for item in receivables if ref.isoformat() <= item.due_date <= week_end and item.status != "Pago"), Decimal("0.00"))
        pagar_semana = sum((item.remaining_amount for item in payables if ref.isoformat() <= item.due_date <= week_end and item.status != "Pago"), Decimal("0.00"))
        latest = [
            {
                "description": payment.description,
                "amount": payment.amount,
                "date": payment.payment_date,
                "kind": payment.kind,
                "method": payment.payment_method,
            }
            for payment in payments[:8]
        ]
        return {
            "receitas_mes": receipts_month,
            "despesas_mes": disbursements_month,
            "saldo": receipts_month - disbursements_month,
            "a_receber": a_receber,
            "a_pagar": a_pagar,
            "valores_atrasados": sum((item.remaining_amount for item in vencidas_receber), Decimal("0.00")) + sum((item.remaining_amount for item in vencidas_pagar), Decimal("0.00")),
            "comissoes_pendentes": commissions_pending,
            "receber_semana": receber_semana,
            "pagar_semana": pagar_semana,
            "alertas": [
                f"{len([item for item in receivables if item.due_date == ref.isoformat() and item.status != 'Pago'])} contas vencem hoje",
                f"{len(vencidas_receber)} contas a receber estao atrasadas",
                f"R$ {receber_semana} a receber esta semana",
                f"R$ {pagar_semana} a pagar esta semana",
            ],
            "ultimas_movimentacoes": latest,
        }

    def create_backup(self, destination: Path | str) -> Path:
        destination_path = self._resolve_backup_destination(destination)
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = destination_path.with_name(f"{destination_path.stem}.tmp{destination_path.suffix}")
        if temp_path.exists():
            temp_path.unlink()
        try:
            self._backup_database(self.database.db_path, temp_path)
            self._validate_sqlite_database(temp_path)
            temp_path.replace(destination_path)
        except Exception:
            if temp_path.exists():
                temp_path.unlink()
            raise
        return destination_path

    def restore_backup(self, source: Path | str) -> Path:
        source_path = Path(source)
        if not source_path.exists():
            raise ValueError("backup file not found")
        if source_path.stat().st_size <= 0:
            raise ValueError("backup file is empty")
        self._validate_sqlite_database(source_path)
        safety_backup = self.create_backup(
            self.database.db_path.parent / f"salonflow-pre-restore-{datetime.now().strftime('%Y%m%d-%H%M%S')}.db"
        )
        try:
            self._remove_sqlite_sidecars(self.database.db_path)
            self._restore_database(source_path, self.database.db_path)
            self._remove_sqlite_sidecars(self.database.db_path)
        except Exception:
            raise
        return safety_backup

    def _resolve_backup_destination(self, destination: Path | str) -> Path:
        destination_path = Path(destination)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        if destination_path.exists() and destination_path.is_dir():
            return destination_path / f"salonflow-backup-{timestamp}.db"
        if destination_path.suffix.lower() != ".db":
            return destination_path / f"salonflow-backup-{timestamp}.db"
        if destination_path.exists():
            return destination_path.with_name(f"{destination_path.stem}-{timestamp}{destination_path.suffix}")
        return destination_path

    def _backup_database(self, source_path: Path, destination_path: Path) -> None:
        source_conn = sqlite3.connect(source_path)
        destination_conn = sqlite3.connect(destination_path)
        try:
            source_conn.execute("PRAGMA wal_checkpoint(FULL)")
            source_conn.backup(destination_conn)
            destination_conn.commit()
        finally:
            destination_conn.close()
            source_conn.close()

    def _restore_database(self, source_path: Path, destination_path: Path) -> None:
        source_conn = sqlite3.connect(source_path)
        destination_conn = sqlite3.connect(destination_path)
        try:
            destination_conn.execute("PRAGMA wal_checkpoint(FULL)")
            destination_conn.execute("PRAGMA foreign_keys = OFF")
            source_conn.backup(destination_conn)
            destination_conn.commit()
        finally:
            destination_conn.close()
            source_conn.close()

    def _validate_sqlite_database(self, path: Path) -> None:
        if not path.exists():
            raise ValueError("backup file not found")
        if path.stat().st_size <= 0:
            raise ValueError("backup file is empty")
        try:
            conn = sqlite3.connect(path)
        except sqlite3.Error as exc:
            raise ValueError("backup file is not a valid sqlite database") from exc
        try:
            quick_check = conn.execute("PRAGMA quick_check").fetchone()
            if quick_check is None or str(quick_check[0]).lower() != "ok":
                raise ValueError("backup file failed integrity check")
            tables = {
                str(row[0])
                for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
            }
            missing_tables = REQUIRED_SQLITE_TABLES - tables
            if missing_tables:
                raise ValueError("backup file is incompatible with SalonFlow")
        except sqlite3.Error as exc:
            raise ValueError("backup file is not a valid sqlite database") from exc
        finally:
            conn.close()

    def _remove_sqlite_sidecars(self, path: Path) -> None:
        for suffix in ("-wal", "-shm", "-journal"):
            candidate = Path(f"{path}{suffix}")
            if candidate.exists():
                candidate.unlink()

    def payment_method_report(self) -> list[dict[str, object]]:
        rows = self.database.fetchall(
            """
            SELECT payment_method, kind, SUM(net_amount_cents) AS total_cents, COUNT(*) AS total_items
            FROM payments
            GROUP BY payment_method, kind
            ORDER BY payment_method, kind
            """
        )
        return [
            {
                "payment_method": str(row["payment_method"]),
                "kind": str(row["kind"]),
                "total": cents_to_money(int(row["total_cents"] or 0)),
                "items": int(row["total_items"] or 0),
            }
            for row in rows
        ]

    def audit_entries(self) -> list[dict[str, object]]:
        rows = self.database.fetchall("SELECT * FROM financial_audit_log ORDER BY id DESC LIMIT 100")
        return [
            {
                "operation_type": str(row["operation_type"]),
                "entity_type": str(row["entity_type"]),
                "entity_id": int(row["entity_id"]),
                "previous_value": str(row["previous_value"]),
                "new_value": str(row["new_value"]),
                "reason": str(row["reason"]),
                "created_at": str(row["created_at"]),
            }
            for row in rows
        ]

    def _row_to_receivable(self, row) -> ReceivableAccount:
        stored_status = str(row["status"])
        computed_status = stored_status
        if stored_status not in {"Pago", "Cancelado"} and str(row["due_date"]) < date.today().isoformat():
            computed_status = "Atrasado"
        return ReceivableAccount(
            client_id=int(row["client_id"]),
            description=str(row["description"]),
            category=str(row["category"]),
            total_amount=cents_to_money(int(row["total_amount_cents"])),
            remaining_amount=cents_to_money(int(row["remaining_amount_cents"])),
            issue_date=str(row["issue_date"]),
            due_date=str(row["due_date"]),
            payment_method=str(row["payment_method"]),
            installment_label=str(row["installment_label"]),
            installment_number=int(row["installment_number"]),
            installment_count=int(row["installment_count"]),
            notes=str(row["notes"]),
            status=computed_status,
            appointment_id=int(row["appointment_id"]) if row["appointment_id"] is not None else None,
            receivable_id=int(row["id"]),
        )

    def _row_to_payable(self, row) -> PayableAccount:
        stored_status = str(row["status"])
        computed_status = stored_status
        if stored_status not in {"Pago", "Cancelado"} and str(row["due_date"]) < date.today().isoformat():
            computed_status = "Atrasado"
        return PayableAccount(
            description=str(row["description"]),
            beneficiary=str(row["beneficiary"]),
            category=str(row["category"]),
            total_amount=cents_to_money(int(row["total_amount_cents"])),
            remaining_amount=cents_to_money(int(row["remaining_amount_cents"])),
            issue_date=str(row["issue_date"]),
            due_date=str(row["due_date"]),
            payment_method=str(row["payment_method"]),
            installment_label=str(row["installment_label"]),
            installment_number=int(row["installment_number"]),
            installment_count=int(row["installment_count"]),
            recurring_key=str(row["recurring_key"]),
            notes=str(row["notes"]),
            status=computed_status,
            payable_id=int(row["id"]),
        )

    def _normalize_date(self, value: str) -> str:
        try:
            return datetime.strptime(str(value), "%Y-%m-%d").date().isoformat()
        except ValueError as exc:
            raise ValueError("invalid financial date") from exc

    def _audit(self, operation_type: str, entity_type: str, entity_id: int, previous_value: str, new_value: str, reason: str) -> None:
        self.database.execute(
            """
            INSERT INTO financial_audit_log (operation_type, entity_type, entity_id, previous_value, new_value, reason)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (operation_type, entity_type, entity_id, previous_value, new_value, reason),
        )

    def _audit_conn(self, conn, operation_type: str, entity_type: str, entity_id: int, previous_value: str, new_value: str, reason: str) -> None:
        conn.execute(
            """
            INSERT INTO financial_audit_log (operation_type, entity_type, entity_id, previous_value, new_value, reason)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (operation_type, entity_type, entity_id, previous_value, new_value, reason),
        )
