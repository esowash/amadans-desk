# Development environment

---

## ⚠ HANDOFF — current state (2026-07-10) — READ FIRST

This supersedes any conflicting detail further down.

### 🎉 OBJECTIVE 4 IS CLOSED — the full pipeline works end to end

`create mod → add asset → Build mod → cook → pak → Steam Workshop upload` all proven.
**`ZZTest` is published Hidden as Steam file id `3761708831`**
(`modinfo.json` → `steamWorkshopFileIds.mainClient`; `steamVisibility: 2` = Hidden).
No Steam Workshop Legal Agreement prompt appeared — that consent was already on file for
the publishing account.

**P1 → P2 → P3 building on `Stocker` is now unblocked.**

#### Publishing gotchas
- **A preview image is mandatory.** Uploading without one aborts with *"No preview image
  found or the path is invalid. You must select a valid preview image before you can
  submit it to Steam!"* — nothing is uploaded and no Workshop item is created. Any PNG
  < 1 MB works (we used a generated 512×512, 4.9 KB). *Select preview image* opens a
  **native** file dialog, which accepts normal typing (unlike Slate fields).
- Dropping the PNG under `Content\Mods\<Mod>\` triggers the editor's *"A change to a
  source content file has been detected. Would you like to import it?"* toast — click
  **Don't Import**, or it becomes a mod asset.
- The upload confirmation warns it **cannot be canceled** (but the item can be deleted
  from the Workshop afterward). On success `Steam file id` fills in and *Steam Workshop
  Page* / *Update mod info to Steam* become enabled.

### The build path — `ModPak code 28` is fixed

A trivial mod (`ZZTest` + one `BP_PipelineTest` Actor Blueprint) went **cook → pak**
cleanly: *"Mod built successfully. The mod is ready for usage!"* + a
*"Pak generation completed!"* toast. Build took **~2 minutes**. Artifacts:

- `UE4\Saved\Mods\ZZTest\Output\ZZTest.pak` (120 KB — the uploadable artifact)
- `UE4\Saved\Mods\ZZTest\Staged\ZZTest-{Windows,WindowsServer,LinuxServer}.{pak,ucas,utoc}`
- Cooked asset for all 3 platforms at
  `UE4\Saved\Mods\_Cooked\<Platform>\ConanSandbox\Content\Mods\ZZTest\BP_PipelineTest.{uasset,uexp}`

**Root cause of the old failure — confirmed.** The blocker was the *unregistered,
hand-created mod folder*, not the long path. A **properly registered** mod emits a
mod-qualified package path, so the mount resolves:

| | `PackageList.txt` contains | Result |
|---|---|---|
| Old (hand-made folder) | `/Game/BP_PipelineTest` | `Unable to find package` → `ModPak code 28` |
| Now (registered mod) | `/Game/Mods/ZZTest/BP_PipelineTest` | cooks + paks ✅ |

Note the `.pak` itself holds only `AssetRegistry.bin` + `ModCompat.bin`; **the Blueprint
ships inside the IoStore `.ucas`/`.utoc`** (see `Staged\Windows-PakListIoStore.txt`).

### Post-reinstall fixes — DONE
1. ✅ **PSO fix re-applied** — `bShareMaterialShaderCode=False` at
   `C:\CEUE5Devkit\UE4\Config\DefaultGame.ini` line 127, under
   `[/Script/UnrealEd.ProjectPackagingSettings]` (only occurrence in `Config\`). Still
   **required**: it is what stops the shader pipeline-cache (PSO) step from looping.
2. ✅ **Start-menu shortcut repointed.** `Conan Dev Kit.lnk` *existed* but still aimed at
   the deleted `C:\Program Files\Epic Games\CEUE5Devkit\...`. Now →
   `C:\CEUE5Devkit\Engine\Binaries\Win64\UnrealEditor.exe`, args
   `"C:\CEUE5Devkit\UE4\ConanSandbox.uproject" -ModDevKit`. (`request_access` picked up
   the new target immediately.)
3. ✅ **No junction.** `Content\Mods` contains no reparse points — the uninstaller can no
   longer delete through one into the repo. Mod content currently lives **only** in the
   DevKit; the repo↔DevKit sync is still an open decision (prefer copying).

### Dev Kit was reinstalled to a short path
- **Location: `C:\CEUE5Devkit`.** The old `C:\Program Files\Epic Games\CEUE5Devkit` is
  **gone**. Version now reads **Conan Exiles Devkit 1001 (1.3.2)** (was 1.3.0).
- Short paths were *not* the pak blocker (see above), but keep them anyway — the
  DevKit's own tooltip showed `Cooking Filepath Length: 145/260` for a trivial asset
  under the old path.

### The mod is now named **Stocker**
- The **mod** = **`Stocker`** (renamed from an earlier placeholder; short name also keeps paths short).
- The **follower thrall NPC** is named **"Amadan Cnoic"** and his bench **"Amadan's Desk"**
  (finalized 2026-07-13, replacing an earlier placeholder name). See
  [`design.md`](design.md).
- Repo folder renamed to **`Mods/Stocker/`**.
- Both `Stocker` and `ZZTest` are registered. **`ZZTest` is currently the active mod.**

### The mod menu — exact labels
A **downward caret in the main toolbar, immediately LEFT of the Play button**
(`x≈460, y≈58` in 1456-px screenshots). It expands to exactly two entries:

- **`Select active mod`** → submenu listing every registered mod; the **currently active
  one is greyed out**. Picking a different mod reloads the Dev Kit.
- **`Create a new mod…`**

(Earlier notes said "Create new mod / Open existing mod" and placed the caret top-right —
both wrong.) The active mod is marked on disk by an empty **`active.txt`** in its folder,
and is the only mod mounted in the Content Browser (under `/All/Game/Mods/<Mod>`).

---

## Machines

| Role | Host | Specs | Notes |
|------|------|-------|-------|
| Mod editing / build / test | the **build box** (desktop) | RTX 4060 Ti **16 GB**, i7-12700K (12C/20T), 32 GB RAM, 1.8 TB NVMe (415 GB free), Win 11 (build 26200) | Runs the UE 5.6.1 Dev Kit and Conan Exiles Enhanced. Green across the board; only future-upgrade note is RAM (32 GB is the comfortable floor). |
| Version control / orchestration | a **secondary box** | Integrated graphics only | Cannot run the UE5 editor. Handles git, backups, scripted/headless steps. |

## Toolchain

| Tool | Purpose |
|------|---------|
| Steam + **Conan Exiles Enhanced** (App 440900) | Live in-game testing. Enhanced is **Steam-only**. |
| **Epic Games Launcher** | Delivery channel for the Dev Kit (Modding tab). |
| **Conan Exiles Dev Kit (UE 5.6.1)** | The modified UE5 editor — assets, Blueprints, meshes, maps, Play-In-Editor. Blueprint-only; no C++. |
| Zen Server (bundled with the Dev Kit) | UE5 Derived Data Cache. Defaults to AppData; relocatable if space-limited. |
| SteamCMD (optional) | Headless Workshop uploads. |
| Conan Mod & Server Manager (Nexus, optional) | Load order, config backups, restore-vanilla for the test loop. |

## Setup runbook (run on the build box)

1. Install **Steam** → Conan Exiles Enhanced (App 440900).
2. Install **Epic Games Launcher** → **Modding** tab → download the **Conan Exiles
   Dev Kit** (UE 5.6.1). Large download; budget disk on C:.
3. Update to the latest **NVIDIA Studio driver** before first editor launch.
4. Install **Claude Code** on the build box and connect a persistent-memory MCP so the
   dev machine shares the homelab memory store.
5. Clone this repo on the build box (`gh repo clone esowash/amadans-desk`). Run
   `git lfs install` once so binary UE assets are handled.
6. **First-run sanity test** — launch the Dev Kit, open a sample mod, hit
   **Play-In-Editor** to confirm the build box drives the UE5.6 editor.
7. **Publish-path test** — push a trivial throwaway mod via **Mod Info → Steam
   Workshop** to find out whether the reported UAT packaging bug affects us.

## Known caveat: Dev Kit packaging

The Enhanced Dev Kit has been reported to ship in "installed-build" mode that
breaks the standard `RunUAT BuildPlugin` / `BuildMod` path (missing precompiled
rules DLLs; UAT deletes its own `deps.json`). Community workaround is a headless
Python + `UnrealEditor-Cmd` + `UnrealPak` + SteamCMD pipeline.
Ref: <https://github.com/daveCode-dot/aegis-ue5-modkit>

We start with the **official Dev Kit UI** and only fall back to the headless
pipeline if step 7 fails.

## Content + git workflow

- The mod's UE content lives under the Dev Kit's `Content/Mods/Stocker/`.
- Keep the git working tree pointed at that content (clone into place, or clone
  elsewhere and junction). Binary `.uasset`/`.umap` go through **Git LFS**
  (configured in `.gitattributes`).
- Cooked output (`.pak`/`.ucas`/`.utoc`) is **git-ignored** — distribution is via
  Steam Workshop, not the repo.

---

## Dev Kit findings (verified on the build box, 2026-07-09)

### Environment + sanity
Toolchain all present. Dev Kit at `C:\CEUE5Devkit`
(**Conan Exiles Devkit 1001 / 1.3.0**, UE 5.6.1, CL 366792, `++exiles+release`);
editor `Engine\Binaries\Win64\UnrealEditor.exe`, project `UE4\ConanSandbox.uproject`,
launcher `RunDevKit.bat`. `Engine\Build\InstalledBuild.txt` **is present**
(installed build). **Play-In-Editor works**: default level `AlmostEmpty`, PIE start
~8.5 s, reached the character-creation screen; only benign offline/DLC log noise.

### Creating a mod — use the built-in flow (do NOT hand-create folders)
On this installed build, only mods the Dev Kit has **registered** are writable;
`SavePackage` rejects a hand-made (even junctioned) mod folder with `Error saving …`.
Correct flow:

1. Click the **caret in the main toolbar immediately LEFT of the Play button** →
   **"Create a new mod…"** → enter a name → **Create**.
2. The Dev Kit **restarts** with the new mod loaded, registered (writable), and marked
   active via an empty `active.txt` in the mod folder.
3. A registered mod's writable content lives at **`Content/Mods/<ModName>/Local/`** —
   assets sit *directly* in `Local/`, **not** in a `Local/Content/` subfolder. Verified:
   saving `BP_PipelineTest` produced
   `Content\Mods\ZZTest\Local\BP_PipelineTest.uasset`. Its runtime path is
   **`/Game/Mods/<ModName>/<Asset>`**. At game load the mod's **Mod Controller** merges
   its tables + blueprint-components.

> Repo implication: our real assets belong under `Mods/Stocker/Local/`.

### Build & publish (Mod Info panel: `Window → Conan Exiles Devkit`)
Fill Name/Author/Version, then **Build mod** (local cook; options: Compress .pak,
Compile All Modded Blueprints). An **empty** mod aborts with *"No modded files found"*.
Below Build is the **Steam** upload section (visibility defaults to **Hidden**).

**`Choose Assets For Cook`** opens *Select Content For Mod*, listing each asset with its
runtime path and a green **`(Mod Asset)`** type tag — a fast way to confirm the DevKit
sees your asset as belonging to the mod before you spend a build on it. Confirm with
**Choose Selected**. A **"Building might take a long while"** prompt precedes the build.

**Publish-path — SOLVED (2026-07-09). Official/GUI path works end to end.**
The DevKit's *Build mod* uses a direct `UnrealEditor-Cmd -run=Cook -NoCompile`
(NOT the broken `RunUAT BuildPlugin`/`BuildMod`), so the famous UAT-DLL bug never
blocked us. Two real walls, both now down:

1. **PSO shader pipeline-cache merge** (~9,816-shader global cache). The GUI cook
   **OOM-crashed** there (single ~27 GB allocation); a headless cook (`-nullrhi`)
   avoided the OOM but **hung** at the same step. Fixed two ways, both applied:
   `bShareMaterialShaderCode=False` **skips** the step, and the page file was enlarged to
   96 GB (commit limit ~128 GB).
2. **Mod-content mount.** The cook reported `Unable to find package for cooking
   /Game/<asset>`. **Cause: the mod folder was hand-created, not registered.** Creating
   the mod through *Create a new mod…* makes the DevKit emit the mod-qualified path
   `/Game/Mods/<Mod>/<Asset>` into `Saved\Mods\_Cooked\PackageList.txt`, which resolves.
   The `aegis-ue5-modkit` headless workaround is **no longer needed**.

The full GUI build (cook + pak, 3 platforms) takes **~2 minutes** for a trivial mod.
Still untested: the Steam Workshop (Hidden) upload.

**CLI gotcha:** pass space-containing path args whole-token-quoted with forward
slashes — `"-PackagesList=C:/Program Files/.../PackageList.txt"` — else UE truncates
at the space (`Couldn't read package list C:\Program`).

