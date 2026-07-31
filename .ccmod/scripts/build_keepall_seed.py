"""KeepAll spike: seed 2 real KeepAll=true rules at the Furnace (actor 81).

Full pull-edit-repaste of the ModController EventGraph -- this graph has been
repasted whole many times already (3R through 3W), unlike ApplyKeepRule's function
body, so this is the well-trodden path, not a new risk.

THE EDIT: splice 2 more rules into the existing hardcoded seed block, right after
the Silk rule's Array_Add and before the "STOCKER_3Q seeded 2 rules" print. Same
pattern as the existing Wood/Silk rules: GetAllActorsOfClass(station class) ->
GetArrayItem[0] -> GetActorUniqueID -> Make S_KeepRule -> Array_Add(KeepRulesV2).

New rules, from the live save DB (Game_0.db, game closed, copy verified):
  Furnace (actor 81, BP_PL_CraftingStation_Furnace) currently holds
  Ironstone 11001 qty~4988 (the ore) and Dry Wood 18025 qty~5998 (the fuel) --
  both would get swept to ~0 on the next tidy pass without this rule. Iron Bar
  11501 (~3005, the smelted output) is deliberately left UNRULED as a control --
  it should keep tidying normally.

  Container=Furnace, TemplateID=11001 (Ironstone), Keep=0 (unused, KeepAll bypasses
  the excess/deficit math entirely), KeepAll=True
  Container=Furnace, TemplateID=18025 (Dry Wood),   Keep=0, KeepAll=True

Furnace2 (82) is left unruled on purpose -- a second control. If the fix works,
81's ore/fuel should survive a tidy pass untouched while 82's identical stacks get
swept to storage, in the same playtest.
"""
import sys

import os, pathlib
CCMOD = os.environ.get("CCMOD_HOME") or str(pathlib.Path(__file__).resolve().parents[3] / "claude-conan-modder")
sys.path.insert(0, CCMOD)
from ccmod import db
from ccmod.t3d import parse, connect, connect_exec
from ccmod.t3d.generator import instantiate
from ccmod.t3d.model import Graph
from ccmod.workspace import Workspace

import pathlib
MOD = str(pathlib.Path(__file__).resolve().parents[2])

FURNACE_CLASS = ("/Game/Systems/Building/Placeables/BP_PL_CraftingStation_Furnace."
                  "BP_PL_CraftingStation_Furnace_C")
IRONSTONE_TID = "11001"
DRYWOOD_TID = "18025"

ws = Workspace.resolve()
conn = db.connect(ws.cache_db)
row = conn.execute("SELECT t3d FROM graphs WHERE name=?", ("modcontroller_keepall_verify",)).fetchone()
assert row, "run `ccmod pull --save modcontroller_keepall_verify` first"
g = parse(row[0])
print("pulled nodes:", len(g.nodes))


def pin(n, name):
    p = n.pin_by_name(name)
    assert p, f"{n.name} has no pin {name}"
    return p


def setf(n, pn, k, raw):
    pin(n, pn)._set(k, raw)


def setd(n, pn, v):
    setf(n, pn, "DefaultValue", f'"{v}"')


def bgc(path):
    return f'''"/Script/Engine.BlueprintGeneratedClass'{path}'"'''


def tmpl_from(graph, name):
    import copy
    n = copy.deepcopy(graph.by_name(name))
    for p in n.pins:
        p.links = []
    return Graph(nodes=[n])


def add(t):
    return instantiate(t, g)[0]


# --- verify the splice point looks exactly as expected -------------------------
addSilk = g.by_name("K2Node_CallArrayFunction_4")   # Array_Add for the Silk rule
seedPrint = g.by_name("K2Node_CallFunction_45")      # "STOCKER_3Q seeded 2 rules"
assert pin(addSilk, "then").links == [("K2Node_CallFunction_45", pin(seedPrint, "execute").pin_id)], \
    "Silk rule's Array_Add no longer points straight at the seed-end print -- re-check topology"
print("splice point verified: Array_Add(Silk).then -> seed-end print (only link)")

# --- templates, derived from the existing Wood-rule seed chain -----------------
GAC_T = tmpl_from(g, "K2Node_CallFunction_10")       # GetAllActorsOfClass(Wood)
ITEM_T = tmpl_from(g, "K2Node_GetArrayItem_1")       # [0]
UID_T = tmpl_from(g, "K2Node_CallFunction_44")       # GetActorUniqueID
RULE_T = tmpl_from(g, "K2Node_MakeStruct_0")         # Make S_KeepRule (Wood shape)
ADD_T = tmpl_from(g, "K2Node_CallArrayFunction_3")   # Array_Add(KeepRulesV2)
GETVAR_T = tmpl_from(g, "K2Node_VariableGet_50")     # Get KeepRulesV2


def furnace_rule(template_id):
    gac = add(GAC_T)
    setf(gac, "OutActors", "PinType.PinSubCategoryObject", bgc(FURNACE_CLASS))
    item = add(ITEM_T)
    connect(gac, "OutActors", item, "Array")
    uid = add(UID_T)
    connect(item, "Output", uid, "self")
    rule = add(RULE_T)
    setd(rule, "TemplateID_6_7331DAFA4369B9E2C105A59FAAA510CD", template_id)
    setd(rule, "Keep_8_5132904E4CC17522C07075A43E93B26E", "0")
    setd(rule, "KeepAll_10_A6025F204FE4948B8C46EE8626A13B30", "True")
    connect(uid, "UniqueID", rule, "Container_4_62E0F0614C1CC5F95CAE6B97F57E9504")
    getvar = add(GETVAR_T)
    addcall = add(ADD_T)
    connect(getvar, "KeepRulesV2", addcall, "TargetArray")
    connect(rule, "S_KeepRule", addcall, "NewItem")
    connect_exec(gac, uid, "then", "execute")
    connect_exec(uid, addcall, "then", "execute")
    return gac, addcall


gacOre, addOre = furnace_rule(IRONSTONE_TID)
gacFuel, addFuel = furnace_rule(DRYWOOD_TID)

# --- rewire exec: Silk's Array_Add -> ore rule -> fuel rule -> seed-end print --
pin(addSilk, "then").links = []
pin(seedPrint, "execute").links = []
connect_exec(addSilk, gacOre, "then", "execute")
connect_exec(addOre, gacFuel, "then", "execute")
connect_exec(addFuel, seedPrint, "then", "execute")

# --- layout: tuck the new chain below the existing seed block ------------------
gacOre.set_position(3200, 2600)
addOre.set_position(3600, 2600)
gacFuel.set_position(3200, 2800)
addFuel.set_position(3600, 2800)

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

wilds = [(n.name, p.name) for n in g.nodes for p in n.pins
         if p._get("PinType.PinCategory") == '"wildcard"']
assert not wilds, f"unresolved wildcards: {wilds}"

out = MOD + r"\.ccmod\graphs\keepall_seed.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"nodes: {len(g.nodes)}   wrote: {out}")
print(f"problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
