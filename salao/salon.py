from __future__ import annotations

from datetime import date, datetime, timedelta

from .database import Database
from .models import APPOINTMENT_STATUSES, Appointment, Client, Professional, Service

DEFAULT_SERVICES: list[dict[str, object]] = [
    {"name": "Corte feminino", "category": "Cabelo", "duration_minutes": 60, "price": 80.0},
    {"name": "Escova simples", "category": "Cabelo", "duration_minutes": 45, "price": 50.0},
    {"name": "Escova modelada", "category": "Cabelo", "duration_minutes": 60, "price": 65.0},
    {"name": "Chapinha", "category": "Cabelo", "duration_minutes": 30, "price": 35.0},
    {"name": "Coloracao raiz", "category": "Coloracao", "duration_minutes": 90, "price": 120.0},
    {"name": "Coloracao completa", "category": "Coloracao", "duration_minutes": 150, "price": 220.0},
    {"name": "Hidratacao capilar", "category": "Tratamento", "duration_minutes": 50, "price": 70.0},
    {"name": "Reconstrucao capilar", "category": "Tratamento", "duration_minutes": 60, "price": 95.0},
    {"name": "Botox capilar", "category": "Tratamento", "duration_minutes": 120, "price": 180.0},
    {"name": "Progressiva", "category": "Alisamento", "duration_minutes": 180, "price": 250.0},
    {"name": "Design de sobrancelha", "category": "Sobrancelhas", "duration_minutes": 30, "price": 35.0},
    {"name": "Henna na sobrancelha", "category": "Sobrancelhas", "duration_minutes": 40, "price": 45.0},
    {"name": "Buco", "category": "Depilacao facial", "duration_minutes": 15, "price": 20.0},
    {"name": "Maquiagem social", "category": "Maquiagem", "duration_minutes": 60, "price": 120.0},
    {"name": "Penteado", "category": "Penteados", "duration_minutes": 75, "price": 150.0},
    {"name": "Manicure", "category": "Unhas", "duration_minutes": 40, "price": 30.0},
    {"name": "Pedicure", "category": "Unhas", "duration_minutes": 50, "price": 35.0},
    {"name": "Manicure e pedicure", "category": "Unhas", "duration_minutes": 90, "price": 60.0},
]


