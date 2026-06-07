import os
import sys
import threading
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QProgressBar, QScrollArea, QFrame,
    QFileDialog, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QFont, QPalette, QColor

from markitdown import MarkItDown

DEFAULT_OUTPUT = str(Path.home() / "Desktop" / "md conversion")


class WorkerSignals(QObject):
    file_done = pyqtSignal(str, bool, str)   # path, success, message
    progress = pyqtSignal(int, int)           # done, total
    finished = pyqtSignal(int)                # total succeeded


class DropZone(QFrame):
    files_dropped = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setMinimumHeight(130)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._set_style(False)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon = QLabel("⬇")
        icon.setFont(QFont("SF Pro Display", 32))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon)

        title = QLabel("Drop files here")
        title.setFont(QFont("SF Pro Display", 15, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        sub = QLabel("PDF, DOCX, PPTX, XLSX, HTML, and more")
        sub.setFont(QFont("SF Pro Display", 11))
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setObjectName("subtitle")
        layout.addWidget(sub)

    def _set_style(self, hover: bool):
        color = "#3B8ED0" if hover else "#555"
        bg = "rgba(59,142,208,0.08)" if hover else "transparent"
        self.setStyleSheet(f"""
            DropZone {{
                border: 2px dashed {color};
                border-radius: 14px;
                background: {bg};
            }}
        """)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._set_style(True)

    def dragLeaveEvent(self, event):
        self._set_style(False)

    def dropEvent(self, event: QDropEvent):
        self._set_style(False)
        paths = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
        if paths:
            self.files_dropped.emit(paths)


class FileRow(QFrame):
    def __init__(self, path: str):
        super().__init__()
        self.path = path
        self.setFixedHeight(40)
        self.setObjectName("fileRow")
        self.setStyleSheet("""
            #fileRow { background: rgba(255,255,255,0.05); border-radius: 8px; }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)

        self.status = QLabel("⏳")
        self.status.setFixedWidth(24)
        self.status.setFont(QFont("SF Pro Display", 14))
        layout.addWidget(self.status)

        self.name = QLabel(Path(path).name)
        self.name.setFont(QFont("SF Pro Display", 12))
        self.name.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(self.name)

        self.msg = QLabel("")
        self.msg.setFont(QFont("SF Pro Display", 11))
        self.msg.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.msg)

    def set_success(self, out_name: str):
        self.status.setText("✅")
        self.msg.setText(out_name)
        self.msg.setStyleSheet("color: #4CAF50;")

    def set_error(self, err: str):
        self.status.setText("❌")
        self.msg.setText(err[:50])
        self.msg.setStyleSheet("color: #F44336;")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MarkItDown Converter")
        self.setMinimumSize(520, 620)
        self.resize(560, 680)

        self.output_folder = DEFAULT_OUTPUT
        self.queued_files: list[str] = []
        self.file_rows: dict[str, FileRow] = {}
        self.converting = False
        self.signals = WorkerSignals()
        self.signals.file_done.connect(self._on_file_done)
        self.signals.progress.connect(self._on_progress)
        self.signals.finished.connect(self._on_finished)

        self._build_ui()
        self._apply_theme()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(24, 24, 24, 20)
        root.setSpacing(12)

        # Header
        title = QLabel("MarkItDown Converter")
        title.setFont(QFont("SF Pro Display", 20, QFont.Weight.Bold))
        root.addWidget(title)

        sub = QLabel("Convert any file to clean Markdown")
        sub.setFont(QFont("SF Pro Display", 12))
        sub.setObjectName("subtitle")
        root.addWidget(sub)

        # Drop zone
        self.drop_zone = DropZone()
        self.drop_zone.files_dropped.connect(self._add_files)
        root.addWidget(self.drop_zone)

        # Browse + output row
        row = QHBoxLayout()
        row.setSpacing(10)

        browse_btn = QPushButton("Choose Files")
        browse_btn.setFixedWidth(120)
        browse_btn.clicked.connect(self._browse_files)
        row.addWidget(browse_btn)

        self.output_label = QLabel(self._short_path(self.output_folder))
        self.output_label.setFont(QFont("SF Pro Display", 11))
        self.output_label.setObjectName("subtitle")
        self.output_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        row.addWidget(self.output_label)

        change_btn = QPushButton("Change Output")
        change_btn.setObjectName("secondary")
        change_btn.setFixedWidth(120)
        change_btn.clicked.connect(self._choose_output)
        row.addWidget(change_btn)

        root.addLayout(row)

        # File list
        list_card = QFrame()
        list_card.setObjectName("card")
        list_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        card_layout = QVBoxLayout(list_card)
        card_layout.setContentsMargins(10, 10, 10, 10)
        card_layout.setSpacing(4)

        files_title = QLabel("Files")
        files_title.setFont(QFont("SF Pro Display", 12, QFont.Weight.Bold))
        card_layout.addWidget(files_title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.list_widget = QWidget()
        self.list_layout = QVBoxLayout(self.list_widget)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(4)
        self.list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.empty_label = QLabel("No files added yet")
        self.empty_label.setFont(QFont("SF Pro Display", 12))
        self.empty_label.setObjectName("subtitle")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.list_layout.addWidget(self.empty_label)

        scroll.setWidget(self.list_widget)
        card_layout.addWidget(scroll)
        root.addWidget(list_card)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(10)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setValue(0)
        root.addWidget(self.progress_bar)

        self.progress_label = QLabel("")
        self.progress_label.setFont(QFont("SF Pro Display", 11))
        self.progress_label.setObjectName("subtitle")
        root.addWidget(self.progress_label)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        clear_btn = QPushButton("Clear All")
        clear_btn.setObjectName("secondary")
        clear_btn.clicked.connect(self._clear_all)
        btn_row.addWidget(clear_btn)

        btn_row.addStretch()

        self.convert_btn = QPushButton("Convert")
        self.convert_btn.setEnabled(False)
        self.convert_btn.setFixedWidth(130)
        self.convert_btn.clicked.connect(self._start_conversion)
        btn_row.addWidget(self.convert_btn)

        self.open_btn = QPushButton("Open Output Folder")
        self.open_btn.setObjectName("secondary")
        self.open_btn.setEnabled(False)
        self.open_btn.clicked.connect(self._open_output)
        btn_row.addWidget(self.open_btn)

        root.addLayout(btn_row)

    def _apply_theme(self):
        self.setStyleSheet("""
            QMainWindow, QWidget { background-color: #1e1e2e; color: #cdd6f4; }
            QLabel { color: #cdd6f4; }
            QLabel#subtitle { color: #6c7086; }
            QPushButton {
                background-color: #3B8ED0;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 13px;
                font-family: "SF Pro Display";
            }
            QPushButton:hover { background-color: #2980b9; }
            QPushButton:disabled { background-color: #45475a; color: #6c7086; }
            QPushButton#secondary {
                background-color: transparent;
                border: 1px solid #45475a;
                color: #cdd6f4;
            }
            QPushButton#secondary:hover { border-color: #3B8ED0; color: #3B8ED0; }
            QPushButton#secondary:disabled { color: #45475a; border-color: #313244; }
            QFrame#card {
                background-color: #181825;
                border-radius: 12px;
            }
            QScrollArea { background: transparent; }
            QScrollArea > QWidget > QWidget { background: transparent; }
            QProgressBar {
                background-color: #313244;
                border-radius: 5px;
            }
            QProgressBar::chunk {
                background-color: #3B8ED0;
                border-radius: 5px;
            }
        """)

    def _short_path(self, path: str) -> str:
        home = str(Path.home())
        return path.replace(home, "~")

    def _add_files(self, paths: list[str]):
        added = False
        for path in paths:
            if not path or path in self.queued_files:
                continue
            if not os.path.isfile(path):
                continue
            self.queued_files.append(path)
            row = FileRow(path)
            self.file_rows[path] = row
            self.list_layout.addWidget(row)
            added = True

        if added:
            self.empty_label.hide()
            self.convert_btn.setEnabled(True)

    def _browse_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Select files to convert")
        if paths:
            self._add_files(paths)

    def _choose_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose output folder")
        if folder:
            self.output_folder = folder
            self.output_label.setText(self._short_path(folder))

    def _clear_all(self):
        for row in self.file_rows.values():
            row.deleteLater()
        self.file_rows.clear()
        self.queued_files.clear()
        self.empty_label.show()
        self.convert_btn.setEnabled(False)
        self.open_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_label.setText("")

    def _start_conversion(self):
        if self.converting:
            return
        self.converting = True
        self.convert_btn.setEnabled(False)
        self.convert_btn.setText("Converting…")
        threading.Thread(target=self._convert_all, daemon=True).start()

    def _convert_all(self):
        out_dir = Path(self.output_folder)
        out_dir.mkdir(parents=True, exist_ok=True)
        md = MarkItDown()
        total = len(self.queued_files)
        done = 0

        for i, path in enumerate(self.queued_files):
            try:
                result = md.convert(path)
                out_path = out_dir / (Path(path).stem + ".md")
                out_path.write_text(result.text_content, encoding="utf-8")
                done += 1
                self.signals.file_done.emit(path, True, out_path.name)
            except Exception as e:
                self.signals.file_done.emit(path, False, str(e))

            self.signals.progress.emit(i + 1, total)

        self.signals.finished.emit(done)

    def _on_file_done(self, path: str, success: bool, msg: str):
        row = self.file_rows.get(path)
        if row:
            if success:
                row.set_success(msg)
            else:
                row.set_error(msg)

    def _on_progress(self, done: int, total: int):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(done)
        self.progress_label.setText(f"{done} of {total} converted…")

    def _on_finished(self, done: int):
        self.converting = False
        self.convert_btn.setEnabled(True)
        self.convert_btn.setText("Convert")
        total = len(self.queued_files)
        self.progress_label.setText(f"Done — {done}/{total} file(s) converted successfully")
        if done > 0:
            self.open_btn.setEnabled(True)

    def _open_output(self):
        os.system(f'open "{self.output_folder}"')


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
