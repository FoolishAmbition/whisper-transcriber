from pathlib import Path

from faster_whisper import WhisperModel

# Load the model
print("Loading model... please wait")
model = WhisperModel("small", device="cpu", compute_type="int8")

# Your audio file
project_dir = Path(__file__).resolve().parent
audio_file = project_dir / "recordings" / "WSQ" / "day1wsq.m4a"

print(f"Transcribing: {audio_file} ...")
segments, info = model.transcribe(str(audio_file), language="en")

# Create transcript with timestamps
full_transcript = ""
for segment in segments:
    # Format time as 00:00:00
    start = segment.start
    hours = int(start // 3600)
    minutes = int((start % 3600) // 60)
    seconds = int(start % 60)
    timestamp = f"[{hours:02d}:{minutes:02d}:{seconds:02d}]"

    full_transcript += f"{timestamp} {segment.text.strip()}\n"

# Save to text file
recording_group = audio_file.parent.relative_to(project_dir / "recordings")
output_dir = project_dir / "transcripts" / recording_group
output_dir.mkdir(parents=True, exist_ok=True)
output_file = output_dir / f"{audio_file.stem}_transcript.txt"
with open(output_file, "w", encoding="utf-8") as f:
    f.write(full_transcript)

print("\n===== DONE =====")
print(f"Transcript with timestamps saved as: {output_file}")