### Driving the editor via computer-use
- Text `type` does **not** reach UE Slate fields; use **clipboard paste** (`Ctrl+A`,
  `Ctrl+V`) — confirmed working for the Content Browser's inline rename. Native file
  dialogs accept normal typing.
- ⚠ `open_application` on the Dev Kit **launches a second editor instance** (same
  command line). The duplicate spins forever on
  `Failed to open database … FileInfo.db: disk I/O error` because the first editor holds
  the lock, while eating ~10 GB. **Never use `open_application` to refocus** — use
  `(New-Object -ComObject WScript.Shell).AppActivate($pid)`. If one does spawn it has no
  main window, so `CloseMainWindow()` is a no-op; `Stop-Process -Force` is the only way
  out.
- `Escape` does **not** dismiss Slate menus — click elsewhere instead.
- ⚠ **Windows `TextInputHost.exe` can wedge itself as the foreground window**, blocking
  every computer-use click with *"Textinputhost is not in the allowed applications and is
  currently in front."* Its window is an invisible ghost parked at `-32000,-32000`.
  `AppActivate`, `SetForegroundWindow` (even with `AttachThreadInput`), `ShowWindow(HIDE)`
  on the ghost, and minimize/restore of the editor **all fail** to reclaim focus.
  `request_access` for it is refused. The only fix found: **`Stop-Process -Force` on
  `TextInputHost`** (a system component — it respawns on next use, nothing is lost).
  Needs operator authorization, since the auto-mode classifier blocks the kill.
