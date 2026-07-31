"""Author stocker_3l.t3d — OPT-OUT tidying: the mod's actual job, for the first time.

Every build so far named the items it managed. This one doesn't: it enumerates
what is ACTUALLY in a bench and tidies everything the rules don't ask it to keep.
That is the semantics the user settled on -- house rules describe what stays in
the bench (arrow materials, repair stock, parts for quick replacements) and
everything else gets put away.

The pleasing part: ApplyKeepRule is UNCHANGED. Opt-out is just

    keep = KeepRules[templateID]   or 0 if the map has no entry

and Map_Find returns the type default (0) for an absent key, so the opt-out
default falls out of the lookup with NO Branch, NO Select, no conditional at all.
An unruled item is simply a rule with keep=0 that nobody had to type.

Flow:
  BeginPlay -> Delay(8s)
    -> desk = GAC(BP_PL_Table_Strategy_Stygian)[0]
    -> ForEach GAC(BP_PlaceableItemContainer): dist(desk) < 3000 -> Array Add
       -> ManagedContainers                                  [3H front half]
    -> Completed:
         wood  = GAC(BP_PL_CraftingStation_Wood)[0]
         inv   = GetInventoryByType(wood, PlaceableInventory)
         items = inv.ItemList                    <- Array of GameItem
         Print header + Array_Length(items)
         ForEach item in items:
             IsValid(item)?  no -> skip          <- the mutate-during-iterate guard
             tid  = item.TemplateID
             keep = Map_Find(KeepRules, tid).Value
             (moved, outcome) = ApplyKeepRule(wood, tid, keep, ManagedContainers)
             Print tid, keep, outcome, moved

TWO THINGS THAT LOOK LIKE FUNCTIONS AND AREN'T. Both are native member VariableGets,
which is why they never turned up as CallFunctions in any EventGraph and why the api
index pointed at three assets that didn't contain them:
  * ItemInventory.ItemList   -> Array of GameItem
  * GameItem.TemplateID      -> int
The api lists their getter names ("GetItemList", "GetTemplateId") from the name
table. Both were found by dragging off a real typed pin with Context Sensitive on.

THE HAZARD: we move items out of the very inventory we are iterating. ItemList is
read once and BP arrays are values, so the ARRAY is a stable snapshot -- but the
GameItem objects in it may be destroyed by a move. Hence IsValid per item. Also
note duplicates self-handle: MoveItemsByTemplateId works by TEMPLATE, not by stack,
so a second stack of the same template finds the bench already drained and returns
NoExcess.

EXPECTED (Wood station, from the baseline -- re-derive from the DB before trusting):
  Wood 731            keep 200 (the only rule) -> NoDestination  (nothing else holds Wood)
  Layered Silk 200    keep 0                   -> Moved 200      -> chest 59 (holds 400)
  Bark 2              keep 0                   -> NoDestination
  Shaped Wood 15      keep 0                   -> NoDestination
  Iron Reinforcement 5 keep 0                  -> NoDestination
Only the Silk should move. 4 of 5 orphan -- which is exactly why NoDestination
stopped being an edge case the moment opt-out was chosen.

Prints template IDs, not names: GetNameFromTemplateID returns TEXT and PrintString
wants a String, and a text-conversion unknown does not belong in a build whose
unknown is enumeration. Decode ids against Items/ItemTable.uasset when reading.
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
WOOD = PRE + "BP_PL_CraftingStation_Wood.BP_PL_CraftingStation_Wood_C"
GAME_ITEM = "/Script/ConanSandbox.GameItem"
RANGE = "3000.000000"

k3 = parse(open(MOD + r"\.ccmod\graphs\stocker_3k.t3d", encoding="utf-8").read())
# Array_Length was not needed in 3K; take it from 3H, where it is proven.
h3 = parse(open(MOD + r"\.ccmod\graphs\stocker_3h.t3d", encoding="utf-8").read())


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


# templates lifted from 3K (all verified in a cooked, working build)
GAC_T     = tmpl_from(k3, "K2Node_CallFunction_8")
GETITEM_T = tmpl_from(k3, "K2Node_GetArrayItem_0")
PRINT_T   = tmpl_from(k3, "K2Node_CallFunction_0")
CONV_T    = tmpl_from(k3, "K2Node_CallFunction_32")
BRANCH_T  = tmpl_from(k3, "K2Node_IfThenElse_0")
FEACH_T   = tmpl_from(k3, "K2Node_MacroInstance_0")
DIST_T    = tmpl_from(k3, "K2Node_CallFunction_65")
CMP_T     = tmpl_from(k3, "K2Node_CallFunction_66")
ADD_T     = tmpl_from(k3, "K2Node_CallArrayFunction_2")
LEN_T     = tmpl_from(h3, "K2Node_CallArrayFunction_0")   # Array_Length (3H)
MCGET_T   = tmpl_file(WLIB + r"\stocker\get_managed_containers.t3d")
CALL_T    = tmpl_file(WLIB + r"\stocker\call_applykeeprule.t3d")
E2S_T     = tmpl_file(WLIB + r"\stocker\enum_to_string.t3d")
KRGET_T   = tmpl_file(WLIB + r"\stocker\get_keeprules.t3d")
FIND_T    = tmpl_file(LIB + r"\map\map_find.t3d")
GIBT_T    = tmpl_file(LIB + r"\inventory\get_inventory_by_type.t3d")
ILIST_T   = tmpl_file(LIB + r"\inventory\get_item_list.t3d")
TID_T     = tmpl_file(LIB + r"\inventory\get_template_id.t3d")
IV_T      = tmpl_file(LIB + r"\call\is_valid.t3d")

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


def cls(path):
    return f'''"/Script/CoreUObject.Class'{path}'"'''


def type_foreach(node, subobj_raw):
    """Resolve the ForEach macro's wildcards. Never leave them to paste-time luck."""
    setf(node, "Array", "PinType.PinCategory", '"object"')
    setf(node, "Array", "PinType.PinSubCategoryObject", subobj_raw)
    setf(node, "Array", "PinType.ContainerType", "Array")
    setf(node, "Array Element", "PinType.PinCategory", '"object"')
    setf(node, "Array Element", "PinType.PinSubCategoryObject", subobj_raw)
    setf(node, "Array Element", "PinType.ContainerType", "None")


