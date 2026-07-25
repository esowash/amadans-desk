"""Author stocker_3i.t3d — the first real reclaim: house rule 1 (Iron Bar).

House rule 1 (docs/design.md): the Metal station keeps exactly 20 Iron Bar; the
excess goes to a container that already holds >0 Iron Bar.

This is also the first honest test of the MOVE. MoveItemsByTemplateId has never
returned nonzero and no item has ever been seen to relocate in Game_0.db -- 3E
only showed the node executes cleanly given a valid source. Every earlier zero is
explained by the source not holding the item, which acquits the move but does not
prove it.

Flow (reuses 3H's proven front half verbatim):
  BeginPlay -> Delay(8s)
    -> desk   = GAC(BP_PL_Table_Strategy_Stygian)[0]
    -> all    = GAC(BP_PlaceableItemContainer)
    -> ForEach c: if GetDistanceTo(desk) < 3000 -> Array Add -> ManagedContainers
    -> source = GAC(BP_PL_CraftingStation_Metal)[0]        (the Blacksmith)
       srcInv = GetInventoryByType(source, PlaceableInventory)
       PRINT srcName, srcIron
    -> ForEach c in ManagedContainers:
         cInv  = GetInventoryByType(c, PlaceableInventory)
         cIron = GetNumberOfItemsByTemplate(cInv, 11501)
         if cIron > 0:                       <- dest must already hold Iron Bar
           if c != source:                   <- ...and must not BE the source
             PRINT destName, cIron
             excess = srcIron - 20
             if excess > 0:
               PRINT excess
               moved = srcInv.MoveItemsByTemplateId(11501, excess, true, cInv, true)
               PRINT moved

Expected on the current save: Blacksmith 57 holds 1000 Iron Bar, Large chest 59
holds 2 and is the only OTHER in-range container holding any. So: excess = 980,
moved = 980, and the DB should end with 57 -> exactly 20 and 59 -> exactly 982.

The move sits inside the loop deliberately: that avoids needing a second member
variable to stash the destination (variables can't be pasted). Only one container
qualifies, so it fires once. srcIron is read ONCE before the loop, so if several
containers ever qualified this would over-move -- fine here, revisit when the
destination search becomes general.

Instrumented so a zero is self-diagnosing in ONE playtest: source, dest, excess
and the return are all printed. Builds 3A-3F each tested one thing and cost six
cook cycles; this should cost one.

NOTE: math/subtract_int is DERIVED, not captured (see its brick json). If this
graph fails to compile, suspect that node first.
"""
import copy
import sys

CCMOD = r"<CCMOD_HOME>"
sys.path.insert(0, CCMOD)
from ccmod.t3d import parse, connect, connect_exec
from ccmod.t3d.generator import instantiate
from ccmod.t3d.model import Graph

MOD = r"<MOD_ROOT>"
LIB = CCMOD + r"\library"
WLIB = MOD + r"\.ccmod\library"

PRE = "/Game/Systems/Building/Placeables/"
BASE_CONTAINER = PRE + "BP_PlaceableItemContainer.BP_PlaceableItemContainer_C"
DESK = PRE + "BP_PL_Table_Strategy_Stygian.BP_PL_Table_Strategy_Stygian_C"
METAL = PRE + "BP_PL_CraftingStation_Metal.BP_PL_CraftingStation_Metal_C"

IRON_BAR = "11501"
KEEP = "20"          # house rule 1: the Metal station keeps exactly 20 Iron Bar
RANGE = "3000.000000"

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