- Monitor via the log `UE4\Saved\Logs\ConanSandbox.log` (grep it), not the on-screen
  Output Log. Engine init ≈ **100 s** (marker:
  `LogLoad: (Engine Initialization) Total time:`).
- ⚠ The cook's own log — `Engine\Programs\AutomationTool\Saved\Cook-<timestamp>.txt`,
  named in the child `UnrealEditor-Cmd` command line — is **deleted on success**. Do not
  poll it for a completion marker (you will wait forever). Watch for
  `UE4\Saved\Mods\<Mod>\Output\<Mod>.pak` to appear, or the editor's success dialog.

---

## Objective 4 — CLOSED (2026-07-10)

✅ Page file (96 GB) ✅ PSO fix ✅ Cook + pak (`ZZTest.pak`) ✅ Hidden Workshop upload
(`3761708831`).

No SteamCMD needed: *Mod Info → Upload built mod to Steam* drives the Steam client
directly. Feasibility for the mod itself is **GO across the board**, so **P1 → P2 → P3
building on `Stocker` is unblocked.**

### Next session — start P1
P1 = the Keep-manifest reclaim logic (instant transfer, stationary bench) per
[`design.md`](design.md). `Stocker` is registered but **not** the active mod — switch to
it via the toolbar caret → *Select active mod* → `Stocker`, which reloads the Dev Kit.
Its assets go in `Content\Mods\Stocker\Local\`. Decide the repo↔DevKit sync (copy, not
junction) before authoring much.
