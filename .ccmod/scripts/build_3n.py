"""Author stocker_3n.t3d — fix THRASH by making benches unreachable as candidates.

THE DISEASE. Once restock existed (3M), items could flow bench->bench in both
directions: a bench qualifies as a tidy DESTINATION if it happens to hold the item,
and as a restock SOURCE for the same reason. Two benches with rules for the same
item -- or a bench whose tidy-destination is another bench's restock-source -- would
ping-pong it every run. 3M had one bench so it couldn't happen; it would the moment
there are two.

THE FIX, and note where it goes: NOT in ApplyKeepRule. Both the tidy destination and
the restock source are drawn from `Candidates`, so if ManagedContainers only ever
contains STORAGE, benches become structurally unreachable in both directions at once.
ApplyKeepRule is untouched. One extra condition in the gather loop.

    ForEach c in GAC(BP_PlaceableItemContainer):
        c.GetDistanceTo(desk) < 3000                       ?
        IsValid(GetComponentByClass(c, BP_BAC_Storage))    ?   <- NEW
            -> Array Add -> ManagedContainers

HOW WE TELL A CHEST FROM A BENCH -- the game's own distinction, not a class allowlist:
chests carry a **BP_BAC_Storage** component; crafting benches do not. Verified by
grepping the shipped uassets:
    BP_PL_Chest_Large           -> BP_BAC_Storage
    BP_PL_Chest_Medium          -> BP_BAC_Storage
    BP_PL_CraftingStation_Wood  -> (none)
    BP_PL_CraftingStation_Metal -> BP_BAC_TurnLightOnOff only
    BP_PL_WorkStation_Artisan   -> (none)
Side benefit: altars and forges drop out for free -- they were only ever noise in the
candidate list.

ManagedContainers now means "storage in range", which is arguably what it should
always have meant. Benches are found separately, by class.

THE TEST IS A DELIBERATE TRAP (the world could not thrash on its own -- no item sat in
two benches, so a filter would have passed without proving anything). The user moved
Shaped Wood into the Artisan bench, so:

    Wood station (56)  ShapedWood = 8   <- the source, unruled => keep 0
    Artisan bench (68) ShapedWood = 7   <- a BENCH holding it
    no storage holds ShapedWood at all

    WITHOUT this filter: Artisan qualifies -> Moved 8 INTO A BENCH   (the disease)
    WITH it:             Artisan isn't storage -> NoDestination      (the cure)

Different outcomes, so the run discriminates. Everything else should read exactly as
3M did.

Also prints the filtered ManagedContainers (count + display names) -- direct evidence
the filter did what it claims, independent of the behavioural test.
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
STORAGE_COMP = ("/Game/Systems/Building/BuildingActorComponents/"
                "BP_BAC_Storage.BP_BAC_Storage_C")
GAME_ITEM = "/Script/ConanSandbox.GameItem"
RANGE = "3000.000000"

m3 = parse(open(MOD + r"\.ccmod\graphs\stocker_3m.t3d", encoding="utf-8").read())
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


def find_tmpl(graph, member):
    """First node in `graph` whose FunctionReference names `member`."""
    import re
    for n in graph.nodes:
        raw = " ".join(t for k, t in n.body if k == "raw")
        if re.search(r'MemberName="%s"' % member, raw):
            return tmpl_from(graph, n.name)
    raise KeyError(member)


GAC_T     = find_tmpl(m3, "GetAllActorsOfClass")
PRINT_T   = find_tmpl(m3, "PrintString")
CONV_T    = find_tmpl(m3, "Conv_IntToString")
DIST_T    = find_tmpl(m3, "GetDistanceTo")
CMP_T     = find_tmpl(m3, "Less_DoubleDouble")
GETITEM_T = tmpl_from(m3, "K2Node_GetArrayItem_0")
BRANCH_T  = tmpl_from(m3, "K2Node_IfThenElse_0")
FEACH_T   = tmpl_from(m3, "K2Node_MacroInstance_0")
ADD_T     = find_tmpl(m3, "Array_Add")
LEN_T     = tmpl_from(h3, "K2Node_CallArrayFunction_0")
KEYS_T    = find_tmpl(m3, "Map_Keys")
FIND_T    = find_tmpl(m3, "Map_Find")
GIBT_T    = find_tmpl(m3, "GetInventoryByType")
ILIST_T   = tmpl_file(LIB + r"\inventory\get_item_list.t3d")
TID_T     = tmpl_file(LIB + r"\inventory\get_template_id.t3d")
IV_T      = tmpl_file(LIB + r"\call\is_valid.t3d")
GCBC_T    = tmpl_file(LIB + r"\actor\get_component_by_class.t3d")
GDN_T     = tmpl_file(LIB + r"\call\get_display_name.t3d")
MCGET_T   = tmpl_file(WLIB + r"\stocker\get_managed_containers.t3d")
KRGET_T   = tmpl_file(WLIB + r"\stocker\get_keeprules.t3d")
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


def cls(path):
    return f'''"/Script/CoreUObject.Class'{path}'"'''


def type_foreach(node, subobj_raw):
    setf(node, "Array", "PinType.PinCategory", '"object"')
    setf(node, "Array", "PinType.PinSubCategoryObject", subobj_raw)
    setf(node, "Array", "PinType.ContainerType", "Array")
    setf(node, "Array Element", "PinType.PinCategory", '"object"')
    setf(node, "Array Element", "PinType.PinSubCategoryObject", subobj_raw)
    setf(node, "Array Element", "PinType.ContainerType", "None")


def type_foreach_int(node):
    for pn in ("Array", "Array Element"):
        setf(node, pn, "PinType.PinCategory", '"int"')
        setf(node, pn, "PinType.PinSubCategoryObject", "None")
    setf(node, "Array", "PinType.ContainerType", "Array")
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
event = copy.deepcopy(m3.by_name("K2Node_Event_0"))
delay8 = copy.deepcopy(m3.by_name("K2Node_CallFunction_1"))
g.nodes += [event, delay8]
pin(delay8, "then").links = []
setd(delay8, "Duration", "8.000000")

# --- gather: in range AND is storage ----------------------------------------
gacDesk, deskItem = first_of(DESK)
gacAll = gac_for(BASE_CONTAINER)
pBegin = add(PRINT_T)
setd(pBegin, "InString", "STOCKER_3N begin (storage-only candidates; benches excluded)")
feGather = add(FEACH_T)
type_foreach(feGather, bgc(BASE_CONTAINER))
dist = add(DIST_T)
cmp_ = add(CMP_T)
setd(cmp_, "B", RANGE)
brRange = add(BRANCH_T)
# NEW: the storage test
gcbc = add(GCBC_T)
setf(gcbc, "ComponentClass", "DefaultObject", f'"{STORAGE_COMP}"')
isStore = add(IV_T)
brStore = add(BRANCH_T)
arradd = add(ADD_T)
mcAdd = add(MCGET_T)

connect(gacAll, "OutActors", feGather, "Array")
connect(feGather, "Array Element", dist, "self")
connect(deskItem, "Output", dist, "OtherActor")
connect(dist, "ReturnValue", cmp_, "A")
connect(cmp_, "ReturnValue", brRange, "Condition")
connect(feGather, "Array Element", gcbc, "self")       # does THIS container have...
connect(gcbc, "ReturnValue", isStore, "Object")        # ...a BP_BAC_Storage component?
connect(isStore, "ReturnValue", brStore, "Condition")
connect(mcAdd, "ManagedContainers", arradd, "TargetArray")
connect(feGather, "Array Element", arradd, "NewItem")

# --- report the filtered list (direct evidence, independent of behaviour) ----
mcLen = add(MCGET_T)
alen = add(LEN_T)
setf(alen, "TargetArray", "PinType.PinSubCategoryObject", bgc(BASE_CONTAINER))
convLen = add(CONV_T)
pStoreLbl = add(PRINT_T)
setd(pStoreLbl, "InString", "STOCKER_3N storage candidates kept:")
pStoreCount = add(PRINT_T)
mcNames = add(MCGET_T)
feNames = add(FEACH_T)
type_foreach(feNames, bgc(BASE_CONTAINER))
gdn = add(GDN_T)
pName = add(PRINT_T)
connect(mcLen, "ManagedContainers", alen, "TargetArray")
connect(alen, "ReturnValue", convLen, "InInt")
connect(convLen, "ReturnValue", pStoreCount, "InString")
connect(mcNames, "ManagedContainers", feNames, "Array")
connect(feNames, "Array Element", gdn, "Object")
connect(gdn, "ReturnValue", pName, "InString")

# --- the bench --------------------------------------------------------------
gacWood, woodItem = first_of(WOOD)
woodInv = add(GIBT_T)
setd(woodInv, "inventoryType", "PlaceableInventory")
connect(woodItem, "Output", woodInv, "owner")
ilist = add(ILIST_T)
connect(woodInv, "ReturnValue", ilist, "self")

# --- PASS 1: tidy unruled (bench contents) ----------------------------------
p1lbl = add(PRINT_T)
setd(p1lbl, "InString", "STOCKER_3N --- pass1 tidy unruled ---")
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
connect(find1, "ReturnValue", brRuled, "Condition")
mc1 = add(MCGET_T)
call1 = add(CALL_T)
setd(call1, "Keep", "0")
connect(woodItem, "Output", call1, "Station")
connect(tid1, "TemplateID", call1, "TemplateID")
connect(mc1, "ManagedContainers", call1, "Candidates")
c1tid = add(CONV_T); p1tid = add(PRINT_T)
connect(tid1, "TemplateID", c1tid, "InInt"); connect(c1tid, "ReturnValue", p1tid, "InString")
e2s1 = add(E2S_T); p1out = add(PRINT_T)
connect(call1, "Outcome", e2s1, "Enumerator"); connect(e2s1, "ReturnValue", p1out, "InString")
c1mv = add(CONV_T); p1mv = add(PRINT_T)
connect(call1, "Moved", c1mv, "InInt"); connect(c1mv, "ReturnValue", p1mv, "InString")

# --- PASS 2: reconcile rules ------------------------------------------------
kr2 = add(KRGET_T)
keys = add(KEYS_T)
connect(kr2, "KeepRules", keys, "TargetMap")
p2lbl = add(PRINT_T)
setd(p2lbl, "InString", "STOCKER_3N --- pass2 reconcile rules ---")
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
connect(find2, "Value", call2, "Keep")
connect(mc2, "ManagedContainers", call2, "Candidates")
c2tid = add(CONV_T); p2tid = add(PRINT_T)
connect(fe2, "Array Element", c2tid, "InInt"); connect(c2tid, "ReturnValue", p2tid, "InString")
c2keep = add(CONV_T); p2keep = add(PRINT_T)
connect(find2, "Value", c2keep, "InInt"); connect(c2keep, "ReturnValue", p2keep, "InString")
e2s2 = add(E2S_T); p2out = add(PRINT_T)
connect(call2, "Outcome", e2s2, "Enumerator"); connect(e2s2, "ReturnValue", p2out, "InString")
c2mv = add(CONV_T); p2mv = add(PRINT_T)
connect(call2, "Moved", c2mv, "InInt"); connect(c2mv, "ReturnValue", p2mv, "InString")

# --- exec -------------------------------------------------------------------
connect_exec(event, delay8) if not pin(delay8, "execute").links else None
connect_exec(delay8, gacDesk)
connect_exec(gacDesk, gacAll)
connect_exec(gacAll, pBegin)
connect_exec(pBegin, feGather, "then", "Exec")
connect_exec(feGather, brRange, "LoopBody", "execute")
connect_exec(brRange, brStore, "then", "execute")      # in range -> is it storage?
connect_exec(brStore, arradd, "then", "execute")       # yes -> keep it
# gather done -> report the filtered list
connect_exec(feGather, pStoreLbl, "Completed", "execute")
connect_exec(pStoreLbl, pStoreCount)
connect_exec(pStoreCount, feNames, "then", "Exec")
connect_exec(feNames, pName, "LoopBody", "execute")
# names done -> the bench -> pass 1
connect_exec(feNames, gacWood, "Completed", "execute")
connect_exec(gacWood, p1lbl)
connect_exec(p1lbl, fe1, "then", "Exec")
connect_exec(fe1, brValid1, "LoopBody", "execute")
connect_exec(brValid1, brRuled, "then", "execute")
connect_exec(brRuled, p1tid, "else", "execute")        # unruled -> tidy
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
feGather.set_position(1280, -600)
dist.set_position(1560, -420); cmp_.set_position(1760, -420)
brRange.set_position(1960, -600)
gcbc.set_position(1560, -260); isStore.set_position(1800, -260)
brStore.set_position(2160, -600)
mcAdd.set_position(2360, -460); arradd.set_position(2400, -600)
pStoreLbl.set_position(1280, -900); mcLen.set_position(1480, -1040)
alen.set_position(1660, -1040); convLen.set_position(1840, -1040)
pStoreCount.set_position(1520, -900)
mcNames.set_position(1760, -1140); feNames.set_position(1780, -900)
gdn.set_position(2060, -1040); pName.set_position(2100, -900)
gacWood.set_position(1280, -1400); woodItem.set_position(1280, -1250)
woodInv.set_position(1500, -1250); ilist.set_position(1700, -1250)
p1lbl.set_position(1500, -1400); fe1.set_position(1760, -1400)
isv1.set_position(2040, -1600); brValid1.set_position(2060, -1400)
tid1.set_position(2040, -1200)
kr1.set_position(2240, -1100); find1.set_position(2440, -1160)
brRuled.set_position(2300, -1400)
c1tid.set_position(2560, -1600); p1tid.set_position(2560, -1400)
mc1.set_position(2760, -1100); call1.set_position(2800, -1400)
e2s1.set_position(3060, -1600); p1out.set_position(3080, -1400)
c1mv.set_position(3300, -1600); p1mv.set_position(3320, -1400)
kr2.set_position(1760, -1950); keys.set_position(1960, -1900)
p2lbl.set_position(2200, -1900); fe2.set_position(2480, -1900)
kr3.set_position(2700, -1720); find2.set_position(2900, -1760)
c2tid.set_position(2760, -2100); p2tid.set_position(2760, -1900)
c2keep.set_position(2960, -2100); p2keep.set_position(2960, -1900)
mc2.set_position(3140, -1700); call2.set_position(3180, -1900)
e2s2.set_position(3440, -2100); p2out.set_position(3460, -1900)
c2mv.set_position(3680, -2100); p2mv.set_position(3700, -1900)

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
assert STORAGE_COMP in g.render(), "BP_BAC_Storage class ref missing"

out = MOD + r"\.ccmod\graphs\stocker_3n.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"nodes: {len(g.nodes)}   wrote: {out}")
print(f"non-reciprocal / dangling problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