# 3H node names (verified by inspection of stocker_3h.t3d)
GAC_T     = tmpl_from(h3, "K2Node_CallFunction_8")    # GetAllActorsOfClass
GETITEM_T = tmpl_from(h3, "K2Node_GetArrayItem_0")
PRINT_T   = tmpl_from(h3, "K2Node_CallFunction_0")    # PrintString
CONV_T    = tmpl_from(h3, "K2Node_CallFunction_32")   # Conv_IntToString
BRANCH_T  = tmpl_from(h3, "K2Node_IfThenElse_0")
ADD_T     = tmpl_from(h3, "K2Node_CallArrayFunction_2")   # Array_Add (typed)
FEACH_T   = tmpl_from(h3, "K2Node_MacroInstance_0")       # ForEachLoop
DIST_T    = tmpl_from(h3, "K2Node_CallFunction_65")       # GetDistanceTo
CMP_T     = tmpl_from(h3, "K2Node_CallFunction_66")       # Less_DoubleDouble
GDN_T     = tmpl_file(LIB + r"\call\get_display_name.t3d")
GIBT_T    = tmpl_file(LIB + r"\inventory\get_inventory_by_type.t3d")
GNIBT_T   = tmpl_file(LIB + r"\inventory\get_number_of_items_by_template.t3d")
MOVE_T    = tmpl_file(LIB + r"\inventory\move_items_by_template.t3d")
NEQ_T     = tmpl_file(LIB + r"\math\not_equal_object.t3d")
GTI_T     = tmpl_file(LIB + r"\math\greater_int.t3d")
SUB_T     = tmpl_file(LIB + r"\math\subtract_int.t3d")
MCGET_T   = tmpl_file(WLIB + r"\stocker\get_managed_containers.t3d")

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


def gac_for(path):
    n = add(GAC_T)
    setf(n, "ActorClass", "DefaultObject", f'"{path}"')
    setf(n, "OutActors", "PinType.PinSubCategoryObject", bgc(path))
    return n


def type_foreach(node, path):
    """Resolve a ForEachLoop macro's wildcard pins to a concrete element type.

    The brick was captured from an UNCONNECTED ForEach, so Array/Array Element are
    `wildcard`; a real connected ForEach serializes with them already resolved.
    Leaving them wildcard makes UE resolve them at paste time from whichever link
    it processes first, which is a race: in 3I the element collapsed to plain
    `Object` (two of its three targets -- NotEqual_ObjectObject.A and
    GetDisplayName.Object -- are CoreUObject.Object), and GetInventoryByType.owner
    wants an Actor, so the paste failed to compile with "Object Reference is not
    compatible with Actor Object Reference". Typing them here makes it deterministic;
    every target then takes an upcast.
    """
    setf(node, "Array", "PinType.PinCategory", '"object"')
    setf(node, "Array", "PinType.PinSubCategoryObject", bgc(path))
    setf(node, "Array", "PinType.ContainerType", "Array")
    setf(node, "Array Element", "PinType.PinCategory", '"object"')
    setf(node, "Array Element", "PinType.PinSubCategoryObject", bgc(path))
    setf(node, "Array Element", "PinType.ContainerType", "None")


# --- entry ------------------------------------------------------------------
event = copy.deepcopy(h3.by_name("K2Node_Event_0"))
delay8 = copy.deepcopy(h3.by_name("K2Node_CallFunction_1"))
g.nodes += [event, delay8]
pin(delay8, "then").links = []
setd(delay8, "Duration", "8.000000")

# --- 3H front half: gather in-range containers ------------------------------
gacDesk = gac_for(DESK)
deskItem = add(GETITEM_T)
setf(deskItem, "Array", "PinType.PinSubCategoryObject", bgc(DESK))
setf(deskItem, "Output", "PinType.PinSubCategoryObject", bgc(DESK))
setd(deskItem, "Dimension 1", "0")

gacAll = gac_for(BASE_CONTAINER)
pBegin = add(PRINT_T)
setd(pBegin, "InString", "STOCKER_3I begin (house rule 1: Metal station keeps 20 IronBar)")

feach = add(FEACH_T)
type_foreach(feach, BASE_CONTAINER)
dist = add(DIST_T)
cmp_ = add(CMP_T)
setd(cmp_, "B", RANGE)
branchRange = add(BRANCH_T)
arradd = add(ADD_T)
mcAdd = add(MCGET_T)

