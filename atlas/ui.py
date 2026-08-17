"""Polished PyQt6 interface for Atlas."""

from __future__ import annotations

import html
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any
from .updater import UpdateCheckerWorker

from PyQt6.QtCore import QEasingCurve, QEvent, QPoint, QPropertyAnimation, Qt, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QAction, QColor, QDesktopServices, QFont, QIcon, QPixmap, QTextCursor
from PyQt6.QtWidgets import (
    QAbstractButton,
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QFileDialog,
)

from .gemini_service import Citation, GeminiService, ResearchResult
from .logging_utils import setup_logging
from .memory_store import MemoryStore
from .project_writer import WrittenProject, WrittenRepair, apply_repair, write_project
from .settings import DEFAULT_MODELS, SettingsStore
from .workers import TaskRunner

logger = setup_logging()


STYLE = """
* { font-family: 'Segoe UI', 'Inter', sans-serif; }
QMainWindow, QWidget#root { background: #0b1020; color: #ecf1ff; }
QFrame#sidebar { background: #10172a; border-right: 1px solid #26304a; }
QFrame#topbar { background: rgba(16, 23, 42, 0.94); border-bottom: 1px solid #26304a; }
QLabel#brand { color: #f4f7ff; font-size: 24px; font-weight: 800; letter-spacing: 0.5px; }
QLabel#eyebrow { color: #8ea2cb; font-size: 11px; font-weight: 700; letter-spacing: 1.5px; }
QLabel#pageTitle { color: #f6f8ff; font-size: 28px; font-weight: 750; }
QLabel#subtitle { color: #9dadcb; font-size: 13px; }
QLabel#muted { color: #9dadcb; font-size: 12px; }
QLabel#status { color: #93e7c0; font-size: 12px; font-weight: 600; }
QLabel#count { color: #8ea2cb; font-size: 12px; font-weight: 600; }
QToolButton#nav { color: #aebbd6; background: transparent; border: 0; border-radius: 11px; padding: 11px 14px; text-align: left; font-size: 14px; font-weight: 600; }
QToolButton#nav:hover { color: #eef4ff; background: #19243d; }
QToolButton#nav:checked { color: white; background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #3430a7, stop:1 #5346cb); }
QFrame#card { background: #141d33; border: 1px solid #263451; border-radius: 16px; }
QFrame#card:hover { border-color: #3c4e77; }
QFrame#innerCard { background: #10182b; border: 1px solid #263451; border-radius: 12px; }
QFrame#sourceCard { background: #111a2f; border: 1px solid #263451; border-radius: 11px; }
QLineEdit, QPlainTextEdit, QTextBrowser, QComboBox { background: #0d1426; color: #eaf0ff; border: 1px solid #2e3d5d; border-radius: 10px; padding: 10px 12px; selection-background-color: #5a49d6; font-size: 13px; }
QLineEdit:focus, QPlainTextEdit:focus, QTextBrowser:focus, QComboBox:focus { border: 1px solid #7569f2; background: #0f1730; }
QPlainTextEdit { padding: 12px; }
QTextBrowser { padding: 15px; line-height: 1.55; }
QTextBrowser a { color: #a99fff; }
QComboBox { min-height: 18px; }
QComboBox::drop-down { border: 0; width: 28px; }
QComboBox QAbstractItemView { background: #111a2f; color: #eff3ff; selection-background-color: #3f36aa; border: 1px solid #33425f; }
QPushButton { border: 0; border-radius: 10px; padding: 10px 15px; font-size: 13px; font-weight: 700; color: #eaf0ff; background: #293956; }
QPushButton:hover { background: #354a70; }
QPushButton:pressed { background: #202e48; }
QPushButton:disabled { background: #202940; color: #71809b; }
QPushButton#primary { color: white; background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #584bd5, stop:1 #7c54e5); }
QPushButton#primary:hover { background: #6a5ae8; }
QPushButton#ghost { background: transparent; border: 1px solid #344562; color: #b9c8e7; }
QPushButton#ghost:hover { background: #1a2740; color: #ffffff; }
QCheckBox { color: #b8c5df; spacing: 8px; font-size: 12px; }
QCheckBox::indicator { width: 16px; height: 16px; border-radius: 5px; border: 1px solid #465979; background: #0e1527; }
QCheckBox::indicator:checked { background: #6b5ce7; border-color: #8a7dff; }
QScrollArea { background: transparent; border: 0; }
QScrollBar:vertical { border: 0; background: transparent; width: 9px; margin: 4px; }
QScrollBar::handle:vertical { background: #31415f; min-height: 30px; border-radius: 4px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
QProgressBar { border: 0; background: #0c1324; border-radius: 5px; height: 7px; text-align: center; color: transparent; }
QProgressBar::chunk { background: #7565ee; border-radius: 5px; }
"""


def _shadow(widget: QWidget, blur: int = 22, alpha: int = 70) -> None:
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setOffset(0, 7)
    effect.setColor(QColor(0, 0, 0, alpha))
    widget.setGraphicsEffect(effect)


def _label(text: str, object_name: str = "", word_wrap: bool = False) -> QLabel:
    result = QLabel(text)
    if object_name:
        result.setObjectName(object_name)
    result.setWordWrap(word_wrap)
    return result


def _button(text: str, *, primary: bool = False, ghost: bool = False) -> QPushButton:
    button = QPushButton(text)
    if primary:
        button.setObjectName("primary")
    elif ghost:
        button.setObjectName("ghost")
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    return button


class Card(QFrame):
    def __init__(self, parent: QWidget | None = None, *, inner: bool = False) -> None:
        super().__init__(parent)
        self.setObjectName("innerCard" if inner else "card")
        _shadow(self, 20 if not inner else 12, 52 if not inner else 30)


class Toast(QFrame):
    """A small self-dismissing in-app status message."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            "QFrame { background: #202c48; border: 1px solid #536689; border-radius: 12px; }"
            "QLabel { color: #f3f6ff; padding: 10px 14px; font-weight: 600; }"
        )
        self.label = QLabel(self)
        self.label.setWordWrap(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.addWidget(self.label)
        self.hide()

    def show_message(self, message: str, *, error: bool = False) -> None:
        color = "#6d3345" if error else "#203d42"
        border = "#bd6075" if error else "#4d968c"
        self.setStyleSheet(
            f"QFrame {{ background: {color}; border: 1px solid {border}; border-radius: 12px; }}"
            "QLabel { color: #f8fbff; padding: 10px 14px; font-weight: 600; }"
        )
        self.label.setText(message)
        self.adjustSize()
        self.move(max(16, self.parentWidget().width() - self.width() - 28), 76)
        self.show()
        self.raise_()
        QTimer.singleShot(5500 if error else 3200, self.hide)


class LoadingSplash(QWidget):
    """Modern startup splash while Atlas restores local memory, recent session context, and checks for updates."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.SplashScreen | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(760, 430)
        self._progress = 0
        self._elapsed = 0
        self._duration_ms = 10000
        self._timer = QTimer(self)
        self._timer.setInterval(35)
        self._timer.timeout.connect(self._tick)

        # Update check states
        self._update_found = False
        self._latest_version = ""
        self._release_url = ""
        self._update_checked = False

        container = QWidget(self)
        container.setObjectName("splashCard")
        container.setStyleSheet(
            "QWidget#splashCard { background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #0b1223, stop:0.5 #0f1c31, stop:1 #101a2f); border: 1px solid #324871; border-radius: 24px; }"
            "QLabel { color: #eaf2ff; }"
        )
        container.setGeometry(0, 0, self.width(), self.height())

        layout = QVBoxLayout(container)
        layout.setContentsMargins(34, 28, 34, 28)
        layout.setSpacing(18)

        self.brand = _label("ATLAS", "brand")
        self.brand.setStyleSheet("font-size: 32px; letter-spacing: 3px; color: #edf4ff; font-weight: 800;")
        layout.addWidget(self.brand)

        self.subtitle = _label("Gemini Research Studio", "eyebrow")
        self.subtitle.setStyleSheet("font-size: 12px; letter-spacing: 2px; color: #9bb2dc; margin-bottom: 4px;")
        layout.addWidget(self.subtitle)

        self.state = _label("Loading local memory & checking updates...", "status")
        self.state.setStyleSheet("font-size: 15px; color: #dfe9ff; font-weight: 700;")
        layout.addWidget(self.state)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setStyleSheet(
            "QProgressBar { border: 0; background: rgba(255,255,255,0.08); border-radius: 4px; }"
            "QProgressBar::chunk { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #6e68ff, stop:1 #8b6cf6); border-radius: 4px; }"
        )
        layout.addWidget(self.progress_bar)

        self.detail = _label("Restoring recent Atlas activity and querying release channels…", "muted", True)
        self.detail.setStyleSheet("color: #b7c8ea; font-size: 12px; line-height: 1.5;")
        layout.addWidget(self.detail)

        layout.addStretch(1)

        footer = QHBoxLayout()
        footer.addStretch(1)
        self.time = _label("00:00", "eyebrow")
        self.time.setStyleSheet("font-size: 11px; color: #b2c5e7;")
        footer.addWidget(self.time)
        layout.addLayout(footer)

        # Trigger background update check on initialization
        self._init_update_checker()

    def _init_update_checker(self) -> None:
        self._update_worker = UpdateCheckerWorker()
        self._update_worker.update_checked.connect(self._on_update_checked)
        self._update_worker.start()

    def _on_update_checked(self, has_update: bool, version: str, url: str) -> None:
        self._update_found = has_update
        self._latest_version = version
        self._release_url = url
        self._update_checked = True

    def _tick(self) -> None:
        self._elapsed += 35
        self._progress = min(100, int((self._elapsed / self._duration_ms) * 100))
        self.progress_bar.setValue(self._progress)
        seconds = self._elapsed // 1000
        self.time.setText(f"00:{seconds:02d}")

        if self._progress < 32:
            self.state.setText("Loading local memory...")
            if not self._update_checked:
                self.detail.setText("Restoring recent Atlas activity and checking for updates…")
            else:
                self.detail.setText("Local memory restored successfully.")
        elif self._progress < 64:
            self.state.setText("Preparing AI workspace...")
            if self._update_checked and self._update_found:
                self.detail.setText(f"New update v{self._latest_version} available online! Synchronising settings…")
            else:
                self.detail.setText("Synchronising settings, models, and last session state…")
        elif self._progress < 88:
            self.state.setText("Finalising launch...")
            self.detail.setText("Opening Atlas and readying the Gemini workspace…")
        else:
            self.state.setText("Ready")
            if self._update_checked and self._update_found:
                self.detail.setText(f"Atlas v{self._latest_version} is available. Launching workspace...")
            else:
                self.detail.setText("Atlas memory and recent context loaded successfully.")

        if self._elapsed >= self._duration_ms:
            self._timer.stop()
            self.close()

    def start(self) -> None:
        self.show()
        self.raise_()
        self._timer.start()

    def finish(self, window: QWidget | None = None) -> None:
        self._timer.stop()
        self.close()
        if window is not None:
            window.activateWindow()
            window.raise_()

