from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from .core.config import AppPaths
from .finance import FinanceService
from .models import ReceiptRecord
from .utils import display_payment_method, format_currency, format_date_br, format_datetime_br, format_time_br


@dataclass(frozen=True)
class SalonReceiptProfile:
    salon_name: str
    document: str
    phone: str
    whatsapp: str
    email: str
    address: str
    logo_path: str = ""


class PdfReceiptGenerator:
    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)

    def build_receipt_path(self, receipt_number: str) -> Path:
        safe_name = receipt_number.lower().replace("/", "-")
        return self.output_dir / f"{safe_name}.pdf"

    def generate(self, receipt: ReceiptRecord, profile: SalonReceiptProfile, target_path: Path | None = None) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = Path(target_path) if target_path else self.build_receipt_path(receipt.receipt_number)
        pdf_path.parent.mkdir(parents=True, exist_ok=True)

        page = canvas.Canvas(str(pdf_path), pagesize=A4, pageCompression=0)
        width, height = A4

        plum_dark = colors.HexColor("#40233F")
        plum_soft = colors.HexColor("#53304F")
        rose = colors.HexColor("#D47F91")
        rose_soft = colors.HexColor("#F4E6E8")
        surface = colors.HexColor("#FFFDFC")
        border = colors.HexColor("#E8D8D5")
        text_main = colors.HexColor("#2D1830")
        text_soft = colors.HexColor("#8A6570")
        paper = colors.HexColor("#F8F3EE")

        page.setFillColor(paper)
        page.rect(0, 0, width, height, stroke=0, fill=1)

        margin_x = 18 * mm
        card_width = width - (margin_x * 2)

        page.setFillColor(surface)
        page.setStrokeColor(border)
        page.roundRect(margin_x, 24 * mm, card_width, height - (42 * mm), 12, stroke=1, fill=1)

        header_y = height - 36 * mm
        page.setFillColor(plum_dark)
        page.roundRect(margin_x + 8, header_y - 8, card_width - 16, 34 * mm, 12, stroke=0, fill=1)

        logo_path = Path(profile.logo_path).expanduser() if profile.logo_path else None
        logo_drawn = False
        if logo_path and logo_path.exists():
            try:
                page.drawImage(ImageReader(str(logo_path)), margin_x + 16, header_y + 2, width=22 * mm, height=22 * mm, preserveAspectRatio=True, mask="auto")
                logo_drawn = True
            except Exception:
                logo_drawn = False

        text_x = margin_x + (45 * mm if logo_drawn else 18)
        page.setFillColor(colors.white)
        page.setFont("Helvetica-Bold", 22)
        page.drawString(text_x, header_y + 18, profile.salon_name or "SalonFlow")
        page.setFont("Helvetica", 10.5)
        page.drawString(text_x, header_y + 9, "Recibo profissional de atendimento")

        page.setFillColor(rose_soft)
        page.roundRect(margin_x + card_width - 60 * mm, header_y + 3, 42 * mm, 20 * mm, 10, stroke=0, fill=1)
        page.setFillColor(rose)
        page.setFont("Helvetica-Bold", 9.5)
        page.drawString(margin_x + card_width - 54 * mm, header_y + 16, "RECIBO")
        page.setFillColor(text_main)
        page.setFont("Helvetica-Bold", 12)
        page.drawString(margin_x + card_width - 54 * mm, header_y + 8, receipt.receipt_number)

        info_y = header_y - 24
        contact_line = " | ".join(
            piece for piece in [
                f"CPF/CNPJ: {profile.document}" if profile.document else "",
                f"Telefone: {profile.phone}" if profile.phone else "",
                f"WhatsApp: {profile.whatsapp}" if profile.whatsapp else "",
            ] if piece
        )
        second_line = " | ".join(piece for piece in [profile.email, profile.address] if piece)
        page.setFillColor(text_soft)
        page.setFont("Helvetica", 9.5)
        if contact_line:
            page.drawString(margin_x + 16, info_y, contact_line)
            info_y -= 12
        if second_line:
            page.drawString(margin_x + 16, info_y, second_line)

        content_left = margin_x + 16
        content_width = card_width - 32
        content_top = header_y - 28 * mm

        page.setFillColor(text_main)
        page.setFont("Helvetica-Bold", 11)
        page.drawString(content_left, content_top, "Dados do recibo")

        column_gap = 6 * mm
        field_width = (content_width - column_gap) / 2
        field_height = 16 * mm
        row_gap = 5 * mm

        row_one_y = content_top - 8 * mm - field_height
        row_two_y = row_one_y - row_gap - field_height
        row_three_y = row_two_y - row_gap - field_height

        self._draw_field(page, content_left, row_one_y, field_width, field_height, receipt.client_label, receipt.client_name, text_main, text_soft, border)
        self._draw_field(page, content_left + field_width + column_gap, row_one_y, field_width, field_height, receipt.professional_label, receipt.professional_name, text_main, text_soft, border)
        self._draw_field(page, content_left, row_two_y, field_width, field_height, receipt.service_label, receipt.service_name, text_main, text_soft, border)
        self._draw_field(page, content_left + field_width + column_gap, row_two_y, field_width, field_height, "Forma de pagamento", display_payment_method(receipt.payment_method), text_main, text_soft, border)
        self._draw_field(page, content_left, row_three_y, field_width, field_height, "Data do pagamento", format_date_br(receipt.payment_date), text_main, text_soft, border)
        self._draw_field(
            page,
            content_left + field_width + column_gap,
            row_three_y,
            field_width,
            field_height,
            "Horario do atendimento" if receipt.appointment_id is not None else "Horario",
            format_time_br(receipt.appointment_time) if receipt.appointment_id is not None else "Nao se aplica",
            text_main,
            text_soft,
            border,
        )

        generated_y = row_three_y - 9 * mm
        page.setFillColor(text_soft)
        page.setFont("Helvetica", 9.5)
        page.drawString(content_left, generated_y, f"Gerado em {format_datetime_br(receipt.created_at)}")

        values_box_y = generated_y - 28 * mm
        box_height = 34 * mm
        page.setFillColor(colors.white)
        page.setStrokeColor(border)
        page.roundRect(content_left, values_box_y, content_width, box_height, 10, stroke=1, fill=1)

        columns = [
            ("Valor original", format_currency(float(receipt.original_amount))),
            ("Desconto", format_currency(float(receipt.discount_amount))),
            ("Valor pago", format_currency(float(receipt.paid_amount))),
        ]
        column_width = content_width / 3
        for index, (label, value) in enumerate(columns):
            column_x = content_left + (index * column_width)
            if index:
                page.setStrokeColor(border)
                page.line(column_x, values_box_y + 10, column_x, values_box_y + box_height - 10)
            page.setFillColor(text_soft)
            page.setFont("Helvetica", 9.5)
            page.drawString(column_x + 12, values_box_y + box_height - 18, label)
            page.setFillColor(rose if label == "Valor pago" else text_main)
            page.setFont("Helvetica-Bold", 16 if label == "Valor pago" else 14)
            page.drawString(column_x + 12, values_box_y + 18, value)

        notes_y = values_box_y - 52 * mm
        page.setFillColor(surface)
        page.setStrokeColor(border)
        page.roundRect(content_left, notes_y, content_width, 40 * mm, 10, stroke=1, fill=1)
        page.setFillColor(text_main)
        page.setFont("Helvetica-Bold", 11)
        page.drawString(content_left + 12, notes_y + 40 * mm - 18, "Observacoes")
        page.setFillColor(text_soft)
        page.setFont("Helvetica", 10)
        notes = receipt.notes or "Pagamento registrado no SalonFlow."
        text_object = page.beginText(content_left + 12, notes_y + 40 * mm - 34)
        text_object.setLeading(14)
        for line in self._wrap_text(notes, 88):
            text_object.textLine(line)
        page.drawText(text_object)

        footer_y = 34 * mm
        page.setStrokeColor(border)
        page.line(content_left, footer_y + 12, content_left + 72 * mm, footer_y + 12)
        page.setFillColor(text_soft)
        page.setFont("Helvetica", 9)
        page.drawString(content_left, footer_y, "Assinatura / confirmacao do recebimento")
        page.drawRightString(margin_x + card_width - 16, footer_y, "Gerado pelo SalonFlow")

        page.showPage()
        page.save()
        return pdf_path

    def _draw_field(self, page, x: float, y: float, width: float, height: float, label: str, value: str, text_main, text_soft, border) -> None:
        page.setFillColor(colors.white)
        page.setStrokeColor(border)
        page.roundRect(x, y, width, height, 8, stroke=1, fill=1)
        page.setFillColor(text_soft)
        page.setFont("Helvetica", 8.5)
        page.drawString(x + 10, y + height - 14, label)
        page.setFillColor(text_main)
        page.setFont("Helvetica-Bold", 11)
        page.drawString(x + 10, y + 10, value or "-")

    def _wrap_text(self, text: str, max_chars: int) -> list[str]:
        words = text.split()
        if not words:
            return [""]
        lines: list[str] = []
        current = words[0]
        for word in words[1:]:
            candidate = f"{current} {word}"
            if len(candidate) <= max_chars:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
        return lines


