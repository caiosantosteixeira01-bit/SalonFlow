from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from pathlib import Path

from ..auth import AuditService, AuthService, PROFILES, SystemUser
from ..client_profile import ClientProfileService
from ..core.config import AppPaths
from ..database import Database
from ..finance import PAYMENT_METHODS, FinanceService
from ..receipt import ReceiptService
from ..models import APPOINTMENT_STATUSES
from ..salon import SalonService
from ..whatsapp import WhatsAppConfirmationService
from ..utils import (
    display_audit_action,
    display_entity,
    display_financial_kind,
    display_payment_method,
    format_currency,
    format_date_br,
    format_datetime_br,
    format_time_br,
)
from .theme import APP_NAME, build_stylesheet

try:
    from PySide6.QtCore import QDate, QTime, Qt
    from PySide6.QtGui import QPixmap
    from PySide6.QtWidgets import (
        QApplication,
        QCheckBox,
        QComboBox,
        QDateEdit,
        QDialog,
        QDialogButtonBox,
        QDoubleSpinBox,
        QFileDialog,
        QFormLayout,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QScrollArea,
        QSpinBox,
        QStackedWidget,
        QStatusBar,
        QTableWidget,
        QTableWidgetItem,
        QTabWidget,
        QTextEdit,
        QTimeEdit,
        QVBoxLayout,
        QWidget,
        QHeaderView,
    )
    QT_AVAILABLE = True
except Exception:
    QT_AVAILABLE = False


