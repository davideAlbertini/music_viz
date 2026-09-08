"""Dark theme for the control panel."""

BG = "#16181d"
PANEL = "#1e2128"
PANEL_ALT = "#252932"
BORDER = "#31363f"
TEXT = "#d7dae0"
TEXT_DIM = "#8b919c"
ACCENT = "#4bc2ff"
ACCENT_DIM = "#2b6f91"
WARN = "#ffb454"
POSITIVE = "#7bd88f"
NEGATIVE = "#ff6b81"

STYLESHEET = f"""
QWidget {{
    background: {BG};
    color: {TEXT};
    font-family: "Segoe UI", sans-serif;
    font-size: 12px;
}}

QScrollArea, QScrollArea > QWidget > QWidget {{ background: {BG}; border: none; }}

QLabel {{ background: transparent; }}
QLabel[role="title"] {{ font-size: 14px; font-weight: 600; color: {TEXT}; }}
QLabel[role="subtle"] {{ color: {TEXT_DIM}; }}
QLabel[role="pending"] {{ color: {WARN}; font-weight: 600; }}
QLabel[role="mono"] {{ font-family: "Cascadia Mono", Consolas, monospace; color: {TEXT_DIM}; }}
QLabel[role="channel"] {{ font-family: "Cascadia Mono", Consolas, monospace; }}

QFrame[role="card"] {{
    background: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 8px;
}}
QFrame[role="row"] {{
    background: {PANEL_ALT};
    border: 1px solid {BORDER};
    border-radius: 6px;
}}
QFrame[role="sep"] {{ background: {BORDER}; max-height: 1px; border: none; }}

QTabWidget::pane {{ border: 1px solid {BORDER}; border-radius: 8px; top: -1px; }}
QTabBar::tab {{
    background: transparent;
    color: {TEXT_DIM};
    padding: 8px 18px;
    border-bottom: 2px solid transparent;
}}
QTabBar::tab:selected {{ color: {TEXT}; border-bottom: 2px solid {ACCENT}; }}
QTabBar::tab:hover {{ color: {TEXT}; }}

QPushButton {{
    background: {PANEL_ALT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 6px 14px;
    color: {TEXT};
}}
QPushButton:hover {{ border-color: {ACCENT_DIM}; }}
QPushButton:pressed {{ background: {BORDER}; }}
QPushButton:disabled {{ color: {TEXT_DIM}; border-color: {BORDER}; }}
QPushButton[role="primary"] {{
    background: {ACCENT_DIM}; border-color: {ACCENT}; color: #ffffff; font-weight: 600;
}}
QPushButton[role="primary"]:hover {{ background: {ACCENT}; }}
QPushButton[role="icon"] {{
    padding: 4px; min-width: 26px; max-width: 26px; min-height: 24px;
    font-weight: 700; color: {TEXT_DIM};
}}
QPushButton[role="icon"]:hover {{ color: {NEGATIVE}; border-color: {NEGATIVE}; }}
QPushButton[role="transport"] {{
    min-width: 40px; min-height: 30px; font-size: 15px; font-weight: 700;
}}

QComboBox, QDoubleSpinBox, QSpinBox, QLineEdit {{
    background: {BG};
    border: 1px solid {BORDER};
    border-radius: 5px;
    padding: 4px 6px;
    selection-background-color: {ACCENT_DIM};
}}
QComboBox:focus, QDoubleSpinBox:focus, QSpinBox:focus, QLineEdit:focus {{
    border-color: {ACCENT_DIM};
}}
QComboBox::drop-down {{ border: none; width: 16px; }}
QComboBox QAbstractItemView {{
    background: {PANEL_ALT}; border: 1px solid {BORDER};
    selection-background-color: {ACCENT_DIM}; outline: none;
}}
QComboBox:disabled, QDoubleSpinBox:disabled, QSpinBox:disabled, QLineEdit:disabled {{
    color: {TEXT_DIM}; background: {PANEL}; border-color: {PANEL_ALT};
}}

QCheckBox {{ spacing: 6px; }}
QCheckBox::indicator {{
    width: 14px; height: 14px; border-radius: 3px;
    border: 1px solid {BORDER}; background: {BG};
}}
QCheckBox::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT}; }}

QSlider::groove:horizontal {{
    height: 4px; background: {BORDER}; border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {TEXT}; width: 12px; height: 12px;
    margin: -5px 0; border-radius: 6px;
}}
QSlider::handle:horizontal:hover {{ background: {ACCENT}; }}
QSlider::sub-page:horizontal {{ background: {ACCENT_DIM}; border-radius: 2px; }}

QScrollBar:vertical {{ background: transparent; width: 10px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 5px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {ACCENT_DIM}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

QSplitter::handle {{ background: {BORDER}; }}
QSplitter::handle:horizontal {{ width: 2px; }}
QSplitter::handle:vertical {{ height: 2px; }}

QToolTip {{
    background: {PANEL_ALT}; color: {TEXT};
    border: 1px solid {BORDER}; padding: 5px;
}}
"""
