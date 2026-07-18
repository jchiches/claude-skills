#!/usr/bin/env bash
# Symlink every skill in this repo into ~/.claude/skills/ so Claude Code
# discovers them. Safe to re-run; existing links are refreshed.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="$HOME/.claude/skills"
mkdir -p "$DEST"

linked=0
for dir in "$REPO_DIR"/*/; do
    name="$(basename "$dir")"
    [ -f "$dir/SKILL.md" ] || continue
    target="$DEST/$name"
    if [ -e "$target" ] && [ ! -L "$target" ]; then
        echo "SKIP  $name — $target exists and is not a symlink (move it aside first)" >&2
        continue
    fi
    ln -sfn "${dir%/}" "$target"
    echo "linked $name -> ${dir%/}"
    linked=$((linked + 1))
done

echo "$linked skill(s) linked into $DEST"
