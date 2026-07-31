"""Author stocker_3k.t3d — three house rules through the reusable mover.

First build where the ModController does no moving itself: it gathers the
candidate containers, then calls BPFL_Stocker2::ApplyKeepRule once per rule. The
logic lives in the function; this graph is just the caller. That is the whole
point of the refactor -- rules are about to become data, and this proves the
function works before a UI starts producing them.

Flow (3H's proven front half, then three calls):
  BeginPlay -> Delay(8s)
    -> desk = GAC(BP_PL_Table_Strategy_Stygian)[0]
    -> ForEach GAC(BP_PlaceableItemContainer): dist(desk) < 3000 -> Array Add
       -> ManagedContainers
    -> Completed:
         metal = GAC(BP_PL_CraftingStation_Metal)[0]
         wood  = GAC(BP_PL_CraftingStation_Wood)[0]
         rule 1: ApplyKeepRule(metal, 11501 IronBar,        keep 20,  ManagedContainers)
         rule 2: ApplyKeepRule(metal, 18061 HardenedSteel,  keep 20,  ManagedContainers)
         rule 3: ApplyKeepRule(wood,  10011 Wood,           keep 200, ManagedContainers)
       each printing: a label, the Outcome (as its user-friendly name), and Moved.

THE TEST MATRIX -- the current save exercises three of the four termini in ONE
cook, and every rule is a real house rule rather than a contrived probe:

  rule 1  Blacksmith holds exactly 20 IronBar (3I left it at the threshold)
          -> excess 0            -> expect NoExcess,      Moved 0
  rule 2  Blacksmith holds 500 HardenedSteel; Medium chest 65 holds 500
          -> excess 480, dest exists -> expect Moved,     Moved 480
  rule 3  Wood station holds 701 Wood and is the ONLY in-range container with any
          -> excess 501, NO dest -> expect NoDestination, Moved 0   <- ORPHAN

Rules 1 and 3 both return Moved 0, which is exactly why the Outcome enum exists:
the number alone cannot tell "nothing to do" from "nowhere to put it". That
distinction IS the user's requested terminus, so printing Outcome is the test.

Post-run DB check: owner 57 HardenedSteel 500 -> 20, owner 65 -> 980;
owner 56 Wood must stay at 701 (the orphan path must not move ANYTHING).

Outcome is printed via K2Node_GetEnumeratorNameAsString, which returns the
display label ("NoDestination"), not the internal NewEnumeratorN.
"""
import copy
import sys

import os, pathlib
CCMOD = os.environ.get("CCMOD_HOME") or str(pathlib.Path(__file__).resolve().parents[3] / "claude-conan-modder")
sys.path.insert(0, CCMOD)
from ccmod.t3d import parse, connect, connect_exec
from ccmod.t3d.generator import instantiate
from ccmod.t3d.model import Graph

import pathlib
MOD = str(pathlib.Path(__file__).resolve().parents[2])
LIB = CCMOD + r"\library"
WLIB = MOD + r"\.ccmod\library"

PRE = "/Game/Systems/Building/Placeables/"
BASE_CONTAINER = PRE + "BP_PlaceableItemContainer.BP_PlaceableItemContainer_C"
DESK = PRE + "BP_PL_Table_Strategy_Stygian.BP_PL_Table_Strategy_Stygian_C"
METAL = PRE + "BP_PL_CraftingStation_Metal.BP_PL_CraftingStation_Metal_C"
WOOD = PRE + "BP_PL_CraftingStation_Wood.BP_PL_CraftingStation_Wood_C"
RANGE = "3000.000000"

i3 = parse(open(MOD + r"\.ccmod\graphs\stocker_3i.t3d", encoding="utf-8").read())


def tmpl_from(graph, name):
    n = copy.deepcopy(graph.by_name(name))
    for p in n.pins:
        p.links = []
    return Graph(nodes=[n])


