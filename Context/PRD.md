# Windows Transcription and Notes

**Status** Draft for review

The current workflow is to export timestamped TXT and share it with ChatGPT manually as needed. In-app notes generation through Ollama is optional.

## Goal

Build a drag-and-drop Windows app that turns course recordings, Zoom meetings, and interviews into editable, timestamped transcripts and useful notes. Prioritize accurate technical vocabulary and accented speech. The current baseline is faster-whisper `small` on CPU with `int8` and English forced.

## First-release workflow

1. Drop in one recording or choose it with a file picker.
2. Select study notes or a meeting summary and choose **Concise** or **Detailed** for this recording. Optionally enter course terms, acronyms, or names.
3. Start local transcription and see progress. Allow cancellation and show a clear error when a file cannot be decoded.
4. Review the transcript, click a timestamp to replay its audio, and edit text without changing its timestamp.
5. Generate notes from the reviewed text and export both files separately.

## Requirements

| Area | Requirement |
| --- | --- |
| Windows app | Accept M4A, MP3, WAV, and MP4, including downloaded Zoom recordings. The workflow works without PowerShell or edits to Python. |
| Transcription | Start with faster-whisper. Offer automatic language detection and a manual override. Show the selected processing mode before starting. |
| Vocabulary | Accept an optional glossary. Prioritize technical terms and names in the accuracy review. Test settings with and without the glossary to check whether it improves real terms or adds words that were never spoken. |
| Glossary reuse | Save named glossaries by course or project, with a per-recording option for one-off terms. |
| Transcript review | Show editable segments with click-to-play timestamps. Keep segment timings when text changes. |
| Study notes | Provide an overview, key concepts, and review questions. Link factual takeaways to transcript timestamps where possible. |
| Meeting summaries | Capture decisions, action items, and open questions. Mark owners and deadlines as unspecified when the recording does not state them. |
| Notes detail | Let the user choose per recording. Concise notes focus on essentials. Detailed study notes expand concepts and examples. Detailed meeting notes add discussion context and rationale when stated. |
| Export and recovery | Export timestamped TXT and Markdown notes. Protect existing exports from accidental overwrite. Preserve completed transcripts and let the user retry notes independently. |
| Session storage | Keep transcript and note edits in the current session. The user retains them through exports. |
| Offline processing | After initial model setup, produce transcripts and notes with the network disconnected. Confirm local notes performance on the target PC. |

## Optional cloud transcription

Add cloud transcription after validating the local workflow. Offer it as a manual retry when a local transcript needs improvement. Before upload, show the provider and the data to be sent and ask for explicit confirmation. Preserve the local transcript and any edits while the user reviews the cloud result. A local error never triggers an automatic upload. Use Zoom transcripts as an accuracy comparison when available for the same recording.

## Target hardware and recording length

The target Windows PC has 32 GB RAM and a GeForce RTX 5070. A typical recording lasts about two hours. Verify GPU compatibility on this PC and benchmark local GPU settings against the current CPU baseline. Measure end-to-end transcription time, notes generation time, and peak RAM and GPU memory. Use the results to set a turnaround target. Include a CPU path when GPU processing is unavailable.

## Release criteria

- **Transcription accuracy.** Manually transcribe excerpts from a technical lecture, a meeting with speaker changes, and a recording with accented speech. On this reference set, the first-release settings should make fewer technical-term and name errors than the current baseline while keeping overall word error rate at or below baseline. Record runtime on the same machine.
- **CCNA first.** Start accuracy tuning with CCNA excerpts that contain acronyms and names. Compare the same audio with and without a CCNA glossary before extending the benchmark to meetings and other courses.
- **Notes fidelity.** Sample key takeaways against the source audio or transcript. Verify that meeting notes contain zero invented decisions, owners, and deadlines in the release set.
- **End-to-end use.** Drop in a supported recording, review a segment, generate notes, and export both files through the Windows app. Confirm that cancelled and failed jobs preserve prior exports.
- **Offline use.** Disconnect networking after model setup and complete both transcript and notes generation.
- **Long recordings.** Complete a representative two-hour job on the target PC. Verify playback near the end and check that detailed notes include relevant material from the final portion.

## Scope and decisions to validate

- The first-release scope assumes one recording at a time. Revisit automatic speaker labels once the transcription accuracy criteria are met. Batch queues and direct Zoom account integration are later candidates.
- The local notes model, cloud provider, and turnaround targets remain open.

## Workspace layout

- `transcribe.py` is the current transcription script and accuracy baseline.
- `recordings/` holds source audio in `CAPM/`, `CCNA/`, `WSQ/`, and `Unsorted/`.
- `transcripts/` holds existing text exports in matching course folders.
- `venv/` holds the local Python environment.
- The recordings, transcripts, and virtual environment are ignored by Git.
