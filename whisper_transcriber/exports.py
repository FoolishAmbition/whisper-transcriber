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
NOTES = ExportFormat("notes", "_notes", "md", "Markdown (*.md)")
