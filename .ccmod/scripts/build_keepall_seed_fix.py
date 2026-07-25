"""Fix the ActorClass bug on the 2 furnace-rule GetAllActorsOfClass nodes.

ROOT CAUSE: GetAllActorsOfClass's OutActors pin type is DERIVED from ActorClass at
compile time, not independently settable -- setting only OutActors.PinSubCategoryObject
(what the original seed script did) gets silently resynced back to match ActorClass
on the next compile. The actual runtime filter lives on ActorClass's DefaultObject,
which the original script never touched, so both new GAC nodes kept querying for
BP_PL_CraftingStation_Wood (copied from the template) instead of Furnace. Confirmed
by playtest: both new rules resolved to the Wood station, Furnace was never actually
protected (Dry Wood fully swept there, identical to the unruled Furnace2 control).

THE FIX is purely 2 property edits on the 2 already-correctly-wired nodes found in
the live graph (K2Node_CallFunction_14 for the Ironstone rule's chain, _15 for Dry
Wood's) -- no topology change, no rewiring, nothing else in the 152-node graph is
touched.
"""
import sys

CCMOD = r"<CCMOD_HOME>"
sys.path.insert(0, CCMOD)
from ccmod import db
from ccmod.t3d import parse
from ccmod.workspace import Workspace

MOD = r"<MOD_ROOT>"

FURNACE_CLASS = ("/Game/Systems/Building/Placeables/BP_PL_CraftingStation_Furnace."
                  "BP_PL_CraftingStation_Furnace_C")

ws = Workspace.resolve()
conn = db.connect(ws.cache_db)
row = conn.execute("SELECT t3d FROM graphs WHERE name=?", ("modcontroller_keepall_fix_base",)).fetchone()
assert row, "run `ccmod pull --save modcontroller_keepall_fix_base` first"
g = parse(row[0])
print("pulled nodes:", len(g.nodes))


def pin(n, name):
    p = n.pin_by_name(name)
    assert p, f"{n.name} has no pin {name}"
    return p


def setf(n, pn, k, raw):
    pin(n, pn)._set(k, raw)


def bgc(path):
    return f'''"/Script/Engine.BlueprintGeneratedClass'{path}'"'''


def cls_ref(path):
    return f'''"/Script/CoreUObject.Class'{path}'"'''


# --- locate the 2 buggy GAC nodes by tracing from the KeepAll MakeStruct nodes -
targets = []
for n in g.nodes:
    if n.class_path.endswith("K2Node_MakeStruct"):
        tidp = pin(n, "TemplateID_6_7331DAFA4369B9E2C105A59FAAA510CD")
        kap = pin(n, "KeepAll_10_A6025F204FE4948B8C46EE8626A13B30")
        if tidp._get("DefaultValue") in ('"11001"', '"18025"') and kap._get("DefaultValue") == '"True"':
            targets.append((n, tidp._get("DefaultValue")))

assert len(targets) == 2, f"expected exactly 2 KeepAll MakeStruct nodes (Ironstone+DryWood), found {len(targets)}"

gac_nodes = []
for makestruct, tid in targets:
    uid = g.by_name(pin(makestruct, "Container_4_62E0F0614C1CC5F95CAE6B97F57E9504").links[0][0])
    item = g.by_name(pin(uid, "self").links[0][0])
    gac = g.by_name(pin(item, "Array").links[0][0])
    ac = pin(gac, "ActorClass")
    before = ac._get("DefaultObject")
    assert before == '"/Game/Systems/Building/Placeables/BP_PL_CraftingStation_Wood.BP_PL_CraftingStation_Wood_C"', \
        f"unexpected ActorClass on {gac.name}: {before}"
    gac_nodes.append((gac, tid))
    print(f"located buggy GAC for TemplateID {tid}: {gac.name} (currently Wood)")

# --- the fix: retype ActorClass.DefaultObject on both -- OutActors will re-derive
# correctly from this on the DevKit's own compile, exactly like the Wood original -
for gac, tid in gac_nodes:
    setf(gac, "ActorClass", "DefaultObject", bgc(FURNACE_CLASS))
    print(f"fixed {gac.name} (TemplateID {tid}) -> ActorClass now Furnace")

# --- validate --------------------------------------------------------------------
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

out = MOD + r"\.ccmod\graphs\keepall_seed_fix.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"nodes: {len(g.nodes)}   wrote: {out}")
print(f"problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
