import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Recording:
    path: Path
    size: int
    modified_ns: int

    @classmethod
    def open(cls, path: Path) -> "Recording":
        resolved = path.resolve(strict=True)
        stat = resolved.stat()
        return cls(resolved, stat.st_size, stat.st_mtime_ns)


@dataclass(frozen=True)
class PreviousTranscript:
    completed: bool = False
    export_path: Path | None = None


class RecordingHistory:
    """Store local completion markers and transcript export locations."""

    def __init__(self, database: Path, recordings: Path, transcripts: Path):
        self.database = database
        self.recordings = recordings
        self.transcripts = transcripts

    def export_folder(self, recording: Recording) -> Path:
        if recording.path.is_relative_to(self.recordings):
            return self.transcripts / recording.path.parent.relative_to(self.recordings)
        return self.transcripts

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database)
        try:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS transcripts (
                    path TEXT PRIMARY KEY, size INTEGER NOT NULL,
                    modified_ns INTEGER NOT NULL, export_path TEXT
                )
            """)
        except sqlite3.Error:
            connection.close()
            raise
        return connection

    def lookup(self, recording: Recording) -> PreviousTranscript:
        if self.database.exists():
            with closing(self._connect()) as connection:
                row = connection.execute(
                    "SELECT size, modified_ns, export_path FROM transcripts WHERE path = ?",
                    (str(recording.path),),
                ).fetchone()
            if row is not None:
                if row[:2] != (recording.size, recording.modified_ns):
                    return PreviousTranscript()
                export_path = Path(row[2]) if row[2] else None
                if export_path and export_path.is_file():
                    return PreviousTranscript(True, export_path)
                # A tracked path may have been moved or deleted by the user.
                if export_path:
                    return PreviousTranscript(True)
                return PreviousTranscript(True, self._legacy_export(recording))
        return PreviousTranscript(export_path=self._legacy_export(recording))

    def _legacy_export(self, recording: Recording) -> Path | None:
        if recording.path.is_relative_to(self.recordings):
            expected = self.export_folder(recording) / f"{recording.path.stem}_transcript.txt"
            if expected.is_file():
                return expected
        return None

    def record(self, recording: Recording, export_path: Path | None = None) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute("""
                INSERT INTO transcripts (path, size, modified_ns, export_path)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    export_path = CASE
                        WHEN excluded.export_path IS NOT NULL THEN excluded.export_path
                        WHEN transcripts.size = excluded.size
                             AND transcripts.modified_ns = excluded.modified_ns
                        THEN transcripts.export_path
                    END,
                    size = excluded.size,
                    modified_ns = excluded.modified_ns
            """, (str(recording.path), recording.size, recording.modified_ns,
                  str(export_path.resolve()) if export_path else None))
