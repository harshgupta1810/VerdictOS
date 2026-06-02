# VerdictOS — Skills Reference

Quick reference for Claude Code skills and tools available in this project.

---

## SuperDesign — UI Design Agent

**Project:** VerdictOS M&A Due Diligence  
**Project ID:** `6792bc52-6c51-4b02-9970-1d7bb52bc2a2`  
**Canvas:** https://app.superdesign.dev/teams/9d44c94d-ef21-4e39-a15e-95ce0495454a/projects/6792bc52-6c51-4b02-9970-1d7bb52bc2a2  
**Initial Draft:** `b2e86337-42f4-4368-b396-e3a308ac2adb`  
**Preview:** https://p.superdesign.dev/draft/b2e86337-42f4-4368-b396-e3a308ac2adb

### How to invoke design help

Type `/superdesign help me design X` in Claude Code. Claude will use the SKILL.md instructions to:
1. Fetch fresh guidelines from the superdesign platform
2. Call `superdesign iterate-design-draft` to generate variations
3. Return a preview URL you can open in your browser

### Common design commands

```bash
# Explore design directions (branch mode — creates multiple variations)
superdesign iterate-design-draft \
  --draft-id b2e86337-42f4-4368-b396-e3a308ac2adb \
  -p "dark glassmorphism" -p "minimal enterprise" -p "bold data-heavy" \
  --mode branch --json

# Replace current draft with a single refined version
superdesign iterate-design-draft \
  --draft-id <draft-id> \
  -p "tighten spacing, increase contrast on severity badges" \
  --mode replace --json

# Auto-explore (superdesign fills in design details)
superdesign iterate-design-draft \
  --draft-id <draft-id> \
  -p "professional SaaS legal platform" \
  --mode branch --count 3 --json

# Get the HTML for a specific draft (to copy back into the codebase)
superdesign get-design --draft-id <draft-id> --json

# List all drafts for this project
superdesign fetch-design-nodes \
  --project-id 6792bc52-6c51-4b02-9970-1d7bb52bc2a2 --json

# Extract brand/style from a reference website
superdesign extract-brand-guide --url https://linear.app --json

# Search design inspiration prompts
superdesign search-prompts --query "enterprise dark dashboard" --json
```

### Pages covered in the design canvas

| Page | Route | Description |
|------|-------|-------------|
| Deal List | `/deals` | Glass table of all deals with animated status badges |
| Create Deal | `/deals/new` | File dropzone + client ID form |
| Pipeline Status | `/deals/[id]/status` | 8-phase stepper + live WebSocket event feed |
| Verdict | `/deals/[id]/verdict` | GO/NO-GO brief + expandable findings table |
| Escalations | `/deals/[id]/escalations` | HITL resolution workflow |
| Audit Trail | `/deals/[id]/audit` | Immutable event timeline |

### Design system (current)

| Token | Value |
|-------|-------|
| Background | `#f4f6f9` neutral app canvas |
| Card | White surface, slate border, minimal shadow |
| Nav | White sticky header with slate bottom border |
| Primary accent | Teal `#0f766e` |
| Secondary accent | Sky `#0369a1` |
| Success | Emerald `#059669` |
| Danger | Red `#dc2626` |
| Font | Geist Sans / Geist Mono |

### Active UI rules

- Purple, violet, indigo, yellow, and amber are prohibited in product UI and SuperDesign drafts.
- New Matter uses a guided full-page form, not a centered glass card.
- Prefer legal SaaS neutral styling: white, off-white, slate, ink, teal, and restrained blue/sky.
- Avoid glassmorphism, decorative glows, large gradients, and marketing-style panels inside app workflows.

---

## Built-in Claude Code Skills

These are available as `/skill-name` in Claude Code:

| Skill | Trigger | What it does |
|-------|---------|--------------|
| `/superdesign` | `help me design X`, `improve design of X`, `set design system` | Generates UI design drafts and variations on superdesign canvas |
| `/code-review` | `review this`, `check the diff` | Reviews current branch diff for bugs and simplifications |
| `/code-review ultra` | `deep review` | Multi-agent cloud review with inline PR comments |
| `/run` | `run the app`, `start the server` | Launches frontend dev server and observes behaviour |
| `/verify` | `verify this works`, `test the change` | Runs the app and checks the feature works end-to-end |
| `/security-review` | `security check` | Reviews pending changes for security issues |
| `/simplify` | `simplify this`, `clean this up` | Removes duplication, applies efficiency improvements |

---

## Backend Commands (Windows — no `make`)

```powershell
# Start FastAPI backend (from VerdictOS-main\VerdictOS-main\)
"C:\Users\Saurabh\AppData\Local\Python\bin\python.exe" -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Start frontend (from VerdictOS-main\VerdictOS-main\frontend\)
npm run dev

# Run DB migrations
"C:\Users\Saurabh\AppData\Local\Python\bin\python.exe" -m alembic upgrade head

# Install backend deps
"C:\Users\Saurabh\AppData\Local\Python\bin\python.exe" -m pip install -r requirements.txt

# Run tests
"C:\Users\Saurabh\AppData\Local\Python\bin\python.exe" -m pytest tests/

# Lint
"C:\Users\Saurabh\AppData\Local\Python\bin\python.exe" -m ruff check src/ tests/
```

## API Quick Reference

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness check |
| GET | `/api/v1/deals` | List all deals |
| POST | `/api/v1/deals` | Create deal + start pipeline |
| GET | `/api/v1/deals/{id}/status` | Current deal status |
| WS | `/api/v1/deals/{id}/stream?api_key=` | Real-time pipeline events |
| GET | `/api/v1/deals/{id}/verdict` | Final findings (complete only) |
| GET | `/api/v1/deals/{id}/audit` | Immutable audit trail |
| GET | `/api/v1/deals/{id}/escalations` | List escalations |
| POST | `/api/v1/deals/{id}/escalations/{eid}/resolve` | Resolve escalation |
| POST | `/api/v1/upload` | Upload PDF/DOCX → returns server paths |

Default API key (dev): `dev-key-123` via `X-API-Key` header or `?api_key=` query param.
