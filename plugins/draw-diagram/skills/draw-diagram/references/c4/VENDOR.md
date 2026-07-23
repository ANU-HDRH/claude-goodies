# Vendored: C4-PlantUML

- **Source:** `plantuml-stdlib/C4-PlantUML` (https://github.com/plantuml-stdlib/C4-PlantUML)
- **Version:** v2.13.0
- **Licence:** MIT (see `LICENSE` in this directory)

Files: `C4.puml`, `C4_Context.puml`, `C4_Container.puml`, `C4_Component.puml`,
`C4_Deployment.puml`, `C4_Dynamic.puml`, `C4_Sequence.puml`.

## Local/offline use requires `-DRELATIVE_INCLUDE=1`

`C4_Container.puml` (and the other layer files) guard their include of
`C4_Context.puml` / `C4.puml` with `!if %variable_exists("RELATIVE_INCLUDE")`:
with the variable set they include the sibling `./C4_Context.puml` locally, else
they fetch it from GitHub over the network. So to render OFFLINE against this
vendored chain you MUST pass `-DRELATIVE_INCLUDE=1` to plantuml (else the
`C4_*.puml` files fetch `C4_Context`/`C4` from GitHub). This vendored copy makes
the skill independent of network at render time.
