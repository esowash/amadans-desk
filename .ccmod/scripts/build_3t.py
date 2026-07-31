"""Author stocker_3t.t3d -- multi-station STEP B: pass 1 iterates ManagedStations.

Operates on the FULL live graph (pull-edit-repaste), per stocker-full-graph-edits.

Wraps the existing per-item tidy loop (fe1) inside a NEW outer ForEach over
ManagedStations (the 5 stations 3S confirmed: Wood, Artisan, Metal, Furnace,
Furnace2). Two data pins get rewired from the hardcoded Wood station
reference to the outer loop's current element:
  - woodInv.owner (GetInventoryByType) -- confirmed its ONLY consumer is
    ilist (ItemList), safe to rewire in place, no fresh copy needed.
  - call1.Station (ApplyKeepRule's tidy call).

The hardcoded woodItem reference ITSELF is left alone and still feeds 3Q's
seed step (callWoodUid) unchanged -- KeepRulesV2's two rules still name the
Wood station specifically; that's a UI concern, not a tidy-loop concern.

Exec restructure (nested nested nested ForEach, standard pattern): the inner
loop's OLD completion signal (fe1.Completed -> resolve_begin, i.e. "run
restock once tidy is done") gets moved to the OUTER loop's completion instead
(feStations.Completed -> resolve_begin) -- restock must run once total, after
ALL stations are tidied, not once per station. fe1.Completed itself is left
dangling once nested inside feStations' LoopBody: that's how a nested
ForEachLoop macro naturally signals "this station is done, advance to the
next" -- no explicit continuation node needed, per how the macro's internal
looping works.
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
LIB = CCMOD + r"\library"
WLIB = MOD + r"\.ccmod\library"

PRE = "/Game/Systems/Building/Placeables/"
BASE_CONTAINER = PRE + "BP_PlaceableItemContainer.BP_PlaceableItemContainer_C"

ws = Workspace.resolve()
conn = db.connect(ws.cache_db)
row = conn.execute("SELECT t3d FROM graphs WHERE name=?", ("stocker_3t_base",)).fetchone()
assert row, "run `ccmod pull --save stocker_3t_base` first"
g = parse(row[0])
print("pulled nodes:", len(g.nodes))


def pin(n, name):
    p = n.pin_by_name(name)
    assert p, f"{n.name} has no pin {name}"
    return p


def tmpl_file(path):
    t = parse(open(path, encoding="utf-8-sig").read())
    for n in t.nodes:
        for p in n.pins:
            p.links = []
    return t


def add(t):
    return instantiate(t, g)[0]


def setf(n, pn, k, raw):
    pin(n, pn)._set(k, raw)


def bgc(path):
    return f'''"/Script/Engine.BlueprintGeneratedClass'{path}'"'''


def type_foreach(node, subobj_raw):
    setf(node, "Array", "PinType.PinCategory", '"object"')
    setf(node, "Array", "PinType.PinSubCategoryObject", subobj_raw)
    setf(node, "Array", "PinType.ContainerType", "Array")
    setf(node, "Array Element", "PinType.PinCategory", '"object"')
    setf(node, "Array Element", "PinType.PinSubCategoryObject", subobj_raw)
    setf(node, "Array Element", "PinType.ContainerType", "None")


# --- identify fixed structural anchors (confirmed by content-trace) --------
call1 = g.by_name("K2Node_CallFunction_118")     # pass1's ApplyKeepRule
fe1 = g.by_name("K2Node_MacroInstance_2")        # pass1's per-item ForEach
woodItem = g.by_name("K2Node_GetArrayItem_1")    # hardcoded Wood station ref
woodInv = g.by_name("K2Node_CallFunction_1757")  # GetInventoryByType(woodItem,...)
feCache = g.by_name("K2Node_MacroInstance_7")    # RuleTemplateID cache ForEach
resolve_begin = g.by_name("K2Node_DynamicCast_6")  # cast2, restock start

assert pin(call1, "Station").links[0][0] == woodItem.name
assert pin(woodInv, "owner").links[0][0] == woodItem.name
assert len(pin(woodInv, "ReturnValue").links) == 1
assert pin(woodInv, "ReturnValue").links[0][0] == "K2Node_VariableGet_3", "woodInv has extra consumers"
assert pin(fe1, "Exec").links[0][0] == feCache.name
assert pin(fe1, "Completed").links[0][0] == resolve_begin.name

FEACH_T = None
for n in g.nodes:
    if n.class_path.endswith("K2Node_MacroInstance"):
        arr = n.pin_by_name("Array")
        if arr and arr.category == "object":
            import copy
            nn = copy.deepcopy(n)
            for p in nn.pins:
                p.links = []
            FEACH_T = Graph(nodes=[nn])
            break
assert FEACH_T

GET_STATIONS_T = tmpl_file(WLIB + r"\stocker\get_managed_stations.t3d")

# --- build the outer ForEach over ManagedStations ---------------------------
stationsGet = add(GET_STATIONS_T)
feStations = add(FEACH_T)
type_foreach(feStations, bgc(BASE_CONTAINER))
connect(stationsGet, "ManagedStations", feStations, "Array")

# --- rewire: woodInv.owner and call1.Station -> feStations' current station
pin(woodInv, "owner").links = []
connect(feStations, "Array Element", woodInv, "owner")
pin(call1, "Station").links = []
connect(feStations, "Array Element", call1, "Station")

# woodItem still legitimately feeds 3Q's seed step -- strip only the two
# stale reverse entries we just detached above, keep the rest
woodItem_out = pin(woodItem, "Output")
woodItem_out.links = [(tn, tp) for (tn, tp) in woodItem_out.links
                       if tn not in (woodInv.name, call1.name)]

# --- rewire exec: feCache.Completed -> feStations -> (LoopBody) -> fe1 -----
pin(feCache, "Completed").links = []
pin(feStations, "Exec").links = []
connect_exec(feCache, feStations, "Completed", "Exec")

pin(fe1, "Exec").links = []
pin(feStations, "LoopBody").links = []
connect_exec(feStations, fe1, "LoopBody", "Exec")

# fe1.Completed is left dangling on purpose (nested ForEach: an empty
# LoopBody-chain tail is how the outer macro knows to advance)
pin(fe1, "Completed").links = []

# --- rewire: restock now triggers off the OUTER loop's completion ----------
pin(resolve_begin, "execute").links = []
pin(feStations, "Completed").links = []
connect_exec(feStations, resolve_begin, "Completed", "execute")

# --- layout ------------------------------------------------------------------
stationsGet.set_position(-2100, -2900)
feStations.set_position(-1900, -2900)

# --- validate ---------------------------------------------------------------
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
         if p._get("PinType.PinCategory") == '"wildcard"'
         and not n.class_path.endswith("K2Node_CallArrayFunction")]
assert not wilds, f"unresolved wildcards: {wilds}"

out = MOD + r"\.ccmod\graphs\stocker_3t.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"nodes: {len(g.nodes)}   wrote: {out}")
print(f"non-reciprocal / dangling problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
