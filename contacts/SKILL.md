---
name: contacts
description: Business-card contact database (people, companies, phones, emails, addresses, tags) stored in this repo as JSONL. Use whenever the user shares a photo of a business card, asks to save/add/remember a contact, or asks who someone is, how to reach a person or company, or "who was the <mortgage guy / doctor / plumber>" — never answer contact questions from memory; always query the database first.
---

# Contacts (business-card database)

All contacts live in `~/claude-skills/contacts/data/contacts.jsonl` (one JSON
object per line) with card photos in `contacts/data/images/`. Everything is
managed through `cards.py` (stdlib-only Python; Pillow is optional and only
shrinks stored photos). Never hand-edit the JSONL; the script keeps it
validated and writes atomically.

```bash
C=~/claude-skills/contacts/cards.py
```

## Adding a card from a photo

1. Read every field off the image yourself (you can see it). Capture
   handwritten notes too and mark them as such.
2. Build one JSON object and pipe it to `add`, passing the photo with `-i`:

```bash
python3 $C add -i /path/to/card.jpg <<'JSON'
{
  "name": "Paul E. Smith",
  "title": "Owner / Loan Officer",
  "company": "MainStreet Mortgage Company",
  "category": "finance / mortgage",
  "phones": [{"type": "office", "number": "713-528-1245"},
             {"type": "cell",   "number": "713-480-7385"}],
  "emails": ["pes@texasmainstreet.com"],
  "website": "https://texasmainstreet.com",
  "social": [],
  "address": "3100 Richmond Ave #107, Houston, TX 77098",
  "hours": "",
  "tags": ["houston", "mortgage", "lender"],
  "notes": "Individual NMLS 193580; company NMLS 296814.",
  "met": "",
  "raw_text": "verbatim transcription of the whole card, pipe-separated"
}
JSON
```

Field rules:
- `id` is auto-generated from the name (`paul-e-smith`); omit it.
- `phones` entries use a `type` of `main`, `office`, `cell`, `fax`,
  `handwritten` or similar. Phone digits are searchable in any format.
- `tags` are lower-case, hyphenated, and are the main query surface. Always
  include the city plus 2–4 words someone would actually search for later
  (profession, industry, product). Reuse existing tags where one fits
  (`python3 $C list` shows them).
- `raw_text` is a faithful transcription of all card text so searches hit
  words that do not fit any structured field.
- `met` and `notes` hold context the user gives ("met at the Heights farmers
  market"). Ask for this only if the user volunteers nothing; do not block on it.
- `add` refuses a record whose phone or email already exists. Tell the user
  which id it matched, then `update` that record instead (or `--force` if the
  user confirms it is a different person).

After adding, commit so the other machines get it:

```bash
git -C ~/claude-skills add contacts/data && git -C ~/claude-skills commit -qm "contacts: add <name>" && git -C ~/claude-skills push -q
```

If the push fails (offline), say so; the commit still exists locally.

## Querying

```bash
python3 $C search mortgage                 # all terms must match (case-insensitive, every field)
python3 $C search houston doctor
python3 $C search 713-480-7385             # phones match on digits, any punctuation
python3 $C search plumber roofer --any     # any term
python3 $C search --tag lender             # filter by tag
python3 $C list                            # everyone, one line each
python3 $C list --json                     # full records
python3 $C show paul-e-smith               # full record by id
python3 $C export > contacts.csv           # CSV for spreadsheets
```

Line output is `id | name | title | company | first phone | first email | tags`.
Add `--json` when you need every phone number or the notes. When a search comes
up empty, retry with broader or alternative terms (`--any`, a synonym, the
company name) before telling the user there is no match. The `image` path is
relative to the `contacts/` directory; open it when the user asks what the card
looked like or when a field seems wrong.

## Editing and maintenance

```bash
echo '{"notes": "Quoted 6.1% on 30yr fixed, Oct 2026"}' | python3 $C update paul-e-smith
echo '{"tags": ["refinance"]}' | python3 $C update paul-e-smith --append   # extend list fields instead of replacing
echo '{}' | python3 $C update paul-e-smith -i new-photo.jpg               # replace the photo only
python3 $C remove paul-e-smith
python3 $C validate                        # schema, duplicate ids, shared phones/emails
```

Run `validate` after any bulk change and before committing.

## Failure modes

- **No such file** → the repo is not at `~/claude-skills` on this machine;
  find it and adjust the path.
- **"refusing to add: missing required field 'name'"** → `name` is required;
  if the card has only a company, put the company in `name` too.
- **"looks like a duplicate of: <id>"** → see field rules above.
- **"bad JSON"** → the JSONL was hand-edited; the error names the line.
