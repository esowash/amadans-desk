"""Read a playtest's ConanSandbox.log and answer, in order, the questions that actually decide
whether a result means anything.

The order matters. A silent log looks identical whether the mod never mounted, the graph never
ran, or the graph ran and the game rejected what it did - so the mount gate comes first and no
later section should be read as a result until it passes.

Usage:
    python analyze_playtest_log.py [path-to-ConanSandbox.log]

Defaults to $CONAN_LOG if set. The stock location is
<Steam>/steamapps/common/Conan Exiles/ConanSandbox/Saved/Logs/ConanSandbox.log
"""
import os
import re
import sys
import pathlib

log_path = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("CONAN_LOG")
if not log_path:
    sys.exit("give a log path as argv[1] or set $CONAN_LOG")
text = pathlib.Path(log_path).read_text(encoding="utf-8", errors="replace")
lines = text.splitlines()
print(f"{log_path}\n{len(lines)} lines\n")


def section(title, patterns, limit=40, flags=re.I):
    rx = re.compile("|".join(patterns), flags)
    hits = [l for l in lines if rx.search(l)]
    print(f"{'=' * 78}\n{title}   [{len(hits)} hits]")
    for l in hits[:limit]:
        print("   " + l.strip()[:200])
    if len(hits) > limit:
        print(f"   ... {len(hits) - limit} more")
    print()
    return hits


# 1. GATE - nothing below this means anything if the mod never mounted (test-loop gotcha #5).
# "Any AddActiveModControllerClass lines at all" is NOT the test: a stock session registers 16
# built-in DLC controllers, so a bare non-empty check passes on a session with no mod loaded.
# The real test is a controller under /Game/Mods/ specifically.
print("=" * 78 + "\n1. MOD MOUNT GATE")
mounts = [l for l in lines if "Mounting mod pak file" in l]
controllers = [l for l in lines if "AddActiveModControllerClass" in l]
ours = [l for l in controllers if "/Game/Mods/" in l]
print(f"   'Mounting mod pak file'      : {len(mounts)}")
for l in mounts[:5]:
    print("      " + l.strip()[:180])
print(f"   AddActiveModControllerClass  : {len(controllers)} total, {len(ours)} under /Game/Mods/")
for l in ours[:5]:
    print("      " + l.strip()[:180])
if not ours:
    print("\n   !! FAIL - no mod controller registered. The pak did not load, or the mod is not\n"
          "      enabled in the in-game Mods menu. Everything below is meaningless; fix this first.")
else:
    print("\n   PASS - our mod controller is registered.")
print()

# 2. Our own checkpoints. MENU_CAMP is this session's camp-trio instrumentation.
section("2. MENU_CAMP checkpoints (camp trio)", [r"MENU_CAMP"])
section("3. All other MENU_ / mod prints", [r"MENU_(?!CAMP)", r"SAVECLICK", r"STOCKER_"])

# 4. THE decisive signal for the render bug. Amadan has never once produced this line.
# Raw hits are useless here - a populated world emits thousands, almost all props (banners,
# awnings, tents). What matters is the ASSET each line is recreating clothing FOR: character
# spawns show up as underwear/hair/armour assets, props do not. Summarise by asset and surface
# the character-shaped ones.
from collections import Counter

print("=" * 78 + "\n4. Recreating Clothing Actors (the render signal)")
rx = re.compile(r"Recreating Clothing Actors for '([^']*)' with '([^']*)'")
assets = [m.group(2) for l in lines for m in [rx.search(l)] if m]
print(f"   {len(assets)} total")
CHAR = re.compile(r"underwear|hair|beard|armor|armour|body|head|torso|leg|feet|hand|cloth_char",
                  re.I)
char_assets = Counter(a for a in assets if CHAR.search(a))
prop_assets = Counter(a for a in assets if not CHAR.search(a))
print(f"\n   character-shaped assets ({sum(char_assets.values())} lines, "
      f"{len(char_assets)} distinct):")
for a, c in char_assets.most_common(20):
    print(f"      {c:5}  {a}")
if not char_assets:
    print("      (none - no character ever had clothing assembled this session)")
print(f"\n   prop/other assets: {sum(prop_assets.values())} lines, "
      f"{len(prop_assets)} distinct (top 5: {[a for a, _ in prop_assets.most_common(5)]})")
print()

# 5. The spawn pipeline's own complaints.
section("5. Spawn / camp / territory errors",
        [r"SpawnTable", r"weighted table", r"NPCTerritorySpawner", r"RegisterCamp",
         r"camp.*(fail|error|invalid)", r"could not find"])

# 6. Blueprint runtime failures - these are silent in-game but loud here.
section("6. Blueprint runtime errors",
        [r"Accessed None", r"Attempted to access index", r"Blueprint Runtime Error",
         r"is not valid|invalid.*blueprint"])

# 7. Known Amadan-specific errors from prior sessions, for comparison against the old failure mode.
section("7. Known prior-failure signatures",
        [r"No animation instance found", r"does not have a valid UID", r"StartEmoteInternal"])

# 8. Anything naming Amadan at all.
section("8. Amadan mentions", [r"Amadan"], limit=30)
