# d2-diagrams (plugin)

This is the **canonical home** for the d2-diagrams skill — vendored here from
`~/innovation/d2diag` so it lives in one place.

## Layout

```
plugins/d2-diagrams/
  .claude-plugin/plugin.json   # plugin manifest
  skills/
    d2-diagrams/               # the SHIPPED skill (what users get on install)
      SKILL.md
      references/
  _source/                     # dev material — NOT shipped, NOT auto-discovered
    SKILL.md                   # the source of truth you edit
    references/                # full references incl. dev-only fixtures
    tests/
    build.sh
    README.md                  # the skill's own operator guide
    PROPOSAL-split-ship-source-layout.md
```

## Editing the skill

1. Edit under `_source/` (SKILL.md, references, tests). This is the working copy.
2. Rebuild the shipped subset into `skills/d2-diagrams/`:

   ```bash
   cd _source
   ./build.sh                      # builds to _source/dist/d2-diagrams/
   rm -rf ../skills/d2-diagrams
   cp -R dist/d2-diagrams ../skills/d2-diagrams
   ```

   `build.sh` copies `SKILL.md` + the non-dev-only `references/` and is the
   single source of truth for what ships. (Adjust the script to emit straight
   into `../skills/d2-diagrams/` if you prefer a one-step build.)
3. Commit both `_source/` and the rebuilt `skills/d2-diagrams/`.

The split keeps tests/fixtures and dev-only references out of what users install,
while keeping the full source tracked in this repo.

See [`_source/README.md`](_source/README.md) for the full skill operator guide.
