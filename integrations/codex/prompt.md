# Global Context for Codex

This project uses `.globalcontext.md` to share context across terminal AI assistants (Claude Code, Kimi Code CLI, Codex, etc.).

## Finding the context file

1. Check whether `.globalcontext.md` exists in the current working directory.
2. If the user mentions a project by name, run:
   ```bash
   globalcontext resolve <project-name>
   ```
3. If the user gives a project path, run:
   ```bash
   globalcontext resolve "<project-path>"
   ```
4. Use the returned path as the active context file.

If the context file does not exist, `globalcontext resolve` creates it automatically.

## During the session

- Treat the resolved project directory as the working directory.
- Read the `.globalcontext.md` and keep it in mind.
- `.globalcontext.md` is a **project state log**, NOT a chat transcript.
- At the start of the session, run `globalcontext recover` to consolidate any stale pending checkpoints.
- Before each assistant response, run `globalcontext checkpoint` against the resolved `.globalcontext.md`.
- After significant changes, append **one concise entry** using the prefix `Codex:`, then run `globalcontext checkpoint-complete --clear-only`.
- Each entry should be 3–8 bullet points covering: what changed, key files touched, how to run/test/use the current state, and any pending blockers.
- Do NOT paste conversation transcripts into the context file.

## Registering projects

```bash
globalcontext register <name> "<project-path>"
```
