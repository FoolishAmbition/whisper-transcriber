# Whisper Transcriber feature backlog

Prioritize changes that make two-hour recordings easier to finish, review, and use for study. All items below are proposals. The [PRD](PRD.md) contains the current product requirements.

## Next release

| Feature | User benefit | Done when |
| --- | --- | --- |
| Save and reopen transcript drafts | Keep corrections after closing the app or if notes generation fails. | The app restores the last saved transcript and its edits for the same recording, with an option to discard the local draft. Drafts stay out of Git. |
| Search transcript and add playback controls | Find a term like OSPF and replay the relevant part without scrolling through hours of text. | Search jumps between matches. A seek bar and playback speed control work alongside existing timestamp clicks. |
| Copy transcript for ChatGPT | Go from a reviewed transcript to the existing manual notes workflow with fewer clicks. | A button copies the reviewed text with timestamps. The user can choose the entire transcript or selected segments. |
| Benchmark CCNA accuracy and two-hour performance | Know which local settings are worth using on the RTX 5070. | Compare the CPU baseline with GPU model and glossary settings on the same manually checked excerpts. Record technical-term errors, overall word error rate, and runtime. Run a representative two-hour recording to measure turnaround and peak memory. |

## After that

| Feature | User benefit | Done when |
| --- | --- | --- |
| Local recording library | Find past recordings by title or course without opening each audio file first. | Search recent recordings and open their source, draft, or last export. Missing files have a clear state. |
| Batch queue with duplicate detection | Drop in several recordings and process them while away. | Each row shows progress and outcome. Existing transcripts are flagged, and a failed input leaves the rest of the queue runnable. |
| Resume interrupted transcription | Recover useful progress when a long job stops. | A checkpoint records completed audio ranges. Resuming the same recording avoids missing or duplicated segments at the boundary. |
| Corrections and glossary suggestions | Reuse fixes to technical terms and names across a course. | The app can propose an edited term for the active glossary. A user approves it before it is saved. |
| More export formats | Use one transcript for reading, subtitles, or downstream tools. | Offer clean TXT without timestamps, SRT subtitles, and structured JSON while retaining the current timestamped TXT. |
| Bookmarks and highlights | Mark definitions, exam tips, or decisions during review. | A bookmark jumps to its audio timestamp and can be included in an export. |

## Later and nice to have

| Feature | User benefit | Done when |
| --- | --- | --- |
| Speaker labels | Follow who said what in meetings and interviews. | Start with manually editable speaker labels. Evaluate automatic labeling after the accuracy benchmark, and keep unknown speakers editable. |
| Study presets | Generate notes in the form that fits a course or exam. | The user can choose a glossary, study guide, or flashcard format. Generated claims retain source timestamps where available. |
| Windows installer and diagnostics | Make setup easier on another PC and clarify GPU or Ollama problems. | An installer creates shortcuts. Diagnostics report missing model files or GPU dependencies while keeping CPU transcription available. |
| Optional cloud retry and comparison | Get a second pass when the local transcript misses too much. | The user explicitly approves any upload, can compare both versions, and keeps the local transcript and edits. |

The first milestone is **save and reopen transcript drafts**. It protects editing work immediately and gives the recording library a reliable draft to reopen. Transcript search and the ChatGPT copy action can follow independently. The CCNA benchmark can run alongside those changes and guide later accuracy work.

## Live Zoom transcription milestone

With Whisper Transcriber running, opening Zoom prompts you to transcribe the meeting. After you accept, you see live captions from the call. When you leave the meeting or close Zoom, the app finishes the last bit of audio, saves a timestamped TXT from the moment capture began, and offers to generate notes with your local Ollama model.

Start with the Windows Zoom desktop client. Windows supports capturing audio output from an individual process and its child processes. Test whether this isolates Zoom's meeting audio on the target PC. Test meeting-end detection separately because Zoom can stay open after you leave a call. [Microsoft's process loopback sample](https://learn.microsoft.com/en-us/samples/microsoft/windows-classic-samples/applicationloopbackaudio-sample/)

| Step | Scope | Done when |
| --- | --- | --- |
| 1. Prove Zoom audio capture | Test a short permitted call with manual start and stop. Capture audio played by Zoom. | The teacher's voice comes through with headphones connected, and unrelated app audio stays out of the capture. Document any limits before choosing the capture approach. |
| 2. Show live captions | Stream local Whisper results into a live subtitle view. Add font family, size, and contrast settings with a preview. | Captions update during the call, the app stays responsive, and caption settings persist. Measure delay and check that consecutive audio chunks avoid repeated or missing words at boundaries. |
| 3. Save the full session and offer notes | Finalize the last chunk on **Stop and save**, then promptly write a uniquely named timestamped TXT. Show its location and offer **Generate notes with Ollama** or **Skip**. | The TXT covers the session from the approved start through stop, including the final words. A skipped or failed notes job leaves the TXT available. Notes use the selected local model. |
| 4. Prompt on Zoom launch and detect when the call ends | Offer **Start transcription** or **Skip** when Zoom opens while the app is watching. Show an active capture indicator. Finalize on a verified leave or Zoom exit and retain **Stop and save** for ambiguous cases. | Test leaving with Zoom still open, closing Zoom, waiting rooms, brief disconnections, and long silences. Capture starts only after approval, and silence alone never ends a session. |
| 5. Design a cute 16-bit interface | Mock up a retro pixel-art style with a small waveform mascot, soft colors, and clear waiting, live, and saved states. Keep controls and captions easy to read. | Review the mockup before styling the app. Confirm that caption readability, contrast, and keyboard navigation work with the theme. |

**Approval gate.** Each step needs its own approval before implementation. Review the result of one step before starting the next. The backlog entry is planning only.
