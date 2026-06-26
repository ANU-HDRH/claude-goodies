#!/usr/bin/env bash
# Build the installable d2-diagrams skill from this source repo.
#
# This repo is the SOURCE, not an installed skill: SKILL.md lives at the root
# alongside dev-only material (README, PROPOSAL, tests/, fixtures). It is
# deliberately NOT placed under ~/.claude/skills, so the skill never
# auto-triggers while we hammer on it — triggering stays explicit.
#
# This script assembles only the SHIPPED subset (SKILL.md + the bundled
# references/) into dist/<name>/, named correctly for installation. That dir is
# the artifact you copy into a project's .claude/skills/ (or ~/.claude/skills/)
# when you want to test the skill live somewhere.
#
# Usage:
#   ./build.sh                    # build to dist/d2-diagrams/
#   ./build.sh /path/to/project   # build, then install into
#                                 #   /path/to/project/.claude/skills/d2-diagrams/
#                                 # (the skill WILL auto-trigger in that project)
set -euo pipefail
cd "$(dirname "$0")"

# Skill name comes from SKILL.md frontmatter — single source of truth.
NAME="$(sed -n 's/^name:[[:space:]]*//p' SKILL.md | head -n1)"
[ -n "$NAME" ] || { echo "error: no 'name:' found in SKILL.md frontmatter" >&2; exit 1; }

OUT="dist/$NAME"

# references/ entries that are dev-only fixtures, not part of the shipped skill.
# Everything else in references/ is bundled (the skill loads it at runtime via
# ${CLAUDE_SKILL_DIR}/references/...).
EXCLUDE=( lyrebird_architecture.md )

is_excluded() {
  local base="$1" e
  for e in "${EXCLUDE[@]}"; do [ "$base" = "$e" ] && return 0; done
  return 1
}

echo "building skill '$NAME' -> $OUT"
rm -rf "$OUT"
mkdir -p "$OUT/references"

cp SKILL.md "$OUT/SKILL.md"
echo "  add   SKILL.md"
for f in references/*; do
  base="$(basename "$f")"
  if is_excluded "$base"; then
    echo "  skip  references/$base (dev-only)"
    continue
  fi
  cp "$f" "$OUT/references/$base"
  echo "  add   references/$base"
done

echo "built $OUT ($(find "$OUT" -type f | wc -l | tr -d ' ') files)"

# Optional: install into a target project's .claude/skills/.
if [ "${1:-}" ]; then
  DEST="$1/.claude/skills/$NAME"
  echo "installing -> $DEST"
  rm -rf "$DEST"
  mkdir -p "$(dirname "$DEST")"
  cp -R "$OUT" "$DEST"
  echo "installed. the skill is now live in $1 — it will auto-trigger there."
fi
