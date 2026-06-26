# claude-goodies

An internal **Claude Code marketplace** for the ANU HDRH / RSE team. It bundles
the skills and frameworks we share, so any team member can install them into
Claude Code with one command.

It currently ships:

| Plugin        | What it is                                                        | Status |
|---------------|------------------------------------------------------------------|--------|
| `d2-diagrams` | Author, iterate on, and render diagrams with D2 as the source.   | ready  |
| `bower`       | Bower spec-driven development (SDD) framework.                    | ready (external repo) |

---

## For users: installing

Add this marketplace, then install the plugins you want.

```
# Add the marketplace (once)
/plugin marketplace add ANU-HDRH/claude-goodies

# Install a plugin
/plugin install d2-diagrams@claude-goodies
/plugin install bower@claude-goodies
```

You can also browse interactively with `/plugin`. To update later:

```
/plugin marketplace update claude-goodies
```

> Installing from a local checkout instead of GitHub? Point the marketplace at
> the path: `/plugin marketplace add /path/to/claude-goodies`.

Once installed, skills auto-trigger when relevant (e.g. ask Claude to "draw the
auth flow" and `d2-diagrams` activates). You can also invoke a skill explicitly
by name.

---

## For maintainers: repository layout

This is a marketplace repo. The shape Claude Code expects:

```
claude-goodies/
  .claude-plugin/
    marketplace.json           # lists every plugin + where it lives
  plugins/
    d2-diagrams/
      .claude-plugin/
        plugin.json            # this plugin's manifest
      skills/
        d2-diagrams/SKILL.md   # a shipped skill
      _source/                 # (our convention) dev material, not shipped
```

Plugins can live in-repo (under `plugins/`) or be referenced from an external
repo in `marketplace.json` (see `bower` below).

### Where things go

- **A new plugin** → a directory under `plugins/<name>/` with a
  `.claude-plugin/plugin.json`, then add an entry to
  `.claude-plugin/marketplace.json`.
- **Skills inside a plugin** → `plugins/<name>/skills/<skill-name>/SKILL.md`
  (plus any `references/`). Skills under `skills/` are auto-discovered.
- **Slash commands** → `plugins/<name>/commands/*.md`.
- **Subagents** → `plugins/<name>/agents/*.md`.
- **Hooks / MCP servers** → declared in the plugin's `plugin.json` (or a
  `hooks/` dir). See the Claude Code plugin docs.

A `_source/` directory (our own convention, prefixed with `_` so the loader
ignores it) is where we keep a skill's editable source, tests, and build script
when the shipped artifact is a built subset. See
[`plugins/d2-diagrams/README.md`](plugins/d2-diagrams/README.md) for the pattern.

### Adding / updating a plugin

1. Create or edit files under `plugins/<name>/`.
2. Make sure `plugins/<name>/.claude-plugin/plugin.json` has a `name`,
   `version`, and `description`.
3. Ensure the plugin is listed in `.claude-plugin/marketplace.json`.
4. Bump the plugin `version` so installs pick up the change.
5. Commit and push. Users update with `/plugin marketplace update claude-goodies`.

### Plugin sources

- **d2-diagrams** — vendored from `~/innovation/d2diag`. This repo is now the one
  place it lives; edit it here.
- **bower** — referenced directly from
  <https://github.com/ANU-HDRH/bower-framework> (branch `plugin-marketplace`) via
  an external `source` entry in `marketplace.json`. It is not vendored into this
  repo; edit it in its own repo.

---

## References

- Claude Code plugins & marketplaces:
  <https://docs.anthropic.com/en/docs/claude-code/plugins>
