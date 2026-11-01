#!/usr/bin/env python3
"""Business-card contact database: one JSON object per line in data/contacts.jsonl.

Stdlib only. Pillow is used to shrink stored images when it is installed;
otherwise the image is copied as-is.

Subcommands:
  add       read one contact (JSON) from stdin or --file, append it
  update    merge JSON fields (stdin or --file) into an existing contact by id
  search    case-insensitive substring match across every field
  list      one line per contact
  show      full JSON for one or more ids
  remove    delete a contact (and its image) by id
  validate  check schema, duplicate ids, duplicate phones/emails
  export    dump as CSV (stdout)
"""
import argparse
import csv
import datetime as dt
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
DB = os.path.join(DATA_DIR, "contacts.jsonl")
IMG_DIR = os.path.join(DATA_DIR, "images")

REQUIRED = ("id", "name")
KNOWN = {
    "id", "name", "title", "company", "category", "phones", "emails",
    "website", "social", "address", "hours", "notes", "tags", "added",
    "image", "raw_text", "met",
}
LIST_FIELDS = ("phones", "emails", "social", "tags")
MAX_IMAGE_PX = 1600


# ---------- storage ----------

def load():
    if not os.path.exists(DB):
        return []
    out = []
    with open(DB, encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError as e:
                sys.exit(f"{DB}:{n}: bad JSON: {e}")
    return out


def save(contacts):
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp = DB + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        for c in contacts:
            fh.write(json.dumps(c, ensure_ascii=False, sort_keys=True) + "\n")
    os.replace(tmp, DB)


def read_json_input(path):
    raw = open(path, encoding="utf-8").read() if path else sys.stdin.read()
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError as e:
        sys.exit(f"input is not valid JSON: {e}")
    if not isinstance(obj, dict):
        sys.exit("input must be a single JSON object")
    return obj


# ---------- helpers ----------

def slugify(text):
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s or "contact"


def unique_id(base, existing):
    ids = {c["id"] for c in existing}
    if base not in ids:
        return base
    n = 2
    while f"{base}-{n}" in ids:
        n += 1
    return f"{base}-{n}"


def digits(s):
    return re.sub(r"\D", "", s or "")


def normalize(c):
    """Coerce list fields, trim strings, fill defaults. Returns problems list."""
    problems = []
    for k in REQUIRED:
        if not c.get(k):
            problems.append(f"missing required field '{k}'")
    for k in LIST_FIELDS:
        v = c.get(k)
        if v is None:
            c[k] = []
        elif isinstance(v, str):
            c[k] = [v]
        elif not isinstance(v, list):
            problems.append(f"'{k}' must be a list")
    # phones: accept "555-1234" or {"type": "cell", "number": "555-1234"}
    phones = []
    for p in c.get("phones", []):
        if isinstance(p, str):
            p = {"type": "main", "number": p}
        if not isinstance(p, dict) or not p.get("number"):
            problems.append(f"bad phone entry: {p!r}")
            continue
        p.setdefault("type", "main")
        phones.append(p)
    c["phones"] = phones
    for k, v in list(c.items()):
        if isinstance(v, str):
            c[k] = v.strip()
    unknown = set(c) - KNOWN
    if unknown:
        problems.append(f"unknown fields: {sorted(unknown)}")
    c.setdefault("added", dt.date.today().isoformat())
    return problems


def flatten(c):
    """All searchable text of a contact, lower-cased, one string."""
    parts = []

    def walk(v):
        if isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)
        elif v is not None:
            parts.append(str(v))

    walk(c)
    return " ".join(parts).lower()


def store_image(src, contact_id):
    """Copy (and shrink if Pillow is available) an image into data/images."""
    if not os.path.exists(src):
        sys.exit(f"image not found: {src}")
    os.makedirs(IMG_DIR, exist_ok=True)
    ext = os.path.splitext(src)[1].lower() or ".jpg"
    dest = os.path.join(IMG_DIR, contact_id + (".jpg" if ext in (".jpeg", ".jpg") else ext))
    try:
        from PIL import Image, ImageOps
        im = Image.open(src)
        im = ImageOps.exif_transpose(im)
        im.thumbnail((MAX_IMAGE_PX, MAX_IMAGE_PX))
        if dest.endswith(".jpg"):
            im = im.convert("RGB")
            im.save(dest, "JPEG", quality=80, optimize=True)
        else:
            im.save(dest)
    except ImportError:
        shutil.copyfile(src, dest)
    return os.path.relpath(dest, HERE)


def one_line(c):
    bits = [c["id"], c.get("name", ""), c.get("title") or "", c.get("company") or ""]
    phone = c["phones"][0]["number"] if c.get("phones") else ""
    email = c["emails"][0] if c.get("emails") else ""
    tags = ",".join(c.get("tags", []))
    return " | ".join(x for x in bits + [phone, email, tags] if x)


# ---------- commands ----------

def cmd_add(a):
    contacts = load()
    c = read_json_input(a.file)
    if not c.get("id"):
        base = slugify(c.get("name", ""))
        c["id"] = unique_id(base, contacts)
    elif c["id"] in {x["id"] for x in contacts}:
        sys.exit(f"id '{c['id']}' already exists (use update)")
    problems = normalize(c)
    if problems:
        sys.exit("refusing to add:\n  " + "\n  ".join(problems))
    dupes = find_dupes(c, contacts)
    if dupes and not a.force:
        sys.exit("looks like a duplicate of: " + ", ".join(dupes) + "  (pass --force to add anyway)")
    if a.image:
        c["image"] = store_image(a.image, c["id"])
    contacts.append(c)
    save(contacts)
    print(json.dumps(c, indent=2, ensure_ascii=False))


