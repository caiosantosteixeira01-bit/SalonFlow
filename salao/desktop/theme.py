from __future__ import annotations


APP_NAME = "SalonFlow"


def build_stylesheet() -> str:
    return """
    QWidget {
        background: #F8F3EE;
        color: #2D1830;
        font-family: 'Segoe UI Variable Text';
        font-size: 11pt;
    }
    QMainWindow {
        background: #F8F3EE;
    }
    QLabel#TitleLabel {
        font-size: 25pt;
        font-weight: 700;
        color: #2D1830;
    }
    QLabel#MetricValue {
        font-size: 23pt;
        font-weight: 700;
        color: #2D1830;
    }
    QLabel#MetricCaption {
        color: #8A6570;
        font-size: 10pt;
    }
    QLabel#PageTitle {
        font-size: 24pt;
        font-weight: 700;
        color: #2D1830;
        padding-top: 2px;
    }
    QLabel#Subtitle {
        color: #8A6570;
        font-size: 10.8pt;
        padding-bottom: 8px;
    }
    QLabel#AgendaHeroTitle {
        font-size: 22pt;
        font-weight: 700;
        color: #2D1830;
    }
    QLabel#AgendaHeroText {
        color: #8A6570;
        font-size: 10.6pt;
    }
    QLabel#AgendaHeroChip {
        background: #FBF3F1;
        color: #8A6570;
        border: 1px solid #EAD8D4;
        border-radius: 12px;
        padding: 4px 10px;
        font-size: 9.2pt;
        font-weight: 600;
    }
    QLabel#AgendaSectionCaption {
        color: #9A7680;
        font-size: 9.8pt;
        padding-left: 2px;
    }
    QLabel#AgendaRangeLabel {
        color: #6B4655;
        font-size: 10.1pt;
        font-weight: 600;
        padding-left: 2px;
    }
    QLabel#AgendaModeBadge {
        background: #F6E8ED;
        color: #8A4E63;
        border: 1px solid #ECD6DD;
        border-radius: 14px;
        padding: 6px 12px;
        font-size: 9.7pt;
        font-weight: 700;
    }
    QLabel#AgendaDateSection {
        color: #5D364F;
        font-size: 10.5pt;
        font-weight: 700;
        background: #F7ECE8;
        border: 1px solid #EADAD4;
        border-radius: 14px;
        padding: 8px 12px;
    }
    QLabel#AgendaContextText {
        color: #8A6570;
        font-size: 9.9pt;
        padding-left: 2px;
    }
    QLabel#ProfileMetaTitle {
        color: #8A6570;
        font-size: 9.8pt;
        font-weight: 600;
    }
    QLabel#ProfileMetaValue {
        color: #2D1830;
        font-size: 11pt;
        font-weight: 700;
    }
    QLabel#ProfileHighlightValue {
        color: #3A2236;
        font-size: 11.2pt;
        font-weight: 700;
    }
    QLabel#ProfileSnapshot {
        color: #8A6570;
        font-size: 10pt;
        line-height: 1.45;
    }
    QLabel#AgendaTimelineTitle {
        color: #3A2236;
        font-size: 11.2pt;
        font-weight: 700;
    }
    QLabel#AgendaTimelineMeta {
        color: #8A6570;
        font-size: 9.9pt;
    }
    QLabel#AgendaDetailLabel {
        color: #8A6570;
        font-size: 9.8pt;
        font-weight: 600;
    }
    QLabel#AgendaDetailValue {
        color: #2D1830;
        font-size: 10.8pt;
        font-weight: 700;
    }
    QLabel#AgendaDetailHint {
        color: #8A6570;
        font-size: 10pt;
        line-height: 1.35;
    }
    QLabel#AgendaDetailNote {
        color: #6F4C58;
        font-size: 10.15pt;
        line-height: 1.45;
        background: #FCF7F3;
        border: 1px solid #EEDFDB;
        border-radius: 16px;
        padding: 12px 14px;
    }
    QLabel#SectionTitle {
        color: #5D364F;
        font-size: 11.4pt;
        font-weight: 700;
        padding: 4px 0 4px 2px;
    }
    QLabel#DialogTitle {
        font-size: 18pt;
        font-weight: 700;
        color: #2D1830;
    }
    QLabel#DialogSubtitle {
        color: #8A6570;
        font-size: 10.4pt;
        line-height: 1.35;
    }
    QLabel#EmptyState {
        background: transparent;
        color: #8A6570;
        border: none;
        padding: 0px;
    }
    QLabel#StatusPill {
        padding: 5px 12px;
        border-radius: 13px;
        font-size: 9.4pt;
        font-weight: 700;
    }
    QFrame#EmptyStateCard {
        background: #FFFDFC;
        border: 1px dashed #E8D8D5;
        border-radius: 22px;
    }
    QLabel#EmptyStateTitle {
        color: #2D1830;
        font-size: 13pt;
        font-weight: 700;
    }
    QLabel#EmptyStateDescription {
        color: #8A6570;
        font-size: 10.5pt;
    }
    QFrame#Card {
        background: #FFFDFC;
        border: 1px solid #E8D8D5;
        border-radius: 20px;
    }
    QFrame#Sidebar {
        background: #40233F;
        border: none;
        border-radius: 28px;
    }
    QLabel#SidebarTitle {
        color: #FFF8F6;
        font-size: 19pt;
        font-weight: 700;
    }
    QLabel#SidebarBadgeTitle {
        color: #FFF8F6;
        font-size: 11pt;
        font-weight: 700;
    }
    QLabel#SidebarSubtitle {
        color: #E8CDD7;
        font-size: 10.2pt;
        line-height: 1.35;
    }
    QLabel#SidebarMeta {
        color: #F0D7E0;
        font-size: 9.8pt;
        font-weight: 600;
    }
    QLabel#PageSubtitle {
        color: #8A6570;
        font-size: 10.2pt;
    }
    QFrame#SidebarBadge {
        background: #4B2B47;
        border: 1px solid rgba(255, 240, 246, 0.14);
        border-radius: 20px;
    }
    QPushButton#SidebarButton {
        text-align: left;
        padding: 14px 16px;
        border-radius: 16px;
        background: transparent;
        color: #F7EAF0;
        border: 1px solid transparent;
        font-weight: 600;
    }
    QPushButton#SidebarButton:hover {
        background: #53304F;
        border: 1px solid rgba(255, 244, 247, 0.08);
    }
    QPushButton#SidebarButton:checked {
        background: #D47F91;
        color: #ffffff;
        border: 1px solid #D47F91;
    }
    QPushButton {
        background: #D47F91;
        color: white;
        border: none;
        border-radius: 14px;
        padding: 10px 15px;
        font-weight: 600;
    }
    QPushButton:hover {
        background: #C96F84;
    }
    QPushButton:pressed {
        background: #B95E76;
    }
    QPushButton:disabled {
        background: #D5B9C0;
        color: #FFF7FA;
    }
    QPushButton[variant="secondary"] {
        background: #F4E5E8;
        color: #7B4D5F;
        border: 1px solid #E7CCD3;
    }
    QPushButton[variant="secondary"]:hover {
        background: #EFDADF;
    }
    QPushButton[variant="secondary"]:pressed {
        background: #E4CAD2;
    }
    QPushButton[variant="ghost"] {
        background: transparent;
        color: #8A4E63;
        border: 1px solid #E6D2D7;
    }
    QPushButton[variant="ghost"]:hover {
        background: #F8EEF1;
    }
    QPushButton[variant="ghost"]:pressed {
        background: #F1E1E6;
    }
    QPushButton[variant="nav"] {
        background: #FFF7F6;
        color: #7B4D5F;
        border: 1px solid #E7CCD3;
        border-radius: 12px;
        min-width: 42px;
        padding: 8px 12px;
    }
    QPushButton[variant="nav"]:hover {
        background: #F8ECEF;
    }
    QPushButton[variant="nav"]:pressed {
        background: #EFDADF;
    }
    QPushButton[role="danger"] {
        background: #FFF4F5;
        color: #9B4B5C;
        border: 1px solid #E7C5CD;
    }
    QPushButton[role="danger"]:hover {
        background: #FCECEF;
    }
    QPushButton[role="danger"]:pressed {
        background: #F6DDE3;
    }
    QDialogButtonBox QPushButton {
        min-width: 110px;
    }
    QFrame#Panel {
        background: #FFFDFC;
        border: 1px solid #E8D8D5;
        border-radius: 20px;
    }
    QFrame#HeroPanel {
        background: #FFFDFC;
        border: 1px solid #E8D8D5;
        border-radius: 24px;
    }
    QFrame#AgendaToolbarPanel {
        background: #FFFDFC;
        border: 1px solid #E8D8D5;
        border-radius: 22px;
    }
    QWidget#AgendaFilterRow, QWidget#AgendaActionRow {
        background: transparent;
    }
    QFrame#AgendaCanvasPanel {
        background: #FFFDFC;
        border: 1px solid #E8D8D5;
        border-radius: 22px;
    }
    QFrame#AgendaDetailsPanel {
        background: #FFFDFC;
        border: 1px solid #E8D8D5;
        border-radius: 22px;
    }
    QFrame#ProfileHeroPanel {
        background: #FFFDFC;
        border: 1px solid #E8D8D5;
        border-radius: 24px;
    }
    QFrame#ProfileHighlightPanel {
        background: #FFFDFC;
        border: 1px solid #E8D8D5;
        border-radius: 20px;
    }
    QFrame#AgendaDetailsPanel QLabel#AgendaDetailValue {
        background: #FCF7F3;
        border: 1px solid #EEDFDB;
        border-radius: 16px;
        padding: 10px 12px;
    }
    QLabel#HeroBadge {
        background: #F6E8ED;
        color: #8A4E63;
        border: 1px solid #ECD6DD;
        border-radius: 14px;
        padding: 6px 12px;
        font-size: 10pt;
        font-weight: 700;
    }
    QLabel#HeroImage {
        background: #F3E4E9;
        border: 1px solid #E8D8D5;
        border-radius: 22px;
        padding: 0px;
    }
    QFrame#TimelineCard {
        background: #FFFDFC;
        border: 1px solid #E8D8D5;
        border-radius: 18px;
    }
    QFrame#AgendaTimelineCard {
        background: #FFFDFC;
        border: 1px solid #E8D8D5;
        border-radius: 20px;
    }
    QFrame#AgendaStatusHost {
        background: #FAF1EE;
        border: 1px solid #ECDCD7;
        border-radius: 16px;
    }
    QFrame#AgendaTimeAccent {
        background: #F7E8EC;
        border: 1px solid #E9D5DC;
        border-radius: 18px;
    }
    QFrame#ScheduleAppointmentCard {
        background: #FFF8F7;
        border: 1px solid #E9D5DC;
        border-radius: 14px;
    }
    QFrame#DialogShell {
        background: #FFFDFC;
        border: 1px solid #E8D8D5;
        border-radius: 24px;
    }
    QFrame#DialogSection {
        background: #FFFDFC;
        border: 1px solid #EEE1DD;
        border-radius: 18px;
    }
    QDialog QScrollArea {
        border: none;
        background: transparent;
    }
    QDialog QFormLayout QLabel {
        min-width: 104px;
        color: #6E4A58;
        font-weight: 600;
    }
    QDialog QDialogButtonBox {
        border-top: 1px solid #F0E3DE;
        padding-top: 12px;
        margin-top: 4px;
    }
    QLabel {
        background: transparent;
    }
    QLabel#ScheduleAppointmentClient {
        color: #3A2236;
        font-size: 10.1pt;
        font-weight: 700;
    }
    QLabel#ScheduleAppointmentMeta {
        color: #8A6570;
        font-size: 9.4pt;
    }
    QLineEdit[error="true"], QComboBox[error="true"], QTextEdit[error="true"] {
        border: 1px solid #C45F6C;
    }
    QLineEdit, QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox, QTextEdit, QTableWidget {
        background: #FFFDFC;
        border: 1px solid #E8D8D5;
        border-radius: 14px;
        padding: 8px 10px;
        min-height: 22px;
        color: #2D1830;
    }
    QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QTextEdit:focus {
        border: 1px solid #D47F91;
    }
    QLineEdit::placeholder, QTextEdit::placeholder {
        color: #B18D96;
    }
    QComboBox::drop-down, QDateEdit::drop-down {
        border: none;
        width: 24px;
    }
    QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox {
        padding-right: 12px;
    }
    QCheckBox {
        spacing: 8px;
        color: #5A3D4A;
    }
    QCheckBox::indicator {
        width: 18px;
        height: 18px;
        border-radius: 6px;
        border: 1px solid #D7C4C8;
        background: #FFFDFC;
    }
    QCheckBox::indicator:checked {
        background: #D47F91;
        border: 1px solid #D47F91;
    }
    QTableWidget {
        gridline-color: #F1E8E4;
        selection-background-color: #F6DFE5;
        selection-color: #2D1830;
        alternate-background-color: #FFFCFA;
        padding: 0px;
        outline: 0;
    }
    QTableWidget::item:selected {
        background: #F6DFE5;
        color: #2D1830;
    }
    QHeaderView::section {
        background: #F5E7E4;
        color: #5D364F;
        border: none;
        padding: 12px 10px;
        font-weight: 700;
    }
    QTableCornerButton::section {
        background: #F5E7E4;
        border: none;
    }
    QTableView::item {
        padding: 10px 8px;
        border-bottom: 1px solid #F3EAE7;
    }
    QTableView::item:hover {
        background: #FAEEF1;
    }
    QTableWidget#AgendaTable, QTableWidget#ScheduleGrid {
        border-radius: 18px;
        border: 1px solid #EDE0DD;
        background: #FFFEFD;
    }
    QTableWidget#AgendaTable::item {
        padding: 12px 10px;
    }
    QTableWidget#ScheduleGrid {
        background: #FCF7F4;
    }
    QTableWidget#ScheduleGrid::item {
        padding: 4px;
        border-bottom: 1px solid #F1E6E2;
    }
    QTabWidget::pane {
        border: 1px solid #E8D8D5;
        border-radius: 18px;
        top: -1px;
        background: #FFFDFC;
        padding: 8px;
    }
    QTabBar::tab {
        background: #F4E6E3;
        color: #7B5765;
        border: 1px solid #E8D8D5;
        border-bottom: none;
        padding: 10px 16px;
        min-width: 120px;
        border-top-left-radius: 12px;
        border-top-right-radius: 12px;
        margin-right: 6px;
        font-weight: 600;
    }
    QTabBar::tab:selected {
        background: #FFFDFC;
        color: #5D364F;
    }
    QTabBar::tab:hover:!selected {
        background: #F8ECE9;
    }
    QScrollArea {
        border: none;
        background: transparent;
    }
    QScrollBar:vertical {
        background: transparent;
        width: 12px;
        margin: 6px 0 6px 0;
    }
    QScrollBar::handle:vertical {
        background: #D8C3C9;
        border-radius: 6px;
        min-height: 28px;
    }
    QScrollBar::handle:vertical:hover {
        background: #CFAAB5;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
        background: none;
        border: none;
    }
    QStatusBar {
        background: #F2E7E2;
        color: #7C5A65;
        border-top: 1px solid #E6D7D3;
    }
    """
