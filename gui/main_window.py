"""
gui/main_window.py
Main application window built with PyQt6.

Architecture
============
- SearchWorker   : QThread that runs youtube search off the main thread
- DownloadWorker : QThread that drives yt-dlp downloads
- VideoCard      : QWidget displayed for each search result
- MainWindow     : top-level QMainWindow tying everything together
"""

from __future__ import annotations

import os
import sys
import urllib.request
from pathlib import Path
from typing import Any, Optional

from PyQt6.QtCore import (
    QObject,
    QRunnable,
    Qt,
    QThread,
    QThreadPool,
    QTimer,
    pyqtSignal,
    pyqtSlot,
)
from PyQt6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QIcon,
    QPalette,
    QPixmap,
)
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QStatusBar,
    QVBoxLayout,
    QWidget,
    QFileDialog,
    QGroupBox,
)

from core.search import search_youtube
from core.downloader import (
    VIDEO_QUALITY_OPTIONS,
    download_video,
)

# ── Colour palette (dark YouTube-inspired theme) ──────────────────────────────
C = {
    "bg":          "#0f0f0f",
    "surface":     "#1a1a1a",
    "surface2":    "#242424",
    "border":      "#2e2e2e",
    "accent":      "#ff0000",
    "accent_soft": "#cc0000",
    "text":        "#f1f1f1",
    "text_muted":  "#aaaaaa",
    "text_dim":    "#717171",
    "hover":       "#272727",
    "selected":    "#3d1f1f",
    "progress_bg": "#282828",
}

STYLESHEET = f"""
QMainWindow, QWidget {{
    background-color: {C["bg"]};
    color: {C["text"]};
    font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
}}
QLineEdit {{
    background-color: {C["surface2"]};
    border: 1.5px solid {C["border"]};
    border-radius: 20px;
    padding: 8px 16px;
    color: {C["text"]};
    font-size: 14px;
    selection-background-color: {C["accent"]};
}}
QLineEdit:focus {{
    border-color: {C["accent"]};
}}
QPushButton {{
    background-color: {C["accent"]};
    color: #ffffff;
    border: none;
    border-radius: 20px;
    padding: 8px 20px;
    font-size: 13px;
    font-weight: 600;
}}
QPushButton:hover {{
    background-color: {C["accent_soft"]};
}}
QPushButton:pressed {{
    background-color: #aa0000;
}}
QPushButton:disabled {{
    background-color: {C["border"]};
    color: {C["text_dim"]};
}}
QPushButton#browse_btn {{
    background-color: {C["surface2"]};
    color: {C["text_muted"]};
    border: 1px solid {C["border"]};
    font-weight: 400;
    font-size: 12px;
}}
QPushButton#browse_btn:hover {{
    background-color: {C["hover"]};
}}
QScrollArea {{
    border: none;
    background-color: {C["bg"]};
}}
QScrollBar:vertical {{
    background: {C["bg"]};
    width: 6px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {C["border"]};
    border-radius: 3px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {C["text_dim"]};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QComboBox {{
    background-color: {C["surface2"]};
    border: 1.5px solid {C["border"]};
    border-radius: 8px;
    padding: 6px 12px;
    color: {C["text"]};
    font-size: 13px;
}}
QComboBox:hover {{
    border-color: {C["accent"]};
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox QAbstractItemView {{
    background-color: {C["surface2"]};
    border: 1px solid {C["border"]};
    color: {C["text"]};
    selection-background-color: {C["accent"]};
}}
QCheckBox {{
    color: {C["text_muted"]};
    spacing: 8px;
    font-size: 13px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1.5px solid {C["border"]};
    border-radius: 4px;
    background: {C["surface2"]};
}}
QCheckBox::indicator:checked {{
    background-color: {C["accent"]};
    border-color: {C["accent"]};
}}
QProgressBar {{
    background-color: {C["progress_bg"]};
    border: none;
    border-radius: 4px;
    height: 6px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{
    background-color: {C["accent"]};
    border-radius: 4px;
}}
QGroupBox {{
    border: 1px solid {C["border"]};
    border-radius: 10px;
    margin-top: 14px;
    padding: 10px;
    font-weight: 600;
    color: {C["text_muted"]};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}}
QLabel#status_label {{
    color: {C["text_dim"]};
    font-size: 12px;
}}
"""


