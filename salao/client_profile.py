from __future__ import annotations

from collections import Counter
from datetime import date, datetime
from decimal import Decimal

from .database import Database
from .finance import cents_to_money
from .salon import SalonService


class ClientProfileService:
    def __init__(self, database: Database):
        self.database = database
        self.salon_service = SalonService(database)

    def get_profile(self, client_id: int) -> dict[str, object]:
        client = self.salon_service.get_client(client_id)
        appointments = self._fetch_appointments(client_id)
        payments = self._fetch_payments(client_id)
        notes = self.list_notes(client_id)
        preferences = self.get_preferences(client_id)
        pending = self._fetch_pending_receivables(client_id)

        paid_appointment_payments = [item for item in payments if item["origin"] == "Atendimento"]
        completed_appointments = [item for item in appointments if item["status"] == "Concluido"]
        total_received = sum((item["amount"] for item in paid_appointment_payments), Decimal("0.00"))
        paid_appointment_ids = {int(item["appointment_id"]) for item in paid_appointment_payments if item["appointment_id"] is not None}
        ticket = (total_received / Decimal(len(paid_appointment_ids))).quantize(Decimal("0.01")) if paid_appointment_ids else Decimal("0.00")

        last_visit = self._find_last_visit(completed_appointments)
        next_appointment = self._find_next_appointment(appointments)
        favorite_service = self._most_common(completed_appointments, "service_name")
        frequent_professional = self._most_common(completed_appointments, "professional_name")
        birthday_badge = self._birthday_badge(client.birthday)

        status = "Nova"
        if pending["count"]:
            status = "Atencao financeira"
        elif next_appointment is not None:
            status = "Agendada"
        elif completed_appointments or paid_appointment_payments:
            status = "Ativa"

        schedule_groups = {
            "upcoming": [item for item in appointments if self._is_future(item) and item["status"] not in {"Cancelado", "Faltou"}],
            "previous": [item for item in appointments if not self._is_future(item) and item["status"] not in {"Cancelado", "Faltou"}],
            "cancelled": [item for item in appointments if item["status"] == "Cancelado"],
            "no_show": [item for item in appointments if item["status"] == "Faltou"],
        }

        client_since = client.created_at
        if not client_since:
            timeline_candidates = [item["created_at"] for item in appointments if item.get("created_at")] + [item["created_at"] for item in payments if item.get("created_at")]
            client_since = min(timeline_candidates) if timeline_candidates else ""

        return {
            "client": client,
            "header": {
                "status": status,
                "client_since": client_since,
                "last_visit": last_visit,
                "next_appointment": next_appointment,
                "birthday_badge": birthday_badge,
            },
            "summary": {
                "total_appointments": len(completed_appointments),
                "total_spent": total_received,
                "average_ticket": ticket,
                "last_visit": last_visit,
                "next_appointment": next_appointment,
                "pending_payments": pending["amount"],
                "pending_count": pending["count"],
                "favorite_service": favorite_service,
                "frequent_professional": frequent_professional,
            },
            "appointments": appointments,
            "payments": payments,
            "schedule": schedule_groups,
            "notes": notes,
            "preferences": preferences,
        }

    def add_note(self, client_id: int, note_text: str, username: str = "") -> dict[str, object]:
        self.salon_service.get_client(client_id)
        if not note_text.strip():
            raise ValueError("client note cannot be empty")
        cursor = self.database.execute(
            """
            INSERT INTO client_notes (client_id, note_text, username)
            VALUES (?, ?, ?)
            """,
            (int(client_id), note_text.strip(), username.strip()),
        )
        row = self.database.fetchone("SELECT * FROM client_notes WHERE id = ?", (int(cursor.lastrowid),))
        return self._row_to_note(row)

    def list_notes(self, client_id: int) -> list[dict[str, object]]:
        rows = self.database.fetchall("SELECT * FROM client_notes WHERE client_id = ? ORDER BY created_at DESC, id DESC", (int(client_id),))
        return [self._row_to_note(row) for row in rows]

    def save_preferences(
        self,
        client_id: int,
        preferred_service: str = "",
        preferred_professional: str = "",
        service_notes: str = "",
        general_preferences: str = "",
    ) -> dict[str, object]:
        self.salon_service.get_client(client_id)
        self.database.execute(
            """
            INSERT INTO client_preferences (
                client_id, preferred_service, preferred_professional, service_notes, general_preferences, updated_at
            ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(client_id) DO UPDATE SET
                preferred_service = excluded.preferred_service,
                preferred_professional = excluded.preferred_professional,
                service_notes = excluded.service_notes,
                general_preferences = excluded.general_preferences,
                updated_at = CURRENT_TIMESTAMP
            """,
            (int(client_id), preferred_service.strip(), preferred_professional.strip(), service_notes.strip(), general_preferences.strip()),
        )
        return self.get_preferences(client_id)

    def get_preferences(self, client_id: int) -> dict[str, object]:
        row = self.database.fetchone("SELECT * FROM client_preferences WHERE client_id = ?", (int(client_id),))
        if row is None:
            return {
                "preferred_service": "",
                "preferred_professional": "",
                "service_notes": "",
                "general_preferences": "",
                "updated_at": "",
            }
        return {
            "preferred_service": str(row["preferred_service"]),
            "preferred_professional": str(row["preferred_professional"]),
            "service_notes": str(row["service_notes"]),
            "general_preferences": str(row["general_preferences"]),
            "updated_at": str(row["updated_at"]),
        }

    def _fetch_appointments(self, client_id: int) -> list[dict[str, object]]:
        rows = self.database.fetchall(
            """
            SELECT
                a.id,
                a.client_id,
                a.professional_id,
                a.service_id,
                a.appointment_date,
                a.appointment_time,
                a.duration_minutes,
                a.price,
                a.status,
                a.notes,
                a.created_at,
                p.name AS professional_name,
                s.name AS service_name,
                COALESCE(SUM(pay.amount_cents), 0) AS total_paid_cents,
                COALESCE(SUM(pay.discount_cents), 0) AS total_discount_cents,
                GROUP_CONCAT(DISTINCT pay.payment_method) AS payment_methods,
                MAX(pay.id) AS latest_payment_id
            FROM appointments a
            JOIN professionals p ON p.id = a.professional_id
            JOIN services s ON s.id = a.service_id
            LEFT JOIN payments pay ON pay.appointment_id = a.id AND pay.kind = 'receipt'
            WHERE a.client_id = ?
            GROUP BY
                a.id, a.client_id, a.professional_id, a.service_id, a.appointment_date, a.appointment_time,
                a.duration_minutes, a.price, a.status, a.notes, a.created_at, p.name, s.name
            ORDER BY a.appointment_date DESC, a.appointment_time DESC, a.id DESC
            """,
            (int(client_id),),
        )
        return [
            {
                "appointment_id": int(row["id"]),
                "client_id": int(row["client_id"]),
                "professional_id": int(row["professional_id"]),
                "service_id": int(row["service_id"]),
                "appointment_date": str(row["appointment_date"]),
                "appointment_time": str(row["appointment_time"]),
                "duration_minutes": int(row["duration_minutes"]),
                "price": Decimal(str(row["price"])).quantize(Decimal("0.01")),
                "status": str(row["status"]),
                "notes": str(row["notes"]),
                "created_at": str(row["created_at"]),
                "professional_name": str(row["professional_name"]),
                "service_name": str(row["service_name"]),
                "paid_amount": cents_to_money(int(row["total_paid_cents"] or 0)),
                "discount_amount": cents_to_money(int(row["total_discount_cents"] or 0)),
                "payment_methods": self._split_methods(str(row["payment_methods"] or "")),
                "payment_method_display": ", ".join(self._split_methods(str(row["payment_methods"] or ""))) or "-",
                "receipt_payment_id": int(row["latest_payment_id"]) if row["latest_payment_id"] is not None else None,
            }
            for row in rows
        ]

    def _fetch_payments(self, client_id: int) -> list[dict[str, object]]:
        rows = self.database.fetchall(
            """
            SELECT
                p.id,
                p.appointment_id,
                p.description,
                p.amount_cents,
                p.payment_method,
                p.payment_date,
                p.status,
                p.created_at,
                COALESCE(a.appointment_date, '') AS appointment_date,
                COALESCE(a.appointment_time, '') AS appointment_time,
                COALESCE(s.name, '') AS service_name,
                COALESCE(pr.name, '') AS professional_name
            FROM payments p
            LEFT JOIN appointments a ON a.id = p.appointment_id
            LEFT JOIN services s ON s.id = a.service_id
            LEFT JOIN professionals pr ON pr.id = a.professional_id
            WHERE p.client_id = ? AND p.kind = 'receipt'
            ORDER BY p.payment_date DESC, p.id DESC
            """,
            (int(client_id),),
        )
        result: list[dict[str, object]] = []
        for row in rows:
            origin = "Atendimento" if row["appointment_id"] is not None else "Pagamento avulso"
            result.append(
                {
                    "payment_id": int(row["id"]),
                    "appointment_id": int(row["appointment_id"]) if row["appointment_id"] is not None else None,
                    "origin": origin,
                    "description": str(row["description"]),
                    "payment_method": str(row["payment_method"]),
                    "payment_date": str(row["payment_date"]),
                    "status": str(row["status"]),
                    "created_at": str(row["created_at"]),
                    "service_name": str(row["service_name"]),
                    "professional_name": str(row["professional_name"]),
                    "appointment_date": str(row["appointment_date"]),
                    "appointment_time": str(row["appointment_time"]),
                    "amount": cents_to_money(int(row["amount_cents"] or 0)),
                }
            )
        return result

    def _fetch_pending_receivables(self, client_id: int) -> dict[str, object]:
        row = self.database.fetchone(
            """
            SELECT
                COUNT(*) AS total_items,
                COALESCE(SUM(remaining_amount_cents), 0) AS total_cents
            FROM receivable_accounts
            WHERE client_id = ? AND status NOT IN ('Pago', 'Cancelado')
            """,
            (int(client_id),),
        )
        return {
            "count": int(row["total_items"] or 0),
            "amount": cents_to_money(int(row["total_cents"] or 0)),
        }

    def _find_last_visit(self, appointments: list[dict[str, object]]) -> dict[str, object] | None:
        now = datetime.now()
        candidates = [item for item in appointments if self._appointment_datetime(item) <= now]
        return max(candidates, key=self._appointment_datetime) if candidates else None

    def _find_next_appointment(self, appointments: list[dict[str, object]]) -> dict[str, object] | None:
        now = datetime.now()
        candidates = [
            item
            for item in appointments
            if self._appointment_datetime(item) >= now and item["status"] not in {"Cancelado", "Concluido", "Faltou"}
        ]
        return min(candidates, key=self._appointment_datetime) if candidates else None

    def _appointment_datetime(self, appointment: dict[str, object]) -> datetime:
        return datetime.strptime(f"{appointment['appointment_date']} {appointment['appointment_time']}", "%Y-%m-%d %H:%M")

    def _is_future(self, appointment: dict[str, object]) -> bool:
        return self._appointment_datetime(appointment) >= datetime.now()

    def _most_common(self, appointments: list[dict[str, object]], field: str) -> dict[str, object] | None:
        counter = Counter(str(item[field]) for item in appointments if str(item[field]).strip())
        if not counter:
            return None
        name, count = counter.most_common(1)[0]
        return {"name": name, "count": count}

    def _birthday_badge(self, birthday: str) -> dict[str, object] | None:
        if not birthday:
            return None
        try:
            birthday_date = datetime.strptime(birthday, "%Y-%m-%d").date()
        except ValueError:
            return None
        today = date.today()
        next_birthday = birthday_date.replace(year=today.year)
        if next_birthday < today:
            next_birthday = birthday_date.replace(year=today.year + 1)
        delta = (next_birthday - today).days
        if delta > 14:
            return None
        return {
            "days": delta,
            "label": "Aniversario hoje" if delta == 0 else f"Aniversario em {delta} dias",
        }

    def _row_to_note(self, row) -> dict[str, object]:
        return {
            "note_id": int(row["id"]),
            "client_id": int(row["client_id"]),
            "text": str(row["note_text"]),
            "username": str(row["username"]),
            "created_at": str(row["created_at"]),
        }

    def _split_methods(self, value: str) -> list[str]:
        methods = []
        seen = set()
        for item in value.split(","):
            normalized = item.strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            methods.append(normalized)
        return methods