# --- the source: the Blacksmith ---------------------------------------------
gacSrc = gac_for(METAL)
srcItem = add(GETITEM_T)
setf(srcItem, "Array", "PinType.PinSubCategoryObject", bgc(METAL))
setf(srcItem, "Output", "PinType.PinSubCategoryObject", bgc(METAL))
setd(srcItem, "Dimension 1", "0")
srcInv = add(GIBT_T)
setd(srcInv, "inventoryType", "PlaceableInventory")
srcIron = add(GNIBT_T)
setd(srcIron, "templateID", IRON_BAR)
srcGdn = add(GDN_T)
pSrcLbl = add(PRINT_T)
setd(pSrcLbl, "InString", "STOCKER_3I source:")
pSrcName = add(PRINT_T)
srcConv = add(CONV_T)
pSrcIron = add(PRINT_T)

# --- the destination search -------------------------------------------------
mcLoop = add(MCGET_T)
feach2 = add(FEACH_T)
type_foreach(feach2, BASE_CONTAINER)
cInv = add(GIBT_T)
setd(cInv, "inventoryType", "PlaceableInventory")
cIron = add(GNIBT_T)
setd(cIron, "templateID", IRON_BAR)
holdsIron = add(GTI_T)          # cIron > 0
setd(holdsIron, "B", "0")
branchHolds = add(BRANCH_T)
notSelf = add(NEQ_T)            # c != source
branchNotSelf = add(BRANCH_T)
cGdn = add(GDN_T)
pDestLbl = add(PRINT_T)
setd(pDestLbl, "InString", "STOCKER_3I dest:")
pDestName = add(PRINT_T)
cConv = add(CONV_T)
pDestIron = add(PRINT_T)

# --- the move ---------------------------------------------------------------
excess = add(SUB_T)             # srcIron - 20
setd(excess, "B", KEEP)
hasExcess = add(GTI_T)          # excess > 0
setd(hasExcess, "B", "0")
branchExcess = add(BRANCH_T)
exConv = add(CONV_T)
pExLbl = add(PRINT_T)
setd(pExLbl, "InString", "STOCKER_3I excess:")
pExcess = add(PRINT_T)
move = add(MOVE_T)
setd(move, "templateID", IRON_BAR)
setd(move, "bMoveAllAvailable", "true")
setd(move, "ignoreSizeLimit", "true")
mvConv = add(CONV_T)
pMvLbl = add(PRINT_T)
setd(pMvLbl, "InString", "STOCKER_3I moved:")
pMoved = add(PRINT_T)

# --- data wiring: gather ----------------------------------------------------
connect(gacDesk, "OutActors", deskItem, "Array")
connect(gacAll, "OutActors", feach, "Array")
connect(feach, "Array Element", dist, "self")
connect(deskItem, "Output", dist, "OtherActor")
connect(dist, "ReturnValue", cmp_, "A")
connect(cmp_, "ReturnValue", branchRange, "Condition")
connect(mcAdd, "ManagedContainers", arradd, "TargetArray")
connect(feach, "Array Element", arradd, "NewItem")

# --- data wiring: source ----------------------------------------------------
connect(gacSrc, "OutActors", srcItem, "Array")
connect(srcItem, "Output", srcInv, "owner")
connect(srcItem, "Output", srcGdn, "Object")
connect(srcInv, "ReturnValue", srcIron, "self")
connect(srcGdn, "ReturnValue", pSrcName, "InString")
connect(srcIron, "ReturnValue", srcConv, "InInt")
connect(srcConv, "ReturnValue", pSrcIron, "InString")

# --- data wiring: dest search ----------------------------------------------
connect(mcLoop, "ManagedContainers", feach2, "Array")
connect(feach2, "Array Element", cInv, "owner")
connect(cInv, "ReturnValue", cIron, "self")
connect(cIron, "ReturnValue", holdsIron, "A")
connect(holdsIron, "ReturnValue", branchHolds, "Condition")
connect(feach2, "Array Element", notSelf, "A")
connect(srcItem, "Output", notSelf, "B")
connect(notSelf, "ReturnValue", branchNotSelf, "Condition")
connect(feach2, "Array Element", cGdn, "Object")
connect(cGdn, "ReturnValue", pDestName, "InString")
connect(cIron, "ReturnValue", cConv, "InInt")
connect(cConv, "ReturnValue", pDestIron, "InString")