def tmpl_file(path):
    g = parse(open(path, encoding="utf-8-sig").read())
    for n in g.nodes:
        for p in n.pins:
            p.links = []
    return g


GAC_T     = tmpl_from(i3, "K2Node_CallFunction_8")
GETITEM_T = tmpl_from(i3, "K2Node_GetArrayItem_0")
PRINT_T   = tmpl_from(i3, "K2Node_CallFunction_0")
CONV_T    = tmpl_from(i3, "K2Node_CallFunction_32")
BRANCH_T  = tmpl_from(i3, "K2Node_IfThenElse_0")
FEACH_T   = tmpl_from(i3, "K2Node_MacroInstance_0")
DIST_T    = tmpl_from(i3, "K2Node_CallFunction_65")
CMP_T     = tmpl_from(i3, "K2Node_CallFunction_66")
ADD_T     = tmpl_from(i3, "K2Node_CallArrayFunction_2")
MCGET_T   = tmpl_file(WLIB + r"\stocker\get_managed_containers.t3d")
CALL_T    = tmpl_file(WLIB + r"\stocker\call_applykeeprule.t3d")
E2S_T     = tmpl_file(WLIB + r"\stocker\enum_to_string.t3d")

g = Graph(nodes=[])


def add(t):
    return instantiate(t, g)[0]


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


def type_foreach(node, path):
    setf(node, "Array", "PinType.PinCategory", '"object"')
    setf(node, "Array", "PinType.PinSubCategoryObject", bgc(path))
    setf(node, "Array", "PinType.ContainerType", "Array")
    setf(node, "Array Element", "PinType.PinCategory", '"object"')
    setf(node, "Array Element", "PinType.PinSubCategoryObject", bgc(path))
    setf(node, "Array Element", "PinType.ContainerType", "None")


def gac_for(path):
    n = add(GAC_T)
    setf(n, "ActorClass", "DefaultObject", f'"{path}"')
    setf(n, "OutActors", "PinType.PinSubCategoryObject", bgc(path))
    return n


def first_of(path):
    """GAC(path)[0] -> the single instance."""
    gac = gac_for(path)
    item = add(GETITEM_T)
    setf(item, "Array", "PinType.PinSubCategoryObject", bgc(path))
    setf(item, "Output", "PinType.PinSubCategoryObject", bgc(path))
    setd(item, "Dimension 1", "0")
    connect(gac, "OutActors", item, "Array")
    return gac, item


# --- entry ------------------------------------------------------------------
event = copy.deepcopy(i3.by_name("K2Node_Event_0"))
delay8 = copy.deepcopy(i3.by_name("K2Node_CallFunction_1"))
g.nodes += [event, delay8]
pin(delay8, "then").links = []
setd(delay8, "Duration", "8.000000")

# --- gather in-range containers (3H front half) -----------------------------
gacDesk, deskItem = first_of(DESK)
gacAll = gac_for(BASE_CONTAINER)
pBegin = add(PRINT_T)
setd(pBegin, "InString", "STOCKER_3K begin (3 house rules via BPFL_Stocker2)")
feach = add(FEACH_T)
type_foreach(feach, BASE_CONTAINER)
dist = add(DIST_T)
cmp_ = add(CMP_T)
setd(cmp_, "B", RANGE)
brRange = add(BRANCH_T)
arradd = add(ADD_T)
mcAdd = add(MCGET_T)

connect(gacAll, "OutActors", feach, "Array")
connect(feach, "Array Element", dist, "self")
connect(deskItem, "Output", dist, "OtherActor")
connect(dist, "ReturnValue", cmp_, "A")
connect(cmp_, "ReturnValue", brRange, "Condition")
connect(mcAdd, "ManagedContainers", arradd, "TargetArray")
connect(feach, "Array Element", arradd, "NewItem")

# --- the two stations -------------------------------------------------------
gacMetal, metalItem = first_of(METAL)
gacWood, woodItem = first_of(WOOD)
mcGet = add(MCGET_T)          # one Get feeds all three calls

