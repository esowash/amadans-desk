"""Author stocker_3m.t3d — tidy AND restock, in two passes.

3L tidied. This adds the mirror: if a bench holds LESS than a rule asks for, pull
the shortfall out of nearby storage.

THE WRINKLE THAT SHAPES THIS BUILD: a restock cannot be discovered by looking at
the bench. An item the bench has ZERO of does not appear in its ItemList at all --
the absence IS the deficit. 3L's loop would never see it. So:

    Pass 1 -- iterate the BENCH's contents  (opt-out: tidy what no rule protects)
    Pass 2 -- iterate the RULES             (reconcile what rules do protect)

That asymmetry is forced, and it's the right one: opt-out means "tidy everything
unruled", but "restock everything unruled" is meaningless. Restock is definitionally
rule-driven.

Each item is handled exactly ONCE. Pass 1 uses Map_Find's bFound output (which we
had been ignoring) to skip ruled items -- they belong to pass 2, which reconciles
them in whichever direction they need.

    Pass 1: ForEach item in bench.ItemList
                IsValid(item)?
                NOT Map_Find(KeepRules, item.TemplateID).bFound?   <- unruled only
                    ApplyKeepRule(bench, tid, keep=0, ManagedContainers)

    Pass 2: ForEach tid in Map_Keys(KeepRules)                     <- ruled only
                ApplyKeepRule(bench, tid, Map_Find(KeepRules,tid).Value, ManagedContainers)

Map_Keys is IMPURE (it has exec pins), unlike Map_Find -- so it sits in the exec
chain between the two passes rather than hanging off as a pure read.

EXPECTED, from the live save (re-derive from the DB before trusting this):
  Pass 1 (bench holds Bark 2, Wood 731, IronReinf 5, ShapedWood 15):
      Wood      -> SKIPPED, it's ruled (pass 2 handles it)
      Bark 2    -> keep 0 -> NoDestination
      IronReinf 5  -> keep 0 -> NoDestination
      ShapedWood 15 -> keep 0 -> NoDestination
  Pass 2 (rules 10011->200, 12515->300):
      10011 Wood  have 731, keep 200 -> excess 531, no dest -> NoDestination
      12515 Silk  have 0,   keep 300 -> deficit 300, chest 59 holds 600
                                     -> RESTOCKED 300   <- the new thing

The Silk case is the exact inverse of 3L: that build moved 200 Silk out of the
bench into chest 59; this one pulls 300 back because a rule now asks for it.
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

l3 = parse(open(MOD + r"\.ccmod\graphs\stocker_3l.t3d", encoding="utf-8").read())
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


GAC_T     = tmpl_from(l3, "K2Node_CallFunction_8")
GETITEM_T = tmpl_from(l3, "K2Node_GetArrayItem_0")
PRINT_T   = tmpl_from(l3, "K2Node_CallFunction_0")
CONV_T    = tmpl_from(l3, "K2Node_CallFunction_32")
BRANCH_T  = tmpl_from(l3, "K2Node_IfThenElse_0")
FEACH_T   = tmpl_from(l3, "K2Node_MacroInstance_0")
DIST_T    = tmpl_from(l3, "K2Node_CallFunction_65")
CMP_T     = tmpl_from(l3, "K2Node_CallFunction_66")
ADD_T     = tmpl_from(l3, "K2Node_CallArrayFunction_2")
LEN_T     = tmpl_from(h3, "K2Node_CallArrayFunction_0")
MCGET_T   = tmpl_file(WLIB + r"\stocker\get_managed_containers.t3d")
CALL_T    = tmpl_file(WLIB + r"\stocker\call_applykeeprule.t3d")
E2S_T     = tmpl_file(WLIB + r"\stocker\enum_to_string.t3d")
KRGET_T   = tmpl_file(WLIB + r"\stocker\get_keeprules.t3d")
FIND_T    = tmpl_file(LIB + r"\map\map_find.t3d")
KEYS_T    = tmpl_file(LIB + r"\map\map_keys.t3d")
GIBT_T    = tmpl_file(LIB + r"\inventory\get_inventory_by_type.t3d")
ILIST_T   = tmpl_file(LIB + r"\inventory\get_item_list.t3d")
TID_T     = tmpl_file(LIB + r"\inventory\get_template_id.t3d")
IV_T      = tmpl_file(LIB + r"\call\is_valid.t3d")
NOT_T     = None   # see below: we invert by using the Branch's else pin instead

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


def type_foreach(node, subobj_raw, category='"object"'):
    setf(node, "Array", "PinType.PinCategory", category)
    setf(node, "Array", "PinType.PinSubCategoryObject", subobj_raw)
    setf(node, "Array", "PinType.ContainerType", "Array")
    setf(node, "Array Element", "PinType.PinCategory", category)
    setf(node, "Array Element", "PinType.PinSubCategoryObject", subobj_raw)
    setf(node, "Array Element", "PinType.ContainerType", "None")


def type_foreach_int(node):
    """Map_Keys yields an Array<int>, not objects."""
    setf(node, "Array", "PinType.PinCategory", '"int"')
    setf(node, "Array", "PinType.PinSubCategoryObject", "None")
    setf(node, "Array", "PinType.ContainerType", "Array")
    setf(node, "Array Element", "PinType.PinCategory", '"int"')
    setf(node, "Array Element", "PinType.PinSubCategoryObject", "None")
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
event = copy.deepcopy(l3.by_name("K2Node_Event_0"))
delay8 = copy.deepcopy(l3.by_name("K2Node_CallFunction_1"))
g.nodes += [event, delay8]
pin(delay8, "then").links = []
setd(delay8, "Duration", "8.000000")

# --- gather in-range containers ---------------------------------------------
gacDesk, deskItem = first_of(DESK)
gacAll = gac_for(BASE_CONTAINER)
pBegin = add(PRINT_T)
setd(pBegin, "InString", "STOCKER_3M begin (tidy + restock, Wood station)")
feGather = add(FEACH_T)
type_foreach(feGather, bgc(BASE_CONTAINER))
dist = add(DIST_T)
cmp_ = add(CMP_T)
setd(cmp_, "B", RANGE)
brRange = add(BRANCH_T)
arradd = add(ADD_T)
mcAdd = add(MCGET_T)
connect(gacAll, "OutActors", feGather, "Array")
connect(feGather, "Array Element", dist, "self")
connect(deskItem, "Output", dist, "OtherActor")
connect(dist, "ReturnValue", cmp_, "A")
connect(cmp_, "ReturnValue", brRange, "Condition")
connect(mcAdd, "ManagedContainers", arradd, "TargetArray")
connect(feGather, "Array Element", arradd, "NewItem")

# --- the bench --------------------------------------------------------------
gacWood, woodItem = first_of(WOOD)
woodInv = add(GIBT_T)
setd(woodInv, "inventoryType", "PlaceableInventory")
connect(woodItem, "Output", woodInv, "owner")
ilist = add(ILIST_T)
connect(woodInv, "ReturnValue", ilist, "self")

# =========================== PASS 1: TIDY UNRULED ===========================
p1lbl = add(PRINT_T)
setd(p1lbl, "InString", "STOCKER_3M --- pass1 tidy unruled (bench contents) ---")
fe1 = add(FEACH_T)
type_foreach(fe1, cls(GAME_ITEM))
connect(ilist, "ItemList", fe1, "Array")
isv1 = add(IV_T)
connect(fe1, "Array Element", isv1, "Object")
brValid1 = add(BRANCH_T)
connect(isv1, "ReturnValue", brValid1, "Condition")
tid1 = add(TID_T)
connect(fe1, "Array Element", tid1, "self")
kr1 = add(KRGET_T)
find1 = add(FIND_T)
connect(kr1, "KeepRules", find1, "TargetMap")
connect(tid1, "TemplateID", find1, "Key")
brRuled = add(BRANCH_T)
connect(find1, "ReturnValue", brRuled, "Condition")   # bFound -> ELSE branch = unruled
mc1 = add(MCGET_T)
call1 = add(CALL_T)
setd(call1, "Keep", "0")                               # unruled => keep nothing
connect(woodItem, "Output", call1, "Station")
connect(tid1, "TemplateID", call1, "TemplateID")
connect(mc1, "ManagedContainers", call1, "Candidates")
c1tid = add(CONV_T)
p1tid = add(PRINT_T)
connect(tid1, "TemplateID", c1tid, "InInt")
connect(c1tid, "ReturnValue", p1tid, "InString")
e2s1 = add(E2S_T)
p1out = add(PRINT_T)
connect(call1, "Outcome", e2s1, "Enumerator")
connect(e2s1, "ReturnValue", p1out, "InString")
c1mv = add(CONV_T)
p1mv = add(PRINT_T)
connect(call1, "Moved", c1mv, "InInt")
connect(c1mv, "ReturnValue", p1mv, "InString")

# =========================== PASS 2: RECONCILE RULES ========================
keys = add(KEYS_T)                                     # IMPURE: lives in the exec chain
kr2 = add(KRGET_T)
connect(kr2, "KeepRules", keys, "TargetMap")
p2lbl = add(PRINT_T)
setd(p2lbl, "InString", "STOCKER_3M --- pass2 reconcile rules (tidy or restock) ---")
fe2 = add(FEACH_T)
type_foreach_int(fe2)
connect(keys, "Keys", fe2, "Array")
kr3 = add(KRGET_T)
find2 = add(FIND_T)
connect(kr3, "KeepRules", find2, "TargetMap")
connect(fe2, "Array Element", find2, "Key")
mc2 = add(MCGET_T)
call2 = add(CALL_T)
connect(woodItem, "Output", call2, "Station")
connect(fe2, "Array Element", call2, "TemplateID")
connect(find2, "Value", call2, "Keep")                 # the rule's keep
connect(mc2, "ManagedContainers", call2, "Candidates")
c2tid = add(CONV_T)
p2tid = add(PRINT_T)
connect(fe2, "Array Element", c2tid, "InInt")
connect(c2tid, "ReturnValue", p2tid, "InString")
c2keep = add(CONV_T)
p2keep = add(PRINT_T)
connect(find2, "Value", c2keep, "InInt")
connect(c2keep, "ReturnValue", p2keep, "InString")
e2s2 = add(E2S_T)
p2out = add(PRINT_T)
connect(call2, "Outcome", e2s2, "Enumerator")
connect(e2s2, "ReturnValue", p2out, "InString")
c2mv = add(CONV_T)
p2mv = add(PRINT_T)
connect(call2, "Moved", c2mv, "InInt")
connect(c2mv, "ReturnValue", p2mv, "InString")

# --- exec wiring ------------------------------------------------------------
connect_exec(event, delay8) if not pin(delay8, "execute").links else None
connect_exec(delay8, gacDesk)
connect_exec(gacDesk, gacAll)
connect_exec(gacAll, pBegin)
connect_exec(pBegin, feGather, "then", "Exec")
connect_exec(feGather, brRange, "LoopBody", "execute")
connect_exec(brRange, arradd, "then", "execute")
# gather done -> resolve the bench -> pass 1
connect_exec(feGather, gacWood, "Completed", "execute")
connect_exec(gacWood, p1lbl)
connect_exec(p1lbl, fe1, "then", "Exec")
connect_exec(fe1, brValid1, "LoopBody", "execute")
connect_exec(brValid1, brRuled, "then", "execute")
# bFound TRUE -> ruled -> skip (pass 2 owns it). FALSE -> unruled -> tidy it.
connect_exec(brRuled, p1tid, "else", "execute")
connect_exec(p1tid, call1)
connect_exec(call1, p1out)
connect_exec(p1out, p1mv)
# pass 1 done -> pass 2
connect_exec(fe1, keys, "Completed", "execute")
connect_exec(keys, p2lbl)
connect_exec(p2lbl, fe2, "then", "Exec")
connect_exec(fe2, p2tid, "LoopBody", "execute")
connect_exec(p2tid, p2keep)
connect_exec(p2keep, call2)
connect_exec(call2, p2out)
connect_exec(p2out, p2mv)

# --- layout -----------------------------------------------------------------
event.set_position(0, -600); delay8.set_position(240, -600)
gacDesk.set_position(480, -600); deskItem.set_position(480, -400)
gacAll.set_position(760, -600); pBegin.set_position(1020, -600)
feGather.set_position(1280, -600); dist.set_position(1560, -430)
cmp_.set_position(1760, -430); brRange.set_position(1960, -600)
mcAdd.set_position(2160, -460); arradd.set_position(2220, -600)
gacWood.set_position(1280, -1100); woodItem.set_position(1280, -950)
woodInv.set_position(1500, -950); ilist.set_position(1700, -950)
p1lbl.set_position(1500, -1100)
fe1.set_position(1760, -1100)
isv1.set_position(2040, -1300); brValid1.set_position(2060, -1100)
tid1.set_position(2040, -900)
kr1.set_position(2240, -800); find1.set_position(2440, -860)
brRuled.set_position(2300, -1100)
c1tid.set_position(2560, -1300); p1tid.set_position(2560, -1100)
mc1.set_position(2760, -800); call1.set_position(2800, -1100)
e2s1.set_position(3060, -1300); p1out.set_position(3080, -1100)
c1mv.set_position(3300, -1300); p1mv.set_position(3320, -1100)
kr2.set_position(1760, -1650); keys.set_position(1960, -1600)
p2lbl.set_position(2200, -1600); fe2.set_position(2480, -1600)
kr3.set_position(2700, -1420); find2.set_position(2900, -1460)
c2tid.set_position(2760, -1800); p2tid.set_position(2760, -1600)
c2keep.set_position(2960, -1800); p2keep.set_position(2960, -1600)
mc2.set_position(3140, -1400); call2.set_position(3180, -1600)
e2s2.set_position(3440, -1800); p2out.set_position(3460, -1600)
c2mv.set_position(3680, -1800); p2mv.set_position(3700, -1600)

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
assert len(calls) == 2, f"expected 2 rule calls (one per pass), got {len(calls)}"

out = MOD + r"\.ccmod\graphs\stocker_3m.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"nodes: {len(g.nodes)}   wrote: {out}")
print(f"non-reciprocal / dangling problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