# --- data wiring: the move --------------------------------------------------
connect(srcIron, "ReturnValue", excess, "A")
connect(excess, "ReturnValue", hasExcess, "A")
connect(hasExcess, "ReturnValue", branchExcess, "Condition")
connect(excess, "ReturnValue", exConv, "InInt")
connect(exConv, "ReturnValue", pExcess, "InString")
connect(srcInv, "ReturnValue", move, "self")          # move is called ON the source
connect(excess, "ReturnValue", move, "quantity")
connect(cInv, "ReturnValue", move, "targetInventory")
connect(move, "ReturnValue", mvConv, "InInt")
connect(mvConv, "ReturnValue", pMoved, "InString")

# --- exec wiring ------------------------------------------------------------
connect_exec(event, delay8) if not pin(delay8, "execute").links else None
connect_exec(delay8, gacDesk)
connect_exec(gacDesk, gacAll)
connect_exec(gacAll, pBegin)
connect_exec(pBegin, feach, "then", "Exec")
connect_exec(feach, branchRange, "LoopBody", "execute")
connect_exec(branchRange, arradd, "then", "execute")
# gather done -> resolve the source, print it
connect_exec(feach, gacSrc, "Completed", "execute")
connect_exec(gacSrc, pSrcLbl)
connect_exec(pSrcLbl, pSrcName)
connect_exec(pSrcName, pSrcIron)
# -> search ManagedContainers for the destination
connect_exec(pSrcIron, feach2, "then", "Exec")
connect_exec(feach2, branchHolds, "LoopBody", "execute")
connect_exec(branchHolds, branchNotSelf, "then", "execute")
connect_exec(branchNotSelf, pDestLbl, "then", "execute")
connect_exec(pDestLbl, pDestName)
connect_exec(pDestName, pDestIron)
connect_exec(pDestIron, branchExcess)
connect_exec(branchExcess, pExLbl, "then", "execute")
connect_exec(pExLbl, pExcess)
connect_exec(pExcess, move)
connect_exec(move, pMvLbl)
connect_exec(pMvLbl, pMoved)

# --- layout -----------------------------------------------------------------
event.set_position(0, -600); delay8.set_position(240, -600)
gacDesk.set_position(480, -600); deskItem.set_position(480, -380)
gacAll.set_position(760, -600); pBegin.set_position(1020, -600)
feach.set_position(1280, -600); dist.set_position(1560, -420)
cmp_.set_position(1760, -420); branchRange.set_position(1960, -600)
mcAdd.set_position(2160, -450); arradd.set_position(2220, -600)
gacSrc.set_position(1280, -1000); srcItem.set_position(1280, -820)
srcInv.set_position(1520, -820); srcIron.set_position(1720, -820)
srcGdn.set_position(1520, -1150)
pSrcLbl.set_position(1520, -1000); pSrcName.set_position(1760, -1000)
srcConv.set_position(1960, -880); pSrcIron.set_position(2000, -1000)
mcLoop.set_position(2240, -1150); feach2.set_position(2300, -1000)
cInv.set_position(2600, -820); cIron.set_position(2800, -820)
holdsIron.set_position(3000, -820); branchHolds.set_position(3200, -1000)
notSelf.set_position(3200, -820); branchNotSelf.set_position(3400, -1000)
cGdn.set_position(3400, -1200)
pDestLbl.set_position(3600, -1000); pDestName.set_position(3800, -1000)
cConv.set_position(3800, -1150); pDestIron.set_position(4000, -1000)
excess.set_position(4000, -820); hasExcess.set_position(4200, -820)
branchExcess.set_position(4200, -1000)
exConv.set_position(4400, -880)
pExLbl.set_position(4400, -1000); pExcess.set_position(4600, -1000)
move.set_position(4800, -1000)
mvConv.set_position(5000, -880)
pMvLbl.set_position(5040, -1000); pMoved.set_position(5240, -1000)

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

out = MOD + r"\.ccmod\graphs\stocker_3i.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"nodes: {len(g.nodes)}   wrote: {out}")
print(f"non-reciprocal / dangling problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
