---
name: contacts
description: Business-card contact database (people, companies, phones, emails, addresses, tags) kept in the PersonalBusinessCardProject repo. Use whenever the user shares a photo of a business card, asks to save/add/remember a contact, or asks who someone is, how to reach a person or company, or "who was the <mortgage guy / doctor / plumber>" — never answer contact questions from memory; always query the database first.
---

# Contacts (business-card database)

This is the portable pointer skill. The database, the `cards.py` CLI, and the
full ingest/query instructions live in the PersonalBusinessCardProject repo, assumed at
`~/PersonalBusinessCardProject`. If it lives elsewhere on this machine, adjust the path.

```bash
B=~/PersonalBusinessCardProject
```

Read `$B/.claude/skills/contacts/SKILL.md` once per session for the record
schema, field rules, and the ingest workflow, then follow it.

## Quick reference

```bash
python3 $B/cards.py search mortgage               # all terms, case-insensitive, every field
python3 $B/cards.py search 713-480-7385           # phone digits match in any format
python3 $B/cards.py search plumber roofer --any
python3 $B/cards.py search --tag lender
python3 $B/cards.py list [--json]
python3 $B/cards.py show <id>
python3 $B/cards.py add -i /path/to/card.jpg < record.json
python3 $B/cards.py validate
```

The `image` path in each record is relative to `$B`. After adding or editing
a contact, commit and push from `$B` so the other machines get it:

```bash
git -C ~/PersonalBusinessCardProject add -A && git -C ~/PersonalBusinessCardProject commit -qm "Add <name>" && git -C ~/PersonalBusinessCardProject push -q
```

## Failure modes

- **No such file** → the PersonalBusinessCardProject clone is not at `~/PersonalBusinessCardProject`;
  find it or tell the user to `git clone git@github.com:jchiches/PersonalBusinessCardProject.git ~/PersonalBusinessCardProject`.
- Anything else → see the failure modes in the repo's own skill file.
