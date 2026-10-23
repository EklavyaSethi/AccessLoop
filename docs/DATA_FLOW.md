# Where your page data goes

| Step | Data | Leaves this computer? |
|---|---|---|
| Load | The HTML you upload, paste or pick | No. Stored in a per-session workspace folder on this machine. |
| Scan | A copy of the page with scripts, event handlers and active URLs removed | No. Headless Chromium on this machine; every network request is blocked (the page's own CSS/images can load from its folder). |
| Fix and verify | Source edits from fixed templates, your typed text | No. |
| Audit log, reports | Decisions, reviewer name as typed, before/after snippets, hashes | No, until you download or share them. |
| AI review (optional) | Up to 10 proposed changes as short snippets, **redacted**: `value`, `placeholder`, `title`, `data-*` attributes and URL query strings blanked; runs of 4+ digits and email addresses masked | **Off by default.** `ACCESSLOOP_AI=local` keeps it on this machine (Ollama on 127.0.0.1). `ACCESSLOOP_AI=gemini` sends the redacted snippets to Google, and only after the reviewer ticks the consent box for that request. The exact payload can be inspected before sending. |

AI advice is never executed: it can only label a proposal "recommend" or "escalate". It cannot change the file, the patch, or the verification result.

For banks: keep `ACCESSLOOP_AI` unset (off) or use `local`. Workspace folders (`.accessloop_workspaces/`) can be deleted at any time; they are also cleaned up automatically after the retention period (see `ACCESSLOOP_WORKSPACE_TTL_HOURS`).