class SourceCard(QFrame):
    opened = pyqtSignal(str)

    def __init__(self, citation: Citation, index: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sourceCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(3)
        layout.addWidget(_label(f"{citation.kind.upper()}  ·  SOURCE {index}", "eyebrow"))
        title = _label(citation.title, "", True)
        title.setStyleSheet("font-weight: 700; color: #eaf0ff; font-size: 13px;")
        layout.addWidget(title)
        url = _label(citation.url, "muted", True)
        url.setMaximumHeight(34)
        layout.addWidget(url)
        self._url = citation.url

    def mouseReleaseEvent(self, event: QEvent) -> None:  # type: ignore[override]
        if event.type() == QEvent.Type.MouseButtonRelease:
            self.opened.emit(self._url)
        super().mouseReleaseEvent(event)


class AtlasWindow(QMainWindow):
    """The complete application window and UI orchestration layer."""

    def __init__(self) -> None:
        super().__init__()
        logger.info("Initializing AtlasWindow")
        self.store = SettingsStore()
        self.settings = self.store.load()
        self.memory = MemoryStore()
        self.runner = TaskRunner(self)
        self._active_tasks = 0
        self._selected_file: Path | None = None
        self._written_project: WrittenProject | None = None
        self._repair_screenshot: Path | None = None
        self._written_repair: WrittenRepair | None = None
        self._nav_buttons: list[QToolButton] = []
        self._chat_messages = self.memory.recent_chat()
        self.token_usage_total = 0
        self.token_usage_used = 0
        self._typing_timer: QTimer | None = None
        self._typing_message = ""
        self._typing_index = 0

        self.setWindowTitle("Atlas — Gemini Research Studio")
        self.setWindowIcon(QIcon("atlas/assets/logo.png"))
        self.setMinimumSize(1160, 720)
        self.resize(1460, 920)
        self.setStyleSheet(STYLE)
        self._build_window()
        self._load_saved_settings()
        self._render_chat_transcript()
        self._remember("app_started", {"application": "Atlas Gemini Research Studio", "version": "1.1.0"})

    def _build_window(self) -> None:
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._build_sidebar())

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        content_layout.addWidget(self._build_topbar())
        self.pages = QStackedWidget()
        self.pages.addWidget(self._build_research_page())
        self.pages.addWidget(self._build_analysis_page())
        self.pages.addWidget(self._build_builder_page())
        self.pages.addWidget(self._build_chat_page())
        self.pages.addWidget(self._build_settings_page())
        content_layout.addWidget(self.pages, 1)
        outer.addWidget(content, 1)
        self.toast = Toast(root)

    def _build_sidebar(self) -> QFrame:
        side = QFrame()
        side.setObjectName("sidebar")
        side.setFixedWidth(238)
        layout = QVBoxLayout(side)
        layout.setContentsMargins(17, 24, 17, 20)
        layout.setSpacing(8)
        layout.addWidget(_label("ATLAS", "brand"))
        layout.addWidget(_label("GEMINI RESEARCH STUDIO", "eyebrow"))
        layout.addSpacing(31)

        nav_items = [
            ("◈  Research", "Search the web with grounded Gemini answers"),
            ("◉  Analyse a file", "Understand media, documents, or source code"),
            ("✦  Build a project", "Generate a complete local code project"),
            ("◌  Chat", "Chat with any Gemini model using local Atlas memory"),
            ("⚙  Settings", "Key, model, and Downloads location"),
        ]
        for index, (label, tooltip) in enumerate(nav_items):
            button = QToolButton()
            button.setObjectName("nav")
            button.setText(label)
            button.setToolTip(tooltip)
            button.setCheckable(True)
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            button.clicked.connect(lambda checked, page=index: self._change_page(page))
            layout.addWidget(button)
            self._nav_buttons.append(button)
        self._nav_buttons[0].setChecked(True)
        layout.addItem(QSpacerItem(1, 1, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        key_hint = Card(inner=True)
        hint_layout = QVBoxLayout(key_hint)
        hint_layout.setContentsMargins(12, 11, 12, 11)
        hint_layout.addWidget(_label("GEMINI CONNECTION", "eyebrow"))
        self.side_connection = _label("Key needed", "status")
        hint_layout.addWidget(self.side_connection)
        settings_link = _button("Open settings", ghost=True)
        settings_link.clicked.connect(lambda: self._change_page(4))
        hint_layout.addWidget(settings_link)
        layout.addWidget(key_hint)
        return side

    def _build_topbar(self) -> QFrame:
        top = QFrame()
        top.setObjectName("topbar")
        top.setFixedHeight(66)
        layout = QHBoxLayout(top)
        layout.setContentsMargins(28, 11, 28, 11)
        layout.setSpacing(12)
        self.activity_status = _label("Ready", "status")
        layout.addWidget(self.activity_status)
        layout.addStretch(1)
        layout.addWidget(_label("GROUNDED BY GEMINI", "eyebrow"))
        return top

    @staticmethod
    def _page_shell(title: str, subtitle: str) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 27, 30, 30)
        layout.setSpacing(17)
        layout.addWidget(_label(title, "pageTitle"))
        layout.addWidget(_label(subtitle, "subtitle"))
        return page, layout

    def _build_research_page(self) -> QWidget:
        page, layout = self._page_shell(
            "Research with live grounding",
            "Ask a question, add public URLs if useful, and inspect the actual sources Gemini cites.",
        )
        composer = Card()
        comp = QVBoxLayout(composer)
        comp.setContentsMargins(19, 18, 19, 18)
        comp.setSpacing(12)
        header = QHBoxLayout()
        header.addWidget(_label("WHAT DO YOU WANT TO UNDERSTAND?", "eyebrow"))
        header.addStretch(1)
        self.research_count = _label("0 / 8,000", "count")
        header.addWidget(self.research_count)
        comp.addLayout(header)
        self.research_query = QPlainTextEdit()
        self.research_query.setPlaceholderText(
            "Example: Compare the latest approaches to on-device AI and give me the strongest primary sources."
        )
        self.research_query.setFixedHeight(105)
        self.research_query.textChanged.connect(
            lambda: self.research_count.setText(f"{len(self.research_query.toPlainText()):,} / 8,000")
        )
        comp.addWidget(self.research_query)
        url_caption = _label("OPTIONAL: PUBLIC WEB PAGES TO EXAMINE (ONE URL PER LINE)", "eyebrow")
        comp.addWidget(url_caption)
        self.source_urls = QPlainTextEdit()
        self.source_urls.setPlaceholderText("https://example.com/article\nhttps://www.youtube.com/watch?v=...")
        self.source_urls.setFixedHeight(55)
        comp.addWidget(self.source_urls)
        controls = QHBoxLayout()
        self.google_search_check = QCheckBox("Search the web")
        self.google_search_check.setChecked(True)
        self.url_context_check = QCheckBox("Read supplied URLs")
        self.url_context_check.setChecked(True)
        controls.addWidget(self.google_search_check)
        controls.addWidget(self.url_context_check)
        controls.addStretch(1)
        self.research_button = _button("✦  Research now", primary=True)
        self.research_button.clicked.connect(self._research)
        controls.addWidget(self.research_button)
        comp.addLayout(controls)
        layout.addWidget(composer)

        result_row = QHBoxLayout()
        result_row.setSpacing(17)
        answer_card = Card()
        answer_layout = QVBoxLayout(answer_card)
        answer_layout.setContentsMargins(18, 17, 18, 18)
        answer_header = QHBoxLayout()
        answer_header.addWidget(_label("RESEARCH BRIEF", "eyebrow"))
        answer_header.addStretch(1)
        copy = _button("Copy", ghost=True)
        copy.clicked.connect(lambda: self._copy_text(self.research_answer.toPlainText()))
        answer_header.addWidget(copy)
        answer_layout.addLayout(answer_header)
        self.research_answer = self._result_browser("Your grounded answer will appear here.")
        answer_layout.addWidget(self.research_answer, 1)
        result_row.addWidget(answer_card, 3)

        source_card = Card()
        source_layout = QVBoxLayout(source_card)
        source_layout.setContentsMargins(14, 17, 14, 14)
        source_header = QHBoxLayout()
        source_header.addWidget(_label("SOURCES", "eyebrow"))
        self.research_source_count = _label("0 cited", "count")
        source_header.addStretch(1)
        source_header.addWidget(self.research_source_count)
        source_layout.addLayout(source_header)
        self.research_sources, self.research_sources_layout = self._source_list("Run research to see Gemini's citations.")
        source_layout.addWidget(self.research_sources, 1)
        result_row.addWidget(source_card, 2)
        layout.addLayout(result_row, 1)
        return page

    def _build_analysis_page(self) -> QWidget:
        page, layout = self._page_shell(
            "Analyse a file",
            "Gemini can reason over your local image, video, audio, PDF, Word, PowerPoint, text, and code files.",
        )
        row = QHBoxLayout()
        row.setSpacing(17)
        controls_card = Card()
        controls = QVBoxLayout(controls_card)
        controls.setContentsMargins(18, 18, 18, 18)
        controls.setSpacing(13)
        controls.addWidget(_label("LOCAL FILE", "eyebrow"))
        self.file_name = _label("No file selected", "subtitle", True)
        self.file_name.setMinimumHeight(42)
        controls.addWidget(self.file_name)
        self.file_preview = QLabel("◇")
        self.file_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.file_preview.setStyleSheet(
            "background: #0c1325; color: #7e72f3; border: 1px dashed #3b4d73; border-radius: 12px; font-size: 42px;"
        )
        self.file_preview.setFixedHeight(150)
        controls.addWidget(self.file_preview)
        browse = _button("Choose file", ghost=True)
        browse.clicked.connect(self._choose_file)
        controls.addWidget(browse)
        controls.addSpacing(7)
        controls.addWidget(_label("WHAT SHOULD GEMINI DO WITH IT?", "eyebrow"))
        self.analysis_prompt = QPlainTextEdit()
        self.analysis_prompt.setPlaceholderText("Summarise it, extract actions, inspect the code, explain a chart, or answer a question…")
        self.analysis_prompt.setFixedHeight(110)
        controls.addWidget(self.analysis_prompt)
        self.analyse_button = _button("◉  Analyse file", primary=True)
        self.analyse_button.clicked.connect(self._analyse_file)
        controls.addWidget(self.analyse_button)
        row.addWidget(controls_card, 2)

        result_card = Card()
        result = QVBoxLayout(result_card)
        result.setContentsMargins(18, 18, 18, 18)
        result_header = QHBoxLayout()
        result_header.addWidget(_label("ANALYSIS", "eyebrow"))
        result_header.addStretch(1)
        copy = _button("Copy", ghost=True)
        copy.clicked.connect(lambda: self._copy_text(self.analysis_answer.toPlainText()))
        result_header.addWidget(copy)
        result.addLayout(result_header)
        self.analysis_answer = self._result_browser("Choose a file and ask what you need to know.")
        result.addWidget(self.analysis_answer, 1)
        row.addWidget(result_card, 3)
        layout.addLayout(row, 1)
        return page

    def _build_builder_page(self) -> QWidget:
        page, layout = self._page_shell(
            "Build a project",
            "Create a complete project, or repair an existing one from its error output, source code, and an optional screenshot.",
        )
        mode_bar = QHBoxLayout()
        self.new_project_mode_button = _button("✦  New project", primary=True)
        self.new_project_mode_button.clicked.connect(lambda: self._set_builder_mode(0))
        mode_bar.addWidget(self.new_project_mode_button)
        self.repair_mode_button = _button("⌁  Repair a project", ghost=True)
        self.repair_mode_button.clicked.connect(lambda: self._set_builder_mode(1))
        mode_bar.addWidget(self.repair_mode_button)
        mode_bar.addStretch(1)
        mode_bar.addWidget(_label("YOUR CODE STAYS LOCAL EXCEPT FOR THIS REPAIR REQUEST", "eyebrow"))
        layout.addLayout(mode_bar)

        self.builder_stack = QStackedWidget()
        self.builder_stack.addWidget(self._build_new_project_workspace())
        self.builder_stack.addWidget(self._build_repair_workspace())
        layout.addWidget(self.builder_stack, 1)
        return page

    def _build_new_project_workspace(self) -> QWidget:
        workspace = QWidget()
        workspace_layout = QVBoxLayout(workspace)
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.setSpacing(0)
        row = QHBoxLayout()
        row.setSpacing(17)
        form_card = Card()
        form = QVBoxLayout(form_card)
        form.setContentsMargins(18, 18, 18, 18)
        form.setSpacing(11)
        form.addWidget(_label("PROJECT DETAILS", "eyebrow"))
        form.addWidget(_label("Project name", "muted"))
        self.project_name = QLineEdit("my-gemini-project")
        form.addWidget(self.project_name)
        form.addWidget(_label("Language", "muted"))
        self.language_combo = QComboBox()
        self.language_combo.addItems(["Python", "TypeScript", "JavaScript", "Go", "Rust", "Java", "C#"])
        form.addWidget(self.language_combo)
        form.addWidget(_label("Framework or platform", "muted"))
        self.framework_combo = QComboBox()
        self.framework_combo.setEditable(True)
        self.framework_combo.addItems(["PyQt6 desktop application", "FastAPI", "Flask", "React", "Next.js", "Standard library"])
        form.addWidget(self.framework_combo)
        form.addWidget(_label("SAVE NEW PROJECTS IN", "eyebrow"))
        destination = QHBoxLayout()
        self.project_destination = QLineEdit()
        destination.addWidget(self.project_destination, 1)
        choose_destination = _button("Choose", ghost=True)
        choose_destination.clicked.connect(self._choose_destination)
        destination.addWidget(choose_destination)
        form.addLayout(destination)
        form.addStretch(1)
        self.build_button = _button("✦  Generate & save project", primary=True)
        self.build_button.clicked.connect(self._build_project)
        form.addWidget(self.build_button)
        row.addWidget(form_card, 2)

        output_card = Card()
        output = QVBoxLayout(output_card)
        output.setContentsMargins(18, 18, 18, 18)
        output.setSpacing(11)
        output.addWidget(_label("BUILD BRIEF", "eyebrow"))
        self.project_description = QPlainTextEdit()
        self.project_description.setPlaceholderText(
            "Example: Create a polished task dashboard with local SQLite storage, keyboard shortcuts, dark mode, tests, and a clear README."
        )
        self.project_description.setFixedHeight(155)
        output.addWidget(self.project_description)
        output.addWidget(_label("RESULT", "eyebrow"))
        self.build_result = self._result_browser(
            "Atlas will validate Gemini's structured response and create a new, non-overwriting folder here."
        )
        output.addWidget(self.build_result, 1)
        output_actions = QHBoxLayout()
        self.open_project_button = _button("Open project folder", ghost=True)
        self.open_project_button.setEnabled(False)
        self.open_project_button.clicked.connect(self._open_project_folder)
        output_actions.addWidget(self.open_project_button)
        output_actions.addStretch(1)
        output.addLayout(output_actions)
        row.addWidget(output_card, 3)
        workspace_layout.addLayout(row, 1)
        return workspace

    def _build_repair_workspace(self) -> QWidget:
        workspace = QWidget()
        workspace_layout = QVBoxLayout(workspace)
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.setSpacing(0)
        row = QHBoxLayout()
        row.setSpacing(17)

        input_card = Card()
        inputs = QVBoxLayout(input_card)
        inputs.setContentsMargins(18, 18, 18, 18)
        inputs.setSpacing(11)
        inputs.addWidget(_label("PROJECT TO REPAIR", "eyebrow"))
        folder_row = QHBoxLayout()
        self.repair_project_directory = QLineEdit()
        self.repair_project_directory.setPlaceholderText("Choose the existing project folder")
        folder_row.addWidget(self.repair_project_directory, 1)
        choose_project = _button("Choose", ghost=True)
        choose_project.clicked.connect(self._choose_repair_project)
        folder_row.addWidget(choose_project)
        inputs.addLayout(folder_row)
        self.repair_context_status = _label("Atlas will read source and configuration files, not build folders or dependencies.", "muted", True)
        inputs.addWidget(self.repair_context_status)
        inputs.addSpacing(4)
        inputs.addWidget(_label("PASTE THE ERROR OR DESCRIBE WHAT WENT WRONG", "eyebrow"))
        self.repair_error = QPlainTextEdit()
        self.repair_error.setPlaceholderText(
            "Paste the full traceback, console output, failing behaviour, or steps that reproduce the problem."
        )
        self.repair_error.setFixedHeight(142)
        inputs.addWidget(self.repair_error)
        inputs.addWidget(_label("OPTIONAL ERROR SCREENSHOT", "eyebrow"))
        screenshot_row = QHBoxLayout()
        self.repair_screenshot_name = _label("No screenshot attached", "muted", True)
        screenshot_row.addWidget(self.repair_screenshot_name, 1)
        choose_screenshot = _button("Upload image", ghost=True)
        choose_screenshot.clicked.connect(self._choose_repair_screenshot)
        screenshot_row.addWidget(choose_screenshot)
        self.clear_screenshot_button = _button("Clear", ghost=True)
        self.clear_screenshot_button.setEnabled(False)
        self.clear_screenshot_button.clicked.connect(self._clear_repair_screenshot)
        screenshot_row.addWidget(self.clear_screenshot_button)
        inputs.addLayout(screenshot_row)
        inputs.addStretch(1)
        self.repair_button = _button("⌁  Diagnose & apply safe repair", primary=True)
        self.repair_button.clicked.connect(self._repair_project)
        inputs.addWidget(self.repair_button)
        row.addWidget(input_card, 2)

        result_card = Card()
        results = QVBoxLayout(result_card)
        results.setContentsMargins(18, 18, 18, 18)
        results.setSpacing(11)
        result_header = QHBoxLayout()
        result_header.addWidget(_label("REPAIR RESULT", "eyebrow"))
        result_header.addStretch(1)
        copy_repair = _button("Copy", ghost=True)
        copy_repair.clicked.connect(lambda: self._copy_text(self.repair_result.toPlainText()))
        result_header.addWidget(copy_repair)
        results.addLayout(result_header)
        self.repair_result = self._result_browser(
            "Choose a project folder, paste the error, and optionally attach a screenshot. Atlas will back up every changed file under `.atlas-backups` before it writes the repair."
        )
        results.addWidget(self.repair_result, 1)
        repair_actions = QHBoxLayout()
        self.open_repaired_project_button = _button("Open repaired project", ghost=True)
        self.open_repaired_project_button.setEnabled(False)
        self.open_repaired_project_button.clicked.connect(self._open_repaired_project)
        repair_actions.addWidget(self.open_repaired_project_button)
        repair_actions.addStretch(1)
        results.addLayout(repair_actions)
        row.addWidget(result_card, 3)
        workspace_layout.addLayout(row, 1)
        return workspace

    def _build_chat_page(self) -> QWidget:
        page, layout = self._page_shell(
            "Chat with Gemini",
            "Chat with Gemini using your selected model. It can answer general questions and use your locally stored Atlas activity as context.",
        )
    
        # --- Memory Card Section ---
        memory_card = Card(inner=True)
        memory_layout = QHBoxLayout(memory_card)
        memory_layout.setContentsMargins(14, 11, 14, 11)
        memory_layout.setSpacing(10)
        memory_layout.addWidget(_label("LOCAL MEMORY", "eyebrow"))
    
        self.memory_path_label = _label(str(self.memory.path), "muted", True)
        self.memory_path_label.setToolTip(str(self.memory.path))
        memory_layout.addWidget(self.memory_path_label, 1)
    
        open_memory = _button("Open memory file", ghost=True)
        open_memory.clicked.connect(self._open_memory_file)
        memory_layout.addWidget(open_memory)
    
        clear_memory = _button("Clear local memory", ghost=True)
        clear_memory.clicked.connect(self._clear_memory)
        memory_layout.addWidget(clear_memory)
        layout.addWidget(memory_card)

        # --- Chat Card Section ---
        chat_card = Card()
        chat_layout = QVBoxLayout(chat_card)
        chat_layout.setContentsMargins(18, 17, 18, 18)
        chat_layout.setSpacing(8)
    
        # Header
        header = QHBoxLayout()
        self.chat_context_status = _label("Local activity context is ready", "status")
        header.addStretch(1)
        header.addWidget(self.chat_context_status)
    
        new_chat = _button("New chat view", ghost=True)
        new_chat.clicked.connect(self._new_chat_view)
        header.addWidget(new_chat)
        chat_layout.addLayout(header)
    
        # Transcript - Stretch factor 1 forces it to absorb all vertical space
        self.chat_transcript = self._result_browser("")
        self.chat_transcript.setMinimumHeight(200)
        self.chat_transcript.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        chat_layout.addWidget(self.chat_transcript, 1)

        # --- Chat Input (Balanced Height) ---
        self.chat_input = QPlainTextEdit()
        self.chat_input.setPlaceholderText("Ask Gemini anything. It can use your earlier Atlas research, analyses, builds, and repairs when relevant.")
        self.chat_input.setMinimumHeight(78)
        self.chat_input.setMaximumHeight(120)
        self.chat_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.chat_input.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.chat_input.setTextInteractionFlags(Qt.TextInteractionFlag.TextEditorInteraction)
        chat_layout.addWidget(self.chat_input, 0)

        # Actions Section
        actions = QHBoxLayout()
        privacy_note = _label("API key and raw file bytes are never written to local memory.", "muted")
        actions.addWidget(privacy_note)
        actions.addStretch(1)
    
        self.chat_send_button = _button("Send to Gemini", primary=True)
        self.chat_send_button.clicked.connect(self._send_chat)
        actions.addWidget(self.chat_send_button)
        chat_layout.addLayout(actions)
    
        layout.addWidget(chat_card, 1)
    
        return page

    def _build_settings_page(self) -> QWidget:
        page, layout = self._page_shell(
            "Settings",
            "Connect your own Gemini API key. The key is never bundled with Atlas or sent anywhere except Google's Gemini API.",
        )
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        card = Card()
        form = QVBoxLayout(card)
        form.setContentsMargins(22, 21, 22, 21)
        form.setSpacing(12)
        form.addWidget(_label("GEMINI API KEY", "eyebrow"))
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_edit.setPlaceholderText("Paste an API key from Google AI Studio")
        self.api_key_edit.setClearButtonEnabled(True)
        form.addWidget(self.api_key_edit)
        key_note = _label(
            "Saved locally with Qt settings only when you choose Save key. You may use GEMINI_API_KEY instead.", "muted", True
        )
        form.addWidget(key_note)
        form.addSpacing(8)
        form.addWidget(_label("DEFAULT MODEL", "eyebrow"))
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.setMinimumWidth(210)
        self.model_combo.addItems(DEFAULT_MODELS)
        self.model_combo.setToolTip("This is the default model used when a task does not have its own override.")
        form.addWidget(self.model_combo)
        form.addWidget(_label("TASK-SPECIFIC MODELS", "eyebrow"))
        self.task_model_grid = QGridLayout()
        self.task_model_grid.setContentsMargins(0, 0, 0, 0)
        self.task_model_grid.setHorizontalSpacing(18)
        self.task_model_grid.setVerticalSpacing(10)
        self.task_model_grid.setColumnStretch(0, 0)
        self.task_model_grid.setColumnStretch(1, 1)
        for row_index, task_name in enumerate(["chat", "research", "analysis", "build", "repair"]):
            label = _label(task_name.upper(), "muted")
            label.setMinimumWidth(110)
            label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            combo = QComboBox()
            combo.setEditable(True)
            combo.setMinimumWidth(360)
            combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            combo.addItems(DEFAULT_MODELS)
            setattr(self, f"{task_name}_model_combo", combo)
            self.task_model_grid.addWidget(label, row_index, 0)
            self.task_model_grid.addWidget(combo, row_index, 1)
        form.addLayout(self.task_model_grid)
        model_note = _label("Set a default model plus separate overrides for chat, research, analysis, build, and repair tasks. The top bar default is used when a task override is empty.", "muted", True)
        form.addWidget(model_note)
        buttons = QHBoxLayout()
        self.save_settings_button = _button("Save key & preferences", primary=True)
        self.save_settings_button.clicked.connect(self._save_settings)
        buttons.addWidget(self.save_settings_button)
        self.connection_button = _button("Test connection", ghost=True)
        self.connection_button.clicked.connect(self._test_connection)
        buttons.addWidget(self.connection_button)
        self.refresh_models_button = _button("Refresh models", ghost=True)
        self.refresh_models_button.clicked.connect(self._refresh_models)
        buttons.addWidget(self.refresh_models_button)
        buttons.addStretch(1)
        form.addLayout(buttons)
        self.settings_message = _label("Add an API key, save it, then test the connection.", "status", True)
        form.addWidget(self.settings_message)

        self.token_usage_panel = self._build_token_usage_panel()
        form.addWidget(self.token_usage_panel)

        self.settings_downloads = QLineEdit()
        self.settings_downloads.setVisible(False)
        self.settings_downloads.setObjectName("hiddenSettingsDownloads")
        form.addWidget(self.settings_downloads)

        copyright_label = _label("© 2026 Anish Sandeep Bhargav • NeuraX • All rights reserved", "muted", True)
        copyright_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        copyright_label.setStyleSheet("color: rgba(158, 177, 220, 150); font-size: 11px; letter-spacing: 0.8px;")
        form.addWidget(copyright_label)

        form.addStretch(1)
        content_layout.addWidget(card)
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)
        self.model_combo.currentTextChanged.connect(self._sync_model_label)
        self._update_token_usage_display()
        return page

    def _build_token_usage_panel(self) -> QWidget:
        panel = Card(inner=True)
        panel.setMinimumHeight(120)
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(18)

        circle = QFrame()
        circle.setFixedSize(72, 72)
        circle.setStyleSheet(
            "QFrame { border: 3px solid #5d6cf0; border-radius: 36px; background: #0d152a; }"
        )
        circle_layout = QVBoxLayout(circle)
        circle_layout.setContentsMargins(0, 0, 0, 0)
        circle_layout.setSpacing(0)
        self.token_usage_circle_value = _label("—", "eyebrow")
        self.token_usage_circle_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.token_usage_circle_value.setStyleSheet("color: #edf3ff; font-size: 16px; font-weight: 800;")
        circle_layout.addWidget(self.token_usage_circle_value)

        info = QVBoxLayout()
        info.setSpacing(4)
        self.token_usage_account_label = _label("Usage for active Google API key: not configured", "muted", True)
        self.token_usage_total_label = _label("Latest request total: no usage yet", "muted", True)
        self.token_usage_used_label = _label("Used in latest request: 0 tokens", "muted", True)
        self.token_usage_remaining_label = _label("Remaining for latest request: 0 tokens", "muted", True)
        self.token_usage_account_label.setStyleSheet("color: #dfe8ff; font-size: 11px; font-weight: 600;")
        self.token_usage_total_label.setStyleSheet("color: #dfe8ff; font-size: 12px; font-weight: 600;")
        self.token_usage_used_label.setStyleSheet("color: #cddaf9; font-size: 12px;")
        self.token_usage_remaining_label.setStyleSheet("color: #cddaf9; font-size: 12px;")
        info.addWidget(_label("TOKEN USAGE", "eyebrow"))
        info.addWidget(self.token_usage_account_label)
        info.addWidget(self.token_usage_total_label)
        info.addWidget(self.token_usage_used_label)
        info.addWidget(self.token_usage_remaining_label)
        self.token_usage_note = _label(
            "This reflects the current Google API key in Atlas and the latest official Google usage_metadata returned for that key's requests. Google does not expose a true total account usage value via the standard API.",
            "muted",
            True,
        )
        self.token_usage_note.setStyleSheet("color: rgba(181, 189, 212, 0.82); font-size: 10px; line-height: 1.4;")
        info.addWidget(self.token_usage_note)

        layout.addWidget(circle)
        layout.addLayout(info, 1)
        return panel

    def _active_api_key_label(self) -> str:
        if not hasattr(self, "api_key_edit"):
            return "Usage for active Google API key: not configured"
        api_key = self.api_key_edit.text().strip()
        if not api_key:
            return "Usage for active Google API key: not configured"
        if len(api_key) <= 8:
            return f"Usage for active Google API key: {api_key[:4]}..."
        return f"Usage for active Google API key: {api_key[:4]}...{api_key[-4:]}"

    def _update_token_usage_display(self, usage: dict[str, int] | None = None) -> None:
        if not hasattr(self, "token_usage_circle_value"):
            return
        if hasattr(self, "token_usage_account_label"):
            self.token_usage_account_label.setText(self._active_api_key_label())
        if usage is None:
            total = int(self.token_usage_total or 0)
            used = int(self.token_usage_used or 0)
        else:
            prompt_tokens = int(usage.get("prompt_tokens", 0) or 0)
            completion_tokens = int(usage.get("completion_tokens", 0) or 0)
            total = int(usage.get("total_tokens", prompt_tokens + completion_tokens) or (prompt_tokens + completion_tokens) or 0)
            used = total
            self.token_usage_total = total
            self.token_usage_used = used

        if total <= 0:
            self.token_usage_circle_value.setText("—")
            circle = self.token_usage_circle_value.parent()
            if circle is not None:
                circle.setStyleSheet("QFrame { border: 3px solid #5d6cf0; border-radius: 36px; background: #0d152a; }")
            self.token_usage_total_label.setText("Latest request total: no usage yet")
            self.token_usage_used_label.setText("Used in latest request: 0 tokens")
            self.token_usage_remaining_label.setText("Remaining for latest request: 0 tokens")
            return

        remaining = max(total - used, 0)
        percent = min(100, max(0, int((used / total) * 100))) if total else 0
        self.token_usage_circle_value.setText(f"{percent}%")
        circle = self.token_usage_circle_value.parent()
        if circle is not None:
            color = "#67d580" if percent < 60 else "#f7c76d" if percent < 85 else "#ff6b7d"
            circle.setStyleSheet(f"QFrame {{ border: 3px solid {color}; border-radius: 36px; background: #0d152a; }}")
        self.token_usage_total_label.setText(f"Latest request total for this API key: {total:,} tokens")
        self.token_usage_used_label.setText(f"Used in latest request: {used:,} tokens")
        self.token_usage_remaining_label.setText(f"Remaining for latest request: {remaining:,} tokens")

    def _with_usage_update(self, service: Any, callback: Callable[[Any], Any]) -> Callable[[Any], Any]:
        def wrapped(value: Any) -> Any:
            self._update_token_usage_display(getattr(service, "last_usage", {}) or {})
            return callback(value)
        return wrapped

    @staticmethod
    def _format_chat_markdown_to_html(text: str) -> str:
        if not text:
            return ""

        safe = text.replace("\r\n", "\n").replace("\r", "\n")
        safe = re.sub(r"<\s*(script|iframe|object|embed|svg|math|style|link|meta)\b.*?>.*?<\s*/\s*\1\s*>", "", safe, flags=re.IGNORECASE | re.DOTALL)
        safe = re.sub(r"<\s*(script|iframe|object|embed|svg|math|style|link|meta)\b[^>]*>", "", safe, flags=re.IGNORECASE)
        safe = safe.replace("&", "&amp;")
        safe = re.sub(r"(?<!&)#([0-9A-Fa-f]{3,6})\b", r"<span style='color:#\1'>#\1</span>", safe)

        protected_blocks: list[str] = []
        protected_pattern = r"<\s*(?:b|strong|i|em|u|s|sub|sup|small|big|span|br|p|code|pre|ul|ol|li|blockquote|mark)\b[^>]*>.*?<\s*/\s*(?:b|strong|i|em|u|s|sub|sup|small|big|span|br|p|code|pre|ul|ol|li|blockquote|mark)\s*>"
        for marker, match in enumerate(re.finditer(protected_pattern, safe, flags=re.IGNORECASE | re.DOTALL)):
            placeholder = f"__RICH_HTML_{marker}__"
            protected_blocks.append((placeholder, match.group(0)))
            safe = safe.replace(match.group(0), placeholder)

        safe = html.escape(safe, quote=False)
        for placeholder, original in protected_blocks:
            safe = safe.replace(placeholder, original)

        replacements = [
            (r"\*\*(.+?)\*\*", r"<strong>\1</strong>"),
            (r"__(.+?)__", r"<strong>\1</strong>"),
            (r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>"),
            (r"(?<!_)_(?!_)(.+?)(?<!_)_(?!_)", r"<u>\1</u>"),
            (r"~~(.+?)~~", r"<span style='text-decoration: line-through;'>\1</span>"),
            (r"<big>(.+?)</big>", r"<span style='font-size: 1.2em; font-weight: 700;'>\1</span>"),
            (r"<small>(.+?)</small>", r"<span style='font-size: 0.85em;'>\1</span>"),
        ]
        for pattern, replacement in replacements:
            safe = re.sub(pattern, replacement, safe, flags=re.DOTALL)

        safe = safe.replace("\n", "<br>")
        safe = re.sub(r"<br>\s*<br>", "<br>", safe)
        safe = re.sub(r"<\s*(?!/?(?:b|strong|i|em|u|s|sub|sup|small|big|span|br|p|code|pre|ul|ol|li|blockquote|mark))[^>]+>", "", safe, flags=re.IGNORECASE)
        safe = safe.replace("&lt;br&gt;", "<br>")
        safe = safe.replace("&amp;#39;", "&#39;")
        return safe

    def _result_browser(self, placeholder: str) -> Any:
        from PyQt6.QtWidgets import QTextBrowser

        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setReadOnly(True)
        browser.setMarkdown(placeholder)
        return browser

    def _source_list(self, placeholder: str) -> tuple[QScrollArea, QVBoxLayout]:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        source_layout = QVBoxLayout(container)
        source_layout.setContentsMargins(1, 2, 4, 2)
        source_layout.setSpacing(8)
        source_layout.addWidget(_label(placeholder, "muted", True))
        source_layout.addStretch(1)
        scroll.setWidget(container)
        return scroll, source_layout

    def _remember(self, event: str, details: dict[str, Any]) -> None:
        """Persist useful local context without allowing memory-write failures to break the app."""
        try:
            self.memory.record(event, details)
        except OSError:
            if hasattr(self, "activity_status"):
                self.activity_status.setText("Memory could not be saved")

    def _render_chat_transcript(self) -> None:
        logger.debug("Rendering chat transcript with %s messages", len(self._chat_messages))
        if not hasattr(self, "chat_transcript"):
            return
        if not self._chat_messages:
            self.chat_transcript.setHtml(
                "<div style='color:#dfe7ff; padding:18px 0 12px 0; line-height:1.6; font-size:17px;'>"
                "<div style='margin:0 0 6px 0; color:#f3f6ff; font-weight:700;'>Hello — I'm your AI assistant.</div>"
                "Ask me anything. I can also use your locally saved Atlas research, file analyses, project builds, and repairs when that helps."
                "</div>"
            )
            return
        bubbles: list[str] = []
        for role, message in self._chat_messages:
            is_user = role == "user"
            justify = "flex-end" if is_user else "flex-start"
            background = "transparent" if is_user else "transparent"
            border = "none" if is_user else "none"
            text_color = "#b68cff" if is_user else "#edf3ff"
            bubble_padding = "padding:0; margin:0;" if is_user else "padding:10px 0;"
            safe_message = self._format_chat_markdown_to_html(message)
            bubbles.append(
                f"<div style='display:flex; justify-content:{justify}; margin:18px 0; width:100%;'>"
                f"<div style='display:block; max-width:82%; text-align:left; background:{background}; border:{border}; "
                f"border-radius:0; {bubble_padding} color:{text_color}; line-height:1.45; white-space:pre-wrap; word-wrap:break-word; box-sizing:border-box; text-shadow:none;'>"
                f"{safe_message}"
                "</div></div>"
            )
        self.chat_transcript.setHtml("<div style='padding:12px 8px'>" + "".join(bubbles) + "</div>")
        QTimer.singleShot(0, lambda: self.chat_transcript.verticalScrollBar().setValue(self.chat_transcript.verticalScrollBar().maximum()))

    def _send_chat(self) -> None:
        message = self.chat_input.toPlainText().strip()
        if not message:
            logger.warning("User attempted empty chat send")
            self.toast.show_message("Write a message before sending it to Gemini.", error=True)
            return
        service = GeminiService(self.api_key_edit.text())
        logger.info("Sending chat message with model %s", self._model_for_task("chat"))
        prior_conversation = tuple(self._chat_messages)
        memory_context = self.memory.recent_context()
        model = self._model_for_task("chat")
        self._chat_messages.append(("user", message))
        self._remember("chat_user", {"message": message, "model": model})
        self.chat_input.clear()
        self._render_chat_transcript()
        self.chat_context_status.setText("Gemini is thinking…")
        self._start_task(
            button=self.chat_send_button,
            activity=f"Chatting with {model}…",
            task=lambda: service.chat(message=message, memory_context=memory_context, conversation=prior_conversation, model=model),
            success=self._with_usage_update(service, lambda response: self._animate_chat_reply(response)),
            failure=lambda _message: self.chat_context_status.setText("Chat needs attention — try again"),
        )

    def _show_chat_reply(self, message: str) -> None:
        if self._typing_timer is not None:
            self._typing_timer.stop()
            self._typing_timer.deleteLater()
            self._typing_timer = None
        self._chat_messages = self._chat_messages[:-1] + [("assistant", message)] if self._chat_messages and self._chat_messages[-1][0] == "assistant" and self._chat_messages[-1][1] == "" else self._chat_messages + [("assistant", message)]
        model = self._model_for_task("chat")
        self._remember("chat_assistant", {"message": message, "model": model})
        self.chat_context_status.setText("Local activity context is ready")
        self._render_chat_transcript()

    def _animate_chat_reply(self, message: str) -> None:
        if self._typing_timer is not None:
            self._typing_timer.stop()
            self._typing_timer.deleteLater()
            self._typing_timer = None

        self._chat_messages.append(("assistant", ""))
        self._typing_message = message
        self._typing_index = 0
        self.chat_context_status.setText("Gemini is typing…")
        self._render_chat_transcript()

        self._typing_timer = QTimer(self)
        self._typing_timer.setInterval(18)
        self._typing_timer.timeout.connect(self._advance_chat_reply)
        self._typing_timer.start()

    def _advance_chat_reply(self) -> None:
        if not self._chat_messages or self._chat_messages[-1][0] != "assistant":
            if self._typing_timer is not None:
                self._typing_timer.stop()
            return

        self._typing_index += 1
        partial = self._typing_message[: self._typing_index]
        self._chat_messages[-1] = ("assistant", partial)
        self._render_chat_transcript()

        if self._typing_index >= len(self._typing_message):
            if self._typing_timer is not None:
                self._typing_timer.stop()
                self._typing_timer.deleteLater()
                self._typing_timer = None
            self.chat_context_status.setText("Local activity context is ready")
            model = self._model_for_task("chat")
            self._remember("chat_assistant", {"message": self._typing_message, "model": model})

    def _new_chat_view(self) -> None:
        self._chat_messages = []
        self._render_chat_transcript()
        self.chat_context_status.setText("New chat view — local activity memory remains available")

    def _open_memory_file(self) -> None:
        try:
            self.memory.path.parent.mkdir(parents=True, exist_ok=True)
            if not self.memory.path.exists():
                self.memory.path.touch()
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.memory.path)))
        except OSError:
            self.toast.show_message("Atlas could not open the local memory file.", error=True)

    def _clear_memory(self) -> None:
        answer = QMessageBox.question(
            self,
            "Clear Atlas local memory?",
            "This permanently removes the local activity and chat memory file. It does not affect your projects or Gemini API account.",
            QMessageBox.StandardButton.Cancel | QMessageBox.StandardButton.Yes,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.memory.clear()
        except OSError:
            self.toast.show_message("Atlas could not clear the local memory file.", error=True)
            return
        self._chat_messages = []
        self._render_chat_transcript()
        self.chat_context_status.setText("Local memory cleared")
        self.toast.show_message("Local Atlas memory was cleared.")

    def _load_saved_settings(self) -> None:
        self.api_key_edit.setText(self.settings.api_key)
        self.settings_downloads.setText(str(self.settings.downloads_dir))
        self.project_destination.setText(str(self.settings.downloads_dir))
        self._set_combo_text(self.model_combo, self.settings.model)
        for task_name, combo in {
            "chat": self.chat_model_combo,
            "research": self.research_model_combo,
            "analysis": self.analysis_model_combo,
            "build": getattr(self, "build_model_combo", None),
            "repair": getattr(self, "repair_model_combo", None),
        }.items():
            if combo is not None:
                self._set_combo_text(combo, self.settings.task_models.get(task_name, self.settings.model))
        self._sync_connection_ui()
        self._sync_model_label(self.model_combo.currentText())

    @staticmethod
    def _set_combo_text(combo: QComboBox, value: str) -> None:
        if combo.findText(value) == -1:
            combo.addItem(value)
        combo.setCurrentText(value)

    def _sync_model_label(self, model: str) -> None:
        # The visible default model is the actual selector field itself.
        # Keeping this as a no-op avoids duplicate text appearing in the Settings UI.
        _ = model

    def _sync_connection_ui(self) -> None:
        has_key = bool(self.api_key_edit.text().strip())
        self.side_connection.setText("Key configured" if has_key else "Key needed")
        self.side_connection.setStyleSheet("color: #93e7c0;" if has_key else "color: #f3bb74;")

    def _change_page(self, index: int) -> None:
        self.pages.setCurrentIndex(index)
        for button_index, button in enumerate(self._nav_buttons):
            button.setChecked(button_index == index)

        # Brief opacity transition adds motion without blocking interaction.
        page = self.pages.currentWidget()
        effect = QGraphicsOpacityEffect(page)
        page.setGraphicsEffect(effect)
        animation = QPropertyAnimation(effect, b"opacity", page)
        animation.setDuration(180)
        animation.setStartValue(0.35)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        animation.finished.connect(lambda: page.setGraphicsEffect(None))
        animation.start()
        page._atlas_animation = animation  # type: ignore[attr-defined]

    def _service(self) -> GeminiService:
        return GeminiService(self.api_key_edit.text())

    def _model_for_task(self, task_name: str) -> str:
        task_combo = getattr(self, f"{task_name}_model_combo", None)
        if task_combo is not None:
            selected = task_combo.currentText().strip()
            if selected:
                return selected
        return self.model_combo.currentText().strip() or self.settings.model

    def _model(self) -> str:
        return self.model_combo.currentText().strip() or self.settings.model

    def _start_task(
        self,
        *,
        button: QAbstractButton,
        activity: str,
        task: Callable[[], Any],
        success: Callable[[Any], None],
        failure: Callable[[str], None] | None = None,
    ) -> None:
        logger.info("Starting task: %s", activity)
        button.setEnabled(False)
        was_idle = self._active_tasks == 0
        self._active_tasks += 1
        self.activity_status.setText(activity)
        if was_idle:
            QApplication.setOverrideCursor(Qt.CursorShape.BusyCursor)

        def complete(value: Any) -> None:
            self._finish_task(button)
            success(value)

        def fail(message: str) -> None:
            logger.error("Task failed: %s", message)
            self._finish_task(button)
            self.toast.show_message(message, error=True)
            self.activity_status.setText("Needs attention")
            if failure is not None:
                failure(message)

        self.runner.run(task, complete, fail)

    def _finish_task(self, button: QAbstractButton) -> None:
        button.setEnabled(True)
        self._active_tasks = max(0, self._active_tasks - 1)
        logger.debug("Finished task: active_tasks=%s", self._active_tasks)
        if self._active_tasks == 0:
            QApplication.restoreOverrideCursor()
            self.activity_status.setText("Ready")

    def _research(self) -> None:
        query = self.research_query.toPlainText()
        urls = tuple(line.strip() for line in self.source_urls.toPlainText().splitlines() if line.strip())
        service = GeminiService(self.api_key_edit.text())
        model = self._model_for_task("research")
        use_search = self.google_search_check.isChecked()
        use_url_context = self.url_context_check.isChecked()
        self._start_task(
            button=self.research_button,
            activity="Researching with Gemini…",
            task=lambda: service.research(
                query=query,
                model=model,
                use_search=use_search,
                use_url_context=use_url_context,
                source_urls=urls,
            ),
            success=self._with_usage_update(service, lambda result: self._show_research_result(result, query, urls, model)),
        )

    def _show_research_result(self, result: ResearchResult, query: str, urls: tuple[str, ...], model: str) -> None:
        self.research_answer.setMarkdown(result.answer)
        self._render_sources(result.citations)
        self.research_source_count.setText(f"{len(result.citations)} cited")
        self._remember(
            "research_completed",
            {
                "query": query,
                "source_urls": list(urls),
                "model": model,
                "answer": result.answer,
                "citations": [{"title": citation.title, "url": citation.url, "kind": citation.kind} for citation in result.citations],
            },
        )
        if result.citations:
            self.toast.show_message(f"Research complete — {len(result.citations)} source links returned.")
        else:
            self.toast.show_message("Research complete. Gemini returned no source citations for this response.")

    def _render_sources(self, citations: tuple[Citation, ...]) -> None:
        while self.research_sources_layout.count():
            item = self.research_sources_layout.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        if citations:
            for index, citation in enumerate(citations, 1):
                source = SourceCard(citation, index)
                source.opened.connect(self._open_url)
                self.research_sources_layout.addWidget(source)
        else:
            self.research_sources_layout.addWidget(
                _label("No citation links were returned. Try enabling web search or using a more specific question.", "muted", True)
            )
        self.research_sources_layout.addStretch(1)

    def _choose_file(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(
            self,
            "Choose a file to analyse",
            str(Path.home()),
            "Supported files (*.pdf *.docx *.doc *.pptx *.ppt *.xlsx *.xls *.csv *.txt *.md *.py *.js *.ts *.json *.html *.css *.jpg *.jpeg *.png *.webp *.gif *.mp4 *.mov *.avi *.mkv *.mp3 *.wav *.m4a);;All files (*.*)",
        )
        if not selected:
            return
        self._selected_file = Path(selected)
        self.file_name.setText(self._selected_file.name + "\n" + str(self._selected_file))
        suffix = self._selected_file.suffix.lower()
        if suffix in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}:
            pixmap = QPixmap(str(self._selected_file))
            if not pixmap.isNull():
                self.file_preview.setPixmap(
                    pixmap.scaled(self.file_preview.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                )
                return
        glyph = "▣" if suffix in {".pdf", ".doc", ".docx", ".ppt", ".pptx"} else "⌘" if suffix in {".py", ".js", ".ts", ".json", ".html", ".css"} else "◌"
        self.file_preview.setPixmap(QPixmap())
        self.file_preview.setText(glyph)

    def _analyse_file(self) -> None:
        path = self._selected_file
        prompt = self.analysis_prompt.toPlainText()
        service = GeminiService(self.api_key_edit.text())
        model = self._model_for_task("analysis")
        self._start_task(
            button=self.analyse_button,
            activity="Uploading and analysing…",
            task=lambda: service.analyse_file(file_path=path or Path(), instruction=prompt, model=model),
            success=self._with_usage_update(service, lambda result: self._show_analysis_result(result, path, prompt, model)),
        )

    def _show_analysis_result(self, result: ResearchResult, path: Path | None, prompt: str, model: str) -> None:
        self.analysis_answer.setMarkdown(result.answer)
        self._remember(
            "file_analysis_completed",
            {
                "file_path": str(path) if path else "",
                "file_name": path.name if path else "",
                "instruction": prompt,
                "model": model,
                "answer": result.answer,
            },
        )
        self.toast.show_message("File analysis complete.")

    def _choose_destination(self) -> None:
        current = self.project_destination.text().strip() or str(Path.home() / "Downloads")
        directory = QFileDialog.getExistingDirectory(self, "Choose project location", current)
        if directory:
            self.project_destination.setText(directory)
            self.settings_downloads.setText(directory)

    def _set_builder_mode(self, index: int) -> None:
        self.builder_stack.setCurrentIndex(index)
        is_new_project = index == 0
        self.new_project_mode_button.setObjectName("primary" if is_new_project else "ghost")
        self.repair_mode_button.setObjectName("ghost" if is_new_project else "primary")
        # Repolish after changing the selector's object name so the active mode
        # receives the same visual treatment as the primary action buttons.
        for button in (self.new_project_mode_button, self.repair_mode_button):
            button.style().unpolish(button)
            button.style().polish(button)

    def _choose_repair_project(self) -> None:
        current = self.repair_project_directory.text().strip() or str(self.settings.downloads_dir)
        directory = QFileDialog.getExistingDirectory(self, "Choose the project folder to repair", current)
        if directory:
            self.repair_project_directory.setText(directory)
            self.repair_context_status.setText(
                "Ready to inspect source and configuration files. Build outputs, dependencies, and existing Atlas backups are excluded."
            )

    def _choose_repair_screenshot(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(
            self,
            "Choose an error screenshot",
            str(Path.home()),
            "Image files (*.png *.jpg *.jpeg *.webp *.gif *.bmp);;All files (*.*)",
        )
        if not selected:
            return
        self._repair_screenshot = Path(selected)
        self.repair_screenshot_name.setText(self._repair_screenshot.name)
        self.clear_screenshot_button.setEnabled(True)

    def _clear_repair_screenshot(self) -> None:
        self._repair_screenshot = None
        self.repair_screenshot_name.setText("No screenshot attached")
        self.clear_screenshot_button.setEnabled(False)

    def _build_project(self) -> None:
        project_name = self.project_name.text()
        description = self.project_description.toPlainText()
        language = self.language_combo.currentText()
        framework = self.framework_combo.currentText()
        directory = Path(self.project_destination.text().strip() or str(self.settings.downloads_dir))
        service = GeminiService(self.api_key_edit.text())
        model = self._model()

        def create() -> WrittenProject:
            specification = service.generate_project(
                project_name=project_name,
                description=description,
                language=language,
                framework=framework,
                model=model,
            )
            return write_project(specification, directory)

        self._start_task(
            button=self.build_button,
            activity="Gemini is generating your project…",
            task=create,
            success=self._with_usage_update(service, lambda result: self._show_build_result(result, project_name, description, language, framework, model)),
        )

    def _show_build_result(
        self,
        result: WrittenProject,
        requested_name: str,
        description: str,
        language: str,
        framework: str,
        model: str,
    ) -> None:
        self._written_project = result
        self.open_project_button.setEnabled(True)
        self.repair_project_directory.setText(str(result.root))
        self._remember(
            "project_generated",
            {
                "requested_name": requested_name,
                "description": description,
                "language": language,
                "framework": framework,
                "model": model,
                "project_root": str(result.root),
                "file_count": result.file_count,
                "summary": result.summary,
                "run_instructions": result.run_instructions,
            },
        )
        self.build_result.setMarkdown(
            f"## Project created\n\n**Folder:** `{result.root}`\n\n"
            f"**Files created:** {result.file_count}\n\n{result.summary}\n\n"
            f"### Run it\n{result.run_instructions}"
        )
        self.toast.show_message(f"Project saved in {result.root.name}.")

    def _repair_project(self) -> None:
        raw_directory = self.repair_project_directory.text().strip()
        if not raw_directory:
            self.toast.show_message("Choose the existing project folder you want Atlas to repair.", error=True)
            return
        project_directory = Path(raw_directory)
        error_description = self.repair_error.toPlainText()
        screenshot = self._repair_screenshot
        service = GeminiService(self.api_key_edit.text())
        model = self._model_for_task("repair")

        def repair() -> tuple[WrittenRepair, int, bool]:
            specification, source_count, context_truncated = service.repair_project(
                project_directory=project_directory,
                error_description=error_description,
                screenshot_path=screenshot,
                model=model,
            )
            return apply_repair(specification, project_directory), source_count, context_truncated

        self._start_task(
            button=self.repair_button,
            activity="Gemini is diagnosing and repairing…",
            task=repair,
            success=self._with_usage_update(service, lambda result: self._show_repair_result(result, project_directory, error_description, screenshot, model)),
        )

    def _show_repair_result(
        self,
        result: tuple[WrittenRepair, int, bool],
        project_directory: Path,
        error_description: str,
        screenshot: Path | None,
        model: str,
    ) -> None:
        repair, source_count, context_truncated = result
        self._written_repair = repair
        self.open_repaired_project_button.setEnabled(True)
        changed = "\n".join(f"- `{path.as_posix()}`" for path in repair.changed_paths)
        coverage = f"Gemini inspected **{source_count}** source/configuration files."
        if context_truncated:
            coverage += " Some large or excess source files were excluded to stay within the safe request limit."
        self._remember(
            "project_repaired",
            {
                "project_root": str(project_directory),
                "error_description": error_description,
                "screenshot_path": str(screenshot) if screenshot else "",
                "model": model,
                "source_files_inspected": source_count,
                "context_truncated": context_truncated,
                "changed_files": [path.as_posix() for path in repair.changed_paths],
                "backup_root": str(repair.backup_root),
                "summary": repair.summary,
                "diagnosis": repair.diagnosis,
                "run_instructions": repair.run_instructions,
            },
        )
        self.repair_result.setMarkdown(
            f"## Repair applied\n\n{repair.summary}\n\n"
            f"### Diagnosis\n{repair.diagnosis}\n\n"
            f"### Changed files\n{changed}\n\n"
            f"### Backup\nOriginal versions are in `{repair.backup_root}`.\n\n"
            f"### Validate it\n{repair.run_instructions}\n\n{coverage}"
        )
        self.toast.show_message(f"Repair applied to {len(repair.changed_paths)} file(s); originals are backed up.")

    def _open_repaired_project(self) -> None:
        if self._written_repair:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._written_repair.project_root)))

    def _open_project_folder(self) -> None:
        if self._written_project:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._written_project.root)))

    def _save_settings(self) -> None:
        directory = Path(self.settings_downloads.text().strip() or str(self.store.default_downloads_dir()))
        task_models = {
            "chat": self.chat_model_combo.currentText().strip() or self.model_combo.currentText().strip(),
            "research": self.research_model_combo.currentText().strip() or self.model_combo.currentText().strip(),
            "analysis": self.analysis_model_combo.currentText().strip() or self.model_combo.currentText().strip(),
            "build": self.build_model_combo.currentText().strip() or self.model_combo.currentText().strip(),
            "repair": self.repair_model_combo.currentText().strip() or self.model_combo.currentText().strip(),
        }
        self.store.save(api_key=self.api_key_edit.text(), model=self._model(), downloads_dir=directory, task_models=task_models)
        self.settings = self.store.load()
        self.project_destination.setText(str(directory))
        self._remember("settings_saved", {"model": self._model(), "downloads_directory": str(directory), "task_models": task_models})
        self._sync_connection_ui()
        self.settings_message.setText("Saved locally. You can now test the Gemini connection.")
        self.toast.show_message("Settings saved on this device.")

    def _test_connection(self) -> None:
        model = self._model()
        service = GeminiService(self.api_key_edit.text())
        self._start_task(
            button=self.connection_button,
            activity="Testing Gemini connection…",
            task=lambda: service.check_connection(model),
            success=lambda response: self._connection_succeeded(response),
        )

    def _connection_succeeded(self, response: str) -> None:
        self._sync_connection_ui()
        self._update_token_usage_display(getattr(self._service(), "last_usage", {}) or {})
        self.settings_message.setText(f"Connection successful. Gemini replied: {response}")
        self.toast.show_message("Gemini connection is working.")

    def _refresh_models(self) -> None:
        current = self._model()
        service = GeminiService(self.api_key_edit.text())
        self._start_task(
            button=self.refresh_models_button,
            activity="Loading available models…",
            task=lambda: service.available_models(),
            success=lambda models: self._models_loaded(models, current),
        )

    def _models_loaded(self, models: list[str], selected: str) -> None:
        combo_targets = [self.model_combo]
        for attr_name in [
            "chat_model_combo",
            "research_model_combo",
            "analysis_model_combo",
            "build_model_combo",
            "repair_model_combo",
        ]:
            combo = getattr(self, attr_name, None)
            if combo is not None:
                combo_targets.append(combo)
        for combo in combo_targets:
            combo.blockSignals(True)
            combo.clear()
            combo.addItems(models)
            current_text = combo.currentText().strip() if combo.count() else ""
            if current_text:
                self._set_combo_text(combo, current_text)
            else:
                self._set_combo_text(combo, selected)
            combo.blockSignals(False)
        self._sync_model_label(self.model_combo.currentText())
        self.settings_message.setText(f"Loaded {len(models)} Gemini model IDs available to this key.")
        self.toast.show_message(f"Loaded {len(models)} models.")

    def _copy_text(self, text: str) -> None:
        if text.strip():
            QApplication.clipboard().setText(text)
            self.toast.show_message("Copied to clipboard.")

    def _open_url(self, url: str) -> None:
        QDesktopServices.openUrl(QUrl(url))

    def resizeEvent(self, event: QEvent) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        if hasattr(self, "toast") and self.toast.isVisible():
            self.toast.move(max(16, self.centralWidget().width() - self.toast.width() - 28), 76)