def gac_for(path):
    n = add(GAC_T)
    setf(n, "ActorClass", "DefaultObject", f'"{path}"')
    setf(n, "OutActors", "PinType.PinSubCategoryObject", bgc(path))
    return n


def first_of(path):
    gac = gac_for(path)
    item = add(GETITEM_T)
    setf(item, "Array", "PinType.PinSubCategoryObject", bgc(path))
    setf(item, "Output", "PinType.PinSubCategoryObject", bgc(path))
    setd(item, "Dimension 1", "0")
    connect(gac, "OutActors", item, "Array")
    return gac, item


# --- entry ------------------------------------------------------------------
event = copy.deepcopy(k3.by_name("K2Node_Event_0"))
delay8 = copy.deepcopy(k3.by_name("K2Node_CallFunction_1"))
g.nodes += [event, delay8]
pin(delay8, "then").links = []
setd(delay8, "Duration", "8.000000")

# --- gather in-range containers (3H front half, unchanged) ------------------
gacDesk, deskItem = first_of(DESK)
gacAll = gac_for(BASE_CONTAINER)
pBegin = add(PRINT_T)
setd(pBegin, "InString", "STOCKER_3L begin (opt-out tidy of the Wood station)")
feach = add(FEACH_T)
type_foreach(feach, bgc(BASE_CONTAINER))
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

# --- the bench + its actual contents ----------------------------------------
gacWood, woodItem = first_of(WOOD)
woodInv = add(GIBT_T)
setd(woodInv, "inventoryType", "PlaceableInventory")
ilist = add(ILIST_T)                 # ItemInventory.ItemList -> Array<GameItem>
alen = add(LEN_T)
setf(alen, "TargetArray", "PinType.PinSubCategoryObject", cls(GAME_ITEM))
convLen = add(CONV_T)
pCount = add(PRINT_T)

connect(woodItem, "Output", woodInv, "owner")
connect(woodInv, "ReturnValue", ilist, "self")
connect(ilist, "ItemList", alen, "TargetArray")
connect(alen, "ReturnValue", convLen, "InInt")
connect(convLen, "ReturnValue", pCount, "InString")