# ══════════════════════════════════════════════════════════════════════════════
# Worker threads
# ══════════════════════════════════════════════════════════════════════════════

class SearchWorker(QThread):
    """Runs youtube search in a background thread."""

    results_ready = pyqtSignal(list)     # list[dict]
    error_occurred = pyqtSignal(str)

    def __init__(self, query: str, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.query = query

    def run(self) -> None:
        try:
            results = search_youtube(self.query)
            self.results_ready.emit(results)
        except Exception as exc:
            self.error_occurred.emit(str(exc))


class DownloadWorker(QThread):
    """Runs yt-dlp download in a background thread."""

    progress_updated = pyqtSignal(float, str)   # percent, status_text
    download_finished = pyqtSignal(bool, str)   # success, message

    def __init__(
        self,
        url: str,
        output_dir: str,
        quality: str,
        audio_only: bool,
        thumbnail_only: bool,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.url           = url
        self.output_dir    = output_dir
        self.quality       = quality
        self.audio_only    = audio_only
        self.thumbnail_only = thumbnail_only

    def run(self) -> None:
        download_video(
            url=self.url,
            output_dir=self.output_dir,
            quality=self.quality,
            audio_only=self.audio_only,
            thumbnail_only=self.thumbnail_only,
            progress_cb=lambda pct, txt: self.progress_updated.emit(pct, txt),
            finished_cb=lambda ok, msg: self.download_finished.emit(ok, msg),
        )


class ThumbnailLoader(QRunnable):
    """Loads a thumbnail image from URL and posts result back via callback."""

    class Signals(QObject):
        loaded = pyqtSignal(QPixmap)
        failed = pyqtSignal()

    def __init__(self, url: str) -> None:
        super().__init__()
        self.url = url
        self.signals = ThumbnailLoader.Signals()

    def run(self) -> None:
        try:
            data = urllib.request.urlopen(self.url, timeout=8).read()
            px = QPixmap()
            px.loadFromData(data)
            if not px.isNull():
                self.signals.loaded.emit(px)
                return
        except Exception:
            pass
        self.signals.failed.emit()


# ══════════════════════════════════════════════════════════════════════════════
# Video result card widget
# ══════════════════════════════════════════════════════════════════════════════

class VideoCard(QWidget):
    """A clickable card representing a single search result."""

    selected = pyqtSignal(dict)   # emits the result dict when clicked

    THUMB_W = 160
    THUMB_H = 90

    def __init__(self, result: dict[str, Any], pool: QThreadPool, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.result  = result
        self._selected = False
        self._pool   = pool
        self._build_ui()
        self._load_thumbnail(result.get("thumbnail", ""))

    # ── Build ─────────────────────────────────────────────────────────────
    def _build_ui(self) -> None:
        self.setFixedHeight(100)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("video_card")

        root = QHBoxLayout(self)
        root.setContentsMargins(10, 6, 10, 6)
        root.setSpacing(14)

        # thumbnail placeholder
        self.thumb_label = QLabel()
        self.thumb_label.setFixedSize(self.THUMB_W, self.THUMB_H)
        self.thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb_label.setStyleSheet(
            f"background:{C['surface2']}; border-radius:6px; color:{C['text_dim']}; font-size:11px;"
        )
        self.thumb_label.setText("Loading…")
        root.addWidget(self.thumb_label)

        # text block
        text_col = QVBoxLayout()
        text_col.setSpacing(4)
        text_col.setContentsMargins(0, 0, 0, 0)

        self.title_label = QLabel(self.result.get("title", ""))
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet(f"font-size:13px; font-weight:600; color:{C['text']}; background:transparent;")
        self.title_label.setMaximumWidth(500)

        meta_row = QHBoxLayout()
        meta_row.setSpacing(10)
        ch_label = QLabel(self.result.get("channel", ""))
        ch_label.setStyleSheet(f"font-size:11px; color:{C['text_muted']}; background:transparent;")
        dur_label = QLabel(self.result.get("duration", ""))
        dur_label.setStyleSheet(
            f"font-size:11px; color:{C['text_dim']}; background:{C['surface2']}; "
            f"border-radius:4px; padding:1px 6px;"
        )
        meta_row.addWidget(ch_label)
        meta_row.addWidget(dur_label)
        meta_row.addStretch()

        text_col.addStretch()
        text_col.addWidget(self.title_label)
        text_col.addLayout(meta_row)
        text_col.addStretch()
        root.addLayout(text_col)

        self._refresh_style()

    # ── Thumbnail async load ──────────────────────────────────────────────
    def _load_thumbnail(self, url: str) -> None:
        if not url:
            self.thumb_label.setText("No image")
            return
        loader = ThumbnailLoader(url)
        loader.signals.loaded.connect(self._on_thumb_loaded)
        loader.signals.failed.connect(lambda: self.thumb_label.setText("No image"))
        self._pool.start(loader)

    @pyqtSlot(QPixmap)
    def _on_thumb_loaded(self, px: QPixmap) -> None:
        scaled = px.scaled(
            self.THUMB_W, self.THUMB_H,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.thumb_label.setPixmap(scaled)
        self.thumb_label.setStyleSheet("border-radius:6px; background:transparent;")

    # ── Selection state ───────────────────────────────────────────────────
    def set_selected(self, state: bool) -> None:
        self._selected = state
        self._refresh_style()

    def _refresh_style(self) -> None:
        if self._selected:
            bg = C["selected"]
            border = f"border: 1.5px solid {C['accent']};"
        else:
            bg = "transparent"
            border = f"border: 1px solid transparent;"
        self.setStyleSheet(
            f"QWidget#video_card {{ background:{bg}; border-radius:10px; {border} }}"
            f"QWidget#video_card:hover {{ background:{C['hover']}; }}"
        )

    # ── Mouse event ───────────────────────────────────────────────────────
    def mousePressEvent(self, _event) -> None:  # type: ignore[override]
        self.selected.emit(self.result)


# ══════════════════════════════════════════════════════════════════════════════
# Main window
# ══════════════════════════════════════════════════════════════════════════════

class MainWindow(QMainWindow):
    """Top-level application window."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("YT Downloader")
        self.setMinimumSize(900, 680)
        self.resize(1060, 750)

        # Set window icon from img/icon.png
        import os as _os
        _root = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
        for _icon_path in [
            _os.path.join(_root, "img", "icon.png"),
            _os.path.join(_root, "assets", "icons", "app_icon.png"),
        ]:
            if _os.path.exists(_icon_path):
                self.setWindowIcon(QIcon(_icon_path))
                break

        self._thread_pool  = QThreadPool.globalInstance()
        self._search_worker: Optional[SearchWorker]   = None
        self._download_worker: Optional[DownloadWorker] = None
        self._cards: list[VideoCard] = []
        self._selected_result: Optional[dict] = None
        self._output_dir = str(Path.home() / "Downloads")

        self._build_ui()
        self._apply_palette()

    # ══════════════════════════════════════════════════════════════════════
    # UI construction
    # ══════════════════════════════════════════════════════════════════════

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Left panel (search + results) ──────────────────────────────
        left = QWidget()
        left.setObjectName("left_panel")
        left.setStyleSheet(f"QWidget#left_panel {{ background:{C['bg']}; }}")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(20, 20, 20, 16)
        left_layout.setSpacing(14)

        # logo row
        logo_row = QHBoxLayout()
        logo_icon = QLabel("▶")
        logo_icon.setStyleSheet(f"color:{C['accent']}; font-size:22px; font-weight:900;")
        logo_text = QLabel("YT Downloader")
        logo_text.setStyleSheet(f"color:{C['text']}; font-size:18px; font-weight:700; letter-spacing:0.5px;")
        logo_row.addWidget(logo_icon)
        logo_row.addWidget(logo_text)
        logo_row.addStretch()
        left_layout.addLayout(logo_row)

        # search bar
        search_row = QHBoxLayout()
        search_row.setSpacing(8)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search YouTube…")
        self.search_input.returnPressed.connect(self._on_search)
        self.search_btn = QPushButton("Search")
        self.search_btn.setFixedWidth(90)
        self.search_btn.clicked.connect(self._on_search)
        search_row.addWidget(self.search_input)
        search_row.addWidget(self.search_btn)
        left_layout.addLayout(search_row)

        # results area
        results_label = QLabel("Results")
        results_label.setStyleSheet(f"color:{C['text_dim']}; font-size:11px; font-weight:600; letter-spacing:1px; text-transform:uppercase;")
        left_layout.addWidget(results_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.results_container = QWidget()
        self.results_container.setStyleSheet(f"background:{C['bg']};")
        self.results_layout = QVBoxLayout(self.results_container)
        self.results_layout.setContentsMargins(0, 0, 0, 0)
        self.results_layout.setSpacing(4)
        self.results_layout.addStretch()
        scroll.setWidget(self.results_container)
        left_layout.addWidget(scroll, stretch=1)

        root.addWidget(left, stretch=1)

        # ── Right panel (options + progress) ───────────────────────────
        right = QWidget()
        right.setFixedWidth(300)
        right.setObjectName("right_panel")
        right.setStyleSheet(
            f"QWidget#right_panel {{ background:{C['surface']}; border-left:1px solid {C['border']}; }}"
        )
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(20, 24, 20, 20)
        right_layout.setSpacing(16)

        # selected video info
        sel_header = QLabel("Selected Video")
        sel_header.setStyleSheet(f"color:{C['text_dim']}; font-size:11px; font-weight:600; letter-spacing:1px;")
        right_layout.addWidget(sel_header)

        self.sel_thumb = QLabel()
        self.sel_thumb.setFixedHeight(130)
        self.sel_thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sel_thumb.setStyleSheet(
            f"background:{C['surface2']}; border-radius:8px; color:{C['text_dim']}; font-size:12px;"
        )
        self.sel_thumb.setText("No video selected")
        right_layout.addWidget(self.sel_thumb)

        self.sel_title = QLabel()
        self.sel_title.setWordWrap(True)
        self.sel_title.setStyleSheet(f"font-size:13px; font-weight:600; color:{C['text']}; line-height:1.4;")
        self.sel_title.hide()
        right_layout.addWidget(self.sel_title)

        self.sel_channel = QLabel()
        self.sel_channel.setStyleSheet(f"font-size:11px; color:{C['text_muted']};")
        self.sel_channel.hide()
        right_layout.addWidget(self.sel_channel)

        # separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color:{C['border']};")
        right_layout.addWidget(sep)

        # download options group
        opts_group = QGroupBox("Download Options")
        opts_layout = QVBoxLayout(opts_group)
        opts_layout.setSpacing(10)

        quality_row = QHBoxLayout()
        quality_row.setSpacing(8)
        q_label = QLabel("Quality")
        q_label.setStyleSheet(f"color:{C['text_muted']}; font-size:12px;")
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(VIDEO_QUALITY_OPTIONS)
        quality_row.addWidget(q_label)
        quality_row.addWidget(self.quality_combo, stretch=1)
        opts_layout.addLayout(quality_row)

        self.audio_check = QCheckBox("Audio only (MP3)")
        self.audio_check.toggled.connect(self._on_audio_toggled)
        opts_layout.addWidget(self.audio_check)

        self.thumb_check = QCheckBox("Thumbnail only")
        self.thumb_check.toggled.connect(self._on_thumb_toggled)
        opts_layout.addWidget(self.thumb_check)

        right_layout.addWidget(opts_group)

        # output directory
        dir_group = QGroupBox("Save Location")
        dir_layout = QVBoxLayout(dir_group)
        dir_layout.setSpacing(6)

        self.dir_label = QLabel(self._shorten_path(self._output_dir))
        self.dir_label.setStyleSheet(f"color:{C['text_muted']}; font-size:11px;")
        self.dir_label.setWordWrap(True)
        dir_layout.addWidget(self.dir_label)

        browse_btn = QPushButton("Browse…")
        browse_btn.setObjectName("browse_btn")
        browse_btn.setFixedHeight(30)
        browse_btn.clicked.connect(self._on_browse)
        dir_layout.addWidget(browse_btn)
        right_layout.addWidget(dir_group)

        right_layout.addStretch()

        # download button
        self.download_btn = QPushButton("⬇  Download")
        self.download_btn.setFixedHeight(44)
        self.download_btn.setEnabled(False)
        self.download_btn.clicked.connect(self._on_download)
        right_layout.addWidget(self.download_btn)

        # progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(6)
        right_layout.addWidget(self.progress_bar)

        # status label
        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("status_label")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)
        right_layout.addWidget(self.status_label)

        root.addWidget(right)

    def _apply_palette(self) -> None:
        """Force dark palette so native widgets also look correct."""
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window,      QColor(C["bg"]))
        palette.setColor(QPalette.ColorRole.WindowText,  QColor(C["text"]))
        palette.setColor(QPalette.ColorRole.Base,        QColor(C["surface2"]))
        palette.setColor(QPalette.ColorRole.Text,        QColor(C["text"]))
        palette.setColor(QPalette.ColorRole.Button,      QColor(C["surface"]))
        palette.setColor(QPalette.ColorRole.ButtonText,  QColor(C["text"]))
        palette.setColor(QPalette.ColorRole.Highlight,   QColor(C["accent"]))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
        self.setPalette(palette)

    # ══════════════════════════════════════════════════════════════════════
    # Search
    # ══════════════════════════════════════════════════════════════════════

    @pyqtSlot()
    def _on_search(self) -> None:
        query = self.search_input.text().strip()
        if not query:
            return
        if self._search_worker and self._search_worker.isRunning():
            return   # ignore rapid double-clicks

        self._clear_results()
        self.search_btn.setEnabled(False)
        self.search_btn.setText("…")
        self.status_label.setText(f"Searching for '{query}'...")

        self._search_worker = SearchWorker(query, parent=self)
        self._search_worker.results_ready.connect(self._on_results_ready)
        self._search_worker.error_occurred.connect(self._on_search_error)
        self._search_worker.finished.connect(lambda: (
            self.search_btn.setEnabled(True),
            self.search_btn.setText("Search"),
        ))
        self._search_worker.start()

    @pyqtSlot(list)
    def _on_results_ready(self, results: list[dict]) -> None:
        if not results:
            self.status_label.setText("No results found.")
            return

        # remove the trailing stretch before adding cards
        item = self.results_layout.takeAt(self.results_layout.count() - 1)
        del item

        for r in results:
            card = VideoCard(r, self._thread_pool, parent=self.results_container)
            card.selected.connect(self._on_card_selected)
            self._cards.append(card)
            self.results_layout.addWidget(card)

        self.results_layout.addStretch()
        self.status_label.setText(f"{len(results)} results found.")

    @pyqtSlot(str)
    def _on_search_error(self, msg: str) -> None:
        self.status_label.setText(f"Search error: {msg}")
        QMessageBox.warning(self, "Search Error", msg)

    def _clear_results(self) -> None:
        for card in self._cards:
            self.results_layout.removeWidget(card)
            card.deleteLater()
        self._cards.clear()
        self._selected_result = None
        self.download_btn.setEnabled(False)
        self._reset_selection_panel()
        # ensure stretch at end
        while self.results_layout.count():
            self.results_layout.takeAt(0)
        self.results_layout.addStretch()

    # ══════════════════════════════════════════════════════════════════════
    # Card selection
    # ══════════════════════════════════════════════════════════════════════

    @pyqtSlot(dict)
    def _on_card_selected(self, result: dict) -> None:
        self._selected_result = result
        # update card highlight states
        for card in self._cards:
            card.set_selected(card.result is result)

        # populate right panel
        self.sel_title.setText(result.get("title", ""))
        self.sel_title.show()
        ch = result.get("channel", "")
        dur = result.get("duration", "")
        self.sel_channel.setText(f"{ch}  •  {dur}")
        self.sel_channel.show()

        # load thumbnail into preview
        self.sel_thumb.setText("Loading…")
        self.sel_thumb.setPixmap(QPixmap())
        url = result.get("thumbnail", "")
        if url:
            loader = ThumbnailLoader(url)
            loader.signals.loaded.connect(self._on_sel_thumb_loaded)
            loader.signals.failed.connect(lambda: self.sel_thumb.setText("No image"))
            self._thread_pool.start(loader)
        else:
            self.sel_thumb.setText("No image")

        self.download_btn.setEnabled(True)
        self.status_label.setText("Ready to download.")

    @pyqtSlot(QPixmap)
    def _on_sel_thumb_loaded(self, px: QPixmap) -> None:
        scaled = px.scaled(
            self.sel_thumb.width() - 4, self.sel_thumb.height() - 4,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.sel_thumb.setPixmap(scaled)
        self.sel_thumb.setStyleSheet("background:transparent; border-radius:8px;")

    def _reset_selection_panel(self) -> None:
        self.sel_thumb.clear()
        self.sel_thumb.setText("No video selected")
        self.sel_thumb.setStyleSheet(
            f"background:{C['surface2']}; border-radius:8px; color:{C['text_dim']}; font-size:12px;"
        )
        self.sel_title.hide()
        self.sel_channel.hide()

    # ══════════════════════════════════════════════════════════════════════
    # Download options
    # ══════════════════════════════════════════════════════════════════════

    def _on_audio_toggled(self, checked: bool) -> None:
        self.quality_combo.setEnabled(not checked)
        if checked:
            self.thumb_check.setChecked(False)

    def _on_thumb_toggled(self, checked: bool) -> None:
        self.quality_combo.setEnabled(not checked)
        self.audio_check.setEnabled(not checked)
        if checked:
            self.audio_check.setChecked(False)

    @pyqtSlot()
    def _on_browse(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Select Download Folder", self._output_dir
        )
        if folder:
            self._output_dir = folder
            self.dir_label.setText(self._shorten_path(folder))

    # ══════════════════════════════════════════════════════════════════════
    # Download
    # ══════════════════════════════════════════════════════════════════════

    @pyqtSlot()
    def _on_download(self) -> None:
        if not self._selected_result:
            return
        if self._download_worker and self._download_worker.isRunning():
            self.status_label.setText("A download is already in progress.")
            return

        url           = self._selected_result.get("url", "")
        quality       = self.quality_combo.currentText()
        audio_only    = self.audio_check.isChecked()
        thumbnail_only = self.thumb_check.isChecked()

        self.download_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_label.setText("Starting download…")

        self._download_worker = DownloadWorker(
            url=url,
            output_dir=self._output_dir,
            quality=quality,
            audio_only=audio_only,
            thumbnail_only=thumbnail_only,
            parent=self,
        )
        self._download_worker.progress_updated.connect(self._on_progress)
        self._download_worker.download_finished.connect(self._on_finished)
        self._download_worker.start()

    @pyqtSlot(float, str)
    def _on_progress(self, percent: float, text: str) -> None:
        self.progress_bar.setValue(int(percent))
        self.status_label.setText(text)

    @pyqtSlot(bool, str)
    def _on_finished(self, success: bool, message: str) -> None:
        self.download_btn.setEnabled(True)
        if success:
            self.progress_bar.setValue(100)
            self.status_label.setText(f"✓ {message}")
            QMessageBox.information(self, "Download Complete", message)
        else:
            self.progress_bar.setValue(0)
            self.status_label.setText(f"✗ {message}")
            QMessageBox.critical(self, "Download Failed", message)

    # ══════════════════════════════════════════════════════════════════════
    # Helpers
    # ══════════════════════════════════════════════════════════════════════

    @staticmethod
    def _shorten_path(path: str, max_len: int = 34) -> str:
        if len(path) <= max_len:
            return path
        return "…" + path[-(max_len - 1):]

    def closeEvent(self, event) -> None:  # type: ignore[override]
        """Gracefully stop threads on close."""
        if self._download_worker and self._download_worker.isRunning():
            self._download_worker.terminate()
            self._download_worker.wait(2000)
        if self._search_worker and self._search_worker.isRunning():
            self._search_worker.terminate()
            self._search_worker.wait(2000)
        event.accept()