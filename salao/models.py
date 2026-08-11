from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path


APPOINTMENT_STATUSES = (
    "Agendado",
    "Confirmado",
    "Em atendimento",
    "Concluido",
    "Cancelado",
    "Faltou",
)


@dataclass
class Client:
    name: str
    phone: str = ""
    whatsapp: str = ""
    email: str = ""
    birthday: str = ""
    notes: str = ""
    created_at: str = ""
    client_id: int | None = None


@dataclass
class Professional:
    name: str
    phone: str = ""
    specialty: str = ""
    active: bool = True
    professional_id: int | None = None


@dataclass
class Service:
    name: str
    category: str = ""
    duration_minutes: int = 60
    price: float = 0.0
    active: bool = True
    service_id: int | None = None


@dataclass
class Appointment:
    client_id: int
    professional_id: int
    service_id: int
    appointment_date: str
    appointment_time: str
    duration_minutes: int
    price: float
    status: str
    notes: str = ""
    appointment_id: int | None = None


@dataclass
class ReceivableAccount:
    client_id: int
    description: str
    category: str
    total_amount: Decimal
    remaining_amount: Decimal
    issue_date: str
    due_date: str
    payment_method: str = ""
    installment_label: str = ""
    installment_number: int = 1
    installment_count: int = 1
    notes: str = ""
    status: str = "Pendente"
    appointment_id: int | None = None
    receivable_id: int | None = None


@dataclass
class PayableAccount:
    description: str
    beneficiary: str
    category: str
    total_amount: Decimal
    remaining_amount: Decimal
    issue_date: str
    due_date: str
    payment_method: str = ""
    installment_label: str = ""
    installment_number: int = 1
    installment_count: int = 1
    recurring_key: str = ""
    notes: str = ""
    status: str = "Pendente"
    payable_id: int | None = None


@dataclass
class PaymentRecord:
    kind: str
    description: str
    amount: Decimal
    gross_amount: Decimal
    net_amount: Decimal
    payment_date: str
    payment_method: str
    status: str = "Confirmado"
    notes: str = ""
    payment_id: int | None = None


@dataclass
class ReceiptRecord:
    payment_id: int
    receipt_number: str
    created_at: str
    payment_date: str
    appointment_time: str
    client_name: str
    client_label: str
    professional_name: str
    professional_label: str
    service_name: str
    service_label: str
    original_amount: Decimal
    discount_amount: Decimal
    paid_amount: Decimal
    payment_method: str
    notes: str = ""
    appointment_id: int | None = None
    receivable_id: int | None = None
    pdf_path: Path | None = None


@dataclass
class CashSession:
    opening_balance: Decimal
    expected_balance: Decimal
    counted_balance: Decimal
    difference: Decimal
    status: str = "Aberto"
    opened_at: str = ""
    closed_at: str = ""
    session_id: int | None = None


@dataclass
class CommissionRecord:
    appointment_id: int
    professional_id: int
    service_id: int
    base_amount: Decimal
    commission_amount: Decimal
    percentage_basis_points: int
    commission_date: str
    status: str = "Pendente"
    commission_id: int | None = None
