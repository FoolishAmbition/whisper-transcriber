# Whisper Transcriber

Windows desktop app that uses faster-whisper to turn recordings into editable, timestamped transcripts. Review the audio in the app, export a TXT file, and share it manually with ChatGPT when you want study notes, flashcards, or a meeting summary.

Double-click **Start Transcription.cmd** after following the [setup guide](Context/README.md). Ollama is optional for generating notes inside the app.

Keep recordings in `recordings/` and exports in `transcripts/`. Git ignores both directories. See the [product requirements](Context/PRD.md) for the planned workflow.

The app code lives in `whisper_transcriber/`, the original transcription script in `scripts/`, and regression tests in `tests/`.