if QT_AVAILABLE:
    class SidebarButton(QPushButton):
        def __init__(self, text: str):
            super().__init__(text)
            self.setObjectName("SidebarButton")
            self.setCheckable(True)


    class EmptyStateCard(QFrame):
        def __init__(self, title: str, description: str, button_text: str, callback):
            super().__init__()
            self.setObjectName("EmptyStateCard")
            self.setMinimumHeight(150)
            layout = QVBoxLayout(self)
            layout.setContentsMargins(24, 22, 24, 22)
            layout.setSpacing(10)
            title_label = QLabel(title)
            title_label.setObjectName("EmptyStateTitle")
            description_label = QLabel(description)
            description_label.setObjectName("EmptyStateDescription")
            description_label.setWordWrap(True)
            action_button = QPushButton(button_text)
            action_button.clicked.connect(callback)
            layout.addWidget(title_label)
            layout.addWidget(description_label)
            layout.addWidget(action_button, 0, Qt.AlignmentFlag.AlignLeft)
            layout.addStretch(1)


    class StatCard(QFrame):
        def __init__(self, title: str, value: str, caption: str):
            super().__init__()
            self.setObjectName("Card")
            layout = QVBoxLayout(self)
            layout.setContentsMargins(20, 18, 20, 18)
            layout.setSpacing(6)
            self.title_label = QLabel(title)
            self.title_label.setObjectName("PageSubtitle")
            self.value_label = QLabel(value)
            self.value_label.setObjectName("MetricValue")
            self.caption_label = QLabel(caption)
            self.caption_label.setObjectName("MetricCaption")
            layout.addWidget(self.title_label)
            layout.addWidget(self.value_label)
            layout.addWidget(self.caption_label)

        def update_content(self, value: str, caption: str) -> None:
            self.value_label.setText(value)
            self.caption_label.setText(caption)


    class StatusPill(QLabel):
        COLORS = {
            "Agendado": ("#F4E7EC", "#8A5164", "#E8CED7"),
            "Confirmado": ("#E4F1EA", "#2D6C55", "#CEE6D9"),
            "Em atendimento": ("#F8EBDD", "#996126", "#EED8BF"),
            "Concluido": ("#E4EEF7", "#3D5E84", "#D1E0F0"),
            "Cancelado": ("#F7E2E5", "#964A59", "#EBC9D0"),
            "Faltou": ("#EEE7EB", "#6D5561", "#DDD2D8"),
        }

        def __init__(self, status: str):
            super().__init__(status)
            self.setObjectName("StatusPill")
            self.apply_status(status)

        def apply_status(self, status: str) -> None:
            background, foreground, border = self.COLORS.get(status, ("#F3ECE8", "#5E4453", "#E3D6D0"))
            self.setText(status)
            self.setStyleSheet(f"background: {background}; color: {foreground}; border: 1px solid {border};")


    class BaseStyledDialog(QDialog):
        def __init__(self, title: str, subtitle: str, parent=None):
            super().__init__(parent)
            self.resize(640, 480)
            self.setMinimumSize(520, 420)
            outer = QVBoxLayout(self)
            outer.setContentsMargins(0, 0, 0, 0)
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            outer.addWidget(scroll)
            shell = QFrame()
            shell.setObjectName("DialogShell")
            scroll.setWidget(shell)
            self.shell_layout = QVBoxLayout(shell)
            self.shell_layout.setContentsMargins(22, 22, 22, 18)
            self.shell_layout.setSpacing(16)
            title_label = QLabel(title)
            title_label.setObjectName("DialogTitle")
            subtitle_label = QLabel(subtitle)
            subtitle_label.setObjectName("DialogSubtitle")
            subtitle_label.setWordWrap(True)
            self.shell_layout.addWidget(title_label)
            self.shell_layout.addWidget(subtitle_label)

        def add_section(self, title: str) -> QFormLayout:
            section = QFrame()
            section.setObjectName("DialogSection")
            section_layout = QVBoxLayout(section)
            section_layout.setContentsMargins(16, 14, 16, 14)
            section_layout.setSpacing(10)
            section_title = QLabel(title)
            section_title.setObjectName("SectionTitle")
            section_layout.addWidget(section_title)
            form = QFormLayout()
            form.setSpacing(10)
            form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
            form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
            form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            section_layout.addLayout(form)
            self.shell_layout.addWidget(section)
            return form

        def add_buttons(self) -> QDialogButtonBox:
            buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
            save_button = buttons.button(QDialogButtonBox.StandardButton.Save)
            cancel_button = buttons.button(QDialogButtonBox.StandardButton.Cancel)
            if save_button is not None:
                save_button.setText("Salvar")
                save_button.setMinimumWidth(132)
            if cancel_button is not None:
                cancel_button.setText("Cancelar")
                cancel_button.setProperty("variant", "secondary")
                cancel_button.setMinimumWidth(120)
            buttons.accepted.connect(self.accept)
            buttons.rejected.connect(self.reject)
            self.shell_layout.addWidget(buttons)
            return buttons


    class LoginDialog(BaseStyledDialog):
        Accepted = QDialog.DialogCode.Accepted

        def __init__(self, auth_service: AuthService, parent=None):
            super().__init__("Entrar no SalonFlow", "Use seu usuario e senha para abrir o sistema com seguranca.", parent)
            self.auth_service = auth_service
            self.user: SystemUser | None = None
            self.setWindowTitle("Login")
            self.resize(480, 320)
            form = self.add_section("Acesso")
            self.username_input = QLineEdit()
            self.username_input.setPlaceholderText("Usuario")
            self.username_input.setText(self.auth_service.get_remembered_username())
            self.password_input = QLineEdit()
            self.password_input.setPlaceholderText("Senha")
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.show_password = QCheckBox("Mostrar senha")
            self.show_password.toggled.connect(self._toggle_password)
            self.remember_username = QCheckBox("Lembrar usuario")
            self.remember_username.setChecked(bool(self.username_input.text().strip()))
            self.error_label = QLabel("")
            self.error_label.setObjectName("EmptyStateDescription")
            form.addRow("Usuario", self.username_input)
            form.addRow("Senha", self.password_input)
            form.addRow("", self.show_password)
            form.addRow("", self.remember_username)
            form.addRow("", self.error_label)
            buttons = self.add_buttons()
            buttons.accepted.disconnect()
            buttons.accepted.connect(self._submit)

        def _toggle_password(self, checked: bool) -> None:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password)

        def _submit(self) -> None:
            try:
                self.user = self.auth_service.authenticate(self.username_input.text(), self.password_input.text())
            except ValueError as exc:
                self.error_label.setText(str(exc).capitalize())
                return
            if self.remember_username.isChecked():
                self.auth_service.remember_username(self.username_input.text())
            else:
                self.auth_service.clear_remembered_username()
            self.accept()


    class UserDialog(BaseStyledDialog):
        Accepted = QDialog.DialogCode.Accepted

        def __init__(self, salon_service: SalonService, parent=None):
            super().__init__("Novo usuario", "Cadastre usuarios com perfil e permissao apropriados para o salao.", parent)
            self.salon_service = salon_service
            self.setWindowTitle("Novo usuario")
            self.resize(560, 420)
            form = self.add_section("Dados de acesso")
            self.name_input = QLineEdit()
            self.username_input = QLineEdit()
            self.password_input = QLineEdit()
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.profile_input = QComboBox()
            self.profile_input.addItems(list(PROFILES))
            self.professional_input = QComboBox()
            self.professional_input.addItem("Nenhum", None)
            for professional in self.salon_service.list_professionals():
                self.professional_input.addItem(professional.name, professional.professional_id)
            self.active_input = QCheckBox("Usuario ativo")
            self.active_input.setChecked(True)
            form.addRow("Nome", self.name_input)
            form.addRow("Usuario", self.username_input)
            form.addRow("Senha", self.password_input)
            form.addRow("Perfil", self.profile_input)
            form.addRow("Profissional", self.professional_input)
            form.addRow("", self.active_input)
            self.add_buttons()

        def payload(self) -> dict[str, object]:
            return {
                "name": self.name_input.text().strip(),
                "username": self.username_input.text().strip(),
                "password": self.password_input.text(),
                "profile": self.profile_input.currentText(),
                "professional_id": self.professional_input.currentData(),
                "active": self.active_input.isChecked(),
            }


    class ClientDialog(BaseStyledDialog):
        Accepted = QDialog.DialogCode.Accepted

        def __init__(self, client=None, parent=None):
            editing = client is not None
            super().__init__(
                "Editar cliente" if editing else "Novo cliente",
                "Atualize os dados essenciais da cliente." if editing else "Cadastre rapidamente os dados essenciais para continuar a agenda.",
                parent,
            )
            self.setWindowTitle("Editar cliente" if editing else "Novo cliente")
            self.client = client
            form = self.add_section("Dados do cliente")
            self.name_input = QLineEdit()
            self.name_input.setPlaceholderText("Ex.: Maria Oliveira")
            self.phone_input = QLineEdit()
            self.phone_input.setPlaceholderText("(11) 99999-0000")
            self.whatsapp_input = QLineEdit()
            self.whatsapp_input.setPlaceholderText("(11) 99999-0000")
            self.email_input = QLineEdit()
            self.email_input.setPlaceholderText("cliente@email.com")
            self.birthday_input = QDateEdit()
            self.birthday_input.setCalendarPopup(True)
            self.birthday_input.setDisplayFormat("yyyy-MM-dd")
            self.notes_input = QTextEdit()
            self.notes_input.setMaximumHeight(100)
            self.notes_input.setPlaceholderText("Preferencias, observacoes e informacoes importantes.")
            form.addRow("Nome", self.name_input)
            form.addRow("Telefone", self.phone_input)
            form.addRow("WhatsApp", self.whatsapp_input)
            form.addRow("E-mail", self.email_input)
            form.addRow("Aniversario", self.birthday_input)
            form.addRow("Observacoes", self.notes_input)
            self.add_buttons()
            if editing:
                self._load_client(client)

        def _load_client(self, client) -> None:
            self.name_input.setText(str(client.name))
            self.phone_input.setText(str(client.phone))
            self.whatsapp_input.setText(str(client.whatsapp))
            self.email_input.setText(str(client.email))
            if str(client.birthday):
                self.birthday_input.setDate(QDate.fromString(str(client.birthday), "yyyy-MM-dd"))
            self.notes_input.setPlainText(str(client.notes))

        def payload(self) -> dict[str, object]:
            return {
                "name": self.name_input.text().strip(),
                "phone": self.phone_input.text().strip(),
                "whatsapp": self.whatsapp_input.text().strip(),
                "email": self.email_input.text().strip(),
                "birthday": self.birthday_input.date().toString("yyyy-MM-dd"),
                "notes": self.notes_input.toPlainText().strip(),
            }


    class ProfessionalDialog(BaseStyledDialog):
        Accepted = QDialog.DialogCode.Accepted

        def __init__(self, parent=None):
            super().__init__("Novo profissional", "Organize a equipe com dados claros e especialidades bem definidas.", parent)
            self.setWindowTitle("Novo profissional")
            form = self.add_section("Perfil profissional")
            self.name_input = QLineEdit()
            self.name_input.setPlaceholderText("Ex.: Ana Souza")
            self.phone_input = QLineEdit()
            self.phone_input.setPlaceholderText("(11) 98888-0000")
            self.specialty_input = QLineEdit()
            self.specialty_input.setPlaceholderText("Cortes, coloracao, escova...")
            self.active_input = QCheckBox("Profissional ativo")
            self.active_input.setChecked(True)
            form.addRow("Nome", self.name_input)
            form.addRow("Telefone", self.phone_input)
            form.addRow("Especialidade", self.specialty_input)
            form.addRow("", self.active_input)
            self.add_buttons()

        def payload(self) -> dict[str, object]:
            return {
                "name": self.name_input.text().strip(),
                "phone": self.phone_input.text().strip(),
                "specialty": self.specialty_input.text().strip(),
                "active": self.active_input.isChecked(),
            }


    class ServiceDialog(BaseStyledDialog):
        Accepted = QDialog.DialogCode.Accepted

        def __init__(self, parent=None):
            super().__init__("Novo servico", "Monte um catalogo organizado com duracao e preco bem definidos.", parent)
            self.setWindowTitle("Novo servico")
            form = self.add_section("Detalhes do servico")
            self.name_input = QLineEdit()
            self.name_input.setPlaceholderText("Ex.: Corte feminino")
            self.category_input = QLineEdit()
            self.category_input.setPlaceholderText("Cabelo, unhas, sobrancelha...")
            self.duration_input = QSpinBox()
            self.duration_input.setRange(5, 480)
            self.duration_input.setValue(60)
            self.price_input = QDoubleSpinBox()
            self.price_input.setRange(0.0, 999999.99)
            self.price_input.setDecimals(2)
            self.active_input = QCheckBox("Servico ativo")
            self.active_input.setChecked(True)
            form.addRow("Nome", self.name_input)
            form.addRow("Categoria", self.category_input)
            form.addRow("Duracao (min)", self.duration_input)
            form.addRow("Preco", self.price_input)
            form.addRow("", self.active_input)
            self.add_buttons()

        def payload(self) -> dict[str, object]:
            return {
                "name": self.name_input.text().strip(),
                "category": self.category_input.text().strip(),
                "duration_minutes": int(self.duration_input.value()),
                "price": float(self.price_input.value()),
                "active": self.active_input.isChecked(),
            }


    class AppointmentDialog(BaseStyledDialog):
        Accepted = QDialog.DialogCode.Accepted

        def __init__(self, service: SalonService, appointment: dict[str, object] | None = None, parent=None):
            super().__init__(
                "Agendamento",
                "Preencha cliente, profissional e horario com clareza. O sistema bloqueia conflitos automaticamente.",
                parent,
            )
            self.service = service
            self.setWindowTitle("Agendamento")
            self.resize(700, 560)
            form = self.add_section("Dados do atendimento")
            self.client_input = QComboBox()
            self.professional_input = QComboBox()
            self.service_input = QComboBox()
            self.date_input = QDateEdit()
            self.date_input.setCalendarPopup(True)
            self.date_input.setDisplayFormat("yyyy-MM-dd")
            self.time_input = QTimeEdit()
            self.time_input.setDisplayFormat("HH:mm")
            self.time_input.setTime(QTime(9, 0))
            self.time_input.setMinimumWidth(110)
            self.duration_input = QSpinBox()
            self.duration_input.setRange(5, 480)
            self.price_input = QDoubleSpinBox()
            self.price_input.setRange(0.0, 999999.99)
            self.price_input.setDecimals(2)
            self.status_input = QComboBox()
            self.status_input.addItems(list(APPOINTMENT_STATUSES))
            self.notes_input = QTextEdit()
            self.notes_input.setMaximumHeight(110)
            self.notes_input.setPlaceholderText("Observacoes para recepcao ou profissional.")

            for client in self.service.list_clients():
                self.client_input.addItem(client.name, client.client_id)
            for professional in self.service.list_professionals(active_only=True):
                self.professional_input.addItem(f"{professional.name} - {professional.specialty}", professional.professional_id)
            for service_item in self.service.list_services(active_only=True):
                self.service_input.addItem(
                    f"{service_item.name} ({service_item.duration_minutes} min)",
                    {
                        "service_id": service_item.service_id,
                        "duration_minutes": service_item.duration_minutes,
                        "price": service_item.price,
                    },
                )
            self.service_input.currentIndexChanged.connect(self._sync_service_defaults)
            self._sync_service_defaults()

            form.addRow("Cliente", self.client_input)
            form.addRow("Profissional", self.professional_input)
            form.addRow("Servico", self.service_input)
            form.addRow("Data", self.date_input)
            form.addRow("Horario", self.time_input)
            form.addRow("Duracao", self.duration_input)
            form.addRow("Valor", self.price_input)
            form.addRow("Status", self.status_input)
            form.addRow("Observacoes", self.notes_input)
            self.add_buttons()
            if appointment:
                self._load_appointment(appointment)

        def _sync_service_defaults(self) -> None:
            payload = self.service_input.currentData() or {}
            if payload:
                self.duration_input.setValue(int(payload.get("duration_minutes") or 60))
                self.price_input.setValue(float(payload.get("price") or 0.0))

        def set_client(self, client_id: int) -> None:
            self._set_combo_data(self.client_input, int(client_id))

        def _load_appointment(self, appointment: dict[str, object]) -> None:
            self._set_combo_data(self.client_input, int(appointment["client_id"]))
            self._set_combo_data(self.professional_input, int(appointment["professional_id"]))
            service_id = int(appointment["service_id"])
            for index in range(self.service_input.count()):
                payload = self.service_input.itemData(index) or {}
                if int(payload.get("service_id") or 0) == service_id:
                    self.service_input.setCurrentIndex(index)
                    break
            self.date_input.setDate(QDate.fromString(str(appointment["appointment_date"]), "yyyy-MM-dd"))
            appointment_time = QTime.fromString(str(appointment["appointment_time"]), "HH:mm")
            self.time_input.setTime(appointment_time if appointment_time.isValid() else QTime(9, 0))
            self.duration_input.setValue(int(appointment["duration_minutes"]))
            self.price_input.setValue(float(appointment["price"]))
            self.status_input.setCurrentText(str(appointment["status"]))
            self.notes_input.setPlainText(str(appointment["notes"]))

        def _set_combo_data(self, combo: QComboBox, target: int) -> None:
            for index in range(combo.count()):
                if int(combo.itemData(index) or 0) == int(target):
                    combo.setCurrentIndex(index)
                    return

        def payload(self) -> dict[str, object]:
            payload = self.service_input.currentData() or {}
            return {
                "client_id": int(self.client_input.currentData()),
                "professional_id": int(self.professional_input.currentData()),
                "service_id": int(payload.get("service_id")),
                "appointment_date": self.date_input.date().toString("yyyy-MM-dd"),
                "appointment_time": self.time_input.time().toString("HH:mm"),
                "duration_minutes": int(self.duration_input.value()),
                "price": float(self.price_input.value()),
                "status": self.status_input.currentText(),
                "notes": self.notes_input.toPlainText().strip(),
            }


    class ReceivableDialog(BaseStyledDialog):
        Accepted = QDialog.DialogCode.Accepted

        def __init__(self, salon_service: SalonService, parent=None):
            super().__init__("Nova conta a receber", "Cadastre receitas futuras, pacotes e cobrancas do salao.", parent)
            self.setWindowTitle("Conta a receber")
            self.salon_service = salon_service
            form = self.add_section("Dados da conta")
            self.client_input = QComboBox()
            self.description_input = QLineEdit()
            self.description_input.setPlaceholderText("Ex.: Pacote de tratamentos")
            self.category_input = QLineEdit()
            self.category_input.setPlaceholderText("Pacotes, atendimento, revenda...")
            self.amount_input = QDoubleSpinBox()
            self.amount_input.setRange(0.0, 999999.99)
            self.amount_input.setDecimals(2)
            self.issue_date_input = QDateEdit()
            self.issue_date_input.setCalendarPopup(True)
            self.issue_date_input.setDisplayFormat("yyyy-MM-dd")
            self.issue_date_input.setDate(QDate.currentDate())
            self.due_date_input = QDateEdit()
            self.due_date_input.setCalendarPopup(True)
            self.due_date_input.setDisplayFormat("yyyy-MM-dd")
            self.due_date_input.setDate(QDate.currentDate())
            self.method_input = QComboBox()
            self.method_input.addItems(list(PAYMENT_METHODS))
            self.installment_input = QSpinBox()
            self.installment_input.setRange(1, 24)
            self.notes_input = QTextEdit()
            self.notes_input.setMaximumHeight(90)
            for client in self.salon_service.list_clients():
                self.client_input.addItem(client.name, client.client_id)
            form.addRow("Cliente", self.client_input)
            form.addRow("Descricao", self.description_input)
            form.addRow("Categoria", self.category_input)
            form.addRow("Valor", self.amount_input)
            form.addRow("Emissao", self.issue_date_input)
            form.addRow("Vencimento", self.due_date_input)
            form.addRow("Forma de pagamento", self.method_input)
            form.addRow("Parcelas", self.installment_input)
            form.addRow("Observacoes", self.notes_input)
            self.add_buttons()

        def payload(self) -> dict[str, object]:
            return {
                "client_id": int(self.client_input.currentData()),
                "description": self.description_input.text().strip(),
                "category": self.category_input.text().strip(),
                "amount": float(self.amount_input.value()),
                "issue_date": self.issue_date_input.date().toString("yyyy-MM-dd"),
                "due_date": self.due_date_input.date().toString("yyyy-MM-dd"),
                "payment_method": self.method_input.currentText(),
                "installment_count": int(self.installment_input.value()),
                "notes": self.notes_input.toPlainText().strip(),
            }


    class PayableDialog(BaseStyledDialog):
        Accepted = QDialog.DialogCode.Accepted

        def __init__(self, parent=None):
            super().__init__("Nova conta a pagar", "Registre despesas fixas e variaveis mantendo o historico do caixa.", parent)
            self.setWindowTitle("Conta a pagar")
            form = self.add_section("Dados da despesa")
            self.description_input = QLineEdit()
            self.beneficiary_input = QLineEdit()
            self.category_input = QLineEdit()
            self.amount_input = QDoubleSpinBox()
            self.amount_input.setRange(0.0, 999999.99)
            self.amount_input.setDecimals(2)
            self.issue_date_input = QDateEdit()
            self.issue_date_input.setCalendarPopup(True)
            self.issue_date_input.setDisplayFormat("yyyy-MM-dd")
            self.issue_date_input.setDate(QDate.currentDate())
            self.due_date_input = QDateEdit()
            self.due_date_input.setCalendarPopup(True)
            self.due_date_input.setDisplayFormat("yyyy-MM-dd")
            self.due_date_input.setDate(QDate.currentDate())
            self.method_input = QComboBox()
            self.method_input.addItems(list(PAYMENT_METHODS))
            self.installment_input = QSpinBox()
            self.installment_input.setRange(1, 24)
            self.notes_input = QTextEdit()
            self.notes_input.setMaximumHeight(90)
            form.addRow("Descricao", self.description_input)
            form.addRow("Fornecedor/beneficiario", self.beneficiary_input)
            form.addRow("Categoria", self.category_input)
            form.addRow("Valor", self.amount_input)
            form.addRow("Emissao", self.issue_date_input)
            form.addRow("Vencimento", self.due_date_input)
            form.addRow("Forma de pagamento", self.method_input)
            form.addRow("Parcelas", self.installment_input)
            form.addRow("Observacoes", self.notes_input)
            self.add_buttons()

        def payload(self) -> dict[str, object]:
            return {
                "description": self.description_input.text().strip(),
                "beneficiary": self.beneficiary_input.text().strip(),
                "category": self.category_input.text().strip(),
                "amount": float(self.amount_input.value()),
                "issue_date": self.issue_date_input.date().toString("yyyy-MM-dd"),
                "due_date": self.due_date_input.date().toString("yyyy-MM-dd"),
                "payment_method": self.method_input.currentText(),
                "installment_count": int(self.installment_input.value()),
                "notes": self.notes_input.toPlainText().strip(),
            }


    class ReceivePaymentDialog(BaseStyledDialog):
        Accepted = QDialog.DialogCode.Accepted

        def __init__(self, title: str, description: str, total_value: float, parent=None, include_commission: bool = False):
            super().__init__(title, description, parent)
            self.setWindowTitle(title)
            form = self.add_section("Recebimento")
            self.amount_input = QDoubleSpinBox()
            self.amount_input.setRange(0.0, 999999.99)
            self.amount_input.setDecimals(2)
            self.amount_input.setValue(float(total_value))
            self.date_input = QDateEdit()
            self.date_input.setCalendarPopup(True)
            self.date_input.setDisplayFormat("yyyy-MM-dd")
            self.date_input.setDate(QDate.currentDate())
            self.method_input = QComboBox()
            self.method_input.addItems(list(PAYMENT_METHODS))
            self.discount_input = QDoubleSpinBox()
            self.discount_input.setRange(0.0, 999999.99)
            self.discount_input.setDecimals(2)
            self.interest_input = QDoubleSpinBox()
            self.interest_input.setRange(0.0, 999999.99)
            self.interest_input.setDecimals(2)
            self.card_fee_input = QDoubleSpinBox()
            self.card_fee_input.setRange(0.0, 999999.99)
            self.card_fee_input.setDecimals(2)
            self.notes_input = QTextEdit()
            self.notes_input.setMaximumHeight(90)
            form.addRow("Valor", self.amount_input)
            form.addRow("Data", self.date_input)
            form.addRow("Forma de pagamento", self.method_input)
            form.addRow("Desconto", self.discount_input)
            form.addRow("Juros", self.interest_input)
            form.addRow("Taxa cartao", self.card_fee_input)
            if include_commission:
                self.commission_input = QDoubleSpinBox()
                self.commission_input.setRange(0.0, 100.0)
                self.commission_input.setDecimals(2)
                self.commission_input.setValue(40.0)
                form.addRow("Comissao %", self.commission_input)
            else:
                self.commission_input = None
            form.addRow("Observacoes", self.notes_input)
            self.add_buttons()

        def payload(self) -> dict[str, object]:
            return {
                "amount": float(self.amount_input.value()),
                "payment_date": self.date_input.date().toString("yyyy-MM-dd"),
                "payment_method": self.method_input.currentText(),
                "discount": float(self.discount_input.value()),
                "interest": float(self.interest_input.value()),
                "card_fee": float(self.card_fee_input.value()),
                "notes": self.notes_input.toPlainText().strip(),
                "commission_percentage": float(self.commission_input.value()) if self.commission_input is not None else None,
            }


    class NoteTextDialog(BaseStyledDialog):
        Accepted = QDialog.DialogCode.Accepted

        def __init__(self, title: str, subtitle: str, parent=None):
            super().__init__(title, subtitle, parent)
            self.setWindowTitle(title)
            self.resize(520, 320)
            form = self.add_section("Observacao")
            self.text_input = QTextEdit()
            self.text_input.setMinimumHeight(140)
            self.text_input.setPlaceholderText("Registre uma observacao util para a equipe do salao.")
            form.addRow("Texto", self.text_input)
            self.add_buttons()

        def payload(self) -> str:
            return self.text_input.toPlainText().strip()


    class AppointmentDetailsDialog(QDialog):
        def __init__(self, appointment: dict[str, object], finance_access: bool, parent=None):
            super().__init__(parent)
            self.appointment = appointment
            self.finance_access = finance_access
            self.setWindowTitle("Detalhes do atendimento")
            self.resize(720, 520)
            self.setStyleSheet(build_stylesheet())
            layout = QVBoxLayout(self)
            layout.setContentsMargins(18, 18, 18, 18)
            layout.setSpacing(14)
            header = QFrame()
            header.setObjectName("Panel")
            header_layout = QVBoxLayout(header)
            header_layout.setContentsMargins(18, 18, 18, 18)
            title = QLabel(str(appointment["service_name"]))
            title.setObjectName("PageTitle")
            subtitle = QLabel(f"{format_date_br(str(appointment['appointment_date']))} as {format_time_br(str(appointment['appointment_time']))}")
            subtitle.setObjectName("Subtitle")
            header_layout.addWidget(title)
            header_layout.addWidget(subtitle)
            layout.addWidget(header)
            grid = QGridLayout()
            grid.setHorizontalSpacing(12)
            grid.setVerticalSpacing(12)
            values = [
                ("Profissional", str(appointment["professional_name"])),
                ("Servico", str(appointment["service_name"])),
                ("Status", str(appointment["status"])),
                ("Duracao", f"{appointment['duration_minutes']} min"),
                ("Valor original", format_currency(float(appointment["price"])) if finance_access else "Protegido"),
                ("Desconto", format_currency(float(appointment["discount_amount"])) if finance_access else "Protegido"),
                ("Valor final", format_currency(float(appointment["paid_amount"])) if finance_access else "Protegido"),
                ("Pagamento", str(appointment["payment_method_display"]) if finance_access else "Protegido"),
            ]
            for index, (label_text, value_text) in enumerate(values):
                card = QFrame()
                card.setObjectName("Card")
                card_layout = QVBoxLayout(card)
                card_layout.setContentsMargins(16, 14, 16, 14)
                label = QLabel(label_text)
                label.setObjectName("PageSubtitle")
                value = QLabel(value_text)
                value.setObjectName("SectionTitle")
                value.setWordWrap(True)
                card_layout.addWidget(label)
                card_layout.addWidget(value)
                grid.addWidget(card, index // 2, index % 2)
            layout.addLayout(grid)
            notes_panel = QFrame()
            notes_panel.setObjectName("Panel")
            notes_layout = QVBoxLayout(notes_panel)
            notes_layout.setContentsMargins(16, 14, 16, 14)
            notes_title = QLabel("Observacoes")
            notes_title.setObjectName("SectionTitle")
            notes_text = QLabel(str(appointment["notes"] or "Nenhuma observacao registrada."))
            notes_text.setObjectName("PageSubtitle")
            notes_text.setWordWrap(True)
            notes_layout.addWidget(notes_title)
            notes_layout.addWidget(notes_text)
            layout.addWidget(notes_panel)
            actions = QHBoxLayout()
            self.receipt_button = QPushButton("Abrir recibo" if appointment.get("receipt_payment_id") else "Gerar recibo")
            self.receipt_button.setVisible(finance_access and appointment.get("receipt_payment_id") is not None)
            actions.addStretch(1)
            actions.addWidget(self.receipt_button)
            close_button = QPushButton("Fechar")
            close_button.clicked.connect(self.accept)
            actions.addWidget(close_button)
            layout.addLayout(actions)


    class ClientProfileDialog(QDialog):
        def __init__(
            self,
            client_id: int,
            profile_service: ClientProfileService,
            receipt_service: ReceiptService,
            finance_access: bool,
            can_manage_clients: bool,
            can_manage_appointments: bool,
            parent=None,
        ):
            super().__init__(parent)
            self.client_id = client_id
            self.profile_service = profile_service
            self.receipt_service = receipt_service
            self.finance_access = finance_access
            self.can_manage_clients = can_manage_clients
            self.can_manage_appointments = can_manage_appointments
            self.profile_data: dict[str, object] | None = None
            self.appointment_rows: list[dict[str, object]] = []
            self.payment_rows: list[dict[str, object]] = []
            self.schedule_rows: list[tuple[str, dict[str, object]]] = []
            self.note_rows: list[dict[str, object]] = []
            self.setWindowTitle("Ficha da cliente")
            self.resize(1120, 760)
            self.setMinimumSize(980, 700)
            self.setStyleSheet(build_stylesheet())
            self._build()
            self.refresh()

        def _build(self) -> None:
            layout = QVBoxLayout(self)
            layout.setContentsMargins(18, 18, 18, 18)
            layout.setSpacing(14)
            header = QFrame()
            header.setObjectName("ProfileHeroPanel")
            header_layout = QVBoxLayout(header)
            header_layout.setContentsMargins(24, 22, 24, 22)
            header_layout.setSpacing(12)
            top_line = QHBoxLayout()
            title_box = QVBoxLayout()
            self.client_name_label = QLabel("")
            self.client_name_label.setObjectName("PageTitle")
            self.client_meta_label = QLabel("")
            self.client_meta_label.setObjectName("Subtitle")
            self.birthday_badge = QLabel("")
            self.birthday_badge.setObjectName("HeroBadge")
            self.birthday_badge.setVisible(False)
            title_box.addWidget(self.client_name_label)
            title_box.addWidget(self.client_meta_label)
            title_box.addWidget(self.birthday_badge, 0, Qt.AlignmentFlag.AlignLeft)
            top_line.addLayout(title_box, 1)
            actions = QHBoxLayout()
            self.edit_client_button = QPushButton("Editar cliente")
            self.edit_client_button.setEnabled(self.can_manage_clients)
            self.new_appointment_button = QPushButton("Novo agendamento")
            self.new_appointment_button.setEnabled(self.can_manage_appointments)
            self.new_note_button = QPushButton("Adicionar observacao")
            self.new_note_button.setEnabled(self.can_manage_clients)
            actions.addWidget(self.edit_client_button)
            actions.addWidget(self.new_appointment_button)
            actions.addWidget(self.new_note_button)
            top_line.addLayout(actions)
            header_layout.addLayout(top_line)
            self.header_info_grid = QGridLayout()
            self.header_info_grid.setHorizontalSpacing(12)
            self.header_info_grid.setVerticalSpacing(10)
            self.header_fields: dict[str, QLabel] = {}
            for index, key in enumerate(["Telefone", "WhatsApp", "E-mail", "Nascimento", "Status", "Cliente desde", "Ultima visita", "Proximo agendamento"]):
                card = QFrame()
                card.setObjectName("Card")
                card_layout = QVBoxLayout(card)
                card_layout.setContentsMargins(14, 12, 14, 12)
                label = QLabel(key)
                label.setObjectName("ProfileMetaTitle")
                value = QLabel("-")
                value.setObjectName("ProfileMetaValue")
                value.setWordWrap(True)
                card_layout.addWidget(label)
                card_layout.addWidget(value)
                self.header_fields[key] = value
                self.header_info_grid.addWidget(card, index // 4, index % 4)
            header_layout.addLayout(self.header_info_grid)
            layout.addWidget(header)
            self.tabs = QTabWidget()
            layout.addWidget(self.tabs, 1)

            self.summary_tab = QWidget()
            summary_layout = QVBoxLayout(self.summary_tab)
            summary_cards = QGridLayout()
            self.summary_total_card = StatCard("Total de atendimentos", "0", "Concluidos")
            self.summary_spent_card = StatCard("Total gasto", "R$ 0,00", "Atendimentos pagos")
            self.summary_ticket_card = StatCard("Ticket medio", "R$ 0,00", "Media por atendimento pago")
            self.summary_last_card = StatCard("Ultima visita", "-", "Historico real")
            self.summary_next_card = StatCard("Proximo agendamento", "-", "Agenda futura")
            self.summary_pending_card = StatCard("Pagamentos pendentes", "R$ 0,00", "Valores em aberto")
            for index, card in enumerate([self.summary_total_card, self.summary_spent_card, self.summary_ticket_card, self.summary_last_card, self.summary_next_card, self.summary_pending_card]):
                summary_cards.addWidget(card, index // 3, index % 3)
            summary_layout.addLayout(summary_cards)
            self.summary_highlights = QFrame()
            self.summary_highlights.setObjectName("ProfileHighlightPanel")
            highlights_layout = QVBoxLayout(self.summary_highlights)
            highlights_layout.setContentsMargins(18, 16, 18, 16)
            highlights_layout.setSpacing(10)
            self.favorite_service_label = QLabel("-")
            self.favorite_service_label.setObjectName("ProfileHighlightValue")
            self.favorite_professional_label = QLabel("-")
            self.favorite_professional_label.setObjectName("ProfileHighlightValue")
            self.preferences_snapshot_label = QLabel("-")
            self.preferences_snapshot_label.setObjectName("ProfileSnapshot")
            favorite_service_title = QLabel("Servico favorito / mais realizado")
            favorite_service_title.setObjectName("ProfileMetaTitle")
            favorite_professional_title = QLabel("Profissional mais frequente")
            favorite_professional_title.setObjectName("ProfileMetaTitle")
            preferences_title = QLabel("Preferencias registradas")
            preferences_title.setObjectName("ProfileMetaTitle")
            highlights_layout.addWidget(favorite_service_title)
            highlights_layout.addWidget(self.favorite_service_label)
            highlights_layout.addSpacing(8)
            highlights_layout.addWidget(favorite_professional_title)
            highlights_layout.addWidget(self.favorite_professional_label)
            highlights_layout.addSpacing(8)
            highlights_layout.addWidget(preferences_title)
            highlights_layout.addWidget(self.preferences_snapshot_label)
            summary_layout.addWidget(self.summary_highlights)
            summary_layout.addStretch(1)
            self.tabs.addTab(self.summary_tab, "Resumo")

            self.appointments_tab = QWidget()
            appointments_layout = QVBoxLayout(self.appointments_tab)
            appointments_actions = QHBoxLayout()
            self.open_appointment_button = QPushButton("Abrir detalhes")
            appointments_actions.addWidget(self.open_appointment_button)
            appointments_actions.addStretch(1)
            appointments_layout.addLayout(appointments_actions)
            self.appointments_table = QTableWidget(0, 6)
            self.appointments_table.setHorizontalHeaderLabels(["Data", "Servico", "Profissional", "Valor", "Status", "Pagamento"])
            self._configure_table(self.appointments_table)
            appointments_layout.addWidget(self.appointments_table, 1)
            self.appointments_empty = QLabel("Nenhum atendimento realizado.")
            self.appointments_empty.setObjectName("EmptyState")
            appointments_layout.addWidget(self.appointments_empty)
            self.tabs.addTab(self.appointments_tab, "Atendimentos")

            self.payments_tab = QWidget()
            payments_layout = QVBoxLayout(self.payments_tab)
            self.payments_table = QTableWidget(0, 6)
            self.payments_table.setHorizontalHeaderLabels(["Data", "Origem", "Descricao", "Forma", "Valor", "Status"])
            self._configure_table(self.payments_table)
            payments_layout.addWidget(self.payments_table, 1)
            self.payments_empty = QLabel("Nenhum pagamento encontrado.")
            self.payments_empty.setObjectName("EmptyState")
            self.payments_restricted = QLabel("Os detalhes financeiros desta cliente estao protegidos para o seu perfil.")
            self.payments_restricted.setObjectName("EmptyState")
            payments_layout.addWidget(self.payments_empty)
            payments_layout.addWidget(self.payments_restricted)
            self.tabs.addTab(self.payments_tab, "Pagamentos")

            self.schedule_tab = QWidget()
            schedule_layout = QVBoxLayout(self.schedule_tab)
            schedule_actions = QHBoxLayout()
            self.schedule_new_button = QPushButton("Novo agendamento")
            self.schedule_new_button.setEnabled(self.can_manage_appointments)
            schedule_actions.addWidget(self.schedule_new_button)
            schedule_actions.addStretch(1)
            schedule_layout.addLayout(schedule_actions)
            self.schedule_table = QTableWidget(0, 6)
            self.schedule_table.setHorizontalHeaderLabels(["Grupo", "Data", "Horario", "Servico", "Profissional", "Status"])
            self._configure_table(self.schedule_table)
            schedule_layout.addWidget(self.schedule_table, 1)
            self.schedule_empty = QLabel("Nenhum agendamento encontrado.")
            self.schedule_empty.setObjectName("EmptyState")
            schedule_layout.addWidget(self.schedule_empty)
            self.tabs.addTab(self.schedule_tab, "Agendamentos")

            self.notes_tab = QWidget()
            notes_layout = QVBoxLayout(self.notes_tab)
            self.preferences_panel = QFrame()
            self.preferences_panel.setObjectName("Panel")
            preferences_layout = QFormLayout(self.preferences_panel)
            preferences_layout.setContentsMargins(18, 16, 18, 16)
            self.preferred_service_input = QLineEdit()
            self.preferred_professional_input = QLineEdit()
            self.service_notes_input = QTextEdit()
            self.service_notes_input.setMaximumHeight(80)
            self.general_preferences_input = QTextEdit()
            self.general_preferences_input.setMaximumHeight(96)
            preferences_layout.addRow("Servico preferido", self.preferred_service_input)
            preferences_layout.addRow("Profissional preferido", self.preferred_professional_input)
            preferences_layout.addRow("Observacoes de atendimento", self.service_notes_input)
            preferences_layout.addRow("Preferencias gerais", self.general_preferences_input)
            self.save_preferences_button = QPushButton("Salvar preferencias")
            self.save_preferences_button.setEnabled(self.can_manage_clients)
            preferences_layout.addRow("", self.save_preferences_button)
            notes_layout.addWidget(self.preferences_panel)
            note_actions = QHBoxLayout()
            self.add_note_button = QPushButton("Nova observacao")
            self.add_note_button.setEnabled(self.can_manage_clients)
            note_actions.addWidget(self.add_note_button)
            note_actions.addStretch(1)
            notes_layout.addLayout(note_actions)
            self.notes_table = QTableWidget(0, 3)
            self.notes_table.setHorizontalHeaderLabels(["Data", "Usuario", "Observacao"])
            self._configure_table(self.notes_table)
            notes_layout.addWidget(self.notes_table, 1)
            self.notes_empty = QLabel("Nenhuma observacao registrada.")
            self.notes_empty.setObjectName("EmptyState")
            notes_layout.addWidget(self.notes_empty)
            self.tabs.addTab(self.notes_tab, "Observacoes")

        def _configure_table(self, table: QTableWidget) -> None:
            table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            table.setAlternatingRowColors(True)
            table.verticalHeader().setVisible(False)
            table.horizontalHeader().setStretchLastSection(True)
            table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)

        def refresh(self) -> None:
            self.profile_data = self.profile_service.get_profile(self.client_id)
            client = self.profile_data["client"]
            header = self.profile_data["header"]
            summary = self.profile_data["summary"]
            self.client_name_label.setText(str(client.name))
            self.client_meta_label.setText("Ficha completa com resumo, historico e preferencias reais da cliente.")
            self.header_fields["Telefone"].setText(str(client.phone or "-"))
            self.header_fields["WhatsApp"].setText(str(client.whatsapp or "-"))
            self.header_fields["E-mail"].setText(str(client.email or "-"))
            self.header_fields["Nascimento"].setText(format_date_br(str(client.birthday)))
            self.header_fields["Status"].setText(str(header["status"]))
            self.header_fields["Cliente desde"].setText(format_datetime_br(str(header["client_since"])))
            self.header_fields["Ultima visita"].setText(self._appointment_caption(header["last_visit"]))
            self.header_fields["Proximo agendamento"].setText(self._appointment_caption(header["next_appointment"]))
            birthday = header["birthday_badge"]
            self.birthday_badge.setVisible(bool(birthday))
            self.birthday_badge.setText(str(birthday["label"]) if birthday else "")
            self.summary_total_card.update_content(str(summary["total_appointments"]), "Concluidos")
            self.summary_last_card.update_content(self._appointment_caption(summary["last_visit"]), "Historico real")
            self.summary_next_card.update_content(self._appointment_caption(summary["next_appointment"]), "Agenda futura")
            if self.finance_access:
                self.summary_spent_card.update_content(format_currency(float(summary["total_spent"])), "Atendimentos pagos")
                self.summary_ticket_card.update_content(format_currency(float(summary["average_ticket"])), "Media por atendimento pago")
                self.summary_pending_card.update_content(format_currency(float(summary["pending_payments"])), f"{summary['pending_count']} pendencia(s)")
            else:
                self.summary_spent_card.update_content("Protegido", "Sem permissao financeira")
                self.summary_ticket_card.update_content("Protegido", "Sem permissao financeira")
                self.summary_pending_card.update_content("Protegido", "Sem permissao financeira")
            favorite_service = summary["favorite_service"]
            favorite_professional = summary["frequent_professional"]
            self.favorite_service_label.setText(f"{favorite_service['name']} - {favorite_service['count']} atendimento(s)" if favorite_service else "Nenhum historico suficiente.")
            self.favorite_professional_label.setText(f"{favorite_professional['name']} - {favorite_professional['count']} atendimento(s)" if favorite_professional else "Nenhum historico suficiente.")
            preferences = self.profile_data["preferences"]
            snapshot_parts = [
                f"Servico preferido: {preferences['preferred_service']}" if preferences["preferred_service"] else "",
                f"Profissional preferido: {preferences['preferred_professional']}" if preferences["preferred_professional"] else "",
                f"Preferencias gerais: {preferences['general_preferences']}" if preferences["general_preferences"] else "",
            ]
            self.preferences_snapshot_label.setText(" | ".join(part for part in snapshot_parts if part) or "Nenhuma preferencia registrada.")
            self.preferred_service_input.setText(str(preferences["preferred_service"]))
            self.preferred_professional_input.setText(str(preferences["preferred_professional"]))
            self.service_notes_input.setPlainText(str(preferences["service_notes"]))
            self.general_preferences_input.setPlainText(str(preferences["general_preferences"]))

            self.appointment_rows = list(self.profile_data["appointments"])
            self.appointments_table.setRowCount(len(self.appointment_rows))
            self.appointments_empty.setVisible(not self.appointment_rows)
            self.appointments_table.setVisible(bool(self.appointment_rows))
            for row_index, item in enumerate(self.appointment_rows):
                values = [
                    f"{format_date_br(str(item['appointment_date']))} {format_time_br(str(item['appointment_time']))}",
                    item["service_name"],
                    item["professional_name"],
                    format_currency(float(item["price"])) if self.finance_access else "Protegido",
                    item["status"],
                    item["payment_method_display"] if self.finance_access else "Protegido",
                ]
                for column_index, value in enumerate(values):
                    self.appointments_table.setItem(row_index, column_index, QTableWidgetItem(str(value)))

            self.payment_rows = list(self.profile_data["payments"])
            self.payments_restricted.setVisible(not self.finance_access)
            self.payments_table.setVisible(self.finance_access and bool(self.payment_rows))
            self.payments_empty.setVisible(self.finance_access and not self.payment_rows)
            if self.finance_access:
                self.payments_table.setRowCount(len(self.payment_rows))
                for row_index, item in enumerate(self.payment_rows):
                    values = [
                        format_date_br(str(item["payment_date"])),
                        item["origin"],
                        item["description"],
                        display_payment_method(str(item["payment_method"])),
                        format_currency(float(item["amount"])),
                        item["status"],
                    ]
                    for column_index, value in enumerate(values):
                        self.payments_table.setItem(row_index, column_index, QTableWidgetItem(str(value)))

            self.schedule_rows = []
            for label, items in [("Proximos", self.profile_data["schedule"]["upcoming"]), ("Anteriores", self.profile_data["schedule"]["previous"]), ("Cancelados", self.profile_data["schedule"]["cancelled"]), ("Faltas", self.profile_data["schedule"]["no_show"])]:
                for item in items:
                    self.schedule_rows.append((label, item))
            self.schedule_table.setRowCount(len(self.schedule_rows))
            self.schedule_empty.setVisible(not self.schedule_rows)
            self.schedule_table.setVisible(bool(self.schedule_rows))
            for row_index, (label, item) in enumerate(self.schedule_rows):
                values = [
                    label,
                    format_date_br(str(item["appointment_date"])),
                    format_time_br(str(item["appointment_time"])),
                    item["service_name"],
                    item["professional_name"],
                    item["status"],
                ]
                for column_index, value in enumerate(values):
                    self.schedule_table.setItem(row_index, column_index, QTableWidgetItem(str(value)))

            self.note_rows = list(self.profile_data["notes"])
            self.notes_table.setRowCount(len(self.note_rows))
            self.notes_empty.setVisible(not self.note_rows)
            self.notes_table.setVisible(bool(self.note_rows))
            for row_index, item in enumerate(self.note_rows):
                for column_index, value in enumerate([format_datetime_br(str(item["created_at"])), item["username"] or "-", item["text"]]):
                    self.notes_table.setItem(row_index, column_index, QTableWidgetItem(str(value)))

        def _appointment_caption(self, appointment: dict[str, object] | None) -> str:
            if appointment is None:
                return "-"
            return f"{format_date_br(str(appointment['appointment_date']))} {format_time_br(str(appointment['appointment_time']))}"

    class DashboardPage(QWidget):
        def __init__(self, service: SalonService, navigate_to_agenda, paths: AppPaths):
            super().__init__()
            self.service = service
            self.navigate_to_agenda = navigate_to_agenda
            self.paths = paths
            root_layout = QVBoxLayout(self)
            root_layout.setContentsMargins(0, 0, 0, 0)
            root_layout.setSpacing(0)
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            root_layout.addWidget(scroll)
            content = QWidget()
            scroll.setWidget(content)
            layout = QVBoxLayout(content)
            layout.setContentsMargins(0, 0, 6, 8)
            layout.setSpacing(16)
            hero = QFrame()
            hero.setObjectName("HeroPanel")
            hero_layout = QHBoxLayout(hero)
            hero_layout.setContentsMargins(24, 22, 24, 22)
            hero_layout.setSpacing(20)
            hero_text = QVBoxLayout()
            hero_text.setSpacing(12)
            hero_badge = QLabel("Visao geral do dia")
            hero_badge.setObjectName("HeroBadge")
            hero_title = QLabel("O que precisa da sua atencao agora")
            hero_title.setObjectName("TitleLabel")
            hero_caption = QLabel("Consulte agenda, proximos vencimentos, aniversariantes e atalhos do salao sem perder tempo.")
            hero_caption.setObjectName("Subtitle")
            hero_caption.setWordWrap(True)
            hero_text.addWidget(hero_badge)
            hero_text.addWidget(hero_title)
            hero_text.addWidget(hero_caption)
            quick_actions = QHBoxLayout()
            agenda_button = QPushButton("Ver agenda de hoje")
            agenda_button.clicked.connect(lambda: self.navigate_to_agenda("Hoje"))
            new_button = QPushButton("Novo agendamento")
            new_button.clicked.connect(lambda: self.navigate_to_agenda("Hoje", create_new=True))
            quick_actions.addWidget(agenda_button)
            quick_actions.addWidget(new_button)
            quick_actions.addStretch(1)
            hero_text.addLayout(quick_actions)
            hero_text.addStretch(1)
            hero_layout.addLayout(hero_text, 3)
            hero_info = QVBoxLayout()
            hero_info.setSpacing(10)
            hero_info_title = QLabel("Pendencias rapidas")
            hero_info_title.setObjectName("SectionTitle")
            self.hero_info_list = QTableWidget(0, 2)
            self.hero_info_list.setHorizontalHeaderLabels(["Item", "Resumo"])
            self.hero_info_list.horizontalHeader().setStretchLastSection(True)
            self._configure_table(self.hero_info_list)
            self.hero_info_list.setMaximumHeight(270)
            hero_info.addWidget(hero_info_title)
            hero_info.addWidget(self.hero_info_list)
            hero_layout.addLayout(hero_info, 2)
            layout.addWidget(hero)
            cards = QGridLayout()
            cards.setHorizontalSpacing(12)
            cards.setVerticalSpacing(12)
            self.today_card = StatCard("Agendamentos hoje", "0", "Compromissos do dia")
            self.today_revenue_card = StatCard("Faturamento hoje", "R$ 0,00", "Pagamentos do dia")
            self.month_revenue_card = StatCard("Faturamento do mes", "R$ 0,00", "Receitas confirmadas")
            self.clients_card = StatCard("Clientes", "0", "Base cadastrada")
            self.professionals_card = StatCard("Profissionais", "0", "Equipe ativa")
            self.services_card = StatCard("Servicos", "0", "Catalogo de atendimento")
            self.receivable_card = StatCard("A receber", "R$ 0,00", "Pendencias abertas")
            self.payable_card = StatCard("A pagar", "R$ 0,00", "Saidas pendentes")
            self.confirmation_card = StatCard("Confirmacoes", "0", "Agendamentos para confirmar")
            self.relationship_card = StatCard("Relacionamento", "0", "Aniversarios da semana")
            dashboard_cards = [
                self.today_card,
                self.today_revenue_card,
                self.month_revenue_card,
                self.clients_card,
                self.professionals_card,
                self.services_card,
                self.receivable_card,
                self.payable_card,
                self.confirmation_card,
                self.relationship_card,
            ]
            for index, card in enumerate(dashboard_cards):
                cards.addWidget(card, index // 4, index % 4)
            layout.addLayout(cards)
            today_title = QLabel("Agenda de hoje")
            today_title.setObjectName("SectionTitle")
            layout.addWidget(today_title)
            self.today_table = QTableWidget(0, 5)
            self.today_table.setHorizontalHeaderLabels(["Horario", "Cliente", "Servico", "Profissional", "Status"])
            self.today_table.horizontalHeader().setStretchLastSection(True)
            self.today_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            self.today_table.setAlternatingRowColors(True)
            self.today_table.verticalHeader().setVisible(False)
            self._configure_table(self.today_table)
            self._apply_column_layout(self.today_table, 2, [0, 4])
            layout.addWidget(self.today_table)
            self.today_empty = EmptyStateCard(
                "Agenda de hoje vazia",
                "Ainda nao existem atendimentos programados para hoje. Crie um agendamento para iniciar a rotina do salao.",
                "+ Novo agendamento",
                lambda: self.navigate_to_agenda("Hoje", create_new=True),
            )
            layout.addWidget(self.today_empty)
            title = QLabel("Proximos agendamentos")
            title.setObjectName("SectionTitle")
            layout.addWidget(title)
            self.upcoming_table = QTableWidget(0, 5)
            self.upcoming_table.setHorizontalHeaderLabels(["Data", "Horario", "Cliente", "Profissional", "Servico"])
            self.upcoming_table.horizontalHeader().setStretchLastSection(True)
            self.upcoming_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            self.upcoming_table.setAlternatingRowColors(True)
            self.upcoming_table.verticalHeader().setVisible(False)
            self._configure_table(self.upcoming_table)
            self._apply_column_layout(self.upcoming_table, 4, [0, 1])
            layout.addWidget(self.upcoming_table)
            self.upcoming_empty = EmptyStateCard(
                "Nenhum proximo agendamento",
                "Quando novos horarios forem cadastrados, eles aparecerao aqui para facilitar a organizacao da recepcao.",
                "Ver agenda",
                lambda: self.navigate_to_agenda("Proximos"),
            )
            layout.addWidget(self.upcoming_empty)
            layout.addStretch(1)

        def _configure_table(self, table: QTableWidget) -> None:
            table.setShowGrid(False)
            table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
            table.verticalHeader().setDefaultSectionSize(44)
            table.horizontalHeader().setMinimumHeight(44)
            table.setWordWrap(False)

        def _apply_column_layout(self, table: QTableWidget, stretch_column: int, compact_columns: list[int] | None = None) -> None:
            header = table.horizontalHeader()
            for column_index in range(table.columnCount()):
                if compact_columns and column_index in compact_columns:
                    header.setSectionResizeMode(column_index, QHeaderView.ResizeMode.ResizeToContents)
                elif column_index == stretch_column:
                    header.setSectionResizeMode(column_index, QHeaderView.ResizeMode.Stretch)
                else:
                    header.setSectionResizeMode(column_index, QHeaderView.ResizeMode.Interactive)

        def _build_status_widget(self, status: str) -> QWidget:
            host = QFrame()
            host.setObjectName("AgendaStatusHost")
            layout = QHBoxLayout(host)
            layout.setContentsMargins(6, 4, 6, 4)
            pill = StatusPill(status)
            layout.addWidget(pill)
            layout.addStretch(1)
            return host

        def refresh(self, summary: dict[str, object]) -> None:
            all_items = self.service.list_appointments()
            today_iso = date.today().isoformat()
            today_items = [item for item in all_items if item["appointment_date"] == today_iso]
            future_items = [
                item for item in all_items
                if (item["appointment_date"] > today_iso or (item["appointment_date"] == today_iso and item["appointment_time"] >= datetime.now().strftime("%H:%M")))
                and item["status"] not in {"Cancelado", "Concluido", "Faltou"}
            ]
            finance = FinanceService(Database(self.paths.database_path)).financial_overview(today_iso)
            today_revenue = sum(
                (movement["amount"] for movement in finance["ultimas_movimentacoes"] if movement["kind"] == "receipt" and movement["date"] == today_iso),
                0,
            )
            self.today_card.update_content(
                str(summary["today_appointments"]),
                f"{summary['pending_today']} pendente(s), {summary['completed_today']} concluido(s)",
            )
            self.today_revenue_card.update_content(format_currency(float(today_revenue)), "Pagamentos do dia")
            self.month_revenue_card.update_content(format_currency(float(finance["receitas_mes"])), "Receitas confirmadas")
            self.clients_card.update_content(str(summary["clients_total"]), "Base cadastrada")
            self.professionals_card.update_content(str(summary["active_professionals"]), "Equipe ativa")
            self.services_card.update_content(str(summary["services_total"]), "Catalogo de atendimento")
            self.receivable_card.update_content(format_currency(float(finance["a_receber"])), "Pendencias abertas")
            self.payable_card.update_content(format_currency(float(finance["a_pagar"])), "Saidas pendentes")
            self.confirmation_card.update_content(
                str(len(summary["confirmation_needed"])),
                f"{summary['pending_today']} pendente(s) na agenda de hoje",
            )
            self.relationship_card.update_content(
                str(len(summary["birthdays_week"])),
                self._birthday_caption(summary["birthdays_today"], summary["birthdays_week"]),
            )
            hero_items = [
                ("Proximo cliente", f"{future_items[0]['client_name']} as {format_time_br(str(future_items[0]['appointment_time']))}" if future_items else "Nenhum agendamento futuro"),
                ("Agenda para confirmar", self._confirmation_resume(summary["confirmation_needed"])),
                ("Aniversariantes hoje", self._birthday_names(summary["birthdays_today"])),
                ("Aniversarios na semana", self._birthday_names(summary["birthdays_week"], empty_text="Nenhuma data especial")),
                ("Vence hoje", finance["alertas"][0] if finance["alertas"] else "Nenhuma conta vence hoje"),
                ("Receber na semana", format_currency(float(finance["receber_semana"]))),
                ("Pagar na semana", format_currency(float(finance["pagar_semana"]))),
            ]
            self.hero_info_list.setRowCount(len(hero_items))
            for row_index, (title, resume) in enumerate(hero_items):
                self.hero_info_list.setItem(row_index, 0, QTableWidgetItem(title))
                self.hero_info_list.setItem(row_index, 1, QTableWidgetItem(resume))
            self.today_table.setRowCount(len(today_items))
            self.today_empty.setVisible(not today_items)
            self.today_table.setVisible(bool(today_items))
            for row_index, appointment in enumerate(today_items):
                values = [
                    format_time_br(str(appointment["appointment_time"])),
                    appointment["client_name"],
                    appointment["service_name"],
                    appointment["professional_name"],
                    appointment["status"],
                ]
                for column_index, value in enumerate(values):
                    if column_index == 4:
                        self.today_table.setCellWidget(row_index, column_index, self._build_status_widget(str(appointment["status"])))
                    else:
                        item = QTableWidgetItem(str(value))
                        self.today_table.setItem(row_index, column_index, item)
            appointments = list(summary["upcoming_appointments"])
            self.upcoming_table.setRowCount(len(appointments))
            self.upcoming_empty.setVisible(not appointments)
            self.upcoming_table.setVisible(bool(appointments))
            for row_index, appointment in enumerate(appointments):
                for column_index, value in enumerate([
                    format_date_br(str(appointment["appointment_date"])),
                    format_time_br(str(appointment["appointment_time"])),
                    appointment["client_name"],
                    appointment["professional_name"],
                    appointment["service_name"],
                ]):
                    self.upcoming_table.setItem(row_index, column_index, QTableWidgetItem(str(value)))

        def _birthday_names(
            self,
            items: list[dict[str, object]],
            *,
            empty_text: str = "Nenhum aniversariante",
            limit: int = 3,
        ) -> str:
            if not items:
                return empty_text
            names = [str(item["name"]) for item in items[:limit]]
            if len(items) > limit:
                names.append(f"+{len(items) - limit}")
            return ", ".join(names)

        def _birthday_caption(self, today_items: list[dict[str, object]], week_items: list[dict[str, object]]) -> str:
            if today_items:
                return f"Hoje: {self._birthday_names(today_items, limit=2)}"
            if week_items:
                return f"Semana: {self._birthday_names(week_items, limit=2)}"
            return "Sem aniversarios proximos"

        def _confirmation_resume(self, items: list[dict[str, object]]) -> str:
            if not items:
                return "Agenda confirmada"
            next_item = items[0]
            return f"{len(items)} pendente(s), proximo com {next_item['client_name']}"

    class SalonWindow(QMainWindow):
        def __init__(self, paths: AppPaths, current_user: SystemUser, auth_service: AuthService, audit_service: AuditService):
            super().__init__()
            self.paths = paths
            self.database = Database(paths.database_path)
            self.service = SalonService(self.database)
            self.finance_service = FinanceService(self.database)
            self.client_profile_service = ClientProfileService(self.database)
            self.receipt_service = ReceiptService(self.finance_service, paths)
            self.whatsapp_service = WhatsAppConfirmationService(self.database)
            self.auth_service = auth_service
            self.audit_service = audit_service
            self.current_user = current_user
            self.permission_service = auth_service.permission_service
            self.setWindowTitle(APP_NAME)
            self.resize(1280, 820)
            self.setMinimumSize(1120, 760)
            self._build()
            self.refresh_all()

        def _build(self) -> None:
            central = QWidget()
            self.setCentralWidget(central)
            root = QHBoxLayout(central)
            root.setContentsMargins(18, 18, 18, 18)
            root.setSpacing(16)

            sidebar = QFrame()
            sidebar.setObjectName("Sidebar")
            sidebar.setFixedWidth(268)
            sidebar_layout = QVBoxLayout(sidebar)
            sidebar_layout.setContentsMargins(20, 24, 20, 22)
            sidebar_layout.setSpacing(12)
            title = QLabel("SalonFlow")
            title.setObjectName("SidebarTitle")
            subtitle = QLabel("Gestao para Salao de Beleza")
            subtitle.setObjectName("SidebarSubtitle")
            subtitle.setWordWrap(True)
            meta = QLabel("Agenda, equipe, clientes e servicos em um unico lugar.")
            meta.setObjectName("SidebarMeta")
            meta.setWordWrap(True)
            user_chip = QLabel(f"{self.current_user.name} • {self.current_user.profile}")
            user_chip.setObjectName("HeroBadge")
            user_chip.setText(f"{self.current_user.name} | {self.current_user.profile}")
            sidebar_layout.addWidget(title)
            sidebar_layout.addWidget(subtitle)
            sidebar_layout.addWidget(meta)
            sidebar_layout.addWidget(user_chip)
            self.nav_buttons = []
            self.page_labels = ["Dashboard", "Agenda", "Clientes", "Servicos", "Profissionais", "Financeiro", "Usuarios", "Configuracoes"]
            for index, label in enumerate(self.page_labels):
                button = SidebarButton(label)
                button.clicked.connect(lambda _checked=False, idx=index: self.navigate(idx))
                self.nav_buttons.append(button)
                sidebar_layout.addWidget(button)
            sidebar_layout.addStretch(1)
            badge = QFrame()
            badge.setObjectName("SidebarBadge")
            badge_layout = QVBoxLayout(badge)
            badge_layout.setContentsMargins(16, 14, 16, 14)
            badge_title = QLabel("Atendimento com presenca")
            badge_title.setObjectName("SidebarTitle")
            badge_title.setStyleSheet("font-size: 11pt;")
            badge_title.setObjectName("SidebarBadgeTitle")
            badge_caption = QLabel("Uma interface calma, organizada e pronta para a rotina do salao.")
            badge_caption.setObjectName("SidebarSubtitle")
            badge_caption.setWordWrap(True)
            badge_layout.addWidget(badge_title)
            badge_layout.addWidget(badge_caption)
            sidebar_layout.addWidget(badge)
            logout_button = QPushButton("Sair")
            logout_button.setProperty("variant", "secondary")
            logout_button.clicked.connect(self.logout)
            sidebar_layout.addWidget(logout_button)
            root.addWidget(sidebar)

            content_layout = QVBoxLayout()
            content_layout.setSpacing(12)
            self.header_title = QLabel("Dashboard")
            self.header_title.setObjectName("PageTitle")
            self.header_subtitle = QLabel("Visao geral da agenda e dos atendimentos.")
            self.header_subtitle.setObjectName("Subtitle")
            content_layout.addWidget(self.header_title)
            content_layout.addWidget(self.header_subtitle)
            self.stack = QStackedWidget()
            self.dashboard_page = DashboardPage(self.service, self.open_agenda_view, self.paths)
            self.agenda_page = self._build_agenda_page()
            self.clients_page = self._build_clients_page()
            self.services_page = self._build_services_page()
            self.professionals_page = self._build_professionals_page()
            self.finance_page = self._build_finance_page()
            self.users_page = self._build_users_page()
            self.settings_page = self._build_settings_page()
            for page in [self.dashboard_page, self.agenda_page, self.clients_page, self.services_page, self.professionals_page, self.finance_page, self.users_page, self.settings_page]:
                self.stack.addWidget(page)
            content_layout.addWidget(self.stack, 1)
            content_host = QWidget()
            content_host.setLayout(content_layout)
            root.addWidget(content_host, 1)
            self.setStatusBar(QStatusBar())
            self.statusBar().showMessage("Pronto")
            self._apply_permissions()

        def _apply_column_layout(self, table: QTableWidget, stretch_column: int, compact_columns: list[int] | None = None) -> None:
            header = table.horizontalHeader()
            for column_index in range(table.columnCount()):
                if compact_columns and column_index in compact_columns:
                    header.setSectionResizeMode(column_index, QHeaderView.ResizeMode.ResizeToContents)
                elif column_index == stretch_column:
                    header.setSectionResizeMode(column_index, QHeaderView.ResizeMode.Stretch)
                else:
                    header.setSectionResizeMode(column_index, QHeaderView.ResizeMode.Interactive)

        def _build_agenda_page(self) -> QWidget:
            page = QWidget()
            root_layout = QVBoxLayout(page)
            root_layout.setContentsMargins(0, 0, 0, 0)
            root_layout.setSpacing(0)
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            root_layout.addWidget(scroll)
            content = QWidget()
            scroll.setWidget(content)
            layout = QVBoxLayout(content)
            layout.setSpacing(14)

            hero_panel = QFrame()
            hero_panel.setObjectName("HeroPanel")
            hero_layout = QHBoxLayout(hero_panel)
            hero_layout.setContentsMargins(20, 18, 20, 18)
            hero_layout.setSpacing(14)
            hero_text = QVBoxLayout()
            hero_text.setSpacing(5)
            hero_badge = QLabel("Rotina da recepcao")
            hero_badge.setObjectName("HeroBadge")
            hero_title = QLabel("Agenda premium do SalonFlow")
            hero_title.setObjectName("AgendaHeroTitle")
            hero_subtitle = QLabel("Visualize horarios, confirme clientes e acompanhe o dia com mais clareza.")
            hero_subtitle.setObjectName("AgendaHeroText")
            hero_subtitle.setWordWrap(True)
            hero_text.addWidget(hero_badge, 0, Qt.AlignmentFlag.AlignLeft)
            hero_text.addWidget(hero_title)
            hero_text.addWidget(hero_subtitle)
            hero_chip_row = QHBoxLayout()
            hero_chip_row.setSpacing(8)
            for text in ["Conflitos bloqueados", "Confirmacao por WhatsApp", "Fechamento integrado"]:
                chip = QLabel(text)
                chip.setObjectName("AgendaHeroChip")
                hero_chip_row.addWidget(chip, 0, Qt.AlignmentFlag.AlignLeft)
            hero_chip_row.addStretch(1)
            hero_text.addLayout(hero_chip_row)
            hero_layout.addLayout(hero_text, 1)
            layout.addWidget(hero_panel)

            toolbar = QFrame()
            toolbar.setObjectName("AgendaToolbarPanel")
            toolbar_layout = QVBoxLayout(toolbar)
            toolbar_layout.setContentsMargins(18, 18, 18, 18)
            toolbar_layout.setSpacing(10)
            filter_row_host = QWidget()
            filter_row_host.setObjectName("AgendaFilterRow")
            filter_row = QHBoxLayout(filter_row_host)
            filter_row.setContentsMargins(0, 0, 0, 0)
            filter_row.setSpacing(10)
            action_row_host = QWidget()
            action_row_host.setObjectName("AgendaActionRow")
            action_row = QHBoxLayout(action_row_host)
            action_row.setContentsMargins(0, 0, 0, 0)
            action_row.setSpacing(10)
            previous_day_button = QPushButton("<")
            previous_day_button.setProperty("variant", "nav")
            previous_day_button.setMinimumWidth(44)
            previous_day_button.clicked.connect(lambda: self.shift_agenda_date(-1))
            today_button = QPushButton("Hoje")
            today_button.setProperty("variant", "nav")
            today_button.setMinimumWidth(72)
            today_button.clicked.connect(self.set_agenda_today)
            next_day_button = QPushButton(">")
            next_day_button.setProperty("variant", "nav")
            next_day_button.setMinimumWidth(44)
            next_day_button.clicked.connect(lambda: self.shift_agenda_date(1))
            self.filter_date = QDateEdit()
            self.filter_date.setCalendarPopup(True)
            self.filter_date.setDisplayFormat("yyyy-MM-dd")
            self.filter_date.setDate(QDate.currentDate())
            self.filter_date.setMinimumWidth(130)
            self.filter_professional = QComboBox()
            self.filter_professional.setMinimumWidth(220)
            self.view_mode = QComboBox()
            self.view_mode.addItems(["Hoje", "Dia", "Semana", "Proximos"])
            self.view_mode.setMinimumWidth(130)
            self.filter_status = QComboBox()
            self.filter_status.addItems(["Todos", "Agendado", "Confirmado", "Em atendimento", "Concluido", "Cancelado", "Faltou"])
            self.filter_status.setMinimumWidth(150)
            self.search_appointments = QLineEdit()
            self.search_appointments.setPlaceholderText("Buscar por cliente, servico ou observacao")
            self.search_appointments.setMinimumWidth(240)
            self.view_mode.currentTextChanged.connect(self.refresh_appointments)
            self.filter_professional.currentTextChanged.connect(self.refresh_appointments)
            self.filter_status.currentTextChanged.connect(self.refresh_appointments)
            self.search_appointments.textChanged.connect(self.refresh_appointments)
            apply_button = QPushButton("Aplicar filtros")
            apply_button.setProperty("variant", "secondary")
            apply_button.setMinimumWidth(138)
            apply_button.clicked.connect(self.refresh_appointments)
            create_button = QPushButton("Novo agendamento")
            create_button.setMinimumWidth(168)
            create_button.clicked.connect(self.create_appointment)
            edit_button = QPushButton("Editar")
            edit_button.setProperty("variant", "secondary")
            edit_button.setMinimumWidth(96)
            edit_button.clicked.connect(self.edit_appointment)
            cancel_button = QPushButton("Cancelar")
            cancel_button.setProperty("variant", "ghost")
            cancel_button.setProperty("role", "danger")
            cancel_button.setMinimumWidth(112)
            cancel_button.clicked.connect(self.cancel_appointment)
            self.confirm_button = QPushButton("Marcar confirmado")
            self.confirm_button.setProperty("variant", "secondary")
            self.confirm_button.setMinimumWidth(160)
            self.confirm_button.clicked.connect(self.confirm_selected_appointment)
            self.whatsapp_button = QPushButton("Confirmar por WhatsApp")
            self.whatsapp_button.setProperty("variant", "secondary")
            self.whatsapp_button.setMinimumWidth(176)
            self.whatsapp_button.clicked.connect(self.open_whatsapp_confirmation)
            self.complete_button = QPushButton("Concluir")
            self.complete_button.setMinimumWidth(112)
            self.complete_button.clicked.connect(self.complete_appointment)
            filter_row.addWidget(previous_day_button)
            filter_row.addWidget(today_button)
            filter_row.addWidget(next_day_button)
            filter_row.addWidget(QLabel("Data"))
            filter_row.addWidget(self.filter_date)
            filter_row.addWidget(QLabel("Visualizacao"))
            filter_row.addWidget(self.view_mode)
            filter_row.addWidget(QLabel("Profissional"))
            filter_row.addWidget(self.filter_professional)
            filter_row.addWidget(QLabel("Status"))
            filter_row.addWidget(self.filter_status)
            filter_row.addWidget(self.search_appointments, 1)
            filter_row.addWidget(apply_button)
            action_row.addWidget(create_button)
            action_row.addWidget(edit_button)
            action_row.addWidget(cancel_button)
            action_row.addWidget(self.confirm_button)
            action_row.addWidget(self.whatsapp_button)
            action_row.addWidget(self.complete_button)
            action_row.addStretch(1)
            toolbar_layout.addWidget(filter_row_host)
            toolbar_layout.addWidget(action_row_host)
            layout.addWidget(toolbar)
            schedule_layout = QHBoxLayout()
            schedule_layout.setSpacing(14)
            schedule_left = QVBoxLayout()
            schedule_panel = QFrame()
            schedule_panel.setObjectName("AgendaCanvasPanel")
            schedule_panel_layout = QVBoxLayout(schedule_panel)
            schedule_panel_layout.setContentsMargins(18, 18, 18, 18)
            schedule_panel_layout.setSpacing(12)
            list_title = QLabel("Agendamentos filtrados")
            list_title.setObjectName("SectionTitle")
            list_caption = QLabel("Selecione um horario para abrir as acoes rapidas, confirmar clientes e finalizar atendimentos.")
            list_caption.setObjectName("AgendaSectionCaption")
            list_caption.setWordWrap(True)
            self.agenda_mode_badge = QLabel("Modo: Hoje")
            self.agenda_mode_badge.setObjectName("AgendaModeBadge")
            self.agenda_range_label = QLabel("Hoje")
            self.agenda_range_label.setObjectName("AgendaRangeLabel")
            self.agenda_context_label = QLabel("Veja rapidamente os compromissos do dia e avance para o atendimento com mais seguranca.")
            self.agenda_context_label.setObjectName("AgendaContextText")
            schedule_panel_layout.addWidget(list_title)
            schedule_panel_layout.addWidget(list_caption)
            schedule_panel_layout.addWidget(self.agenda_mode_badge, 0, Qt.AlignmentFlag.AlignLeft)
            schedule_panel_layout.addWidget(self.agenda_range_label)
            schedule_panel_layout.addWidget(self.agenda_context_label)
            self.appointments_table = QTableWidget(0, 8)
            self.appointments_table.setObjectName("AgendaTable")
            self.appointments_table.setHorizontalHeaderLabels(["ID", "Cliente", "Profissional", "Servico", "Data", "Horario", "Valor", "Status"])
            self.appointments_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            self.appointments_table.setAlternatingRowColors(True)
            self.appointments_table.verticalHeader().setVisible(False)
            self.appointments_table.verticalHeader().setDefaultSectionSize(44)
            self.appointments_table.setMinimumHeight(330)
            self.dashboard_page._configure_table(self.appointments_table)
            self._apply_column_layout(self.appointments_table, 1, [0, 4, 5, 6, 7])
            self.appointments_table.setColumnWidth(2, 170)
            self.appointments_table.setColumnWidth(3, 170)
            self.appointments_table.itemSelectionChanged.connect(self._refresh_selected_appointment_details)
            self.appointments_table.itemDoubleClicked.connect(lambda _item: self.edit_appointment())
            schedule_panel_layout.addWidget(self.appointments_table, 1)
            self.appointments_empty = EmptyStateCard(
                "Nenhum agendamento encontrado",
                "Ajuste os filtros ou crie um novo horario para comecar a preencher a agenda do salao.",
                "+ Novo agendamento",
                self.create_appointment,
            )
            schedule_panel_layout.addWidget(self.appointments_empty)
            self.schedule_grid = QTableWidget(0, 0)
            self.schedule_grid.setObjectName("ScheduleGrid")
            self.dashboard_page._configure_table(self.schedule_grid)
            self.schedule_grid.setMinimumHeight(300)
            self.schedule_grid.setVisible(False)
            schedule_panel_layout.addWidget(self.schedule_grid)
            schedule_left.addWidget(schedule_panel, 1)
            schedule_layout.addLayout(schedule_left, 5)

            details_panel = QFrame()
            details_panel.setObjectName("AgendaDetailsPanel")
            details_panel.setMinimumWidth(340)
            details_panel.setMaximumWidth(430)
            details_layout = QVBoxLayout(details_panel)
            details_layout.setContentsMargins(18, 18, 18, 18)
            details_layout.setSpacing(12)
            details_title = QLabel("Detalhes do atendimento")
            details_title.setObjectName("SectionTitle")
            self.detail_hint = QLabel("Selecione um agendamento para ver informacoes completas, observacoes e proximas acoes.")
            self.detail_hint.setObjectName("AgendaDetailHint")
            self.detail_status = StatusPill("Sem selecao")
            self.detail_client = QLabel("Cliente\n-")
            self.detail_professional = QLabel("Profissional\n-")
            self.detail_service = QLabel("Servico\n-")
            self.detail_datetime = QLabel("Quando\n-")
            self.detail_duration = QLabel("Duracao\n-")
            self.detail_value = QLabel("Valor\n-")
            for label in [
                self.detail_client,
                self.detail_professional,
                self.detail_service,
                self.detail_datetime,
                self.detail_duration,
                self.detail_value,
            ]:
                label.setObjectName("AgendaDetailValue")
            self.detail_notes = QLabel("Nenhuma observacao registrada para este atendimento.")
            self.detail_notes.setWordWrap(True)
            self.detail_notes.setObjectName("AgendaDetailNote")
            quick_actions = QHBoxLayout()
            detail_edit_button = QPushButton("Editar")
            detail_edit_button.setProperty("variant", "secondary")
            detail_edit_button.clicked.connect(self.edit_appointment)
            self.detail_confirm_button = QPushButton("Marcar confirmado")
            self.detail_confirm_button.setProperty("variant", "secondary")
            self.detail_confirm_button.clicked.connect(self.confirm_selected_appointment)
            self.detail_whatsapp_button = QPushButton("Confirmar por WhatsApp")
            self.detail_whatsapp_button.setProperty("variant", "secondary")
            self.detail_whatsapp_button.clicked.connect(self.open_whatsapp_confirmation)
            self.detail_complete_button = QPushButton("Concluir")
            self.detail_complete_button.setMinimumWidth(112)
            self.detail_complete_button.clicked.connect(self.complete_appointment)
            detail_edit_button.setMinimumWidth(96)
            self.detail_confirm_button.setMinimumWidth(160)
            self.detail_whatsapp_button.setMinimumWidth(176)
            quick_actions_grid = QGridLayout()
            quick_actions_grid.setHorizontalSpacing(10)
            quick_actions_grid.setVerticalSpacing(10)
            quick_actions_grid.addWidget(detail_edit_button, 0, 0)
            quick_actions_grid.addWidget(self.detail_confirm_button, 0, 1)
            quick_actions_grid.addWidget(self.detail_whatsapp_button, 1, 0)
            quick_actions_grid.addWidget(self.detail_complete_button, 1, 1)
            details_layout.addWidget(details_title)
            details_layout.addWidget(self.detail_hint)
            details_layout.addWidget(self.detail_status)
            detail_grid = QGridLayout()
            detail_grid.setHorizontalSpacing(10)
            detail_grid.setVerticalSpacing(10)
            detail_grid.addWidget(self.detail_client, 0, 0)
            detail_grid.addWidget(self.detail_professional, 0, 1)
            detail_grid.addWidget(self.detail_service, 1, 0)
            detail_grid.addWidget(self.detail_datetime, 1, 1)
            detail_grid.addWidget(self.detail_duration, 2, 0)
            detail_grid.addWidget(self.detail_value, 2, 1)
            details_layout.addLayout(detail_grid)
            notes_title = QLabel("Observacoes")
            notes_title.setObjectName("AgendaDetailLabel")
            details_layout.addWidget(notes_title)
            details_layout.addWidget(self.detail_notes)
            details_layout.addStretch(1)
            details_layout.addLayout(quick_actions_grid)
            schedule_layout.addWidget(details_panel, 3)
            self._update_appointment_action_buttons(None)
            layout.addLayout(schedule_layout, 1)
            overview_title = QLabel("Resumo rapido da agenda")
            overview_title.setObjectName("SectionTitle")
            layout.addWidget(overview_title)
            overview_caption = QLabel("Use este resumo para entender o ritmo do dia antes de abrir cada horario.")
            overview_caption.setObjectName("AgendaSectionCaption")
            layout.addWidget(overview_caption)
            self.agenda_cards_layout = QGridLayout()
            self.agenda_cards_layout.setHorizontalSpacing(12)
            self.agenda_cards_layout.setVerticalSpacing(12)
            self.agenda_total_card = StatCard("Na selecao", "0", "Itens visiveis")
            self.agenda_confirmed_card = StatCard("Confirmados", "0", "Com chegada prevista")
            self.agenda_progress_card = StatCard("Em atendimento", "0", "Atendimentos em curso")
            self.agenda_pending_card = StatCard("Pendentes", "0", "Agendado ou confirmado")
            for index, card in enumerate([
                self.agenda_total_card,
                self.agenda_confirmed_card,
                self.agenda_progress_card,
                self.agenda_pending_card,
            ]):
                self.agenda_cards_layout.addWidget(card, 0, index)
            layout.addLayout(self.agenda_cards_layout)
            timeline_title = QLabel("Calendario visual")
            timeline_title.setObjectName("SectionTitle")
            layout.addWidget(timeline_title)
            self.timeline_caption = QLabel("Blocos organizados por data para acompanhar o fluxo da equipe com mais conforto.")
            self.timeline_caption.setObjectName("AgendaSectionCaption")
            layout.addWidget(self.timeline_caption)
            self.timeline_panel = QFrame()
            self.timeline_panel.setObjectName("AgendaCanvasPanel")
            self.timeline_panel_layout = QVBoxLayout(self.timeline_panel)
            self.timeline_panel_layout.setContentsMargins(16, 16, 16, 16)
            self.timeline_panel_layout.setSpacing(10)
            self.timeline_host = QWidget()
            self.timeline_layout = QVBoxLayout(self.timeline_host)
            self.timeline_layout.setContentsMargins(0, 0, 0, 0)
            self.timeline_layout.setSpacing(10)
            self.timeline_panel_layout.addWidget(self.timeline_host)
            layout.addWidget(self.timeline_panel)
            return page

        def _build_clients_page(self) -> QWidget:
            page = QWidget()
            layout = QVBoxLayout(page)
            actions = QHBoxLayout()
            add_button = QPushButton("Novo cliente")
            add_button.clicked.connect(self.create_client)
            actions.addWidget(add_button)
            view_button = QPushButton("Visualizar ficha")
            view_button.clicked.connect(self.open_selected_client_profile)
            actions.addWidget(view_button)
            self.clients_search = QLineEdit()
            self.clients_search.setPlaceholderText("Buscar por nome, telefone, WhatsApp ou e-mail")
            self.clients_search.textChanged.connect(self.refresh_clients)
            actions.addWidget(self.clients_search, 1)
            actions.addStretch(1)
            layout.addLayout(actions)
            self.clients_table = QTableWidget(0, 5)
            self.clients_table.setHorizontalHeaderLabels(["Nome", "Telefone", "WhatsApp", "E-mail", "Aniversario"])
            self.clients_table.horizontalHeader().setStretchLastSection(True)
            self.clients_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            self.clients_table.setAlternatingRowColors(True)
            self.clients_table.verticalHeader().setVisible(False)
            self.clients_table.itemDoubleClicked.connect(lambda _item: self.open_selected_client_profile())
            self.dashboard_page._configure_table(self.clients_table)
            layout.addWidget(self.clients_table, 1)
            self.clients_empty = EmptyStateCard(
                "Nenhum cliente cadastrado",
                "Cadastre os clientes do salao para comecar a organizar a agenda e registrar preferencias importantes.",
                "+ Cadastrar cliente",
                self.create_client,
            )
            layout.addWidget(self.clients_empty)
            return page

        def _build_services_page(self) -> QWidget:
            page = QWidget()
            layout = QVBoxLayout(page)
            actions = QHBoxLayout()
            add_button = QPushButton("Novo servico")
            add_button.clicked.connect(self.create_service)
            actions.addWidget(add_button)
            seed_button = QPushButton("Adicionar servicos prontos")
            seed_button.clicked.connect(self.seed_default_services)
            actions.addWidget(seed_button)
            self.services_search = QLineEdit()
            self.services_search.setPlaceholderText("Buscar por nome ou categoria")
            self.services_search.textChanged.connect(self.refresh_services)
            actions.addWidget(self.services_search, 1)
            actions.addStretch(1)
            layout.addLayout(actions)
            self.services_table = QTableWidget(0, 5)
            self.services_table.setHorizontalHeaderLabels(["Nome", "Categoria", "Duracao", "Preco", "Ativo"])
            self.services_table.horizontalHeader().setStretchLastSection(True)
            self.services_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            self.services_table.setAlternatingRowColors(True)
            self.services_table.verticalHeader().setVisible(False)
            self.dashboard_page._configure_table(self.services_table)
            layout.addWidget(self.services_table, 1)
            self.services_empty = EmptyStateCard(
                "Nenhum servico cadastrado",
                "Monte o catalogo do salao com nome, duracao e preco para agilizar os agendamentos.",
                "+ Cadastrar servico",
                self.create_service,
            )
            layout.addWidget(self.services_empty)
            return page

        def _build_professionals_page(self) -> QWidget:
            page = QWidget()
            layout = QVBoxLayout(page)
            actions = QHBoxLayout()
            add_button = QPushButton("Novo profissional")
            add_button.clicked.connect(self.create_professional)
            actions.addWidget(add_button)
            self.professionals_search = QLineEdit()
            self.professionals_search.setPlaceholderText("Buscar por nome, telefone ou especialidade")
            self.professionals_search.textChanged.connect(self.refresh_professionals)
            actions.addWidget(self.professionals_search, 1)
            actions.addStretch(1)
            layout.addLayout(actions)
            self.professionals_table = QTableWidget(0, 4)
            self.professionals_table.setHorizontalHeaderLabels(["Nome", "Telefone", "Especialidade", "Ativo"])
            self.professionals_table.horizontalHeader().setStretchLastSection(True)
            self.professionals_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            self.professionals_table.setAlternatingRowColors(True)
            self.professionals_table.verticalHeader().setVisible(False)
            self.dashboard_page._configure_table(self.professionals_table)
            layout.addWidget(self.professionals_table, 1)
            self.professionals_empty = EmptyStateCard(
                "Nenhum profissional cadastrado",
                "Cadastre os profissionais do salao para comecar a distribuir horarios e organizar a equipe.",
                "+ Cadastrar profissional",
                self.create_professional,
            )
            layout.addWidget(self.professionals_empty)
            return page

        def _build_finance_page(self) -> QWidget:
            page = QWidget()
            layout = QVBoxLayout(page)
            self.finance_tabs = QTabWidget()
            layout.addWidget(self.finance_tabs, 1)

            overview_tab = QWidget()
            overview_layout = QVBoxLayout(overview_tab)
            overview_cards = QGridLayout()
            self.fin_receitas_card = StatCard("Receitas do mes", "R$ 0,00", "Entradas confirmadas")
            self.fin_despesas_card = StatCard("Despesas do mes", "R$ 0,00", "Saidas confirmadas")
            self.fin_saldo_card = StatCard("Saldo", "R$ 0,00", "Resultado do periodo")
            self.fin_receber_card = StatCard("A receber", "R$ 0,00", "Contas em aberto")
            self.fin_pagar_card = StatCard("A pagar", "R$ 0,00", "Despesas pendentes")
            self.fin_atrasados_card = StatCard("Atrasados", "R$ 0,00", "Titulos vencidos")
            for index, card in enumerate([
                self.fin_receitas_card,
                self.fin_despesas_card,
                self.fin_saldo_card,
                self.fin_receber_card,
                self.fin_pagar_card,
                self.fin_atrasados_card,
            ]):
                overview_cards.addWidget(card, index // 3, index % 3)
            overview_layout.addLayout(overview_cards)
            overview_actions = QHBoxLayout()
            backup_button = QPushButton("Criar backup")
            backup_button.clicked.connect(self.create_finance_backup)
            overview_actions.addWidget(backup_button)
            overview_actions.addStretch(1)
            overview_layout.addLayout(overview_actions)
            alerts_title = QLabel("Alertas e ultimas movimentacoes")
            alerts_title.setObjectName("SectionTitle")
            overview_layout.addWidget(alerts_title)
            self.finance_alerts = QTableWidget(0, 1)
            self.finance_alerts.setHorizontalHeaderLabels(["Alertas financeiros"])
            self.finance_alerts.horizontalHeader().setStretchLastSection(True)
            self.dashboard_page._configure_table(self.finance_alerts)
            overview_layout.addWidget(self.finance_alerts)
            self.finance_movements = QTableWidget(0, 4)
            self.finance_movements.setHorizontalHeaderLabels(["Data", "Descricao", "Tipo", "Valor"])
            self.finance_movements.horizontalHeader().setStretchLastSection(True)
            self.dashboard_page._configure_table(self.finance_movements)
            overview_layout.addWidget(self.finance_movements)
            self.finance_tabs.addTab(overview_tab, "Visao geral")

            cash_tab = QWidget()
            cash_layout = QVBoxLayout(cash_tab)
            cash_actions = QHBoxLayout()
            open_cash_button = QPushButton("Abrir caixa")
            open_cash_button.clicked.connect(self.open_cash_session)
            close_cash_button = QPushButton("Fechar caixa")
            close_cash_button.clicked.connect(self.close_cash_session)
            cash_actions.addWidget(open_cash_button)
            cash_actions.addWidget(close_cash_button)
            cash_actions.addStretch(1)
            cash_layout.addLayout(cash_actions)
            self.cash_entries_table = QTableWidget(0, 5)
            self.cash_entries_table.setHorizontalHeaderLabels(["Data", "Tipo", "Descricao", "Forma", "Valor"])
            self.cash_entries_table.horizontalHeader().setStretchLastSection(True)
            self.dashboard_page._configure_table(self.cash_entries_table)
            self._apply_column_layout(self.cash_entries_table, 2, [0, 1, 3, 4])
            cash_layout.addWidget(self.cash_entries_table)
            self.finance_tabs.addTab(cash_tab, "Caixa")

            receivable_tab = QWidget()
            receivable_layout = QVBoxLayout(receivable_tab)
            receivable_actions = QHBoxLayout()
            new_receivable_button = QPushButton("Nova conta")
            new_receivable_button.clicked.connect(self.create_receivable_account)
            receive_button = QPushButton("Receber")
            receive_button.clicked.connect(self.receive_selected_receivable)
            billing_button = QPushButton("Gerar cobranca")
            billing_button.clicked.connect(self.create_billing_for_selected_receivable)
            receivable_actions.addWidget(new_receivable_button)
            receivable_actions.addWidget(receive_button)
            receivable_actions.addWidget(billing_button)
            receivable_actions.addStretch(1)
            receivable_layout.addLayout(receivable_actions)
            self.receivables_table = QTableWidget(0, 8)
            self.receivables_table.setHorizontalHeaderLabels(["ID", "Cliente", "Descricao", "Parcela", "Vencimento", "Restante", "Forma", "Status"])
            self.receivables_table.horizontalHeader().setStretchLastSection(True)
            self.dashboard_page._configure_table(self.receivables_table)
            self._apply_column_layout(self.receivables_table, 2, [0, 3, 4, 5, 7])
            receivable_layout.addWidget(self.receivables_table)
            self.finance_tabs.addTab(receivable_tab, "Contas a receber")

            payable_tab = QWidget()
            payable_layout = QVBoxLayout(payable_tab)
            payable_actions = QHBoxLayout()
            new_payable_button = QPushButton("Nova conta")
            new_payable_button.clicked.connect(self.create_payable_account)
            pay_button = QPushButton("Pagar")
            pay_button.clicked.connect(self.pay_selected_payable)
            payable_actions.addWidget(new_payable_button)
            payable_actions.addWidget(pay_button)
            payable_actions.addStretch(1)
            payable_layout.addLayout(payable_actions)
            self.payables_table = QTableWidget(0, 7)
            self.payables_table.setHorizontalHeaderLabels(["ID", "Descricao", "Beneficiario", "Parcela", "Vencimento", "Restante", "Status"])
            self.payables_table.horizontalHeader().setStretchLastSection(True)
            self.dashboard_page._configure_table(self.payables_table)
            self._apply_column_layout(self.payables_table, 1, [0, 3, 4, 5, 6])
            payable_layout.addWidget(self.payables_table)
            self.finance_tabs.addTab(payable_tab, "Contas a pagar")

            billing_tab = QWidget()
            billing_layout = QVBoxLayout(billing_tab)
            self.billings_table = QTableWidget(0, 6)
            self.billings_table.setHorizontalHeaderLabels(["ID", "Pagador", "Descricao", "Vencimento", "Valor", "Status"])
            self.billings_table.horizontalHeader().setStretchLastSection(True)
            self.dashboard_page._configure_table(self.billings_table)
            self._apply_column_layout(self.billings_table, 2, [0, 3, 4, 5])
            billing_layout.addWidget(self.billings_table)
            self.finance_tabs.addTab(billing_tab, "Cobrancas")

            commissions_tab = QWidget()
            commissions_layout = QVBoxLayout(commissions_tab)
            commissions_actions = QHBoxLayout()
            pay_commission_button = QPushButton("Pagar comissao")
            pay_commission_button.clicked.connect(self.pay_selected_commission)
            commissions_actions.addWidget(pay_commission_button)
            commissions_actions.addStretch(1)
            commissions_layout.addLayout(commissions_actions)
            self.commissions_table = QTableWidget(0, 6)
            self.commissions_table.setHorizontalHeaderLabels(["ID", "Profissional", "Atendimento", "Base", "Comissao", "Status"])
            self.commissions_table.horizontalHeader().setStretchLastSection(True)
            self.dashboard_page._configure_table(self.commissions_table)
            self._apply_column_layout(self.commissions_table, 1, [0, 2, 3, 4, 5])
            commissions_layout.addWidget(self.commissions_table)
            self.finance_tabs.addTab(commissions_tab, "Comissoes")

            reports_tab = QWidget()
            reports_layout = QVBoxLayout(reports_tab)
            methods_title = QLabel("Recebimentos por forma de pagamento")
            methods_title.setObjectName("SectionTitle")
            reports_layout.addWidget(methods_title)
            self.payment_methods_table = QTableWidget(0, 4)
            self.payment_methods_table.setHorizontalHeaderLabels(["Forma", "Tipo", "Total", "Lancamentos"])
            self.payment_methods_table.horizontalHeader().setStretchLastSection(True)
            self.dashboard_page._configure_table(self.payment_methods_table)
            self._apply_column_layout(self.payment_methods_table, 0, [2, 3])
            reports_layout.addWidget(self.payment_methods_table)
            audit_title = QLabel("Auditoria financeira")
            audit_title.setObjectName("SectionTitle")
            reports_layout.addWidget(audit_title)
            self.audit_table = QTableWidget(0, 5)
            self.audit_table.setHorizontalHeaderLabels(["Data", "Operacao", "Entidade", "ID", "Motivo"])
            self.audit_table.horizontalHeader().setStretchLastSection(True)
            self.dashboard_page._configure_table(self.audit_table)
            self._apply_column_layout(self.audit_table, 4, [0, 1, 2, 3])
            reports_layout.addWidget(self.audit_table)
            self.finance_tabs.addTab(reports_tab, "Relatorios")

            receipts_tab = QWidget()
            receipts_layout = QVBoxLayout(receipts_tab)
            receipts_actions = QHBoxLayout()
            generate_receipt_button = QPushButton("Gerar recibo")
            generate_receipt_button.clicked.connect(self.generate_selected_receipt)
            open_receipt_button = QPushButton("Abrir recibo")
            open_receipt_button.clicked.connect(self.open_selected_receipt)
            save_receipt_button = QPushButton("Salvar como PDF")
            save_receipt_button.clicked.connect(self.export_selected_receipt)
            reprint_receipt_button = QPushButton("Reimprimir")
            reprint_receipt_button.clicked.connect(self.reprint_selected_receipt)
            receipts_actions.addWidget(generate_receipt_button)
            receipts_actions.addWidget(open_receipt_button)
            receipts_actions.addWidget(save_receipt_button)
            receipts_actions.addWidget(reprint_receipt_button)
            receipts_actions.addStretch(1)
            receipts_layout.addLayout(receipts_actions)
            self.receipts_table = QTableWidget(0, 8)
            self.receipts_table.setHorizontalHeaderLabels(
                ["Pagamento", "Recibo", "Data", "Cliente", "Profissional", "Servico", "Forma", "Valor pago"]
            )
            self.receipts_table.horizontalHeader().setStretchLastSection(True)
            self.dashboard_page._configure_table(self.receipts_table)
            self._apply_column_layout(self.receipts_table, 5, [0, 1, 2, 6, 7])
            receipts_layout.addWidget(self.receipts_table)
            self.finance_tabs.addTab(receipts_tab, "Recibos")
            return page

        def _build_users_page(self) -> QWidget:
            page = QWidget()
            layout = QVBoxLayout(page)
            actions = QHBoxLayout()
            add_button = QPushButton("Novo usuario")
            add_button.clicked.connect(self.create_user_account)
            actions.addWidget(add_button)
            actions.addStretch(1)
            layout.addLayout(actions)
            self.users_table = QTableWidget(0, 5)
            self.users_table.setHorizontalHeaderLabels(["ID", "Nome", "Usuario", "Perfil", "Status"])
            self.users_table.horizontalHeader().setStretchLastSection(True)
            self.dashboard_page._configure_table(self.users_table)
            self._apply_column_layout(self.users_table, 1, [0, 3, 4])
            layout.addWidget(self.users_table)
            self.audit_log_table = QTableWidget(0, 5)
            self.audit_log_table.setHorizontalHeaderLabels(["Data", "Usuario", "Acao", "Entidade", "Descricao"])
            self.audit_log_table.horizontalHeader().setStretchLastSection(True)
            self.dashboard_page._configure_table(self.audit_log_table)
            self._apply_column_layout(self.audit_log_table, 4, [0, 1, 2, 3])
            layout.addWidget(self.audit_log_table)
            return page

        def _build_settings_page(self) -> QWidget:
            page = QWidget()
            layout = QVBoxLayout(page)
            salon_panel = QFrame()
            salon_panel.setObjectName("Panel")
            salon_layout = QFormLayout(salon_panel)
            salon_layout.setContentsMargins(18, 18, 18, 18)
            salon_layout.setSpacing(12)
            self.setting_salon_name = QLineEdit()
            self.setting_phone = QLineEdit()
            self.setting_whatsapp = QLineEdit()
            self.setting_email = QLineEdit()
            self.setting_address = QLineEdit()
            self.setting_document = QLineEdit()
            self.setting_document.setPlaceholderText("CPF ou CNPJ")
            self.setting_logo_path = QLineEdit()
            self.setting_logo_path.setPlaceholderText("Caminho opcional da logo")
            logo_actions = QHBoxLayout()
            logo_actions.setSpacing(8)
            logo_actions.addWidget(self.setting_logo_path, 1)
            browse_logo_button = QPushButton("Escolher logo")
            browse_logo_button.clicked.connect(self.choose_logo_file)
            logo_actions.addWidget(browse_logo_button)
            salon_layout.addRow("Nome do salao", self.setting_salon_name)
            salon_layout.addRow("CPF/CNPJ", self.setting_document)
            salon_layout.addRow("Telefone", self.setting_phone)
            salon_layout.addRow("WhatsApp", self.setting_whatsapp)
            salon_layout.addRow("E-mail", self.setting_email)
            salon_layout.addRow("Endereco", self.setting_address)
            salon_layout.addRow("Logo", logo_actions)
            save_salon_button = QPushButton("Salvar configuracoes")
            save_salon_button.clicked.connect(self.save_settings)
            salon_layout.addRow("", save_salon_button)
            layout.addWidget(salon_panel)
            backup_panel = QFrame()
            backup_panel.setObjectName("Panel")
            backup_layout = QVBoxLayout(backup_panel)
            backup_layout.setContentsMargins(18, 18, 18, 18)
            backup_layout.setSpacing(10)
            backup_title = QLabel("Backup")
            backup_title.setObjectName("SectionTitle")
            self.last_backup_label = QLabel("Nenhum backup registrado.")
            self.last_backup_label.setObjectName("PageSubtitle")
            backup_now_button = QPushButton("Criar backup agora")
            backup_now_button.clicked.connect(self.create_finance_backup)
            backup_layout.addWidget(backup_title)
            backup_layout.addWidget(self.last_backup_label)
            backup_layout.addWidget(backup_now_button, 0, Qt.AlignmentFlag.AlignLeft)
            layout.addWidget(backup_panel)
            layout.addStretch(1)
            return page

        def navigate(self, index: int) -> None:
            if index < len(self.nav_buttons) and not self.nav_buttons[index].isEnabled():
                self.statusBar().showMessage("Acesso restrito para o seu perfil.", 4000)
                return
            self.stack.setCurrentIndex(index)
            titles = ["Dashboard", "Agenda", "Clientes", "Servicos", "Profissionais", "Financeiro", "Usuarios", "Configuracoes"]
            subtitles = [
                "Visao geral da agenda e dos atendimentos.",
                "Crie, edite, conclua e cancele agendamentos.",
                "Cadastro de clientes e observacoes importantes.",
                "Catalogo de servicos com duracao e preco.",
                "Equipe ativa e especialidades do salao.",
                "Recebimentos, caixa, cobrancas e comissoes integrados ao salao.",
                "Controle de acesso e historico de acoes do sistema.",
                "Dados do salao, backup e preferencias operacionais.",
            ]
            for button_index, button in enumerate(self.nav_buttons):
                button.setChecked(button_index == index)
            self.header_title.setText(titles[index])
            self.header_subtitle.setText(subtitles[index])

        def _apply_permissions(self) -> None:
            page_permissions = [
                "view_dashboard",
                "view_agenda",
                "view_clients",
                "view_services",
                "view_professionals",
                "view_finance",
                "view_users",
                "view_settings",
            ]
            first_allowed = 0
            for index, permission in enumerate(page_permissions):
                allowed = self.permission_service.has_permission(self.current_user, permission)
                self.nav_buttons[index].setEnabled(allowed)
                if allowed and first_allowed == 0:
                    first_allowed = index
            self.navigate(first_allowed)

        def _require_permission(self, permission: str, message: str = "Acesso negado.") -> bool:
            if self.permission_service.has_permission(self.current_user, permission):
                return True
            QMessageBox.warning(self, "Permissao negada", message)
            return False

        def logout(self) -> None:
            self.audit_service.log(self.current_user.username, "logout", "session", 0, "Encerramento da sessao")
            self.close()

        def choose_logo_file(self) -> None:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Selecionar logo",
                str(self.paths.user_data_dir),
                "Imagens (*.png *.jpg *.jpeg *.bmp *.webp)",
            )
            if file_path:
                self.setting_logo_path.setText(file_path)

        def load_settings(self) -> None:
            values = {}
            for key in [
                "salon_name",
                "salon_phone",
                "salon_whatsapp",
                "salon_email",
                "salon_address",
                "salon_document",
                "salon_logo_path",
                "last_backup_path",
            ]:
                row = self.database.fetchone("SELECT setting_value FROM app_settings WHERE setting_key = ?", (key,))
                values[key] = str(row["setting_value"]) if row else ""
            if hasattr(self, "setting_salon_name"):
                self.setting_salon_name.setText(values["salon_name"])
                self.setting_document.setText(values["salon_document"])
                self.setting_phone.setText(values["salon_phone"])
                self.setting_whatsapp.setText(values["salon_whatsapp"])
                self.setting_email.setText(values["salon_email"])
                self.setting_address.setText(values["salon_address"])
                self.setting_logo_path.setText(values["salon_logo_path"])
                self.last_backup_label.setText(values["last_backup_path"] or "Nenhum backup registrado.")

        def save_settings(self) -> None:
            if not self._require_permission("view_settings", "Seu perfil nao pode alterar configuracoes."):
                return
            payload = {
                "salon_name": self.setting_salon_name.text().strip(),
                "salon_document": self.setting_document.text().strip(),
                "salon_phone": self.setting_phone.text().strip(),
                "salon_whatsapp": self.setting_whatsapp.text().strip(),
                "salon_email": self.setting_email.text().strip(),
                "salon_address": self.setting_address.text().strip(),
                "salon_logo_path": self.setting_logo_path.text().strip(),
            }
            for key, value in payload.items():
                self.database.execute(
                    """
                    INSERT INTO app_settings (setting_key, setting_value)
                    VALUES (?, ?)
                    ON CONFLICT(setting_key) DO UPDATE SET setting_value = excluded.setting_value
                    """,
                    (key, value),
                )
            self.audit_service.log(self.current_user.username, "update", "settings", 0, "Configuracoes do salao atualizadas")
            self.statusBar().showMessage("Configuracoes salvas com sucesso.", 4000)

        def open_agenda_view(self, mode: str = "Hoje", create_new: bool = False) -> None:
            self.navigate(1)
            self.view_mode.setCurrentText(mode)
            self.filter_date.setDate(QDate.currentDate())
            self.refresh_appointments()
            if create_new:
                self.create_appointment()

        def create_client(self) -> None:
            if not self._require_permission("manage_clients", "Seu perfil nao pode cadastrar clientes."):
                return
            dialog = ClientDialog(parent=self)
            if dialog.exec() != dialog.Accepted:
                return
            try:
                client = self.service.add_client(**dialog.payload())
            except ValueError as exc:
                QMessageBox.critical(self, "Erro", str(exc))
                return
            self.refresh_all()
            self.audit_service.log(self.current_user.username, "create", "client", client.client_id or 0, client.name)
            self.statusBar().showMessage(f"Cliente criado: {client.client_id} - {client.name}", 4000)

        def edit_client_record(self, client_id: int) -> bool:
            if not self._require_permission("manage_clients", "Seu perfil nao pode editar clientes."):
                return False
            client = self.service.get_client(client_id)
            dialog = ClientDialog(client=client, parent=self)
            if dialog.exec() != dialog.Accepted:
                return False
            try:
                updated = self.service.update_client(client_id=client_id, **dialog.payload())
            except ValueError as exc:
                QMessageBox.critical(self, "Erro", str(exc))
                return False
            self.refresh_all()
            self.audit_service.log(self.current_user.username, "update", "client", updated.client_id or 0, updated.name)
            self.statusBar().showMessage(f"Cliente atualizado: {updated.name}", 4000)
            return True

        def create_appointment_for_client(self, client_id: int) -> bool:
            if not self._require_permission("manage_appointments", "Seu perfil nao pode criar agendamentos."):
                return False
            dialog = AppointmentDialog(self.service, parent=self)
            dialog.set_client(client_id)
            if dialog.exec() != dialog.Accepted:
                return False
            try:
                created = self.service.create_appointment(**dialog.payload())
            except ValueError as exc:
                QMessageBox.critical(self, "Erro", str(exc))
                return False
            self.refresh_all()
            self.audit_service.log(self.current_user.username, "create", "appointment", created.appointment_id or 0, f"Agendamento da cliente {client_id}")
            self.statusBar().showMessage("Agendamento criado.", 4000)
            return True

        def add_client_note(self, client_id: int) -> bool:
            if not self._require_permission("manage_clients", "Seu perfil nao pode registrar observacoes."):
                return False
            dialog = NoteTextDialog("Nova observacao", "Registre uma observacao importante para a equipe.", self)
            if dialog.exec() != dialog.Accepted:
                return False
            try:
                created = self.client_profile_service.add_note(client_id, dialog.payload(), self.current_user.username)
            except ValueError as exc:
                QMessageBox.critical(self, "Erro", str(exc))
                return False
            self.audit_service.log(self.current_user.username, "create", "client_note", created["note_id"], f"Observacao na cliente {client_id}")
            self.statusBar().showMessage("Observacao adicionada.", 4000)
            return True

        def save_client_preferences(self, client_id: int, payload: dict[str, str]) -> bool:
            if not self._require_permission("manage_clients", "Seu perfil nao pode alterar preferencias da cliente."):
                return False
            self.client_profile_service.save_preferences(client_id=client_id, **payload)
            self.audit_service.log(self.current_user.username, "update", "client_preferences", client_id, "Preferencias atualizadas")
            self.statusBar().showMessage("Preferencias salvas.", 4000)
            return True

        def create_professional(self) -> None:
            if not self._require_permission("manage_professionals", "Seu perfil nao pode cadastrar profissionais."):
                return
            dialog = ProfessionalDialog(self)
            if dialog.exec() != dialog.Accepted:
                return
            try:
                professional = self.service.add_professional(**dialog.payload())
            except ValueError as exc:
                QMessageBox.critical(self, "Erro", str(exc))
                return
            self.refresh_all()
            self.audit_service.log(self.current_user.username, "create", "professional", professional.professional_id or 0, professional.name)
            self.statusBar().showMessage(f"Profissional criado: {professional.professional_id} - {professional.name}", 4000)

        def create_service(self) -> None:
            if not self._require_permission("manage_services", "Seu perfil nao pode cadastrar servicos."):
                return
            dialog = ServiceDialog(self)
            if dialog.exec() != dialog.Accepted:
                return
            try:
                service_item = self.service.add_service(**dialog.payload())
            except ValueError as exc:
                QMessageBox.critical(self, "Erro", str(exc))
                return
            self.refresh_all()
            self.audit_service.log(self.current_user.username, "create", "service", service_item.service_id or 0, service_item.name)
            self.statusBar().showMessage(f"Servico criado: {service_item.service_id} - {service_item.name}", 4000)

        def seed_default_services(self) -> None:
            created = self.service.seed_default_services()
            self.refresh_all()
            if created:
                QMessageBox.information(
                    self,
                    "Servicos adicionados",
                    f"{created} servicos prontos foram adicionados ao catalogo.",
                )
                self.statusBar().showMessage(f"{created} servicos prontos adicionados.", 4000)
                return
            QMessageBox.information(
                self,
                "Nada para adicionar",
                "Os servicos padrao ja estao cadastrados no sistema.",
            )

        def create_receivable_account(self) -> None:
            if not self._require_permission("manage_finance", "Seu perfil nao pode criar contas a receber."):
                return
            if not self.service.list_clients():
                QMessageBox.information(self, "Clientes necessarios", "Cadastre ao menos um cliente antes de criar contas a receber.")
                return
            dialog = ReceivableDialog(self.service, self)
            if dialog.exec() != dialog.Accepted:
                return
            try:
                self.finance_service.create_receivable(**dialog.payload())
            except ValueError as exc:
                QMessageBox.critical(self, "Erro", str(exc))
                return
            self.refresh_all()
            self.audit_service.log(self.current_user.username, "create", "receivable", 0, "Nova conta a receber")
            self.statusBar().showMessage("Conta a receber criada.", 4000)

        def create_payable_account(self) -> None:
            if not self._require_permission("manage_finance", "Seu perfil nao pode criar contas a pagar."):
                return
            dialog = PayableDialog(self)
            if dialog.exec() != dialog.Accepted:
                return
            try:
                self.finance_service.create_payable(**dialog.payload())
            except ValueError as exc:
                QMessageBox.critical(self, "Erro", str(exc))
                return
            self.refresh_all()
            self.audit_service.log(self.current_user.username, "create", "payable", 0, "Nova conta a pagar")
            self.statusBar().showMessage("Conta a pagar criada.", 4000)

        def receive_selected_receivable(self) -> None:
            if not self._require_permission("receive_payments", "Seu perfil nao pode registrar recebimentos."):
                return
            item = self._selected_table_id(self.receivables_table)
            if item is None:
                QMessageBox.information(self, "Selecao", "Selecione uma conta a receber.")
                return
            receivable = self.finance_service.get_receivable(item)
            dialog = ReceivePaymentDialog(
                "Receber conta",
                f"Receba valores de {receivable.description} com atualizacao imediata do caixa.",
                float(receivable.remaining_amount),
                self,
            )
            if dialog.exec() != dialog.Accepted:
                return
            payload = dialog.payload()
            try:
                self.finance_service.receive_receivable(
                    receivable_id=item,
                    received_amount=payload["amount"],
                    payment_date=payload["payment_date"],
                    payment_method=payload["payment_method"],
                    discount=payload["discount"],
                    interest=payload["interest"],
                    notes=payload["notes"],
                    card_fee=payload["card_fee"],
                )
            except ValueError as exc:
                QMessageBox.critical(self, "Erro", str(exc))
                return
            self.refresh_all()
            self.audit_service.log(self.current_user.username, "receive", "receivable", item, receivable.description)
            self.statusBar().showMessage("Recebimento registrado.", 4000)

        def pay_selected_payable(self) -> None:
            if not self._require_permission("manage_finance", "Seu perfil nao pode pagar contas."):
                return
            item = self._selected_table_id(self.payables_table)
            if item is None:
                QMessageBox.information(self, "Selecao", "Selecione uma conta a pagar.")
                return
            row = next((payable for payable in self.finance_service.list_payables() if payable.payable_id == item), None)
            if row is None:
                QMessageBox.information(self, "Selecao", "Conta a pagar nao encontrada.")
                return
            dialog = ReceivePaymentDialog(
                "Pagar conta",
                f"Registre a saida referente a {row.description}.",
                float(row.remaining_amount),
                self,
            )
            if dialog.exec() != dialog.Accepted:
                return
            payload = dialog.payload()
            try:
                self.finance_service.pay_payable(
                    payable_id=item,
                    paid_amount=payload["amount"],
                    payment_date=payload["payment_date"],
                    payment_method=payload["payment_method"],
                    notes=payload["notes"],
                )
            except ValueError as exc:
                QMessageBox.critical(self, "Erro", str(exc))
                return
            self.refresh_all()
            self.audit_service.log(self.current_user.username, "pay", "payable", item, row.description)
            self.statusBar().showMessage("Pagamento registrado.", 4000)

        def create_billing_for_selected_receivable(self) -> None:
            if not self._require_permission("manage_finance", "Seu perfil nao pode criar cobrancas."):
                return
            item = self._selected_table_id(self.receivables_table)
            if item is None:
                QMessageBox.information(self, "Selecao", "Selecione uma conta a receber primeiro.")
                return
            receivable = self.finance_service.get_receivable(item)
            client = self.service.get_client(receivable.client_id)
            billing_id = self.finance_service.billing_service.create_charge(
                receivable_id=item,
                payer_name=client.name,
                description=receivable.description,
                amount=receivable.remaining_amount,
                issue_date=date.today().isoformat(),
                due_date=receivable.due_date,
                notes="Cobranca gerada no controle interno do SalonFlow.",
            )
            self.refresh_all()
            self.audit_service.log(self.current_user.username, "create", "billing", billing_id, receivable.description)
            self.statusBar().showMessage(f"Cobranca registrada: {billing_id}", 4000)

        def open_cash_session(self) -> None:
            if not self._require_permission("manage_finance", "Seu perfil nao pode abrir caixa."):
                return
            dialog = ReceivePaymentDialog("Abrir caixa", "Defina o saldo inicial do caixa do dia.", 0.0, self)
            if dialog.exec() != dialog.Accepted:
                return
            payload = dialog.payload()
            session_id = self.finance_service.cash_service.open_cash(payload["amount"], payload["notes"])
            self.refresh_all()
            self.audit_service.log(self.current_user.username, "open", "cash_session", session_id, "Abertura de caixa")
            self.statusBar().showMessage(f"Caixa aberto: {session_id}", 4000)

        def close_cash_session(self) -> None:
            if not self._require_permission("manage_finance", "Seu perfil nao pode fechar caixa."):
                return
            dialog = ReceivePaymentDialog("Fechar caixa", "Informe o saldo contado para fechar o caixa atual.", 0.0, self)
            if dialog.exec() != dialog.Accepted:
                return
            payload = dialog.payload()
            try:
                result = self.finance_service.cash_service.close_cash(payload["amount"], payload["notes"])
            except ValueError as exc:
                QMessageBox.critical(self, "Erro", str(exc))
                return
            self.refresh_all()
            self.audit_service.log(self.current_user.username, "close", "cash_session", 0, "Fechamento de caixa")
            QMessageBox.information(
                self,
                "Caixa fechado",
                f"Saldo esperado: {format_currency(float(result['expected_balance']))}\n"
                f"Saldo contado: {format_currency(float(result['counted_balance']))}\n"
                f"Diferenca: {format_currency(float(result['difference']))}",
            )

        def pay_selected_commission(self) -> None:
            if not self._require_permission("manage_finance", "Seu perfil nao pode pagar comissoes."):
                return
            item = self._selected_table_id(self.commissions_table)
            if item is None:
                QMessageBox.information(self, "Selecao", "Selecione uma comissao.")
                return
            row = next((commission for commission in self.finance_service.commission_service.list_commissions() if commission.commission_id == item), None)
            if row is None:
                QMessageBox.information(self, "Selecao", "Comissao nao encontrada.")
                return
            dialog = ReceivePaymentDialog(
                "Pagar comissao",
                "Registre o pagamento da comissao e, se desejar, gere a saida financeira correspondente.",
                float(row.commission_amount),
                self,
            )
            if dialog.exec() != dialog.Accepted:
                return
            payload = dialog.payload()
            try:
                self.finance_service.pay_commission(
                    commission_id=item,
                    payment_date=str(payload["payment_date"]),
                    payment_method=str(payload["payment_method"]),
                    notes=str(payload["notes"]),
                    create_cash_entry=True,
                )
            except ValueError as exc:
                QMessageBox.critical(self, "Erro", str(exc))
                return
            self.refresh_all()
            self.audit_service.log(self.current_user.username, "pay", "commission", item, "Pagamento de comissao")
            self.statusBar().showMessage("Comissao paga.", 4000)

        def create_finance_backup(self) -> None:
            if not self._require_permission("manage_finance", "Seu perfil nao pode criar backups."):
                return
            backup_name = f"salonflow-backup-{date.today().isoformat()}.db"
            target = self.paths.backups_dir / backup_name
            created = self.finance_service.create_backup(target)
            self.database.execute(
                """
                INSERT INTO app_settings (setting_key, setting_value)
                VALUES ('last_backup_path', ?)
                ON CONFLICT(setting_key) DO UPDATE SET setting_value = excluded.setting_value
                """,
                (str(created),),
            )
            self.load_settings()
            self.audit_service.log(self.current_user.username, "backup", "database", 0, str(created))
            QMessageBox.information(
                self,
                "Backup criado",
                f"Backup financeiro salvo em:\n{created}",
            )

        def generate_selected_receipt(self) -> None:
            if not self._require_permission("manage_finance", "Seu perfil nao pode gerar recibos."):
                return
            payment_id = self._selected_table_id(self.receipts_table)
            if payment_id is None:
                QMessageBox.information(self, "Selecao", "Selecione um pagamento para gerar o recibo.")
                return
            try:
                pdf_path = self.receipt_service.generate_receipt(payment_id)
            except ValueError as exc:
                QMessageBox.critical(self, "Erro", str(exc))
                return
            self.audit_service.log(self.current_user.username, "create", "receipt", payment_id, str(pdf_path))
            self.refresh_finance()
            QMessageBox.information(self, "Recibo gerado", f"Recibo salvo em:\n{pdf_path}")

        def open_selected_receipt(self) -> None:
            if not self._require_permission("view_finance", "Seu perfil nao pode visualizar recibos."):
                return
            payment_id = self._selected_table_id(self.receipts_table)
            if payment_id is None:
                QMessageBox.information(self, "Selecao", "Selecione um pagamento para abrir o recibo.")
                return
            try:
                pdf_path = self.receipt_service.receipt_path_for_payment(payment_id)
                if not pdf_path.exists():
                    pdf_path = self.receipt_service.generate_receipt(payment_id)
            except ValueError as exc:
                QMessageBox.critical(self, "Erro", str(exc))
                return
            try:
                os.startfile(str(pdf_path))
            except AttributeError:
                QMessageBox.information(self, "Recibo", f"Arquivo pronto em:\n{pdf_path}")
            except OSError as exc:
                QMessageBox.critical(self, "Erro", f"Nao foi possivel abrir o recibo.\n{exc}")
                return
            self.audit_service.log(self.current_user.username, "open", "receipt", payment_id, str(pdf_path))

        def export_selected_receipt(self) -> None:
            if not self._require_permission("manage_finance", "Seu perfil nao pode exportar recibos."):
                return
            payment_id = self._selected_table_id(self.receipts_table)
            if payment_id is None:
                QMessageBox.information(self, "Selecao", "Selecione um pagamento para salvar o recibo.")
                return
            default_path = self.receipt_service.receipt_path_for_payment(payment_id)
            target_path, _ = QFileDialog.getSaveFileName(
                self,
                "Salvar recibo como PDF",
                str(default_path),
                "PDF (*.pdf)",
            )
            if not target_path:
                return
            try:
                pdf_path = self.receipt_service.generate_receipt(payment_id, Path(target_path))
            except ValueError as exc:
                QMessageBox.critical(self, "Erro", str(exc))
                return
            self.audit_service.log(self.current_user.username, "create", "receipt", payment_id, f"Exportado: {pdf_path}")
            QMessageBox.information(self, "Recibo exportado", f"Arquivo salvo em:\n{pdf_path}")

        def reprint_selected_receipt(self) -> None:
            self.generate_selected_receipt()

        def create_appointment(self) -> None:
            if not self._require_permission("manage_appointments", "Seu perfil nao pode criar agendamentos."):
                return
            if not self.service.list_clients() or not self.service.list_professionals(active_only=True) or not self.service.list_services(active_only=True):
                QMessageBox.information(self, "Dados necessarios", "Cadastre cliente, profissional ativo e servico ativo antes de agendar.")
                return
            dialog = AppointmentDialog(self.service, parent=self)
            if dialog.exec() != dialog.Accepted:
                return
            try:
                appointment = self.service.create_appointment(**dialog.payload())
            except ValueError as exc:
                QMessageBox.critical(self, "Erro", str(exc))
                return
            self.refresh_all()
            self.audit_service.log(self.current_user.username, "create", "appointment", appointment.appointment_id or 0, "Novo agendamento")
            self.statusBar().showMessage(f"Agendamento criado: {appointment.appointment_id}", 4000)

        def edit_appointment(self) -> None:
            if not self._require_permission("manage_appointments", "Seu perfil nao pode editar agendamentos."):
                return
            appointment = self._selected_appointment()
            if not appointment:
                return
            if self.current_user.profile == "Profissional" and self.current_user.professional_id != int(appointment["professional_id"]):
                QMessageBox.warning(self, "Permissao negada", "Voce so pode editar a propria agenda.")
                return
            dialog = AppointmentDialog(self.service, appointment, self)
            if dialog.exec() != dialog.Accepted:
                return
            try:
                updated = self.service.update_appointment(int(appointment["appointment_id"]), **dialog.payload())
            except ValueError as exc:
                QMessageBox.critical(self, "Erro", str(exc))
                return
            self.refresh_all()
            self.audit_service.log(self.current_user.username, "update", "appointment", updated.appointment_id or 0, "Agendamento atualizado")
            self.statusBar().showMessage(f"Agendamento atualizado: {updated.appointment_id}", 4000)

        def cancel_appointment(self) -> None:
            if not self._require_permission("manage_appointments", "Seu perfil nao pode cancelar agendamentos."):
                return
            appointment = self._selected_appointment()
            if not appointment:
                return
            if self.finance_service.appointment_has_financial_activity(int(appointment["appointment_id"])):
                QMessageBox.warning(
                    self,
                    "Cancelamento bloqueado",
                    "Este atendimento ja possui movimentacao financeira. Registre estorno ou ajuste financeiro antes de cancelar.",
                )
                return
            answer = QMessageBox.question(
                self,
                "Cancelar agendamento",
                f"Deseja cancelar o horario de {appointment['client_name']} com {appointment['professional_name']}?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            try:
                updated = self.service.cancel_appointment(int(appointment["appointment_id"]))
            except ValueError as exc:
                QMessageBox.critical(self, "Erro", str(exc))
                return
            self.refresh_all()
            self.audit_service.log(self.current_user.username, "cancel", "appointment", updated.appointment_id or 0, "Agendamento cancelado")
            self.statusBar().showMessage(f"Agendamento cancelado: {updated.appointment_id}", 4000)

        def complete_appointment(self) -> None:
            if not self._require_permission("complete_appointments", "Seu perfil nao pode concluir atendimentos."):
                return
            appointment = self._selected_appointment()
            if not appointment:
                return
            if str(appointment["status"]) == "Concluido":
                QMessageBox.information(self, "Atendimento concluido", "Este atendimento ja foi concluido.")
                return
            if str(appointment["status"]) == "Cancelado":
                QMessageBox.information(self, "Atendimento cancelado", "Agendamentos cancelados nao podem ser concluidos.")
                return
            if str(appointment["status"]) == "Faltou":
                QMessageBox.information(self, "Atendimento ausente", "Agendamentos marcados como falta nao podem ser concluidos.")
                return
            if self.current_user.profile == "Profissional" and self.current_user.professional_id != int(appointment["professional_id"]):
                QMessageBox.warning(self, "Permissao negada", "Voce so pode concluir os proprios atendimentos.")
                return
            dialog = ReceivePaymentDialog(
                "Finalizar atendimento",
                "Concluir o atendimento agora tambem registra recebimento, caixa e comissao.",
                float(appointment["price"]),
                self,
                include_commission=True,
            )
            if dialog.exec() != dialog.Accepted:
                return
            payload = dialog.payload()
            try:
                self.finance_service.finalize_appointment_with_payment(
                    appointment_id=int(appointment["appointment_id"]),
                    payment_method=str(payload["payment_method"]),
                    commission_percentage=float(payload["commission_percentage"] or 40.0),
                    payment_date=str(payload["payment_date"]),
                    received_amount=float(payload["amount"]),
                    discount=float(payload["discount"]),
                    interest=float(payload["interest"]),
                    card_fee=float(payload["card_fee"]),
                    notes=str(payload["notes"]),
                )
            except ValueError as exc:
                QMessageBox.critical(self, "Erro", str(exc))
                return
            self.refresh_all()
            self.audit_service.log(self.current_user.username, "complete", "appointment", int(appointment["appointment_id"]), "Atendimento concluido com pagamento")
            self.statusBar().showMessage(f"Atendimento concluido e recebido: {appointment['appointment_id']}", 4000)

        def confirm_selected_appointment(self) -> None:
            if not self._require_permission("manage_appointments", "Seu perfil nao pode confirmar agendamentos."):
                return
            appointment = self._selected_appointment()
            if not appointment:
                return
            try:
                updated = self.service.confirm_appointment(int(appointment["appointment_id"]))
            except ValueError as exc:
                QMessageBox.information(self, "Confirmacao", str(exc))
                return
            self.refresh_all()
            self.audit_service.log(
                self.current_user.username,
                "confirm",
                "appointment",
                updated.appointment_id or 0,
                f"Agendamento confirmado para {appointment['client_name']}",
            )
            self.statusBar().showMessage(f"Agendamento confirmado: {updated.appointment_id}", 4000)

        def open_whatsapp_confirmation(self) -> None:
            appointment = self._selected_appointment()
            if not appointment:
                return
            try:
                context = self.service.get_appointment_context(int(appointment["appointment_id"]))
                if str(context["status"]) in {"Cancelado", "Concluido", "Faltou"}:
                    raise ValueError("agendamento sem confirmacao disponivel")
                self.whatsapp_service.open_confirmation(context)
            except ValueError as exc:
                QMessageBox.information(self, "WhatsApp", str(exc))
                return
            self.audit_service.log(
                self.current_user.username,
                "open",
                "whatsapp",
                int(appointment["appointment_id"]),
                f"Confirmacao do agendamento {appointment['appointment_id']} para {appointment['client_name']}",
            )
            self.statusBar().showMessage(f"WhatsApp aberto para {appointment['client_name']}", 4000)

        def _selected_appointment(self) -> dict[str, object] | None:
            row = self.appointments_table.currentRow()
            if row < 0:
                QMessageBox.information(self, "Selecao", "Selecione um agendamento primeiro.")
                return None
            item = self.appointments_table.item(row, 0)
            if item is None:
                return None
            target_id = int(item.text())
            for appointment in self.service.list_appointments():
                if int(appointment["appointment_id"]) == target_id:
                    return appointment
            QMessageBox.information(self, "Selecao", "Agendamento nao encontrado.")
            return None

        def _selected_table_id(self, table: QTableWidget) -> int | None:
            row = table.currentRow()
            if row < 0:
                return None
            item = table.item(row, 0)
            if item is None:
                return None
            return int(item.text())

        def _selected_client_id(self) -> int | None:
            row = self.clients_table.currentRow()
            if row < 0:
                QMessageBox.information(self, "Selecao", "Selecione uma cliente primeiro.")
                return None
            item = self.clients_table.item(row, 0)
            if item is None:
                return None
            client_id = item.data(Qt.ItemDataRole.UserRole)
            if client_id is None:
                return None
            return int(client_id)

        def open_selected_client_profile(self) -> None:
            client_id = self._selected_client_id()
            if client_id is None:
                return
            self.open_client_profile(client_id)

        def open_client_profile(self, client_id: int) -> None:
            if not self._require_permission("view_clients", "Seu perfil nao pode visualizar fichas de clientes."):
                return
            finance_access = self.permission_service.has_permission(self.current_user, "view_finance") or self.permission_service.has_permission(self.current_user, "receive_payments")
            dialog = ClientProfileDialog(
                client_id=client_id,
                profile_service=self.client_profile_service,
                receipt_service=self.receipt_service,
                finance_access=finance_access,
                can_manage_clients=self.permission_service.has_permission(self.current_user, "manage_clients"),
                can_manage_appointments=self.permission_service.has_permission(self.current_user, "manage_appointments"),
                parent=self,
            )
            dialog.edit_client_button.clicked.connect(lambda: self._edit_client_from_profile(dialog))
            dialog.new_appointment_button.clicked.connect(lambda: self._create_client_appointment_from_profile(dialog))
            dialog.schedule_new_button.clicked.connect(lambda: self._create_client_appointment_from_profile(dialog))
            dialog.new_note_button.clicked.connect(lambda: self._add_note_from_profile(dialog))
            dialog.add_note_button.clicked.connect(lambda: self._add_note_from_profile(dialog))
            dialog.save_preferences_button.clicked.connect(lambda: self._save_preferences_from_profile(dialog))
            dialog.open_appointment_button.clicked.connect(lambda: self._open_profile_appointment_details(dialog))
            dialog.appointments_table.itemDoubleClicked.connect(lambda _item: self._open_profile_appointment_details(dialog))
            dialog.notes_table.itemDoubleClicked.connect(lambda _item: dialog.tabs.setCurrentWidget(dialog.notes_tab))
            self.audit_service.log(self.current_user.username, "open", "client_profile", client_id, f"Ficha da cliente {client_id}")
            dialog.exec()

        def _edit_client_from_profile(self, dialog: ClientProfileDialog) -> None:
            if self.edit_client_record(dialog.client_id):
                dialog.refresh()

        def _create_client_appointment_from_profile(self, dialog: ClientProfileDialog) -> None:
            if self.create_appointment_for_client(dialog.client_id):
                dialog.refresh()

        def _add_note_from_profile(self, dialog: ClientProfileDialog) -> None:
            if self.add_client_note(dialog.client_id):
                dialog.refresh()
                dialog.tabs.setCurrentWidget(dialog.notes_tab)

        def _save_preferences_from_profile(self, dialog: ClientProfileDialog) -> None:
            payload = {
                "preferred_service": dialog.preferred_service_input.text().strip(),
                "preferred_professional": dialog.preferred_professional_input.text().strip(),
                "service_notes": dialog.service_notes_input.toPlainText().strip(),
                "general_preferences": dialog.general_preferences_input.toPlainText().strip(),
            }
            if self.save_client_preferences(dialog.client_id, payload):
                dialog.refresh()

        def _open_profile_appointment_details(self, dialog: ClientProfileDialog) -> None:
            row = dialog.appointments_table.currentRow()
            if row < 0 or row >= len(dialog.appointment_rows):
                QMessageBox.information(self, "Selecao", "Selecione um atendimento primeiro.")
                return
            appointment = dialog.appointment_rows[row]
            details = AppointmentDetailsDialog(appointment, dialog.finance_access, dialog)
            if dialog.finance_access and appointment.get("receipt_payment_id") is not None:
                details.receipt_button.clicked.connect(lambda: self.open_receipt_for_payment_id(int(appointment["receipt_payment_id"])))
            details.exec()

        def open_receipt_for_payment_id(self, payment_id: int) -> None:
            try:
                pdf_path = self.receipt_service.receipt_path_for_payment(payment_id)
                if not pdf_path.exists():
                    pdf_path = self.receipt_service.generate_receipt(payment_id)
            except ValueError as exc:
                QMessageBox.critical(self, "Erro", str(exc))
                return
            try:
                os.startfile(str(pdf_path))
            except AttributeError:
                QMessageBox.information(self, "Recibo", f"Arquivo pronto em:\n{pdf_path}")
            except OSError as exc:
                QMessageBox.critical(self, "Erro", f"Nao foi possivel abrir o recibo.\n{exc}")

        def create_user_account(self) -> None:
            if not self._require_permission("manage_users", "Seu perfil nao pode cadastrar usuarios."):
                return
            dialog = UserDialog(self.service, self)
            if dialog.exec() != dialog.Accepted:
                return
            try:
                created = self.auth_service.create_user(**dialog.payload())
            except ValueError as exc:
                QMessageBox.critical(self, "Erro", str(exc))
                return
            self.audit_service.log(self.current_user.username, "create", "user", created.user_id or 0, created.username)
            self.refresh_users()
            self.statusBar().showMessage(f"Usuario criado: {created.username}", 4000)

        def refresh_all(self) -> None:
            self.refresh_dashboard()
            self.refresh_clients()
            self.refresh_services()
            self.refresh_professionals()
            self.refresh_professional_filter()
            self.refresh_appointments()
            self.refresh_finance()
            self.refresh_users()
            self.load_settings()

        def refresh_dashboard(self) -> None:
            self.dashboard_page.refresh(self.service.summary())

        def refresh_users(self) -> None:
            if not hasattr(self, "users_table"):
                return
            users = self.auth_service.list_users()
            self.users_table.setRowCount(len(users))
            for row_index, user in enumerate(users):
                values = [user.user_id, user.name, user.username, user.profile, "Ativo" if user.active else "Inativo"]
                for column_index, value in enumerate(values):
                    self.users_table.setItem(row_index, column_index, QTableWidgetItem(str(value)))
            entries = self.audit_service.list_entries()
            self.audit_log_table.setRowCount(len(entries))
            for row_index, entry in enumerate(entries):
                values = [
                    format_datetime_br(str(entry["created_at"])),
                    entry["username"],
                    display_audit_action(str(entry["action"])),
                    display_entity(str(entry["entity_type"])),
                    entry["description"],
                ]
                for column_index, value in enumerate(values):
                    self.audit_log_table.setItem(row_index, column_index, QTableWidgetItem(str(value)))

        def refresh_finance(self) -> None:
            overview = self.finance_service.financial_overview()
            self.fin_receitas_card.update_content(format_currency(float(overview["receitas_mes"])), "Entradas confirmadas")
            self.fin_despesas_card.update_content(format_currency(float(overview["despesas_mes"])), "Saidas confirmadas")
            self.fin_saldo_card.update_content(format_currency(float(overview["saldo"])), "Resultado do periodo")
            self.fin_receber_card.update_content(format_currency(float(overview["a_receber"])), "Contas em aberto")
            self.fin_pagar_card.update_content(format_currency(float(overview["a_pagar"])), "Despesas pendentes")
            self.fin_atrasados_card.update_content(format_currency(float(overview["valores_atrasados"])), "Titulos vencidos")
            alerts = list(overview["alertas"])
            self.finance_alerts.setRowCount(len(alerts))
            for row_index, alert in enumerate(alerts):
                self.finance_alerts.setItem(row_index, 0, QTableWidgetItem(str(alert)))
            movements = list(overview["ultimas_movimentacoes"])
            self.finance_movements.setRowCount(len(movements))
            for row_index, movement in enumerate(movements):
                values = [
                    format_date_br(str(movement["date"])),
                    movement["description"],
                    display_financial_kind(str(movement["kind"])),
                    format_currency(float(movement["amount"])),
                ]
                for column_index, value in enumerate(values):
                    self.finance_movements.setItem(row_index, column_index, QTableWidgetItem(str(value)))
            cash_entries = self.finance_service.cash_service.list_entries()
            self.cash_entries_table.setRowCount(len(cash_entries))
            for row_index, entry in enumerate(cash_entries):
                values = [
                    format_datetime_br(str(entry["created_at"])),
                    str(entry["entry_type"]),
                    entry["description"],
                    display_payment_method(str(entry["payment_method"])),
                    format_currency(float(entry["amount"])),
                ]
                for column_index, value in enumerate(values):
                    self.cash_entries_table.setItem(row_index, column_index, QTableWidgetItem(str(value)))
            receivables = self.finance_service.list_receivables()
            self.receivables_table.setRowCount(len(receivables))
            clients_by_id = {client.client_id: client.name for client in self.service.list_clients()}
            for row_index, receivable in enumerate(receivables):
                values = [
                    receivable.receivable_id,
                    clients_by_id.get(receivable.client_id, f"Cliente {receivable.client_id}"),
                    receivable.description,
                    receivable.installment_label,
                    format_date_br(receivable.due_date),
                    format_currency(float(receivable.remaining_amount)),
                    display_payment_method(receivable.payment_method),
                    receivable.status,
                ]
                for column_index, value in enumerate(values):
                    self.receivables_table.setItem(row_index, column_index, QTableWidgetItem(str(value)))
            payables = self.finance_service.list_payables()
            self.payables_table.setRowCount(len(payables))
            for row_index, payable in enumerate(payables):
                values = [
                    payable.payable_id,
                    payable.description,
                    payable.beneficiary,
                    payable.installment_label,
                    format_date_br(payable.due_date),
                    format_currency(float(payable.remaining_amount)),
                    payable.status,
                ]
                for column_index, value in enumerate(values):
                    self.payables_table.setItem(row_index, column_index, QTableWidgetItem(str(value)))
            charges = self.finance_service.billing_service.list_charges()
            self.billings_table.setRowCount(len(charges))
            for row_index, charge in enumerate(charges):
                values = [
                    charge["billing_id"],
                    charge["payer_name"],
                    charge["description"],
                    format_date_br(str(charge["due_date"])),
                    format_currency(float(charge["amount"])),
                    charge["status"],
                ]
                for column_index, value in enumerate(values):
                    self.billings_table.setItem(row_index, column_index, QTableWidgetItem(str(value)))
            commissions = self.finance_service.commission_service.list_commissions()
            professionals = {professional.professional_id: professional.name for professional in self.service.list_professionals()}
            self.commissions_table.setRowCount(len(commissions))
            for row_index, commission in enumerate(commissions):
                values = [
                    commission.commission_id,
                    professionals.get(commission.professional_id, f"Profissional {commission.professional_id}"),
                    commission.appointment_id,
                    format_currency(float(commission.base_amount)),
                    format_currency(float(commission.commission_amount)),
                    commission.status,
                ]
                for column_index, value in enumerate(values):
                    self.commissions_table.setItem(row_index, column_index, QTableWidgetItem(str(value)))
            payment_methods = self.finance_service.payment_method_report()
            self.payment_methods_table.setRowCount(len(payment_methods))
            for row_index, item in enumerate(payment_methods):
                values = [
                    display_payment_method(str(item["payment_method"] or "-")),
                    display_financial_kind(str(item["kind"])),
                    format_currency(float(item["total"])),
                    item["items"],
                ]
                for column_index, value in enumerate(values):
                    self.payment_methods_table.setItem(row_index, column_index, QTableWidgetItem(str(value)))
            audits = self.finance_service.audit_entries()
            self.audit_table.setRowCount(len(audits))
            for row_index, entry in enumerate(audits):
                values = [
                    format_datetime_br(str(entry["created_at"])),
                    display_audit_action(str(entry["operation_type"])),
                    display_entity(str(entry["entity_type"])),
                    entry["entity_id"],
                    entry["reason"],
                ]
                for column_index, value in enumerate(values):
                    self.audit_table.setItem(row_index, column_index, QTableWidgetItem(str(value)))
            receipts = self.receipt_service.list_receipts()
            self.receipts_table.setRowCount(len(receipts))
            for row_index, receipt in enumerate(receipts):
                values = [
                    receipt.payment_id,
                    receipt.receipt_number,
                    format_datetime_br(receipt.created_at),
                    receipt.client_name,
                    receipt.professional_name,
                    receipt.service_name,
                    display_payment_method(receipt.payment_method),
                    format_currency(float(receipt.paid_amount)),
                ]
                for column_index, value in enumerate(values):
                    self.receipts_table.setItem(row_index, column_index, QTableWidgetItem(str(value)))

        def refresh_professional_filter(self) -> None:
            selected = self.filter_professional.currentData() if hasattr(self, "filter_professional") else None
            self.filter_professional.blockSignals(True)
            self.filter_professional.clear()
            if self.current_user.profile == "Profissional" and self.current_user.professional_id is not None:
                professional = self.service.get_professional(self.current_user.professional_id)
                self.filter_professional.addItem(professional.name, professional.professional_id)
                self.filter_professional.setEnabled(False)
            else:
                self.filter_professional.setEnabled(True)
                self.filter_professional.addItem("Todos", None)
                for professional in self.service.list_professionals():
                    self.filter_professional.addItem(professional.name, professional.professional_id)
            if selected is not None:
                for index in range(self.filter_professional.count()):
                    if self.filter_professional.itemData(index) == selected:
                        self.filter_professional.setCurrentIndex(index)
                        break
            self.filter_professional.blockSignals(False)

        def refresh_appointments(self) -> None:
            appointment_date = self.filter_date.date().toString("yyyy-MM-dd")
            professional_id = self.current_user.professional_id if self.current_user.profile == "Profissional" else self.filter_professional.currentData()
            mode = self.view_mode.currentText()
            appointments = self._appointments_for_mode(mode, appointment_date, professional_id if professional_id else None)
            selected_status = self.filter_status.currentText()
            if selected_status != "Todos":
                appointments = [item for item in appointments if str(item["status"]) == selected_status]
            search_term = self.search_appointments.text().strip().lower()
            if search_term:
                appointments = [
                    item for item in appointments
                    if search_term in str(item["client_name"]).lower()
                    or search_term in str(item["service_name"]).lower()
                    or search_term in str(item.get("notes", "")).lower()
                ]
            self.appointments_table.setRowCount(len(appointments))
            self.appointments_empty.setVisible(not appointments)
            self.appointments_table.setVisible(bool(appointments))
            self.agenda_mode_badge.setText(f"Modo: {mode}")
            self.agenda_range_label.setText(self._describe_agenda_range(mode, appointment_date, len(appointments)))
            self.agenda_context_label.setText(self._describe_agenda_context(mode, len(appointments)))
            self.timeline_caption.setText(self._describe_timeline_caption(mode))
            self._refresh_schedule_grid(mode, appointment_date, appointments)
            self._refresh_agenda_cards(appointments)
            self._refresh_timeline(mode, appointments)
            for row_index, appointment in enumerate(appointments):
                values = [
                    appointment["appointment_id"],
                    appointment["client_name"],
                    appointment["professional_name"],
                    appointment["service_name"],
                    format_date_br(str(appointment["appointment_date"])),
                    format_time_br(str(appointment["appointment_time"])),
                    format_currency(float(appointment["price"])),
                    appointment["status"],
                ]
                for column_index, value in enumerate(values):
                    if column_index == 7:
                        self.appointments_table.setCellWidget(row_index, column_index, self._build_status_widget(str(appointment["status"])))
                    else:
                        item = QTableWidgetItem(str(value))
                        self.appointments_table.setItem(row_index, column_index, item)
            if appointments:
                self.appointments_table.selectRow(0)
                self._refresh_selected_appointment_details()
            else:
                self._refresh_selected_appointment_details(None)

        def set_agenda_today(self) -> None:
            self.filter_date.setDate(QDate.currentDate())
            self.refresh_appointments()

        def shift_agenda_date(self, days: int) -> None:
            self.filter_date.setDate(self.filter_date.date().addDays(days))
            self.refresh_appointments()

        def _describe_agenda_range(self, mode: str, appointment_date: str, count: int) -> str:
            selected = datetime.strptime(appointment_date, "%Y-%m-%d").date()
            if mode == "Semana":
                end_date = selected + timedelta(days=6)
                return (
                    f"Semana de {self._weekday_label(selected)} {format_date_br(selected.isoformat())} "
                    f"ate {self._weekday_label(end_date)} {format_date_br(end_date.isoformat())}  -  {count} horario(s)"
                )
            if mode == "Proximos":
                return f"Proximos agendamentos a partir de {self._weekday_label(date.today())} {format_date_br(date.today().isoformat())}  -  {count} horario(s)"
            label = "Hoje" if selected == date.today() else f"{self._weekday_label(selected)} {format_date_br(selected.isoformat())}"
            return f"{label}  -  {count} horario(s)"

        def _describe_agenda_context(self, mode: str, count: int) -> str:
            if mode == "Semana":
                return f"Visao semanal para equilibrar horarios, equipe e encaixes. {count} compromisso(s) no periodo."
            if mode == "Proximos":
                return f"Lista priorizada dos proximos atendimentos ativos. {count} compromisso(s) aguardando andamento."
            if mode == "Dia":
                return f"Leitura completa de um dia especifico da agenda. {count} compromisso(s) encontrados."
            return f"Panorama rapido do dia para recepcao e confirmacoes. {count} compromisso(s) visiveis."

        def _describe_timeline_caption(self, mode: str) -> str:
            if mode == "Semana":
                return "Blocos separados por dia para acompanhar distribuicao da semana com mais clareza."
            if mode == "Proximos":
                return "Linha do tempo dos proximos atendimentos ativos, destacando o que vem primeiro."
            if mode == "Dia":
                return "Sequencia visual do dia escolhido para facilitar encaixes, pausas e conclusoes."
            return "Blocos organizados por horario para acompanhar o fluxo do dia com mais conforto."

        def _weekday_label(self, value: date) -> str:
            labels = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sab", "Dom"]
            return labels[value.weekday()]

        def _refresh_schedule_grid(self, mode: str, appointment_date: str, appointments: list[dict[str, object]]) -> None:
            if mode not in {"Hoje", "Dia"}:
                self.schedule_grid.setVisible(False)
                return
            professionals = self.service.list_professionals(active_only=True)
            if self.current_user.profile == "Profissional" and self.current_user.professional_id is not None:
                professionals = [item for item in professionals if item.professional_id == self.current_user.professional_id]
            if not professionals:
                self.schedule_grid.setVisible(False)
                return
            slots = []
            current = datetime.strptime("08:00", "%H:%M")
            end = datetime.strptime("19:30", "%H:%M")
            while current <= end:
                slots.append(current.strftime("%H:%M"))
                current += timedelta(minutes=30)
            self.schedule_grid.setVisible(True)
            self.schedule_grid.setColumnCount(len(professionals))
            self.schedule_grid.setRowCount(len(slots))
            self.schedule_grid.setHorizontalHeaderLabels([item.name for item in professionals])
            self.schedule_grid.setVerticalHeaderLabels(slots)
            self.schedule_grid.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            self.schedule_grid.verticalHeader().setDefaultSectionSize(92)
            for row_index, slot in enumerate(slots):
                for column_index, professional in enumerate(professionals):
                    match = next(
                        (
                            item for item in appointments
                            if str(item["appointment_time"]) == slot and int(item["professional_id"]) == int(professional.professional_id)
                        ),
                        None,
                    )
                    if match is None:
                        self.schedule_grid.setItem(row_index, column_index, QTableWidgetItem(""))
                        continue
                    block = QFrame()
                    block.setObjectName("ScheduleAppointmentCard")
                    block_layout = QVBoxLayout(block)
                    block_layout.setContentsMargins(8, 8, 8, 8)
                    block_layout.setSpacing(4)
                    client_label = QLabel(str(match["client_name"]))
                    client_label.setObjectName("ScheduleAppointmentClient")
                    service_label = QLabel(str(match["service_name"]))
                    service_label.setObjectName("ScheduleAppointmentMeta")
                    service_label.setWordWrap(True)
                    meta_label = QLabel(format_currency(float(match["price"])))
                    meta_label.setObjectName("ScheduleAppointmentMeta")
                    status_label = StatusPill(str(match["status"]))
                    block_layout.addWidget(client_label)
                    block_layout.addWidget(service_label)
                    block_layout.addWidget(meta_label)
                    block_layout.addWidget(status_label, 0, Qt.AlignmentFlag.AlignLeft)
                    block.setToolTip(
                        f"{match['client_name']}\n{match['service_name']}\n{format_date_br(appointment_date)} {format_time_br(slot)}"
                    )
                    self.schedule_grid.setCellWidget(row_index, column_index, block)

        def refresh_clients(self) -> None:
            clients = self.service.list_clients()
            if self.current_user.profile == "Profissional" and self.current_user.professional_id is not None:
                visible_client_ids = {
                    int(item["client_id"])
                    for item in self.service.list_appointments(None, self.current_user.professional_id)
                }
                clients = [client for client in clients if client.client_id in visible_client_ids]
            search_term = self.clients_search.text().strip().lower()
            if search_term:
                clients = [
                    client for client in clients
                    if search_term in client.name.lower()
                    or search_term in client.phone.lower()
                    or search_term in client.whatsapp.lower()
                    or search_term in client.email.lower()
                ]
            self.clients_table.setRowCount(len(clients))
            self.clients_empty.setVisible(not clients)
            self.clients_table.setVisible(bool(clients))
            for row_index, client in enumerate(clients):
                values = [client.name, client.phone, client.whatsapp, client.email, format_date_br(client.birthday)]
                for column_index, value in enumerate(values):
                    item = QTableWidgetItem(str(value))
                    if column_index == 0:
                        item.setData(Qt.ItemDataRole.UserRole, int(client.client_id))
                    self.clients_table.setItem(row_index, column_index, item)

        def refresh_services(self) -> None:
            services = self.service.list_services()
            search_term = self.services_search.text().strip().lower()
            if search_term:
                services = [
                    service_item for service_item in services
                    if search_term in service_item.name.lower() or search_term in service_item.category.lower()
                ]
            self.services_table.setRowCount(len(services))
            self.services_empty.setVisible(not services)
            self.services_table.setVisible(bool(services))
            for row_index, service_item in enumerate(services):
                values = [
                    service_item.name,
                    service_item.category,
                    f"{service_item.duration_minutes} min",
                    format_currency(service_item.price),
                    "Sim" if service_item.active else "Nao",
                ]
                for column_index, value in enumerate(values):
                    self.services_table.setItem(row_index, column_index, QTableWidgetItem(str(value)))

        def refresh_professionals(self) -> None:
            professionals = self.service.list_professionals()
            search_term = self.professionals_search.text().strip().lower()
            if search_term:
                professionals = [
                    professional for professional in professionals
                    if search_term in professional.name.lower()
                    or search_term in professional.phone.lower()
                    or search_term in professional.specialty.lower()
                ]
            self.professionals_table.setRowCount(len(professionals))
            self.professionals_empty.setVisible(not professionals)
            self.professionals_table.setVisible(bool(professionals))
            for row_index, professional in enumerate(professionals):
                values = [professional.name, professional.phone, professional.specialty, "Sim" if professional.active else "Nao"]
                for column_index, value in enumerate(values):
                    self.professionals_table.setItem(row_index, column_index, QTableWidgetItem(str(value)))

        def _refresh_selected_appointment_details(self, appointment: dict[str, object] | None = None) -> None:
            if appointment is None:
                appointment = self._selected_appointment_from_table()
            if appointment is None:
                self.detail_status.apply_status("Sem selecao")
                self.detail_client.setText("Cliente\n-")
                self.detail_professional.setText("Profissional\n-")
                self.detail_service.setText("Servico\n-")
                self.detail_datetime.setText("Quando\n-")
                self.detail_duration.setText("Duracao\n-")
                self.detail_value.setText("Valor\n-")
                self.detail_notes.setText("Nenhuma observacao registrada para este atendimento.")
                self._update_appointment_action_buttons(None)
                return
            self.detail_status.apply_status(str(appointment["status"]))
            self.detail_client.setText(f"Cliente\n{appointment['client_name']}")
            self.detail_professional.setText(f"Profissional\n{appointment['professional_name']}")
            self.detail_service.setText(f"Servico\n{appointment['service_name']}")
            self.detail_datetime.setText(
                f"Quando\n{format_date_br(str(appointment['appointment_date']))} as {format_time_br(str(appointment['appointment_time']))}"
            )
            self.detail_duration.setText(f"Duracao\n{appointment['duration_minutes']} min")
            self.detail_value.setText(f"Valor\n{format_currency(float(appointment['price']))}")
            self.detail_notes.setText(str(appointment.get("notes") or "Nenhuma observacao registrada para este atendimento."))
            self._update_appointment_action_buttons(appointment)

        def _selected_appointment_from_table(self) -> dict[str, object] | None:
            row = self.appointments_table.currentRow()
            if row < 0:
                return None
            item = self.appointments_table.item(row, 0)
            if item is None:
                return None
            target_id = int(item.text())
            for appointment in self.service.list_appointments():
                if int(appointment["appointment_id"]) == target_id:
                    return appointment
            return None

        def _appointments_for_mode(self, mode: str, appointment_date: str, professional_id: int | None) -> list[dict[str, object]]:
            if mode == "Dia":
                return self.service.list_appointments(appointment_date, professional_id)
            all_items = self.service.list_appointments(None, professional_id)
            selected = datetime.strptime(appointment_date, "%Y-%m-%d").date()
            if mode == "Hoje":
                return [item for item in all_items if item["appointment_date"] == date.today().isoformat()]
            if mode == "Semana":
                end_date = selected + timedelta(days=6)
                return [
                    item for item in all_items
                    if selected <= datetime.strptime(str(item["appointment_date"]), "%Y-%m-%d").date() <= end_date
                ]
            if mode == "Proximos":
                now_date = date.today()
                now_time = datetime.now().strftime("%H:%M")
                return [
                    item for item in all_items
                    if (
                        datetime.strptime(str(item["appointment_date"]), "%Y-%m-%d").date() > now_date
                        or (
                            datetime.strptime(str(item["appointment_date"]), "%Y-%m-%d").date() == now_date
                            and str(item["appointment_time"]) >= now_time
                        )
                    )
                    and item["status"] not in {"Cancelado", "Concluido", "Faltou"}
                ]
            return self.service.list_appointments(appointment_date, professional_id)

        def _refresh_agenda_cards(self, appointments: list[dict[str, object]]) -> None:
            confirmed = len([item for item in appointments if item["status"] == "Confirmado"])
            in_progress = len([item for item in appointments if item["status"] == "Em atendimento"])
            pending = len([item for item in appointments if item["status"] in {"Agendado", "Confirmado"}])
            self.agenda_total_card.update_content(str(len(appointments)), "Itens visiveis")
            self.agenda_confirmed_card.update_content(str(confirmed), "Com chegada prevista")
            self.agenda_progress_card.update_content(str(in_progress), "Atendimentos em curso")
            self.agenda_pending_card.update_content(str(pending), "Agendado ou confirmado")

        def _build_status_widget(self, status: str) -> QWidget:
            host = QFrame()
            host.setObjectName("AgendaStatusHost")
            layout = QHBoxLayout(host)
            layout.setContentsMargins(6, 4, 6, 4)
            pill = StatusPill(status)
            layout.addWidget(pill)
            layout.addStretch(1)
            return host

        def _update_appointment_action_buttons(self, appointment: dict[str, object] | None) -> None:
            allow_confirm = False
            allow_whatsapp = False
            allow_complete = False
            if appointment is not None:
                status = str(appointment.get("status") or "")
                allow_confirm = status == "Agendado" and self.permission_service.has_permission(self.current_user, "manage_appointments")
                if status not in {"Cancelado", "Concluido", "Faltou"}:
                    try:
                        context = self.service.get_appointment_context(int(appointment["appointment_id"]))
                        self.whatsapp_service.get_contact_phone(context)
                        allow_whatsapp = True
                    except ValueError:
                        allow_whatsapp = False
                allow_complete = (
                    status not in {"Cancelado", "Concluido", "Faltou"}
                    and self.permission_service.has_permission(self.current_user, "complete_appointments")
                )
            for button in [self.confirm_button, self.detail_confirm_button]:
                button.setEnabled(allow_confirm)
            for button in [self.whatsapp_button, self.detail_whatsapp_button]:
                button.setEnabled(allow_whatsapp)
            for button in [self.complete_button, self.detail_complete_button]:
                button.setEnabled(allow_complete)

        def _clear_layout(self, layout: QVBoxLayout) -> None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                child_layout = item.layout()
                if widget is not None:
                    widget.deleteLater()
                elif child_layout is not None:
                    self._clear_layout(child_layout)

        def _refresh_timeline(self, mode: str, appointments: list[dict[str, object]]) -> None:
            self._clear_layout(self.timeline_layout)
            if not appointments:
                empty = QLabel("Nenhum bloco de atendimento para montar neste periodo.")
                empty.setObjectName("EmptyState")
                self.timeline_layout.addWidget(empty)
                self.timeline_layout.addStretch(1)
                return
            grouped: dict[str, list[dict[str, object]]] = {}
            for appointment in appointments:
                grouped.setdefault(str(appointment["appointment_date"]), []).append(appointment)
            for appointment_date, items in grouped.items():
                current_date = datetime.strptime(appointment_date, "%Y-%m-%d").date()
                section = QLabel(
                    f"{self._weekday_label(current_date)}  {format_date_br(appointment_date)}"
                    + ("  - Hoje" if appointment_date == date.today().isoformat() else "")
                    + f"  -  {len(items)} agendamento(s)"
                )
                section.setObjectName("AgendaDateSection")
                self.timeline_layout.addWidget(section)
                for appointment in sorted(items, key=lambda current: str(current["appointment_time"])):
                    self.timeline_layout.addWidget(self._build_timeline_card(mode, appointment))
            self.timeline_layout.addStretch(1)

        def _build_timeline_card(self, mode: str, appointment: dict[str, object]) -> QWidget:
            card = QFrame()
            card.setObjectName("AgendaTimelineCard")
            layout = QHBoxLayout(card)
            layout.setContentsMargins(16, 14, 16, 14)
            layout.setSpacing(12)

            accent = QFrame()
            accent.setObjectName("AgendaTimeAccent")
            accent.setFixedWidth(86)
            accent_layout = QVBoxLayout(accent)
            accent_layout.setContentsMargins(14, 12, 14, 12)
            accent_layout.setSpacing(4)
            time_block = QVBoxLayout()
            time_label = QLabel(format_time_br(str(appointment["appointment_time"])))
            time_label.setObjectName("TitleLabel")
            time_label.setStyleSheet("font-size: 15pt;")
            duration_label = QLabel(f"{appointment['duration_minutes']} min")
            duration_label.setObjectName("PageSubtitle")
            time_block.addWidget(time_label)
            time_block.addWidget(duration_label)
            time_block.addStretch(1)
            accent_layout.addLayout(time_block)
            layout.addWidget(accent)

            details = QVBoxLayout()
            details.setSpacing(6)
            name_label = QLabel(f"{appointment['client_name']} - {appointment['service_name']}")
            name_label.setObjectName("AgendaTimelineTitle")
            name_label.setWordWrap(True)
            meta_label = QLabel(
                f"Profissional: {appointment['professional_name']} - Valor: {format_currency(float(appointment['price']))}"
            )
            meta_label.setObjectName("AgendaTimelineMeta")
            meta_label.setWordWrap(True)
            details.addWidget(name_label)
            details.addWidget(meta_label)
            if appointment.get("notes"):
                notes_label = QLabel(str(appointment["notes"]))
                notes_label.setObjectName("AgendaTimelineMeta")
                notes_label.setWordWrap(True)
                details.addWidget(notes_label)
            if mode != "Dia":
                date_label = QLabel(f"Data: {format_date_br(str(appointment['appointment_date']))}")
                date_label.setObjectName("AgendaTimelineMeta")
                details.addWidget(date_label)
            layout.addLayout(details, 1)

            status_host = QFrame()
            status_host.setObjectName("AgendaStatusHost")
            status_host.setMinimumWidth(132)
            status_host.setMaximumWidth(148)
            status_layout = QVBoxLayout(status_host)
            status_layout.setContentsMargins(10, 10, 10, 10)
            status_layout.setSpacing(6)
            status_layout.addWidget(StatusPill(str(appointment["status"])))
            status_layout.addStretch(1)
            layout.addWidget(status_host, 0, Qt.AlignmentFlag.AlignTop)
            return card


def run_desktop_app(paths: AppPaths | None = None) -> None:
    paths = paths or AppPaths()
    database = Database(paths.database_path)
    service = SalonService(database)
    auth_service = AuthService(database)
    audit_service = AuditService(database)
    if (
        not QT_AVAILABLE
        or os.environ.get("MULTIAGENTAI_FORCE_CONSOLE") == "1"
        or (not os.environ.get("MULTIAGENTAI_GUI") and not os.isatty(0))
    ):
        summary = service.summary()
        print("Projeto inicializado com sucesso.")
        print(f"Agendamentos de hoje: {summary['today_appointments']}")
        print(f"Clientes cadastrados: {summary['clients_total']}")
        print(f"Profissionais ativos: {summary['active_professionals']}")
        print(f"Servicos cadastrados: {summary['services_total']}")
        print("Login padrao inicial: admin / admin123")
        return
    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(build_stylesheet())
    login = LoginDialog(auth_service)
    if login.exec() != login.Accepted or login.user is None:
        return
    audit_service.log(login.user.username, "login", "session", 0, "Inicio de sessao")
    window = SalonWindow(paths, login.user, auth_service, audit_service)
    window.show()
    app.exec()