class SalonService:
    def __init__(self, database: Database):
        self.database = database

    def add_client(
        self,
        name: str,
        phone: str = "",
        whatsapp: str = "",
        email: str = "",
        birthday: str = "",
        notes: str = "",
    ) -> Client:
        if not name.strip():
            raise ValueError("client name cannot be empty")
        birthday_value = self._normalize_optional_date(birthday)
        cursor = self.database.execute(
            """
            INSERT INTO clients (name, phone, whatsapp, email, birthday, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (name.strip(), phone.strip(), whatsapp.strip(), email.strip(), birthday_value, notes.strip()),
        )
        return self.get_client(int(cursor.lastrowid))

    def update_client(
        self,
        client_id: int,
        name: str,
        phone: str = "",
        whatsapp: str = "",
        email: str = "",
        birthday: str = "",
        notes: str = "",
    ) -> Client:
        self.get_client(client_id)
        if not name.strip():
            raise ValueError("client name cannot be empty")
        birthday_value = self._normalize_optional_date(birthday)
        self.database.execute(
            """
            UPDATE clients
            SET name = ?, phone = ?, whatsapp = ?, email = ?, birthday = ?, notes = ?
            WHERE id = ?
            """,
            (name.strip(), phone.strip(), whatsapp.strip(), email.strip(), birthday_value, notes.strip(), int(client_id)),
        )
        return self.get_client(int(client_id))

    def add_professional(self, name: str, phone: str = "", specialty: str = "", active: bool = True) -> Professional:
        if not name.strip():
            raise ValueError("professional name cannot be empty")
        if not specialty.strip():
            raise ValueError("specialty cannot be empty")
        cursor = self.database.execute(
            "INSERT INTO professionals (name, phone, specialty, active) VALUES (?, ?, ?, ?)",
            (name.strip(), phone.strip(), specialty.strip(), 1 if active else 0),
        )
        return self.get_professional(int(cursor.lastrowid))

    def add_service(self, name: str, category: str, duration_minutes: int, price: float, active: bool = True) -> Service:
        if not name.strip():
            raise ValueError("service name cannot be empty")
        if int(duration_minutes) <= 0:
            raise ValueError("service duration must be positive")
        if float(price) < 0:
            raise ValueError("service price must be non-negative")
        cursor = self.database.execute(
            "INSERT INTO services (name, category, duration_minutes, price, active) VALUES (?, ?, ?, ?, ?)",
            (name.strip(), category.strip(), int(duration_minutes), float(price), 1 if active else 0),
        )
        return self.get_service(int(cursor.lastrowid))

    def create_appointment(
        self,
        client_id: int,
        professional_id: int,
        service_id: int,
        appointment_date: str,
        appointment_time: str,
        duration_minutes: int,
        price: float,
        status: str = "Agendado",
        notes: str = "",
    ) -> Appointment:
        self._require_client(client_id)
        self._require_professional(professional_id)
        self._require_service(service_id)
        normalized_date = self._normalize_required_date(appointment_date)
        normalized_time = self._normalize_required_time(appointment_time)
        if int(duration_minutes) <= 0:
            raise ValueError("appointment duration must be positive")
        if float(price) < 0:
            raise ValueError("appointment price must be non-negative")
        self._validate_status(status)
        self._ensure_no_conflict(professional_id, normalized_date, normalized_time, int(duration_minutes), None)
        cursor = self.database.execute(
            """
            INSERT INTO appointments (
                client_id, professional_id, service_id, appointment_date, appointment_time,
                duration_minutes, price, status, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(client_id),
                int(professional_id),
                int(service_id),
                normalized_date,
                normalized_time,
                int(duration_minutes),
                float(price),
                status,
                notes.strip(),
            ),
        )
        return self.get_appointment(int(cursor.lastrowid))

    def update_appointment(
        self,
        appointment_id: int,
        client_id: int,
        professional_id: int,
        service_id: int,
        appointment_date: str,
        appointment_time: str,
        duration_minutes: int,
        price: float,
        status: str,
        notes: str = "",
    ) -> Appointment:
        self.get_appointment(appointment_id)
        self._require_client(client_id)
        self._require_professional(professional_id)
        self._require_service(service_id)
        normalized_date = self._normalize_required_date(appointment_date)
        normalized_time = self._normalize_required_time(appointment_time)
        self._validate_status(status)
        self._ensure_no_conflict(professional_id, normalized_date, normalized_time, int(duration_minutes), appointment_id)
        self.database.execute(
            """
            UPDATE appointments
            SET client_id = ?, professional_id = ?, service_id = ?, appointment_date = ?, appointment_time = ?,
                duration_minutes = ?, price = ?, status = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                int(client_id),
                int(professional_id),
                int(service_id),
                normalized_date,
                normalized_time,
                int(duration_minutes),
                float(price),
                status,
                notes.strip(),
                int(appointment_id),
            ),
        )
        return self.get_appointment(int(appointment_id))

    def cancel_appointment(self, appointment_id: int) -> Appointment:
        return self._update_status(appointment_id, "Cancelado")

    def confirm_appointment(self, appointment_id: int) -> Appointment:
        appointment = self.get_appointment(appointment_id)
        if appointment.status == "Cancelado":
            raise ValueError("canceled appointment cannot be confirmed")
        if appointment.status == "Concluido":
            raise ValueError("completed appointment cannot be confirmed")
        if appointment.status == "Faltou":
            raise ValueError("missed appointment cannot be confirmed")
        if appointment.status == "Confirmado":
            return appointment
        return self._update_status(appointment_id, "Confirmado")

    def complete_appointment(self, appointment_id: int) -> Appointment:
        return self._update_status(appointment_id, "Concluido")

    def list_clients(self) -> list[Client]:
        return [self._row_to_client(row) for row in self.database.fetchall("SELECT * FROM clients ORDER BY name")]

    def list_professionals(self, active_only: bool = False) -> list[Professional]:
        sql = "SELECT * FROM professionals"
        if active_only:
            sql += " WHERE active = 1"
        sql += " ORDER BY name"
        return [self._row_to_professional(row) for row in self.database.fetchall(sql)]

    def list_services(self, active_only: bool = False) -> list[Service]:
        sql = "SELECT * FROM services"
        if active_only:
            sql += " WHERE active = 1"
        sql += " ORDER BY name"
        return [self._row_to_service(row) for row in self.database.fetchall(sql)]

    def seed_default_services(self) -> int:
        existing = {
            (service.name.strip().lower(), service.category.strip().lower())
            for service in self.list_services()
        }
        created = 0
        for payload in DEFAULT_SERVICES:
            service_key = (str(payload["name"]).strip().lower(), str(payload["category"]).strip().lower())
            if service_key in existing:
                continue
            self.add_service(
                name=str(payload["name"]),
                category=str(payload["category"]),
                duration_minutes=int(payload["duration_minutes"]),
                price=float(payload["price"]),
                active=True,
            )
            existing.add(service_key)
            created += 1
        return created

    def list_appointments(self, appointment_date: str | None = None, professional_id: int | None = None) -> list[dict[str, object]]:
        clauses: list[str] = []
        params: list[object] = []
        if appointment_date:
            clauses.append("a.appointment_date = ?")
            params.append(self._normalize_required_date(appointment_date))
        if professional_id:
            clauses.append("a.professional_id = ?")
            params.append(int(professional_id))
        where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.database.fetchall(
            f"""
            SELECT
                a.id, a.client_id, a.professional_id, a.service_id, a.appointment_date, a.appointment_time,
                a.duration_minutes, a.price, a.status, a.notes,
                c.name AS client_name,
                p.name AS professional_name,
                s.name AS service_name
            FROM appointments a
            JOIN clients c ON c.id = a.client_id
            JOIN professionals p ON p.id = a.professional_id
            JOIN services s ON s.id = a.service_id
            {where_clause}
            ORDER BY a.appointment_date, a.appointment_time
            """,
            tuple(params),
        )
        return [
            {
                "appointment_id": int(row["id"]),
                "client_id": int(row["client_id"]),
                "professional_id": int(row["professional_id"]),
                "service_id": int(row["service_id"]),
                "client_name": str(row["client_name"]),
                "professional_name": str(row["professional_name"]),
                "service_name": str(row["service_name"]),
                "appointment_date": str(row["appointment_date"]),
                "appointment_time": str(row["appointment_time"]),
                "duration_minutes": int(row["duration_minutes"]),
                "price": float(row["price"]),
                "status": str(row["status"]),
                "notes": str(row["notes"]),
            }
            for row in rows
        ]

    def get_client(self, client_id: int) -> Client:
        row = self.database.fetchone("SELECT * FROM clients WHERE id = ?", (int(client_id),))
        if row is None:
            raise ValueError("client id not found")
        return self._row_to_client(row)

    def get_professional(self, professional_id: int) -> Professional:
        row = self.database.fetchone("SELECT * FROM professionals WHERE id = ?", (int(professional_id),))
        if row is None:
            raise ValueError("professional id not found")
        return self._row_to_professional(row)

    def get_service(self, service_id: int) -> Service:
        row = self.database.fetchone("SELECT * FROM services WHERE id = ?", (int(service_id),))
        if row is None:
            raise ValueError("service id not found")
        return self._row_to_service(row)

    def get_appointment(self, appointment_id: int) -> Appointment:
        row = self.database.fetchone("SELECT * FROM appointments WHERE id = ?", (int(appointment_id),))
        if row is None:
            raise ValueError("appointment id not found")
        return self._row_to_appointment(row)

    def get_appointment_context(self, appointment_id: int) -> dict[str, object]:
        row = self.database.fetchone(
            """
            SELECT
                a.id, a.client_id, a.professional_id, a.service_id, a.appointment_date, a.appointment_time,
                a.duration_minutes, a.price, a.status, a.notes,
                c.name AS client_name, c.phone AS client_phone, c.whatsapp AS client_whatsapp,
                p.name AS professional_name,
                s.name AS service_name
            FROM appointments a
            JOIN clients c ON c.id = a.client_id
            LEFT JOIN professionals p ON p.id = a.professional_id
            LEFT JOIN services s ON s.id = a.service_id
            WHERE a.id = ?
            """,
            (int(appointment_id),),
        )
        if row is None:
            raise ValueError("appointment id not found")
        return {
            "appointment_id": int(row["id"]),
            "client_id": int(row["client_id"]),
            "professional_id": int(row["professional_id"]),
            "service_id": int(row["service_id"]),
            "client_name": str(row["client_name"]),
            "client_phone": str(row["client_phone"]),
            "client_whatsapp": str(row["client_whatsapp"]),
            "professional_name": str(row["professional_name"] or ""),
            "service_name": str(row["service_name"] or ""),
            "appointment_date": str(row["appointment_date"]),
            "appointment_time": str(row["appointment_time"]),
            "duration_minutes": int(row["duration_minutes"]),
            "price": float(row["price"]),
            "status": str(row["status"]),
            "notes": str(row["notes"]),
        }

    def summary(self) -> dict[str, object]:
        today = date.today()
        today_iso = today.isoformat()
        all_appointments = self.list_appointments()
        today_items = [item for item in all_appointments if item["appointment_date"] == today_iso]
        upcoming = [
            item
            for item in all_appointments
            if item["status"] not in {"Cancelado", "Concluido", "Faltou"}
        ][:5]
        birthdays_today = self._clients_with_birthdays_between(today, today)
        birthdays_week = self._clients_with_birthdays_between(today, today + timedelta(days=6))
        confirmation_needed = [
            item
            for item in all_appointments
            if item["status"] == "Agendado"
            and today <= datetime.strptime(str(item["appointment_date"]), "%Y-%m-%d").date() <= today + timedelta(days=2)
        ]
        completed_today = len([item for item in today_items if item["status"] == "Concluido"])
        pending_today = len([item for item in today_items if item["status"] in {"Agendado", "Confirmado"}])
        return {
            "today_appointments": len(today_items),
            "clients_total": len(self.list_clients()),
            "active_professionals": len([item for item in self.list_professionals() if item.active]),
            "services_total": len(self.list_services()),
            "upcoming_appointments": upcoming,
            "birthdays_today": birthdays_today,
            "birthdays_week": birthdays_week,
            "confirmation_needed": confirmation_needed,
            "completed_today": completed_today,
            "pending_today": pending_today,
        }

    def _clients_with_birthdays_between(self, start: date, end: date) -> list[dict[str, object]]:
        birthdays_by_slot = {(start + timedelta(days=offset)).strftime("%m-%d") for offset in range((end - start).days + 1)}
        matches: list[dict[str, object]] = []
        for client in self.list_clients():
            birthday = str(client.birthday or "").strip()
            if not birthday:
                continue
            try:
                birthday_date = datetime.strptime(birthday, "%Y-%m-%d").date()
            except ValueError:
                continue
            month_day = birthday_date.strftime("%m-%d")
            if month_day not in birthdays_by_slot:
                continue
            upcoming_date = date(start.year, birthday_date.month, birthday_date.day)
            if upcoming_date < start:
                upcoming_date = date(start.year + 1, birthday_date.month, birthday_date.day)
            matches.append(
                {
                    "client_id": int(client.client_id),
                    "name": client.name,
                    "birthday": birthday,
                    "upcoming_date": upcoming_date.isoformat(),
                }
            )
        matches.sort(key=lambda item: str(item["upcoming_date"]))
        return matches

    def _require_client(self, client_id: int) -> None:
        self.get_client(client_id)

    def _require_professional(self, professional_id: int) -> None:
        professional = self.get_professional(professional_id)
        if not professional.active:
            raise ValueError("professional is inactive")

    def _require_service(self, service_id: int) -> None:
        service = self.get_service(service_id)
        if not service.active:
            raise ValueError("service is inactive")

    def _ensure_no_conflict(
        self,
        professional_id: int,
        appointment_date: str,
        appointment_time: str,
        duration_minutes: int,
        ignore_appointment_id: int | None,
    ) -> None:
        candidate_start = self._combine(appointment_date, appointment_time)
        candidate_end = candidate_start + timedelta(minutes=int(duration_minutes))
        rows = self.database.fetchall(
            """
            SELECT id, appointment_date, appointment_time, duration_minutes, status
            FROM appointments
            WHERE professional_id = ? AND appointment_date = ?
            """,
            (int(professional_id), appointment_date),
        )
        for row in rows:
            existing_id = int(row["id"])
            if ignore_appointment_id and existing_id == int(ignore_appointment_id):
                continue
            if str(row["status"]) in {"Cancelado", "Faltou"}:
                continue
            existing_start = self._combine(str(row["appointment_date"]), str(row["appointment_time"]))
            existing_end = existing_start + timedelta(minutes=int(row["duration_minutes"]))
            if candidate_start < existing_end and existing_start < candidate_end:
                raise ValueError("appointment conflict for professional")

    def _update_status(self, appointment_id: int, status: str) -> Appointment:
        self._validate_status(status)
        self.get_appointment(appointment_id)
        self.database.execute(
            "UPDATE appointments SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (status, int(appointment_id)),
        )
        return self.get_appointment(int(appointment_id))

    def _validate_status(self, status: str) -> None:
        if status not in APPOINTMENT_STATUSES:
            raise ValueError("invalid appointment status")

    def _normalize_required_date(self, value: str) -> str:
        try:
            return datetime.strptime(value.strip(), "%Y-%m-%d").date().isoformat()
        except Exception as exc:
            raise ValueError("invalid appointment date") from exc

    def _normalize_optional_date(self, value: str) -> str:
        if not value.strip():
            return ""
        try:
            return datetime.strptime(value.strip(), "%Y-%m-%d").date().isoformat()
        except Exception as exc:
            raise ValueError("invalid birthday") from exc

    def _normalize_required_time(self, value: str) -> str:
        try:
            return datetime.strptime(value.strip(), "%H:%M").strftime("%H:%M")
        except Exception as exc:
            raise ValueError("invalid appointment time") from exc

    def _combine(self, appointment_date: str, appointment_time: str) -> datetime:
        return datetime.strptime(f"{appointment_date} {appointment_time}", "%Y-%m-%d %H:%M")

    def _row_to_client(self, row) -> Client:
        return Client(
            client_id=int(row["id"]),
            name=str(row["name"]),
            phone=str(row["phone"]),
            whatsapp=str(row["whatsapp"]),
            email=str(row["email"]),
            birthday=str(row["birthday"]),
            notes=str(row["notes"]),
            created_at=str(row["created_at"]) if "created_at" in row.keys() else "",
        )

    def _row_to_professional(self, row) -> Professional:
        return Professional(
            professional_id=int(row["id"]),
            name=str(row["name"]),
            phone=str(row["phone"]),
            specialty=str(row["specialty"]),
            active=bool(int(row["active"])),
        )

    def _row_to_service(self, row) -> Service:
        return Service(
            service_id=int(row["id"]),
            name=str(row["name"]),
            category=str(row["category"]),
            duration_minutes=int(row["duration_minutes"]),
            price=float(row["price"]),
            active=bool(int(row["active"])),
        )

    def _row_to_appointment(self, row) -> Appointment:
        return Appointment(
            appointment_id=int(row["id"]),
            client_id=int(row["client_id"]),
            professional_id=int(row["professional_id"]),
            service_id=int(row["service_id"]),
            appointment_date=str(row["appointment_date"]),
            appointment_time=str(row["appointment_time"]),
            duration_minutes=int(row["duration_minutes"]),
            price=float(row["price"]),
            status=str(row["status"]),
            notes=str(row["notes"]),
        )
