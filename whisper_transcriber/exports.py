import os
import re
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile


def filename_stem(title: str) -> str:
    title = re.sub(r'[<>:"/\\|?*\x00-\x1f]', " ", title)
    title = " ".join(title.split()).strip(" .")
    return title[:100].rstrip(" .")


def save_text(path: Path, content: str, *, replace: bool = False) -> None:
    """Publish a complete UTF-8 file and replace an existing one only on request."""
    temp_path = None
    try:
        with NamedTemporaryFile(dir=path.parent, delete=False, mode="w",
                                encoding="utf-8", newline="\n") as temp:
            temp_path = Path(temp.name)
            temp.write(content)
        if replace:
            os.replace(temp_path, path)
        elif os.name == "nt":
            os.rename(temp_path, path)
        else:
            # On POSIX, rename would silently overwrite the destination.
            os.link(temp_path, path)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


@dataclass(frozen=True)
class ExportFormat:
    label: str
    suffix: str
    extension: str
    file_filter: str

    def default_path(self, folder: Path, title: str, recording: Path) -> Path:
        stem = filename_stem(title) or recording.stem
        return folder / f"{stem}{self.suffix}.{self.extension}"


TRANSCRIPT = ExportFormat("transcript", "_transcript", "txt", "Text (*.txt)")
SUBTITLES = ExportFormat("subtitles", "", "srt", "SubRip subtitles (*.srt)")
NOTES = ExportFormat("notes", "_notes", "md", "Markdown (*.md)")


def _srt_timestamp(milliseconds: int) -> str:
    seconds, millis = divmod(milliseconds, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def srt_text(segments) -> str:
    cues = []
    for segment in segments:
        # Blank lines separate SRT cues, including when a transcript edit spans lines.
        lines = [line.strip() for line in segment.text.splitlines() if line.strip()]
        if not lines:
            continue
        start = max(0, round(segment.start * 1000))
        end = max(start + 1, round(segment.end * 1000))
        timing = f"{_srt_timestamp(start)} --> {_srt_timestamp(end)}"
        cues.append("\n".join([str(len(cues) + 1), timing, *lines]))
    return "\n\n".join(cues) + "\n" if cues else ""
