# Global Context file format specification

This document defines the exact structure of `.globalcontext.md` so that multiple terminal AI assistants can read and append to it without corrupting each other's work.

---

## 1. File location

- **Primary name:** `.globalcontext.md`
- **Location:** in the project root directory.
- **Resolution:** `globalcontext resolve <name-or-path>` walks up from the current working directory or looks up a registered project name, then returns the path to the context file.
- **Legacy alias:** `.ai-shared-context.md` is supported for reading but new projects should use `.globalcontext.md`.
- **Auto-created project folders:** When an AI creates a project with `globalcontext new <name>`, the folder under `~/GlobalContext-Projects/` is named `<name>--<path-suffix>/`. The suffix is derived from the project path (drive + parent directory) to avoid collisions between projects with the same name and make the folder easy to locate.

---

## 2. Encoding

- **UTF-8**, no BOM.
- Line endings may be LF or CRLF; parsers must treat both equivalently.

---

## 3. Header

The first part of the file is a fixed header created by `globalcontext init` or `globalcontext resolve` when the file does not exist.

```markdown
# Global Context

Shared context for terminal AI assistants (Claude Code, Kimi Code CLI, Codex, Gemini, etc.).

- **Project:** `/absolute/path/to/project`
- **Name:** `optional-registered-name`
- **Created:** `YYYY-MM-DD HH:MM:SS UTC`

## What this file is

This is a **project state log** (a hand-off journal), NOT a chat transcript. Each terminal AI assistant writes a short entry after a meaningful session so the next AI can continue without re-reading every file.

## Rules

- One entry per AI session when something important changed.
- Keep entries concise: 3–8 bullet points, no long prose.
- Start each entry with the AI name, e.g. **Claude:**, **Kimi:**, **Codex:**, **Gemini:**.
- Each entry must include:
  - What was done (created, modified, fixed, refactored).
  - Key files or directories touched.
  - How to run / test / use the current state.
  - Current status and any blockers or pending next steps.
- Do NOT paste conversation transcripts here.
- Do not delete old entries unless requested.
- If the file grows too large, add a `## Compacted Summary` section and archive older details.

---
```

Rules:

- The header must remain at the top of the file.
- The `## What this file is` and `## Rules` sections are informational; an AI may read them but must not edit them.
- After the header, a separator line `---` marks the boundary before the first entry.

---

## 4. Entries

Each entry documents one meaningful AI session.

### 4.1 Entry format

```markdown
## <AI> — YYYY-MM-DD HH:MM:SS UTC

- <what changed>
- <key files touched>
- <how to run / test / use>
- <status / pending / blockers>

---
```

### 4.2 Entry rules

- **Heading:** exactly `## <AI> — <timestamp>` where `<AI>` is the assistant name (`Claude`, `Kimi`, `Codex`, `Gemini`, `Recovery`, etc.) and `<timestamp>` is UTC in `YYYY-MM-DD HH:MM:SS UTC` format.
- **Body:** a Markdown bullet list.
- **Length:** 3–8 bullets, no long paragraphs.
- **Required content:**
  1. What changed.
  2. Files or directories touched.
  3. How to run, test or use the current state.
  4. Current status and any blockers or pending steps.
- **Separator:** every entry ends with `---` on its own line.
- **Order:** entries are always appended to the end of the file. Never insert entries in the middle.

### 4.3 Recovery entries

When a session is interrupted and a `.globalcontext.pending` marker is recovered, Global Context appends a `Recovery` entry:

```markdown
## Recovery — YYYY-MM-DD HH:MM:SS UTC

- Session with **<AI>** started at `<timestamp>` was interrupted before the context could be updated.
- Last known intent: <summary from pending marker>.
- Please review recent changes and update this log with a concise entry.

---
```

---

## 5. Compacted summary

When the file grows large, a `## Compacted Summary` section may be inserted between the header and the most recent entries.

### 5.1 When to compact

Compact when **any** of the following is true:

- More than 100 entries.
- File size exceeds 100 KB.
- The user explicitly asks to compact.

### 5.2 Compaction rules

1. Keep the **10 most recent entries** verbatim at the end of the file.
2. Summarize all older entries into 5–10 bullets under a new `## Compacted Summary` section.
3. Move the full old detail to an archive file named `.globalcontext.md.archive.<YYYYMMDD-HHMMSS>`.
4. Do not delete the archive unless the user asks.

Example after compaction:

```markdown
# Global Context
...

## Compacted Summary — 2026-07-10 14:00:00 UTC

- Initial project scaffold and dependencies.
- Built core API endpoints for user management.
- Added authentication middleware.
- ...

---

## Kimi — 2026-07-10 15:00 UTC

- Latest entry...

---
```

---

## 6. Concurrency and locking

Multiple AI assistants may attempt to append to the same `.globalcontext.md` simultaneously.

### 6.1 Lock file

- Before reading or appending, acquire the lock file `.globalcontext.md.lock`.
- The lock file contains `<pid>:<unix_timestamp>` of the owning process.
- After finishing, release the lock by deleting the lock file.
- Lock acquisition is reentrant within the same thread.

### 6.2 Stale locks

A lock is considered stale and may be broken if:

- The owning process no longer exists.
- The lock is older than 60 seconds.

### 6.3 Append semantics

- Always append; never rewrite the whole file.
- Use the lock to ensure atomic append operations.

---

## 7. Pending checkpoint marker

To survive crashes, Global Context uses a companion file `.globalcontext.pending`.

### 7.1 Marker format

JSON with the following fields:

```json
{
  "context_file": "/absolute/path/to/.globalcontext.md",
  "ai": "Claude",
  "pid": 12345,
  "started_at": "2026-07-10T14:30:00+00:00",
  "summary": "short intent description"
}
```

### 7.2 Lifecycle

1. **Checkpoint:** create `.globalcontext.pending` before starting a response.
2. **Complete:** after appending the summary to `.globalcontext.md`, delete `.globalcontext.pending`.
3. **Recover:** on the next session start, if `.globalcontext.pending` exists and its owner is gone or the marker is stale, append a `Recovery` entry and delete the marker.

---

## 8. Backward compatibility

- Legacy `.ai-shared-context.md` files are read and migrated to `.globalcontext.md` on first use.
- New entries must follow this spec; older entries that do not follow it should be preserved as-is.
