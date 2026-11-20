import json
import sqlite3
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QFormLayout, QHBoxLayout, QInputDialog,
    QLabel, QLineEdit, QMainWindow, QMessageBox, QPlainTextEdit, QProgressBar,
    QPushButton, QSplitter, QTabWidget, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget, QHeaderView,
)

from exports import NOTES, TRANSCRIPT, save_text
from jobs import Job
from recording_history import PreviousTranscript, Recording, RecordingHistory
from transcription import EXTENSIONS, Segment, generate_notes_with_title
from transcription import suggest_export_title, timestamp
from transcription import transcribe, transcript_text


ROOT = Path(__file__).resolve().parent
GLOSSARIES = ROOT / "glossaries.local.json"
DROP_HINT = "Drop an M4A, MP3, WAV, or MP4 recording"


def choices(*items):
    combo = QComboBox()
    combo.addItems(items)
    return combo


def button(label, callback):
    control = QPushButton(label)
    control.clicked.connect(callback)
    return control


class Window(QMainWindow):
    def __init__(self, history: RecordingHistory | None = None):
        super().__init__()
        self.setWindowTitle("Transcription & Notes")
        self.resize(1150, 760)
        self.setAcceptDrops(True)
        self.history = history or RecordingHistory(
            ROOT / "recording-history.local.sqlite3", ROOT / "recordings", ROOT / "transcripts",
        )
        self.recording: Recording | None = None
        self.previous = PreviousTranscript()
        self.segments = []
        self.job = None
        self.suggested_title = ""
        self.glossaries = {}
        self.audio = QAudioOutput(self)
        self.player = QMediaPlayer(self)
        self.player.setAudioOutput(self.audio)
        self.player.errorOccurred.connect(lambda _error, message: self.statusBar().showMessage(message))
        self.player.positionChanged.connect(self.show_position)

        self.file_name = QLabel(DROP_HINT)
        self.file_name.setTextFormat(Qt.TextFormat.PlainText)
        self.open_button = button("Open recording…", self.open_recording)
        self.clear_button = button("Clear recording", self.clear_recording)
        self.clear_button.setToolTip("Remove the selection and leave the file on disk")
        self.play_button = button("Play / pause", self.toggle_playback)
        self.position = QLabel("00:00:00")
        header = QHBoxLayout()
        header.addWidget(self.file_name, 1)
        header.addWidget(self.position)
        header.addWidget(self.play_button)
        header.addWidget(self.open_button)
        header.addWidget(self.clear_button)
        self.history_label = QLabel()
        self.history_label.setTextFormat(Qt.TextFormat.PlainText)
        self.history_label.setWordWrap(True)
        self.open_previous = button("Open previous transcript", self.open_previous_transcript)
        history_row = QHBoxLayout()
        history_row.addWidget(self.history_label, 1)
        history_row.addWidget(self.open_previous)

        self.model = choices("small", "medium", "turbo", "large-v3")
        self.device = choices("CPU", "NVIDIA GPU")
        self.language = QLineEdit()
        self.language.setPlaceholderText("Auto · enter en to force English")
        self.profile = choices("Per recording")
        self.profile.currentTextChanged.connect(self.load_glossary)
        self.terms = QPlainTextEdit()
        self.terms.setAcceptDrops(False)
        self.terms.setPlaceholderText("Terms and names, separated by commas or lines")
        self.terms.setMaximumHeight(100)
        self.save_profile_button = button("Save glossary…", self.save_glossary)
        self.kind = choices("Study notes", "Meeting summary")
        self.detail = choices("Concise", "Detailed")
        self.notes_model = QLineEdit("qwen2.5:7b")
        self.start_button = button("Transcribe locally", self.start_transcription)
        self.notes_button = button("Generate local notes", self.start_notes)
        self.cancel_button = button("Cancel job", self.cancel_job)
        settings = QWidget()
        form = QFormLayout(settings)
        form.addRow("Whisper model", self.model)
        form.addRow("Run on", self.device)
        form.addRow("Language code", self.language)
        form.addRow("Glossary", self.profile)
        form.addRow(self.terms)
        form.addRow(self.save_profile_button)
        form.addRow(self.start_button)
        form.addRow("Notes type", self.kind)
        form.addRow("Detail", self.detail)
        form.addRow("Ollama model", self.notes_model)
        form.addRow(self.notes_button)
        form.addRow(self.cancel_button)

        self.table = QTableWidget(0, 2)
        self.table.setAcceptDrops(False)
        self.table.viewport().setAcceptDrops(False)
        self.table.setHorizontalHeaderLabels(["Play from", "Transcript"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().hide()
        self.table.cellClicked.connect(self.seek_segment)
        self.notes = QPlainTextEdit()
        self.notes.setAcceptDrops(False)
        self.notes.setPlaceholderText("Generated notes appear here and can be edited before export.")
        self.notes.textChanged.connect(self.refresh)
        self.tabs = QTabWidget()
        self.tabs.addTab(self.table, "Transcript")
        self.tabs.addTab(self.notes, "Notes")
        splitter = QSplitter()
        splitter.addWidget(settings)
        splitter.addWidget(self.tabs)
        splitter.setSizes([335, 815])
        splitter.setStretchFactor(1, 1)
        self.export_transcript = button("Export transcript…", lambda: self.export(False))
        self.export_notes = button("Export notes…", lambda: self.export(True))
        self.export_title = QLineEdit()
        self.export_title.setPlaceholderText("Title suggested after generating notes")
        self.export_title.setClearButtonEnabled(True)
        self.export_title.setAccessibleName("Export title")
        self.title_button = button("Suggest title", self.start_title)
        self.progress = QProgressBar()
        self.progress.hide()
        footer = QHBoxLayout()
        footer.addWidget(self.progress, 1)
        footer.addStretch()
        footer.addWidget(self.export_transcript)
        footer.addWidget(self.export_notes)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(18, 18, 18, 12)
        layout.addLayout(header)
        layout.addLayout(history_row)
        layout.addWidget(splitter, 1)
        title_row = QHBoxLayout()
        title_row.addWidget(QLabel("Export title"))
        title_row.addWidget(self.export_title, 1)
        title_row.addWidget(self.title_button)
        layout.addLayout(title_row)
        layout.addLayout(footer)
        self.setCentralWidget(central)
        self.statusBar().showMessage("Local transcription")
        self.read_glossaries()
        self.refresh()

    def refresh(self):
        busy = self.job is not None
        has_recording = self.recording is not None
        self.open_button.setEnabled(not busy)
        self.clear_button.setEnabled(has_recording and not busy)
        self.start_button.setEnabled(has_recording and not busy)
        self.play_button.setEnabled(has_recording)
        self.notes_button.setEnabled(bool(self.segments) and not busy)
        self.cancel_button.setEnabled(busy and not self.job.isInterruptionRequested())
        self.export_transcript.setEnabled(bool(self.segments) and not busy)
        self.export_notes.setEnabled(bool(self.notes.toPlainText().strip()) and not busy)
        self.table.setEnabled(not busy)
        self.notes.setReadOnly(busy)
        self.export_title.setEnabled(has_recording and not busy)
        self.title_button.setEnabled(bool(self.segments) and not busy)
        self.open_previous.setEnabled(not busy)

    def read_glossaries(self):
        try:
            if GLOSSARIES.exists():
                data = json.loads(GLOSSARIES.read_text(encoding="utf-8"))
                if not isinstance(data, dict) or any(not isinstance(v, str) for v in data.values()):
                    raise ValueError("Expected glossary names and text.")
                self.glossaries = data
        except (OSError, ValueError) as error:
            self.statusBar().showMessage(f"Cannot read saved glossaries · {error}")
        self.profile.addItems(sorted(self.glossaries, key=str.casefold))

    def load_glossary(self, name):
        self.terms.setPlainText(self.glossaries.get(name, ""))

    def save_glossary(self):
        initial = self.profile.currentText() if self.profile.currentIndex() else ""
        name, accepted = QInputDialog.getText(self, "Save glossary", "Course or project", text=initial)
        name = name.strip()
        if not accepted or not name or name == "Per recording":
            return
        updated = {**self.glossaries, name: self.terms.toPlainText().strip()}
        try:
            save_text(GLOSSARIES, json.dumps(updated, ensure_ascii=False, indent=2), replace=True)
        except OSError as error:
            QMessageBox.warning(self, "Could not save glossary", str(error))
            return
        if name not in self.glossaries:
            self.profile.addItem(name)
        self.glossaries = updated
        self.profile.setCurrentText(name)
        self.statusBar().showMessage(f"Saved glossary · {name}")

    def dragEnterEvent(self, event):
        if self.dropped_path(event) is not None and self.job is None:
            event.acceptProposedAction()

    def dropEvent(self, event):
        path = self.dropped_path(event)
        if path is not None and self.job is None:
            event.acceptProposedAction()
            self.set_recording(path)

    @staticmethod
    def dropped_path(event):
        urls = event.mimeData().urls()
        if len(urls) == 1 and urls[0].isLocalFile():
            path = Path(urls[0].toLocalFile())
            if path.suffix.lower() in EXTENSIONS:
                return path
        return None

    def open_recording(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Open a recording", str(ROOT / "recordings"),
            "Recordings (*.m4a *.mp3 *.wav *.mp4)",
        )
        if filename:
            self.set_recording(Path(filename))

    def confirm_discard(self):
        if not self.segments and not self.notes.toPlainText().strip():
            return True
        return QMessageBox.question(
            self, "Leave current recording?",
            "Only exported files are kept. Leave the current recording?",
        ) == QMessageBox.StandardButton.Yes

    def set_recording(self, path):
        if not path.is_file() or path.suffix.lower() not in EXTENSIONS:
            QMessageBox.warning(self, "Unsupported recording", "Choose an M4A, MP3, WAV, or MP4 file.")
            return
        try:
            recording = Recording.open(path)
        except OSError as error:
            QMessageBox.warning(self, "Could not open recording", str(error))
            return
        if recording == self.recording or not self.confirm_discard():
            return
        self.reset_recording(recording)
        if path.parent.name in self.glossaries:
            self.profile.setCurrentText(path.parent.name)
        self.language.setFocus()
        self.statusBar().showMessage("Ready to transcribe locally")

    def clear_recording(self):
        if self.confirm_discard():
            self.reset_recording(None)
            self.statusBar().showMessage("Recording cleared")

    def reset_recording(self, recording: Recording | None):
        self.recording = recording
        path = recording.path if recording else None
        self.suggested_title = ""
        self.export_title.clear()
        self.export_title.setPlaceholderText(path.stem if path else "Title suggested after generating notes")
        self.file_name.setText(path.name if path else DROP_HINT)
        self.file_name.setToolTip(str(path) if path else "")
        self.player.stop()
        self.player.setSource(QUrl.fromLocalFile(str(path)) if path else QUrl())
        self.show_position(0)
        self.set_transcript([])
        self.notes.clear()
        self.tabs.setCurrentWidget(self.table)
        self.update_history()

    def update_history(self):
        self.previous = PreviousTranscript()
        message = ""
        if self.recording:
            try:
                self.previous = self.history.lookup(self.recording)
            except (OSError, sqlite3.Error) as error:
                message = f"Could not read local transcript history · {error}"
            if self.previous.export_path:
                message = f"Previously transcribed · {self.previous.export_path.name}"
            elif self.previous.completed:
                message = "Previously transcribed · no saved transcript found"
        self.history_label.setText(message)
        self.history_label.setVisible(bool(message))
        self.open_previous.setVisible(self.previous.export_path is not None)

    def record_completion(self, export_path: Path | None = None):
        try:
            self.history.record(self.recording, export_path)
        except (OSError, sqlite3.Error) as error:
            self.history_label.setText(f"Could not save local transcript history · {error}")
            self.history_label.show()
        else:
            self.update_history()

    def open_previous_transcript(self):
        path = self.previous.export_path
        if path and path.is_file() and QDesktopServices.openUrl(QUrl.fromLocalFile(str(path))):
            return
        self.update_history()
        QMessageBox.warning(self, "Could not open transcript", "The saved transcript could not be opened.")

    def show_position(self, milliseconds):
        self.position.setText(timestamp(milliseconds / 1000))

    def toggle_playback(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def seek_segment(self, row, column):
        if column == 0:
            self.player.setPosition(int(1000 * self.segments[row].start))
            self.player.play()

    def set_transcript(self, segments):
        self.segments = segments
        self.table.clearContents()
        self.table.setRowCount(len(segments))
        for row, segment in enumerate(segments):
            start = QTableWidgetItem(timestamp(segment.start))
            start.setFlags(start.flags() & ~Qt.ItemFlag.ItemIsEditable)
            start.setToolTip("Click to play from this point")
            self.table.setItem(row, 0, start)
            self.table.setItem(row, 1, QTableWidgetItem(segment.text))
        self.refresh()

    def edited_segments(self):
        return [
            Segment(segment.start, segment.end, self.table.item(row, 1).text())
            for row, segment in enumerate(self.segments)
            if self.table.item(row, 1).text().strip()
        ]

    def start_transcription(self):
        self.update_history()
        if self.segments or self.previous.completed or self.previous.export_path:
            message = (
                "A successful run will replace the transcript in this window. Export edits first if needed."
                if self.segments else "This recording has been transcribed before. Run transcription again?"
            )
            if QMessageBox.question(self, "Transcribe again?", message,
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                    QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
                return
        path = self.recording.path
        model = self.model.currentText()
        device = "cuda" if self.device.currentIndex() else "cpu"
        language = self.language.text().strip().lower() or None
        glossary = ", ".join(line.strip() for line in self.terms.toPlainText().splitlines() if line.strip())
        self.start_job(
            lambda progress, cancel: transcribe(path, model, device, language, glossary, progress, cancel),
            self.transcription_done,
        )

    def transcription_done(self, result):
        segments, language = result
        if not segments:
            self.statusBar().showMessage("No speech was detected")
            return
        self.set_transcript(segments)
        self.record_completion()
        self.tabs.setCurrentWidget(self.table)
        self.statusBar().showMessage(f"Transcript ready · {len(segments)} segments · {language}")

    def start_notes(self):
        segments = self.edited_segments()
        if not segments:
            self.statusBar().showMessage("Add transcript text before generating notes")
            return
        if self.notes.toPlainText().strip() and QMessageBox.question(
            self, "Regenerate notes?", "A successful run will replace the notes in this window.",
        ) != QMessageBox.StandardButton.Yes:
            return
        kind, detail, model = self.kind.currentText(), self.detail.currentText(), self.notes_model.text().strip()
        self.start_job(
            lambda progress, cancel: generate_notes_with_title(segments, kind, detail, model, progress, cancel),
            self.notes_done,
        )

    def notes_done(self, result):
        self.notes.setPlainText(result.text)
        if result.title and self.export_title.text() in ("", self.suggested_title):
            self.set_suggested_title(result.title)
        self.tabs.setCurrentWidget(self.notes)
        self.title_button.setToolTip(result.title_error)
        message = "Notes ready" if result.title else "Notes ready · title unavailable; enter one or retry"
        self.statusBar().showMessage(message)

    def start_title(self):
        source = self.notes.toPlainText().strip() or transcript_text(self.edited_segments())
        if not source:
            self.statusBar().showMessage("Add transcript text before suggesting a title")
            return
        model = self.notes_model.text().strip()
        self.start_job(lambda _, cancel: suggest_export_title(source, model, cancel), self.title_done)

    def title_done(self, title):
        self.title_button.setToolTip("")
        if title:
            self.set_suggested_title(title)
            self.statusBar().showMessage(f"Export title · {title}")
        else:
            self.statusBar().showMessage("No usable title returned · enter a title or retry")

    def set_suggested_title(self, title):
        self.export_title.setText(title)
        self.suggested_title = title

    def start_job(self, operation, on_result):
        self.job = Job(operation, self)
        self.job.progress.connect(self.job_progress)
        self.job.result.connect(on_result)
        self.job.failed.connect(self.job_failed)
        self.job.cancelled.connect(lambda: self.statusBar().showMessage("Job cancelled"))
        self.job.finished.connect(self.job_finished)
        self.job_progress(None, "Starting…")
        self.refresh()
        self.job.start()

    def job_progress(self, percent, message):
        if self.job.isInterruptionRequested():
            return
        self.progress.setRange(0, 0 if percent is None else 100)
        if percent is not None:
            self.progress.setValue(percent)
        self.progress.show()
        self.statusBar().showMessage(message)

    def cancel_job(self):
        self.job.requestInterruption()
        self.statusBar().showMessage("Cancelling when the current processing step ends…")
        self.refresh()

    def job_failed(self, message):
        self.statusBar().showMessage("Job failed")
        if "cublas" in message.lower() or "cudnn" in message.lower():
            message += "\n\nTry CPU mode or see the NVIDIA setup in README.md."
        QMessageBox.warning(self, "Job failed", message)

    def job_finished(self):
        self.job.deleteLater()
        self.job = None
        self.progress.hide()
        self.refresh()

    def export(self, notes):
        export_format = NOTES if notes else TRANSCRIPT
        content = self.notes.toPlainText().strip() + "\n" if notes else transcript_text(self.edited_segments())
        destination = self.history.export_folder(self.recording)
        suggested = export_format.default_path(destination, self.export_title.text(), self.recording.path)
        try:
            destination.mkdir(parents=True, exist_ok=True)
            dialog = QFileDialog(self)
            # Explicitly fill the filename field instead of relying on the native dialog's initial path.
            dialog.setOption(QFileDialog.Option.DontUseNativeDialog)
            dialog.setOption(QFileDialog.Option.DontConfirmOverwrite)
            dialog.setWindowTitle(f"Export {export_format.label}")
            dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
            dialog.setNameFilter(export_format.file_filter)
            dialog.setDefaultSuffix(export_format.extension)
            dialog.setDirectory(str(destination))
            dialog.selectFile(suggested.name)
            if not dialog.exec():
                return
            target = Path(dialog.selectedFiles()[0])
            if target.suffix.lower() != f".{export_format.extension}":
                QMessageBox.warning(self, "Invalid export filename",
                                    f"Use a .{export_format.extension} extension for this export.")
                return
            try:
                save_text(target, content)
            except FileExistsError:
                if QMessageBox.question(self, "Replace export?", f"Replace {target.name}?") != QMessageBox.StandardButton.Yes:
                    return
                save_text(target, content, replace=True)
        except OSError as error:
            QMessageBox.warning(self, "Could not export", str(error))
            return
        if not notes:
            self.record_completion(target)
        self.statusBar().showMessage(f"Exported · {target}")

    def closeEvent(self, event):
        if self.job is not None:
            self.cancel_job()
            event.ignore()
        elif not self.confirm_discard():
            event.ignore()
        else:
            event.accept()


def main():
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(str(ROOT / "assets" / "whisper-transcriber.ico")))
    app.setStyle("Fusion")
    app.setStyleSheet("""
        QMainWindow, QWidget { font-family: "Segoe UI"; font-size: 10pt; }
        QPushButton { padding: 6px 12px; }
        QHeaderView::section { padding: 7px; }
        QStatusBar { padding-left: 12px; }
    """)
    window = Window()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