# --- per-item: look up its keep, apply the rule -----------------------------
feach2 = add(FEACH_T)
type_foreach(feach2, cls(GAME_ITEM))
isv = add(IV_T)
brValid = add(BRANCH_T)
tid = add(TID_T)
krGet = add(KRGET_T)
find = add(FIND_T)
mcGet = add(MCGET_T)
call = add(CALL_T)
e2s = add(E2S_T)
convTid = add(CONV_T)
pTid = add(PRINT_T)
convKeep = add(CONV_T)
pKeep = add(PRINT_T)
pOut = add(PRINT_T)
convMoved = add(CONV_T)
pMoved = add(PRINT_T)

connect(ilist, "ItemList", feach2, "Array")
connect(feach2, "Array Element", isv, "Object")
connect(isv, "ReturnValue", brValid, "Condition")
connect(feach2, "Array Element", tid, "self")
# keep = KeepRules[tid], or 0 when absent -- THIS is opt-out, in one node
connect(krGet, "KeepRules", find, "TargetMap")
connect(tid, "TemplateID", find, "Key")
# the rule call
connect(woodItem, "Output", call, "Station")
connect(tid, "TemplateID", call, "TemplateID")
connect(find, "Value", call, "Keep")
connect(mcGet, "ManagedContainers", call, "Candidates")
# reporting
connect(tid, "TemplateID", convTid, "InInt")
connect(convTid, "ReturnValue", pTid, "InString")
connect(find, "Value", convKeep, "InInt")
connect(convKeep, "ReturnValue", pKeep, "InString")
connect(call, "Outcome", e2s, "Enumerator")
connect(e2s, "ReturnValue", pOut, "InString")
connect(call, "Moved", convMoved, "InInt")
connect(convMoved, "ReturnValue", pMoved, "InString")

# --- exec wiring ------------------------------------------------------------
connect_exec(event, delay8) if not pin(delay8, "execute").links else None
connect_exec(delay8, gacDesk)
connect_exec(gacDesk, gacAll)
connect_exec(gacAll, pBegin)
connect_exec(pBegin, feach, "then", "Exec")
connect_exec(feach, brRange, "LoopBody", "execute")
connect_exec(brRange, arradd, "then", "execute")
# gather done -> resolve the bench, report its item count, then walk it
connect_exec(feach, gacWood, "Completed", "execute")
connect_exec(gacWood, pCount)
connect_exec(pCount, feach2, "then", "Exec")
# per item: IsValid -> print tid/keep -> call -> print outcome/moved
connect_exec(feach2, brValid, "LoopBody", "execute")
connect_exec(brValid, pTid, "then", "execute")
connect_exec(pTid, pKeep)
connect_exec(pKeep, call)
connect_exec(call, pOut)
connect_exec(pOut, pMoved)

# --- layout -----------------------------------------------------------------
event.set_position(0, -600); delay8.set_position(240, -600)
gacDesk.set_position(480, -600); deskItem.set_position(480, -400)
gacAll.set_position(760, -600); pBegin.set_position(1020, -600)
feach.set_position(1280, -600); dist.set_position(1560, -430)
cmp_.set_position(1760, -430); brRange.set_position(1960, -600)
mcAdd.set_position(2160, -460); arradd.set_position(2220, -600)
gacWood.set_position(1280, -1050); woodItem.set_position(1280, -900)
woodInv.set_position(1520, -900); ilist.set_position(1740, -900)
alen.set_position(1740, -1150); convLen.set_position(1900, -1150)
pCount.set_position(1540, -1050)
feach2.set_position(1960, -1050)
isv.set_position(2240, -1250); brValid.set_position(2280, -1050)
tid.set_position(2240, -880)
krGet.set_position(2440, -760); find.set_position(2640, -820)
mcGet.set_position(2640, -680)
convTid.set_position(2500, -1250)
pTid.set_position(2500, -1050); pKeep.set_position(2700, -1050)
convKeep.set_position(2700, -1180)
call.set_position(2900, -1050)
e2s.set_position(3160, -1250); pOut.set_position(3200, -1050)
convMoved.set_position(3400, -1250); pMoved.set_position(3420, -1050)

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
         if p._get("PinType.PinCategory") == '"wildcard"']
assert not wilds, f"unresolved wildcards: {wilds}"
calls = [n for n in g.nodes if "ApplyKeepRule" in " ".join(t for k, t in n.body if k == "raw")]
assert len(calls) == 1, f"expected 1 rule call (driven by the loop), got {len(calls)}"

out = MOD + r"\.ccmod\graphs\stocker_3l.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"nodes: {len(g.nodes)}   wrote: {out}")
print(f"non-reciprocal / dangling problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
