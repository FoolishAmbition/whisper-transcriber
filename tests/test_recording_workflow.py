import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QFileDialog, QLineEdit, QMessageBox

from whisper_transcriber.app import Window
from whisper_transcriber.recording_history import PreviousTranscript, Recording, RecordingHistory
from whisper_transcriber.transcription import NotesResult, Segment


class RecordingWorkflowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self):
        scratch = TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.root = Path(scratch.name)
        self.recordings = self.root / "recordings"
        self.transcripts = self.root / "transcripts"
        self.source = self.recordings / "CCNA" / "Voice.m4a"
        self.source.parent.mkdir(parents=True)
        self.source.touch()
        self.history = RecordingHistory(
            self.root / "history.sqlite3", self.recordings, self.transcripts,
        )

    def test_history_recognizes_legacy_export_and_distinguishes_replaced_recording(self):
        recording = Recording.open(self.source)
        legacy = self.transcripts / "CCNA" / "Voice_transcript.txt"
        legacy.parent.mkdir(parents=True)
        legacy.write_text("Legacy transcript", encoding="utf-8")
        self.assertEqual(self.history.lookup(recording).export_path, legacy)
        self.history.record(recording)
        self.history.record(recording, legacy)
        self.history.record(recording)
        self.assertEqual(self.history.lookup(recording), PreviousTranscript(True, legacy))
        self.source.write_bytes(b"different recording")
        self.assertEqual(self.history.lookup(Recording.open(self.source)), PreviousTranscript())

    def test_suggested_name_is_prefilled_and_saved_export_can_be_reopened(self):
        window = Window(self.history)
        self.addCleanup(window.reset_recording, None)
        # Avoid opening the empty audio fixture in Qt's media backend.
        with patch.object(window.player, "setSource"):
            window.set_recording(self.source)
        window.transcription_done(([Segment(0, 2, "Virtual LANs")], "en"))
        self.assertIn("no saved transcript", window.history_label.text())
        window.notes_done(NotesResult("## Overview", "VLANs and Trunks"))

        def accept_prefilled(dialog):
            name = dialog.findChild(QLineEdit, "fileNameEdit").text()
            self.assertEqual(name, "VLANs and Trunks_transcript.txt")
            return 1

        with patch.object(QFileDialog, "exec", accept_prefilled):
            window.export(False)
        target = self.transcripts / "CCNA" / "VLANs and Trunks_transcript.txt"
        self.assertIn("Virtual LANs", target.read_text(encoding="utf-8"))

        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
            window.clear_recording()
        self.assertIsNone(window.recording)
        self.assertTrue(self.source.exists())
        self.assertTrue(target.exists())

        reopened = Window(RecordingHistory(self.history.database, self.recordings, self.transcripts))
        self.addCleanup(reopened.reset_recording, None)
        with patch.object(reopened.player, "setSource"):
            reopened.set_recording(self.source)
        self.assertEqual(reopened.previous.export_path, target)
        with patch("whisper_transcriber.app.QDesktopServices.openUrl", return_value=True) as open_url:
            reopened.open_previous_transcript()
        self.assertEqual(Path(open_url.call_args.args[0].toLocalFile()), target)
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.No):
            reopened.start_transcription()
        self.assertIsNone(reopened.job)


if __name__ == "__main__":
    unittest.main()
