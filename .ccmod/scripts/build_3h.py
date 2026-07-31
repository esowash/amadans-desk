"""Author stocker_3h.t3d — gather in-range containers into the ManagedContainers member array.

First build that writes to a real Blueprint member variable. Single-shot (not the
parked repeating timer): BeginPlay fires once, so ManagedContainers starts empty by
default and needs no clear step.

Flow:
  BeginPlay -> Delay(8s)
    -> GAC(BP_PL_Table_Zingaran_Mercenary_Captains) -> GetArrayItem[0] = desk anchor
    -> GAC(BP_PlaceableItemContainer)               -> every container (17 in 3G)
    -> Print "STOCKER_3H begin"
    -> ForEach c in containers:
         Branch( Less_DoubleDouble( c.GetDistanceTo(desk), 3000 ) )
           True -> Array_Add(TargetArray = Get ManagedContainers, NewItem = c)
           False -> (skip)
    -> Completed -> Print "STOCKER_3H in range:" -> Print Length(ManagedContainers)
                 -> ForEach m in ManagedContainers: Print GetDisplayName(m)

Ground truth behind the range test (BTS_CancelOrderDistance, pulled 2026-07-16):
  Character.GetDistanceTo(Player) -> Greater_DoubleDouble.A ; B = threshold -> Branch.Condition
We keep that shape, flip the operator to Less_DoubleDouble (identical signature,
same KismetMathLibrary), and put the literal 3000 in B.

Note GetDistanceTo.ReturnValue is real/FLOAT while Less_DoubleDouble.A/B are
real/DOUBLE. Shipped content wires them directly and UE promotes within the "real"
category -- do NOT "fix" the subcategories to match.

Array_Add is captured as wildcard; resolve TargetArray/NewItem to the concrete
container type here (same approach as build_3f's hand-written Array_Length).
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

BASE_CONTAINER = ("/Game/Systems/Building/Placeables/"
                  "BP_PlaceableItemContainer.BP_PlaceableItemContainer_C")
# Anchor = stand-in for Amadan's Desk. NOT the Zingaran table the kickoff doc
# named: that is DLC content and the DevKit ships no DLC placeables, so the class
# is unreferenceable here (checked 2026-07-16). This Stygian table is base game,
# present in the DevKit, and placed exactly once in the save (actor id 69) with
# zero inventory rows, so it never enters the container enumeration.
DESK = ("/Game/Systems/Building/Placeables/"
        "BP_PL_Table_Strategy_Stygian.BP_PL_Table_Strategy_Stygian_C")
RANGE = "3000.000000"

# Array_Length: hand-written pure K2Node_CallArrayFunction (proven in 3F/3G).
ARRAY_LENGTH = '''Begin Object Class=/Script/BlueprintGraph.K2Node_CallArrayFunction Name="K2Node_CallArrayFunction_0"
   bIsPureFunc=True
   FunctionReference=(MemberParent="/Script/CoreUObject.Class'/Script/Engine.KismetArrayLibrary'",MemberName="Array_Length")
   NodePosX=0
   NodePosY=0
   NodeGuid=A1000000000000000000000000000001
   CustomProperties Pin (PinId=A1000000000000000000000000000011,PinName="self",PinFriendlyName=NSLOCTEXT("K2Node", "Target", "Target"),PinType.PinCategory="object",PinType.PinSubCategory="",PinType.PinSubCategoryObject="/Script/CoreUObject.Class'/Script/Engine.KismetArrayLibrary'",PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,DefaultObject="/Script/Engine.Default__KismetArrayLibrary",PersistentGuid=00000000000000000000000000000000,bHidden=True,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=A1000000000000000000000000000012,PinName="TargetArray",PinType.PinCategory="object",PinType.PinSubCategory="",PinType.PinSubCategoryObject="/Script/CoreUObject.Class'/Script/Engine.Actor'",PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=Array,PinType.bIsReference=True,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=A1000000000000000000000000000013,PinName="ReturnValue",Direction="EGPD_Output",PinType.PinCategory="int",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
End Object
'''

e3 = parse(open(MOD + r"\.ccmod\graphs\stocker_3e.t3d", encoding="utf-8").read())
d3 = parse(open(MOD + r"\.ccmod\graphs\stocker_3d.t3d", encoding="utf-8").read())


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


GAC_T    = tmpl_from(e3, "K2Node_CallFunction_8")     # GetAllActorsOfClass
PRINT_T  = tmpl_from(e3, "K2Node_CallFunction_0")     # PrintString
CONV_T   = tmpl_from(e3, "K2Node_CallFunction_32")    # Conv_IntToString
DELAY_T  = tmpl_from(e3, "K2Node_CallFunction_1")     # Delay
GETITEM_T = tmpl_from(e3, "K2Node_GetArrayItem_0")    # GetArrayItem
BRANCH_T = tmpl_from(d3, "K2Node_IfThenElse_0")       # Branch
LEN_T    = parse(ARRAY_LENGTH)
FEACH_T  = tmpl_file(LIB + r"\flow\foreach.t3d")
GDN_T    = tmpl_file(LIB + r"\call\get_display_name.t3d")
DIST_T   = tmpl_file(LIB + r"\actor\get_distance_to.t3d")
CMP_T    = tmpl_file(LIB + r"\math\greater_double.t3d")
ADD_T    = tmpl_file(LIB + r"\array\array_add.t3d")
MCGET_T  = tmpl_file(WLIB + r"\stocker\get_managed_containers.t3d")

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


def as_container(node, pinname):
    """Resolve a wildcard/typed pin to a BP_PlaceableItemContainer object ref."""
    setf(node, pinname, "PinType.PinCategory", '"object"')
    setf(node, pinname, "PinType.PinSubCategoryObject", bgc(BASE_CONTAINER))


# --- entry: Event + Delay(8), reusing 3E's pair and their mutual link --------
event = copy.deepcopy(e3.by_name("K2Node_Event_0"))
delay8 = copy.deepcopy(e3.by_name("K2Node_CallFunction_1"))
g.nodes += [event, delay8]
pin(delay8, "then").links = []          # drop delay -> old 3E GAC
setd(delay8, "Duration", "8.000000")

# --- the desk anchor: GAC(table)[0] -----------------------------------------
gacDesk = add(GAC_T)
setf(gacDesk, "ActorClass", "DefaultObject", f'"{DESK}"')
setf(gacDesk, "OutActors", "PinType.PinSubCategoryObject", bgc(DESK))
deskItem = add(GETITEM_T)
setf(deskItem, "Array", "PinType.PinSubCategoryObject", bgc(DESK))
setf(deskItem, "Output", "PinType.PinSubCategoryObject", bgc(DESK))
setd(deskItem, "Dimension 1", "0")

# --- every container --------------------------------------------------------
gacAll = add(GAC_T)
setf(gacAll, "ActorClass", "DefaultObject", f'"{BASE_CONTAINER}"')
setf(gacAll, "OutActors", "PinType.PinSubCategoryObject", bgc(BASE_CONTAINER))

pBegin = add(PRINT_T)
setd(pBegin, "InString", "STOCKER_3H begin (gather containers within 3000 of desk)")

# --- the range filter loop --------------------------------------------------
feach = add(FEACH_T)
dist = add(DIST_T)
cmp_ = add(CMP_T)
# Greater_DoubleDouble and Less_DoubleDouble share a signature; flip the operator
# so the test reads distance < RANGE with A = distance, B = threshold.
for i, (kind, text) in enumerate(cmp_.body):
    if kind == "raw" and "Greater_DoubleDouble" in text:
        cmp_.body[i] = (kind, text.replace("Greater_DoubleDouble", "Less_DoubleDouble"))
setd(cmp_, "B", RANGE)
branch = add(BRANCH_T)
arradd = add(ADD_T)
mcAdd = add(MCGET_T)
as_container(arradd, "TargetArray")
setf(arradd, "TargetArray", "PinType.ContainerType", "Array")
as_container(arradd, "NewItem")
setf(arradd, "NewItem", "PinType.ContainerType", "None")

# --- report -----------------------------------------------------------------
pInRange = add(PRINT_T)
setd(pInRange, "InString", "STOCKER_3H in range:")
mcLen = add(MCGET_T)
alen = add(LEN_T)
setf(alen, "TargetArray", "PinType.PinSubCategoryObject", bgc(BASE_CONTAINER))
convLen = add(CONV_T)
pLen = add(PRINT_T)
mcNames = add(MCGET_T)
feach2 = add(FEACH_T)
gdn = add(GDN_T)
pName = add(PRINT_T)

# --- data wiring ------------------------------------------------------------
connect(gacDesk, "OutActors", deskItem, "Array")
connect(gacAll, "OutActors", feach, "Array")
connect(feach, "Array Element", dist, "self")        # container = distance source
connect(deskItem, "Output", dist, "OtherActor")      # desk = the other end
connect(dist, "ReturnValue", cmp_, "A")              # A = distance (shipped idiom)
connect(cmp_, "ReturnValue", branch, "Condition")
connect(mcAdd, "ManagedContainers", arradd, "TargetArray")
connect(feach, "Array Element", arradd, "NewItem")
# report
connect(mcLen, "ManagedContainers", alen, "TargetArray")
connect(alen, "ReturnValue", convLen, "InInt")
connect(convLen, "ReturnValue", pLen, "InString")
connect(mcNames, "ManagedContainers", feach2, "Array")
connect(feach2, "Array Element", gdn, "Object")
connect(gdn, "ReturnValue", pName, "InString")

# --- exec wiring ------------------------------------------------------------
connect_exec(event, delay8) if not pin(delay8, "execute").links else None
connect_exec(delay8, gacDesk)
connect_exec(gacDesk, gacAll)
connect_exec(gacAll, pBegin)
connect_exec(pBegin, feach, "then", "Exec")
# loop body: Branch -> (true) Array Add ; false falls through
connect_exec(feach, branch, "LoopBody", "execute")
connect_exec(branch, arradd, "then", "execute")
# after the loop: report
connect_exec(feach, pInRange, "Completed", "execute")
connect_exec(pInRange, pLen)
connect_exec(pLen, feach2, "then", "Exec")
connect_exec(feach2, pName, "LoopBody", "execute")

# --- layout (readability only) ----------------------------------------------
event.set_position(0, -600)
delay8.set_position(260, -600)
gacDesk.set_position(520, -600)
deskItem.set_position(520, -380)
gacAll.set_position(820, -600)
pBegin.set_position(1080, -600)
feach.set_position(1340, -600)
dist.set_position(1660, -420)
cmp_.set_position(1860, -420)
branch.set_position(2060, -600)
mcAdd.set_position(2260, -450)
arradd.set_position(2320, -600)
pInRange.set_position(1340, -900)
mcLen.set_position(1560, -1050)
alen.set_position(1720, -1050)
convLen.set_position(1880, -1050)
pLen.set_position(1600, -900)
mcNames.set_position(1860, -1200)
feach2.set_position(2060, -900)
gdn.set_position(2360, -1050)
pName.set_position(2560, -900)

# --- validate reciprocity ---------------------------------------------------
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

# Guard the operator flip actually landed.
cmp_raw = " ".join(t for k, t in cmp_.body if k == "raw")
assert "Less_DoubleDouble" in cmp_raw, "operator flip failed"
assert "Greater_DoubleDouble" not in cmp_raw, "stale Greater_DoubleDouble remains"

out = MOD + r"\.ccmod\graphs\stocker_3h.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"nodes: {len(g.nodes)}   wrote: {out}")
print(f"non-reciprocal / dangling problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
