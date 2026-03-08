# Frontend

React web application for the Strategic Intelligence Platform. React Native iOS app in a later phase.

## Stack

- **React** — web client
- **React Native** — iOS (future phase)

## Core Responsibilities

- **Module UI** — guided flows for each strategy module (portfolio strategy, vendor management, etc.). Each module walks the user through structured context-gathering and presents scored/ranked outputs.
- **Voice capture** — mic input from browser, streamed to the backend for Whisper transcription. The voice interface is the primary input method — the UI should treat it as first-class, not bolted on.
- **Session management** — users can pause and resume strategy sessions. The backend handles state durability via LangGraph checkpointing; the frontend needs to handle re-entry gracefully (showing where the user left off, what context has been gathered so far).
- **Collaboration** — tap other org members to weigh in on specific questions. File/document upload for additional context.
- **Visualizations** — initiative scoring (e.g., "activity rings" that fill as context is gathered across Value, Feasibility, Scalability dimensions), portfolio ranking views, and cross-module context indicators.

## Key Considerations

- **Enterprise look and feel** — the target audience is C-suite and senior leadership. The UI needs to feel polished and trustworthy, not like a developer tool.
- **Mobile-first voice UX** — even before the React Native app, the web experience should work well on tablets and phones for voice input scenarios (pacing around an office, boardroom use).
- **Real-time feedback** — as voice input is transcribed and processed, the UI should reflect progress (context being gathered, scores updating, follow-up questions surfacing).