# --- the three rules --------------------------------------------------------
RULES = [
    ("rule1 IronBar@Blacksmith keep20 ->",       metalItem, "11501", "20"),
    ("rule2 HardenedSteel@Blacksmith keep20 ->", metalItem, "18061", "20"),
    ("rule3 Wood@WoodStation keep200 ->",        woodItem,  "10011", "200"),
]

rule_nodes = []
for label, station, tid, keep in RULES:
    pLbl = add(PRINT_T)
    setd(pLbl, "InString", "STOCKER_3K " + label)
    call = add(CALL_T)
    setd(call, "TemplateID", tid)
    setd(call, "Keep", keep)
    e2s = add(E2S_T)
    pOut = add(PRINT_T)
    conv = add(CONV_T)
    pMoved = add(PRINT_T)

    connect(station, "Output", call, "Station")
    connect(mcGet, "ManagedContainers", call, "Candidates")
    connect(call, "Outcome", e2s, "Enumerator")
    connect(e2s, "ReturnValue", pOut, "InString")
    connect(call, "Moved", conv, "InInt")
    connect(conv, "ReturnValue", pMoved, "InString")
    rule_nodes.append((pLbl, call, e2s, pOut, conv, pMoved))

# --- exec wiring ------------------------------------------------------------
connect_exec(event, delay8) if not pin(delay8, "execute").links else None
connect_exec(delay8, gacDesk)
connect_exec(gacDesk, gacAll)
connect_exec(gacAll, pBegin)
connect_exec(pBegin, feach, "then", "Exec")
connect_exec(feach, brRange, "LoopBody", "execute")
connect_exec(brRange, arradd, "then", "execute")
# gather done -> resolve stations -> run the rules in order
connect_exec(feach, gacMetal, "Completed", "execute")
connect_exec(gacMetal, gacWood)
prev = gacWood
for pLbl, call, e2s, pOut, conv, pMoved in rule_nodes:
    connect_exec(prev, pLbl)
    connect_exec(pLbl, call)
    connect_exec(call, pOut)
    connect_exec(pOut, pMoved)
    prev = pMoved

# --- layout -----------------------------------------------------------------
event.set_position(0, -600); delay8.set_position(240, -600)
gacDesk.set_position(480, -600); deskItem.set_position(480, -400)
gacAll.set_position(760, -600); pBegin.set_position(1020, -600)
feach.set_position(1280, -600); dist.set_position(1560, -430)
cmp_.set_position(1760, -430); brRange.set_position(1960, -600)
mcAdd.set_position(2160, -460); arradd.set_position(2220, -600)
gacMetal.set_position(1280, -1000); metalItem.set_position(1280, -840)
gacWood.set_position(1540, -1000); woodItem.set_position(1540, -840)
mcGet.set_position(1800, -840)
x = 2000
for pLbl, call, e2s, pOut, conv, pMoved in rule_nodes:
    pLbl.set_position(x, -1000)
    call.set_position(x + 240, -1000)
    e2s.set_position(x + 520, -860)
    pOut.set_position(x + 700, -1000)
    conv.set_position(x + 700, -860)
    pMoved.set_position(x + 900, -1000)
    x += 1180

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

calls = [n for n in g.nodes if "ApplyKeepRule" in " ".join(t for k, t in n.body if k == "raw")]
assert len(calls) == 3, f"expected 3 rule calls, got {len(calls)}"
wilds = [(n.name, p.name) for n in g.nodes for p in n.pins
         if p._get("PinType.PinCategory") == '"wildcard"']
assert not wilds, f"unresolved wildcards: {wilds}"

out = MOD + r"\.ccmod\graphs\stocker_3k.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"nodes: {len(g.nodes)}   wrote: {out}")
print(f"rule calls: {len(calls)}")
print(f"non-reciprocal / dangling problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
