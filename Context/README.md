# Transcription & Notes

Windows desktop app for local transcription, timestamp review, and notes. See [PRD.md](PRD.md) for product scope and release criteria.

## Setup

Use Python 3.12. From the project folder, create the virtual environment if it does not already exist, then install dependencies.

```powershell
py -3.12 -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

Double-click **Start Transcription.cmd**. Drop one M4A, MP3, WAV, or MP4 file into the window. Select a Whisper model, add optional terms or names, and start transcription. The first use of a Whisper model may download its weights. Start with `small` on CPU to verify basic setup. For NVIDIA inference and runtime requirements, see [faster-whisper setup](https://github.com/SYSTRAN/faster-whisper#requirements).

On this PC, Whisper ran on the RTX 5070 using the CUDA 12 libraries bundled with the installed Ollama. The launcher adds that folder to its own PATH when present. If your CUDA 12 libraries are elsewhere, set `WHISPER_CUDA_DLL_DIR` to their directory before launching or use CPU mode.

Click a timestamp to play from that position. Double-click transcript text to edit it and press Enter to commit the edit. Save glossary terms under a course or project name to reuse them. Transcript edits and notes stay in the open window until exported.

## Notes in ChatGPT

Export a timestamped TXT transcript and share it manually with ChatGPT when you want study notes or a meeting summary. Transcription, playback, editing, and TXT export work without Ollama. Git ignores recordings, exports, and saved glossaries.

## Subtitles for PotPlayer

The **Spoken language** dropdown defaults to **English (EN)**. Select another spoken language or **Auto-detect** when needed.

**Export transcript** defaults to **SRT subtitles (.srt)**. It suggests saving beside the source video with the same base name, such as `lecture.mp4` and `lecture.srt`. Open the video in PotPlayer, or drag the SRT onto the video if it does not load. Cues use Whisper's segment start and end times in milliseconds and include your edits. Choose **Timestamped text (.txt)** in the **Format** dropdown for the existing text export.

## Optional local notes with Ollama

Start Ollama and install a local model, for example `ollama pull qwen2.5:7b`. Model setup needs internet access. In the app, choose **Study notes** or **Meeting summary**, select the detail level, and generate notes. The app sends transcript text to Ollama on this computer at `127.0.0.1:11434`. Longer files are processed in chronological sections. Check generated details and timestamp references against the transcript.

To disable cloud models in Ollama itself, set `OLLAMA_NO_CLOUD=1` for the Ollama server and restart it. See [Ollama's local-only configuration](https://docs.ollama.com/faq#how-do-i-disable-ollamas-cloud-features).

Generate notes to get a suggested export title, or use **Suggest title** to get one from the transcript without generating notes. Edit **Export title** to use your own wording for TXT and Markdown. If the field is blank, the app uses the recording name. The app asks before replacing an existing file.

When you reopen a recording, the app shows if it was transcribed before. **Open previous transcript** opens the last TXT or SRT export when the file is available. Older TXT exports are recognized by their original filename in the corresponding workspace folder. **Clear recording** closes the selection and leaves the recording and exports on disk. The history database stays local and is ignored by Git.

## Code layout

- `whisper_transcriber/` contains the desktop UI, transcription and notes, background jobs, history, and exports. The launcher runs `python -m whisper_transcriber`.
- `scripts/transcribe.py` is the original single-file baseline. From the project root, run it with `.\venv\Scripts\python.exe scripts\transcribe.py`.
- `tests/` contains workflow regression tests. Run them from the project root with `.\venv\Scripts\python.exe -m unittest discover -s tests`.
- `assets/` holds the Windows app icon used by the launcher shortcut.
- `recordings/` holds source audio and `transcripts/` holds exports. Both are ignored by Git, along with saved local glossaries and history.

Cloud transcription and speaker labeling are planned separately. The starting accuracy comparison uses CCNA excerpts. A complete two-hour performance and accuracy evaluation is part of release validation.
