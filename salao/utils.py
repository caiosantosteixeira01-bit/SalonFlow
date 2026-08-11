from __future__ import annotations

from datetime import datetime
from decimal import Decimal


FINANCIAL_KIND_LABELS = {
    "receipt": "Recebimento",
    "disbursement": "Saida",
}

AUDIT_ACTION_LABELS = {
    "CREATE": "Criacao",
    "RECEIVE": "Recebimento",
    "PAY": "Pagamento",
    "FINALIZE_APPOINTMENT": "Conclusao de atendimento",
    "PAY_COMMISSION": "Pagamento de comissao",
    "create": "Criacao",
    "update": "Atualizacao",
    "cancel": "Cancelamento",
    "complete": "Conclusao",
    "receive": "Recebimento",
    "pay": "Pagamento",
    "open": "Abertura",
    "close": "Fechamento",
    "backup": "Backup",
    "login": "Login",
    "logout": "Logout",
    "confirm": "Confirmacao",
}

ENTITY_LABELS = {
    "receivable_accounts": "Conta a receber",
    "payable_accounts": "Conta a pagar",
    "appointments": "Agendamento",
    "commissions": "Comissao",
    "client": "Cliente",
    "professional": "Profissional",
    "service": "Servico",
    "appointment": "Agendamento",
    "receivable": "Conta a receber",
    "payable": "Conta a pagar",
    "billing": "Cobranca",
    "cash_session": "Caixa",
    "commission": "Comissao",
    "database": "Banco de dados",
    "user": "Usuario",
    "session": "Sessao",
    "client_note": "Observacao da cliente",
    "client_preferences": "Preferencias da cliente",
    "client_profile": "Ficha da cliente",
    "settings": "Configuracoes",
    "receipt": "Recibo",
    "whatsapp": "WhatsApp",
}

PAYMENT_METHOD_LABELS = {
    "Dinheiro": "Dinheiro",
    "Pix": "Pix",
    "Cartao de debito": "Cartao de debito",
    "Cartao de credito": "Cartao de credito",
}


def format_currency(value: float) -> str:
    integer, decimal = f"{value:,.2f}".split(".")
    integer = integer.replace(",", ".")
    return f"R$ {integer},{decimal}"


def format_date_br(value: str) -> str:
    if not value:
        return "-"
    try:
        return datetime.strptime(value, "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return value


def format_time_br(value: str) -> str:
    if not value:
        return "-"
    try:
        return datetime.strptime(value, "%H:%M").strftime("%H:%M")
    except ValueError:
        return value


def format_datetime_br(value: str) -> str:
    if not value:
        return "-"
    for pattern in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(value, pattern).strftime("%d/%m/%Y %H:%M")
        except ValueError:
            continue
    return value


def display_financial_kind(value: str) -> str:
    return FINANCIAL_KIND_LABELS.get(value, value.replace("_", " ").capitalize())


def display_audit_action(value: str) -> str:
    return AUDIT_ACTION_LABELS.get(value, value.replace("_", " ").capitalize())


def display_entity(value: str) -> str:
    return ENTITY_LABELS.get(value, value.replace("_", " ").capitalize())


def display_payment_method(value: str) -> str:
    return PAYMENT_METHOD_LABELS.get(value, value)


def format_decimal_currency(value: Decimal | float) -> str:
    return format_currency(float(value))
