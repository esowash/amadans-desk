# Build scripts

Python scripts that assemble Blueprint node graphs as T3D text, rather than hand-wiring
them by dragging pins in the DevKit. See [`../../docs/TECHNICAL-NOTES.md`](../../docs/TECHNICAL-NOTES.md)
for the method and its limits.

Each script generally reads one or more captured graphs from [`../graphs/`](../graphs/),
clones and rewires nodes, and writes a new paste-ready `.t3d`.

## Paths

Two locations are resolved at run time — neither is hardcoded:

| | How it resolves |
|---|---|
| `MOD` | This repo's root, derived from the script's own location. Nothing to configure. |
| `CCMOD` | The [`ccmod`](https://github.com/esowash/claude-conan-modder) tool checkout. Defaults to a **sibling directory** of this repo (`../claude-conan-modder`). Override with the `CCMOD_HOME` environment variable. |

So the zero-config layout is:

```
some-parent/
  amadans-desk/            <- this repo
  claude-conan-modder/     <- the ccmod tool
```

If `ccmod` lives somewhere else:

```powershell
$env:CCMOD_HOME = "D:\src\claude-conan-modder"
python .ccmod\scripts\build_3n.py
```

These scripts were written against the state of the graphs at the time each was run, and
are kept as a record of how each graph was produced. They are **not** a general-purpose
build system, and many will only make sense alongside the specific `.t3d` inputs they
reference.
