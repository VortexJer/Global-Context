# Global Context

Share context across terminal AI coding assistants: **Claude Code**, **Kimi Code CLI**, **OpenAI Codex CLI**, and any future terminal-based AI that reads files from your project.

When you switch from one AI to another, you lose the conversation thread. Global Context solves this by keeping a single Markdown file in each project that every AI can read and update.

---

## Supported AI assistants

| AI | Integration type | Auto-load |
|---|---|---|
| Claude Code | Plugin with `SessionStart` hook | ✅ Yes |
| Kimi Code CLI | Skill (system prompt) | ✅ Yes |
| OpenAI Codex CLI | Skill + prompt template | ✅ Yes |
| Google Gemini CLI | Skill (system prompt) | ✅ Yes |
| Other terminal AIs | Read `.globalcontext.md` | ⚠️ Manual start |

---

## Installation

### macOS / Linux / Git Bash on Windows

```bash
curl -fsSL https://raw.githubusercontent.com/YOUR_USER/globalcontext/main/install.sh | bash
```

Install for all detected AIs without prompting:

```bash
curl -fsSL https://raw.githubusercontent.com/YOUR_USER/globalcontext/main/install.sh | bash -s -- --ai all
```

### Windows (PowerShell)

```powershell
irm https://raw.githubusercontent.com/YOUR_USER/globalcontext/main/install.ps1 | iex
```

Install for all AIs:

```powershell
irm https://raw.githubusercontent.com/YOUR_USER/globalcontext/main/install.ps1 | iex; install-globalcontext -Ai all
```

### Local install (for development)

```bash
git clone https://github.com/YOUR_USER/globalcontext.git
cd globalcontext
./install.sh --local
```

---

## Quick start

1. **Install** Global Context for the AIs you use.
2. Register a project (optional but recommended):

   ```bash
   globalcontext register mi-web "~/projects/mi-web"
   ```

3. Open Claude, Kimi, or Codex anywhere and say:

   > "Open project mi-web"

   The AI will run `globalcontext resolve mi-web`, find the project's `.globalcontext.md`, and load it.

4. You can also start a brand-new project without a path:

   > "Let's build a calculator"

   The AI will run:

   ```bash
   globalcontext new calculator
   ```

   This creates `~/GlobalContext-Projects/calculator/.globalcontext.md` automatically.

5. When you finish a task, the AI appends a summary to the resolved `.globalcontext.md`.
6. Switch AI tools and continue — the context is already there.

You can also use `.globalcontext.md` in the current directory without registering anything.

---

## CLI commands

```bash
globalcontext init                  # Create .globalcontext.md in current folder
globalcontext status                # Show active context file
globalcontext status --show         # Show active context contents
globalcontext append notes.md --label Kimi   # Append a file to the context

globalcontext new <name>               # Create a project under ~/GlobalContext-Projects/
globalcontext new <name> --dir <path>  # Create a project at a custom path

globalcontext register <name> <path>   # Name a project directory
globalcontext unregister <name>        # Remove a registered name
globalcontext list                     # List registered projects
globalcontext resolve <name-or-path>   # Get/create the context file for a project

globalcontext install               # Install AI integrations (interactive)
globalcontext install --ai all      # Install all integrations
globalcontext doctor                # Check installation status
globalcontext --version             # Show version
```

---

## How it works

Global Context does **not** try to corrupt or rewrite internal AI session files. Instead it uses the one thing every AI can do: **read and write Markdown files on disk**.

- Each project gets a `.globalcontext.md` file inside its own directory.
- Projects can be registered with a friendly name (`globalcontext register <name> <path>`).
- Claude Code loads the local context automatically via a `SessionStart` hook and can resolve named projects on request.
- Kimi Code CLI loads the local context via a skill and can resolve named projects by running `globalcontext resolve <name>`.
- Codex loads the local context via a skill and can resolve named projects the same way.
- Gemini CLI loads the local context via a skill and can resolve named projects the same way.
- Every AI prefixes its summaries with its name (`Claude:`, `Kimi:`, `Codex:`) so you know who did what.

This means you can open your AI in any directory and say *"open project mi-web"* instead of `cd`-ing into the project folder.

---

## Context file format

`.globalcontext.md` is plain Markdown:

```markdown
# Global Context

Shared context for terminal AI assistants.

- **Project:** `/home/user/my-project`
- **Created:** 2026-07-10 12:00:00 UTC

## Rules

- Prefix important session summaries with the AI name.
- Keep entries concise but informative.
- Do not delete old entries unless requested.

---

## Claude — 2026-07-10 12:30 UTC

- Set up the project structure.
- Pending: implement the API endpoint.

---

## Kimi — 2026-07-10 13:00 UTC

- Implemented the API endpoint.
- Added basic tests.

---
```

---

## Limitations

- **No native session sync**: Global Context cannot make a Claude session appear inside Kimi or vice versa. It keeps a shared Markdown journal instead.
- **Auto-update depends on the AI**: Claude, Kimi and Codex are instructed to update the file, but they decide when to do so. For other AIs, the user must load the file manually.
- **Large contexts**: If the file grows too large, add a `## Compacted Summary` section and archive old details.

---

## Contributing

Pull requests are welcome. The project is intentionally simple: a CLI, a Markdown convention, and small integrations for each AI tool.

## License

MIT
