from __future__ import annotations

import webbrowser

from .database import Database
from .utils import format_date_br, format_time_br


class WhatsAppConfirmationService:
    def __init__(self, database: Database):
        self.database = database

    def normalize_brazil_phone(self, raw_value: str) -> str:
        digits = "".join(character for character in str(raw_value or "") if character.isdigit())
        if not digits:
            raise ValueError("cliente sem telefone para WhatsApp")
        if digits.startswith("00"):
            digits = digits[2:]
        if digits.startswith("55"):
            national = digits[2:]
        else:
            national = digits
        if len(national) not in {10, 11}:
            raise ValueError("telefone invalido para WhatsApp")
        return f"55{national}"

    def get_contact_phone(self, appointment_context: dict[str, object]) -> str:
        preferred = str(appointment_context.get("client_whatsapp") or "").strip()
        fallback = str(appointment_context.get("client_phone") or "").strip()
        return self.normalize_brazil_phone(preferred or fallback)

    def build_confirmation_message(self, appointment_context: dict[str, object]) -> str:
        client_name = str(appointment_context.get("client_name") or "Cliente").strip()
        salon_name = self._get_setting("salon_name") or "SalonFlow"
        return (
            f"Ola, {client_name}! Tudo bem?\n\n"
            f"Estamos confirmando seu horario no {salon_name}.\n\n"
            f"Data: {format_date_br(str(appointment_context.get('appointment_date') or ''))}\n"
            f"Horario: {format_time_br(str(appointment_context.get('appointment_time') or ''))}\n"
            f"Servico: {self._safe_label(appointment_context.get('service_name'), 'Nao informado')}\n"
            f"Profissional: {self._safe_label(appointment_context.get('professional_name'), 'Nao informado')}\n\n"
            "Podemos confirmar seu atendimento?"
        )

    def build_whatsapp_url(self, appointment_context: dict[str, object]) -> str:
        phone = self.get_contact_phone(appointment_context)
        message = self.build_confirmation_message(appointment_context)
        encoded_message = "".join(f"%{byte:02X}" for byte in message.encode("utf-8"))
        return f"https://wa.me/{phone}?text={encoded_message}"

    def open_confirmation(self, appointment_context: dict[str, object]) -> str:
        url = self.build_whatsapp_url(appointment_context)
        webbrowser.open(url)
        return url

    def _get_setting(self, key: str) -> str:
        row = self.database.fetchone("SELECT setting_value FROM app_settings WHERE setting_key = ?", (key,))
        return str(row["setting_value"]) if row else ""

    def _safe_label(self, value: object, fallback: str) -> str:
        text = str(value or "").strip()
        return text or fallback
