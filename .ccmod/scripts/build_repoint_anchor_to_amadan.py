"""Repoint the ModController's single-anchor gather from the retired Stygian
test stand-in to the real, now-placed Amadan's Desk.

Found while prepping the interact-event work: the anchor's GetAllActorsOfClass
(K2Node_CallFunction_8) still targets BP_PL_Table_Strategy_Stygian_C (actor 69
in the old save) -- that actor no longer exists in the current world (the
07-18 fresh baseline confirms it's gone, replaced by actor 90,
BP_PL_WorkStation_Amadan_C). ManagedStations/ManagedContainers would come back
empty on every future run until this is fixed.

Per stocker-test-loop-gotchas #12: only ActorClass's DefaultObject actually
controls the runtime filter. OutActors's declared PinSubCategoryObject is
cosmetic/derived and UE resyncs it to ActorClass's DefaultObject on every
compile regardless of what's set here -- but it's set anyway for a T3D that
reads correctly before that resync happens, matching the style already used
in keepall_seed_fix.py.

Base: modcontroller_widget_removed_compact.t3d (150 nodes, this session's own
last edit -- already reflects live-graph ground truth since the user pasted
it as-is before kicking off the current cook). Downstream of OutActors is a
plain GetArrayItem(0) (grab the single anchor instance) with no other
Stygian-specific assumptions -- confirmed by tracing pin links, not assumed.
"""
import sys

import os, pathlib
CCMOD = os.environ.get("CCMOD_HOME") or str(pathlib.Path(__file__).resolve().parents[3] / "claude-conan-modder")
sys.path.insert(0, CCMOD)
from ccmod.t3d import parse

import pathlib
MOD = str(pathlib.Path(__file__).resolve().parents[2])

BASE = MOD + r"\.ccmod\graphs\modcontroller_widget_removed_compact.t3d"
g = parse(open(BASE, encoding="utf-8").read())
print("base graph nodes:", len(g.nodes))

OLD_CLASS = "/Game/Systems/Building/Placeables/BP_PL_Table_Strategy_Stygian.BP_PL_Table_Strategy_Stygian_C"
NEW_CLASS = "/Game/Mods/Stocker/BP_PL_WorkStation_Amadan.BP_PL_WorkStation_Amadan_C"


def setf(n, pn, k, raw):
    n.pin_by_name(pn)._set(k, raw)


anchor = g.by_name("K2Node_CallFunction_8")
actorClass = anchor.pin_by_name("ActorClass")
outActors = anchor.pin_by_name("OutActors")

before = actorClass._get("DefaultObject")
assert before == f'"{OLD_CLASS}"', f"unexpected pre-state: {before}"

setf(anchor, "ActorClass", "DefaultObject", f'"{NEW_CLASS}"')
setf(anchor, "OutActors", "PinType.PinSubCategoryObject",
     f"\"/Script/Engine.BlueprintGeneratedClass'{NEW_CLASS}'\"")

after = actorClass._get("DefaultObject")
print(f"ActorClass.DefaultObject: {before} -> {after}")

# --- validate (unchanged graph shape, just one literal) -------------------------
problems = []
names = {n.name for n in g.nodes}
for n in g.nodes:
    for p in n.pins:
        for (lnn, lp) in p.links:
            if lnn not in names:
                problems.append(f"{n.name}.{p.name} -> missing {lnn}")
                continue
            other = g.by_name(lnn).pin_by_id(lp)
            if other is None:
                problems.append(f"{n.name}.{p.name} -> {lnn} missing pin {lp}")
                continue
            if (n.name, p.pin_id) not in other.links:
                problems.append(f"non-reciprocal: {n.name}.{p.name} -> {lnn}.{other.name}")

out = MOD + r"\.ccmod\graphs\modcontroller_anchor_repointed.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"\nnodes: {len(g.nodes)}   wrote: {out}")
print(f"problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