def cmd_update(a):
    contacts = load()
    patch = read_json_input(a.file)
    for c in contacts:
        if c["id"] == a.id:
            for k, v in patch.items():
                if k == "id":
                    continue
                if a.append and k in LIST_FIELDS and isinstance(v, list):
                    c.setdefault(k, []).extend(v)
                else:
                    c[k] = v
            problems = normalize(c)
            if problems:
                sys.exit("refusing to update:\n  " + "\n  ".join(problems))
            if a.image:
                c["image"] = store_image(a.image, c["id"])
            save(contacts)
            print(json.dumps(c, indent=2, ensure_ascii=False))
            return
    sys.exit(f"no contact with id '{a.id}'")


def find_dupes(c, contacts):
    hits = []
    my_phones = {digits(p["number"]) for p in c.get("phones", []) if digits(p["number"])}
    my_emails = {e.lower() for e in c.get("emails", [])}
    for o in contacts:
        if o["id"] == c["id"]:
            continue
        o_phones = {digits(p["number"]) for p in o.get("phones", [])}
        o_emails = {e.lower() for e in o.get("emails", [])}
        if my_phones & o_phones or my_emails & o_emails:
            hits.append(o["id"])
    return hits


def cmd_search(a):
    contacts = load()
    terms = [t.lower() for t in a.terms]
    out = []
    for c in contacts:
        hay = flatten(c)
        hay_digits = digits(hay)
        ok = []
        for t in terms:
            td = digits(t)
            ok.append(t in hay or (len(td) >= 4 and td in hay_digits))
        if (all(ok) if not a.any else any(ok)):
            out.append(c)
    if a.tag:
        out = [c for c in out if a.tag.lower() in [t.lower() for t in c.get("tags", [])]]
    emit(out, a.json)


def cmd_list(a):
    contacts = load()
    if a.tag:
        contacts = [c for c in contacts if a.tag.lower() in [t.lower() for t in c.get("tags", [])]]
    contacts.sort(key=lambda c: c.get("name", "").lower())
    emit(contacts, a.json)


def cmd_show(a):
    contacts = {c["id"]: c for c in load()}
    missing = [i for i in a.ids if i not in contacts]
    if missing:
        sys.exit("no such id: " + ", ".join(missing))
    print(json.dumps([contacts[i] for i in a.ids], indent=2, ensure_ascii=False))


def cmd_remove(a):
    contacts = load()
    keep = [c for c in contacts if c["id"] != a.id]
    if len(keep) == len(contacts):
        sys.exit(f"no contact with id '{a.id}'")
    gone = next(c for c in contacts if c["id"] == a.id)
    img = gone.get("image")
    if img and os.path.exists(os.path.join(HERE, img)):
        os.remove(os.path.join(HERE, img))
    save(keep)
    print(f"removed {a.id}")


def cmd_validate(a):
    contacts = load()
    bad = 0
    seen = set()
    for c in contacts:
        probs = normalize(dict(c))
        if c["id"] in seen:
            probs.append("duplicate id")
        seen.add(c["id"])
        img = c.get("image")
        if img and not os.path.exists(os.path.join(HERE, img)):
            probs.append(f"image file missing: {img}")
        probs += [f"shares phone/email with {d}" for d in find_dupes(c, contacts)]
        for p in probs:
            bad += 1
            print(f"{c.get('id', '?')}: {p}")
    print(f"{len(contacts)} contacts, {bad} problem(s)")
    sys.exit(1 if bad else 0)


def cmd_export(a):
    contacts = load()
    cols = ["id", "name", "title", "company", "category", "phones", "emails",
            "website", "social", "address", "hours", "tags", "notes", "added", "met"]
    w = csv.writer(sys.stdout)
    w.writerow(cols)
    for c in sorted(contacts, key=lambda c: c.get("name", "").lower()):
        row = []
        for k in cols:
            v = c.get(k, "")
            if k == "phones":
                v = "; ".join(f"{p['type']}: {p['number']}" for p in v)
            elif isinstance(v, list):
                v = "; ".join(v)
            row.append(v)
        w.writerow(row)


def emit(contacts, as_json):
    if as_json:
        print(json.dumps(contacts, indent=2, ensure_ascii=False))
    else:
        for c in contacts:
            print(one_line(c))
        print(f"-- {len(contacts)} match(es)", file=sys.stderr)


# ---------- main ----------

def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("add", help="append a contact from JSON (stdin or --file)")
    s.add_argument("--file", "-f")
    s.add_argument("--image", "-i", help="path to the card photo to store")
    s.add_argument("--force", action="store_true", help="add even if phone/email matches an existing contact")
    s.set_defaults(fn=cmd_add)

    s = sub.add_parser("update", help="merge JSON fields into an existing contact")
    s.add_argument("id")
    s.add_argument("--file", "-f")
    s.add_argument("--image", "-i")
    s.add_argument("--append", action="store_true", help="extend list fields instead of replacing them")
    s.set_defaults(fn=cmd_update)

    s = sub.add_parser("search", help="substring search across all fields")
    s.add_argument("terms", nargs="+")
    s.add_argument("--any", action="store_true", help="match any term instead of all")
    s.add_argument("--tag")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_search)

    s = sub.add_parser("list", help="list every contact")
    s.add_argument("--tag")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_list)

    s = sub.add_parser("show", help="full record(s) by id")
    s.add_argument("ids", nargs="+")
    s.set_defaults(fn=cmd_show)

    s = sub.add_parser("remove", help="delete a contact by id")
    s.add_argument("id")
    s.set_defaults(fn=cmd_remove)

    s = sub.add_parser("validate", help="check the database for problems")
    s.set_defaults(fn=cmd_validate)

    s = sub.add_parser("export", help="CSV to stdout")
    s.set_defaults(fn=cmd_export)

    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