class ReceiptService:
    def __init__(self, finance_service: FinanceService, paths: AppPaths):
        self.finance_service = finance_service
        self.paths = paths
        self.generator = PdfReceiptGenerator(paths.receipts_dir)

    def receipt_path_for_payment(self, payment_id: int) -> Path:
        record = self.finance_service.get_receipt_record(payment_id)
        return self.generator.build_receipt_path(record.receipt_number)

    def list_receipts(self) -> list[ReceiptRecord]:
        result: list[ReceiptRecord] = []
        for record in self.finance_service.list_receipt_records():
            result.append(
                ReceiptRecord(
                    **{**record.__dict__, "pdf_path": self.generator.build_receipt_path(record.receipt_number)}
                )
            )
        return result

    def generate_receipt(self, payment_id: int, target_path: Path | None = None) -> Path:
        record = self.finance_service.get_receipt_record(payment_id)
        profile = self._build_profile()
        pdf_path = self.generator.generate(record, profile, target_path=target_path)
        return pdf_path

    def _build_profile(self) -> SalonReceiptProfile:
        values = self.finance_service.get_receipt_settings()
        logo_path = values["salon_logo_path"].strip()
        if logo_path:
            candidate = self.paths.resolve_user_file(logo_path)
            logo_path = str(candidate)
        return SalonReceiptProfile(
            salon_name=values["salon_name"] or "SalonFlow",
            document=values["salon_document"],
            phone=values["salon_phone"],
            whatsapp=values["salon_whatsapp"],
            email=values["salon_email"],
            address=values["salon_address"],
            logo_path=logo_path,
        )
