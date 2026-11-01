# claude-skills

Personal Claude Code skills, versioned here and synced across machines.

Each top-level directory is one skill and must contain a `SKILL.md` (uppercase)
with `name` and `description` frontmatter. Claude Code discovers skills by
scanning `~/.claude/skills/`, so this repo is symlinked into that folder
rather than copied — a `git pull` updates every machine's skills in place.

## Install (per machine)

```bash
git clone git@github.com:jchiches/claude-skills.git ~/claude-skills
~/claude-skills/install.sh
```

Re-run `install.sh` after adding a new skill directory (existing links are
refreshed harmlessly). Restart any running Claude Code session to pick up
newly added skills — the scan happens at session start.

## Update (per machine)

```bash
git -C ~/claude-skills pull
```

Edits to an existing skill take effect the next time the skill is invoked;
brand-new skill directories need `install.sh` + a session restart.

## Skills

| Skill | What it does | Depends on |
|-------|--------------|------------|
| `market-data` | Live stock/ETF/index/option/futures quotes and option chains from Schwab | quiver clone at `~/quiver` (script + `config.json` + schwab-mcp token) |
| `contacts` | Business-card database: add a contact from a card photo, search by name/company/phone/tag, export CSV. Data lives in `contacts/data/` and syncs with the repo | python3 (Pillow optional, shrinks stored photos) |

## Adding a skill

1. `mkdir <skill-name>` and write `<skill-name>/SKILL.md`. The frontmatter
   `description` is what triggers the skill — write it as a rule for *when*
   Claude must use it, not just what it is.
2. Keep skills here machine-portable: use `~`-based absolute paths (with a
   noted default) instead of repo-relative paths, since sessions can start in
   any directory. Project-coupled skills that only make sense inside one repo
   belong in that repo's `.claude/skills/` instead.
3. Commit, push, then `git pull` + `install.sh` on the other machines.
