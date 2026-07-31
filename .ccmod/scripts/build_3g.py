"""Author stocker_3g.t3d — a READ-ONLY repeating diagnostic (no move).

Goal (user spec): every ~10s, list each container BY NAME (GetDisplayName, not
owner-id) and the quantity of each known item BY NAME, so we can compare across
many runs while nothing is moved — to learn whether containers can be identified
reliably (GetAllActorsOfClass proved unreliable/volatile in 3F).

Flow (self-looping via Delay, no timer node):
  BeginPlay -> Delay(8s) -> LOOP:
     GetAllActorsOfClass(BP_PlaceableItemContainer)
     -> Print "===TICK==="  -> Print <total count via Array_Length>
     -> ForEach container:
          Print GetDisplayName(container)
          inv = GetInventoryByType(container, PlaceableInventory)
          Print GetNumberOfItemsByTemplate(inv, 11501)   # IronBar
          Print ... 10011 Wood, 12515 LayeredSilk, 18061 HardenedSteelBar
     -> (Completed) Delay(10s) -> back to GetAllActorsOfClass

Per container the log prints: name, then 4 counts in FIXED ORDER
[IronBar, Wood, LayeredSilk, HardenedSteelBar]. Bare name/number lines carry no
STOCKER_3G prefix (no string-concat node), so read the whole ModController
BlueprintUserMessages stream in the tick's time window, not just STOCKER_3G lines.
"""
import sys, copy
import os, pathlib
CCMOD = os.environ.get("CCMOD_HOME") or str(pathlib.Path(__file__).resolve().parents[3] / "claude-conan-modder")
sys.path.insert(0, CCMOD)
from ccmod.t3d import parse, connect, connect_exec
from ccmod.t3d.generator import instantiate
from ccmod.t3d.model import Graph

import pathlib
MOD = str(pathlib.Path(__file__).resolve().parents[2])
LIB = CCMOD + r"\library"
BASE_CONTAINER = "/Game/Systems/Building/Placeables/BP_PlaceableItemContainer.BP_PlaceableItemContainer_C"
# (label, templateID) in the fixed print order
ITEMS = [("IronBar", "11501"), ("Wood", "10011"), ("LayeredSilk", "12515"), ("HardenedSteelBar", "18061")]

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
def tmpl_from(graph, name):
    n = copy.deepcopy(graph.by_name(name))
    for p in n.pins: p.links = []
    return Graph(nodes=[n])
def tmpl_file(path):
    g = parse(open(path, encoding="utf-8").read())
    for n in g.nodes:
        for p in n.pins: p.links = []
    return g

GAC_T   = tmpl_from(e3, "K2Node_CallFunction_8")
PRINT_T = tmpl_from(e3, "K2Node_CallFunction_0")
CONV_T  = tmpl_from(e3, "K2Node_CallFunction_32")
DELAY_T = tmpl_from(e3, "K2Node_CallFunction_1")
LEN_T   = parse(ARRAY_LENGTH)
FEACH_T = tmpl_file(LIB + r"\flow\foreach.t3d")
GDN_T   = tmpl_file(LIB + r"\call\get_display_name.t3d")
GIBT_T  = tmpl_file(LIB + r"\inventory\get_inventory_by_type.t3d")
GNIBT_T = tmpl_file(LIB + r"\inventory\get_number_of_items_by_template.t3d")

g = Graph(nodes=[])
def add(t):  return instantiate(t, g)[0]

def pin(n, name):
    p = n.pin_by_name(name); assert p, f"{n.name} has no pin {name}"; return p
def setf(n, pn, k, raw): pin(n, pn)._set(k, raw)
def setd(n, pn, v):      setf(n, pn, "DefaultValue", f'"{v}"')

# --- entry: Event + Delay(8) (reuse from 3e, keep their mutual link) --------
event = copy.deepcopy(e3.by_name("K2Node_Event_0"))
delay8 = copy.deepcopy(e3.by_name("K2Node_CallFunction_1"))
g.nodes += [event, delay8]
pin(delay8, "then").links = []                 # drop delay -> old GAC
setd(delay8, "Duration", "8.000000")

# --- loop head --------------------------------------------------------------
gac = add(GAC_T)
setf(gac, "ActorClass", "DefaultObject", f'"{BASE_CONTAINER}"')
setf(gac, "OutActors", "PinType.PinSubCategoryObject",
     f'''"/Script/Engine.BlueprintGeneratedClass'{BASE_CONTAINER}'"''')
alen = add(LEN_T)
convTotal = add(CONV_T)
pHeader = add(PRINT_T); setd(pHeader, "InString", "STOCKER_3G ===TICK=== count/name/[Iron,Wood,Silk,HSteel]:")
pCount  = add(PRINT_T)
feach = add(FEACH_T)
delay10 = add(DELAY_T); setd(delay10, "Duration", "10.000000")

# per-container body
gdn  = add(GDN_T)
gibt = add(GIBT_T); setd(gibt, "inventoryType", "PlaceableInventory")
pName = add(PRINT_T)
item_nodes = []
for label, tid in ITEMS:
    gnibt = add(GNIBT_T); setd(gnibt, "templateID", tid)
    conv  = add(CONV_T)
    plbl  = add(PRINT_T); setd(plbl, "InString", f"  {label}:")
    pval  = add(PRINT_T)
    item_nodes.append((gnibt, conv, plbl, pval))

# --- data wiring ------------------------------------------------------------
connect(gac, "OutActors", feach, "Array")
connect(gac, "OutActors", alen, "TargetArray")
connect(alen, "ReturnValue", convTotal, "InInt")
connect(convTotal, "ReturnValue", pCount, "InString")
connect(feach, "Array Element", gdn, "Object")
connect(feach, "Array Element", gibt, "owner")
connect(gdn, "ReturnValue", pName, "InString")
for gnibt, conv, plbl, pval in item_nodes:
    connect(gibt, "ReturnValue", gnibt, "self")
    connect(gnibt, "ReturnValue", conv, "InInt")
    connect(conv, "ReturnValue", pval, "InString")

# --- exec wiring ------------------------------------------------------------
connect_exec(event, delay8) if not pin(delay8, "execute").links else None
connect_exec(delay8, gac)                        # initial entry
connect_exec(delay10, gac)                       # loop-back (2nd exec into gac.execute)
connect_exec(gac, pHeader)
connect_exec(pHeader, pCount)
connect_exec(pCount, feach, "then", "Exec")
# per-container body chain hung off LoopBody
connect_exec(feach, pName, "LoopBody", "execute")
prev = pName
for gnibt, conv, plbl, pval in item_nodes:
    connect_exec(prev, plbl)
    connect_exec(plbl, pval)
    prev = pval
# after all containers -> wait -> loop
connect_exec(feach, delay10, "Completed", "execute")

# --- layout (readability only) ---------------------------------------------
event.set_position(300, -600); delay8.set_position(560, -600)
gac.set_position(820, -600); pHeader.set_position(1080, -600); pCount.set_position(1300, -600)
alen.set_position(1080, -400); convTotal.set_position(1200, -400)
feach.set_position(1560, -600); delay10.set_position(1560, -300)
gdn.set_position(1900, -750); gibt.set_position(1900, -560); pName.set_position(2120, -820)
x = 2120
for gnibt, conv, plbl, pval in item_nodes:
    gnibt.set_position(x, -560); conv.set_position(x+150, -560)
    plbl.set_position(x, -700); pval.set_position(x+200, -700); x += 460

# --- validate reciprocity ---------------------------------------------------
problems = []; names = {n.name for n in g.nodes}
for n in g.nodes:
    for p in n.pins:
        for (lnn, lp) in p.links:
            if lnn not in names: problems.append(f"{n.name}.{p.name} -> missing {lnn}"); continue
            other = g.by_name(lnn).pin_by_id(lp)
            if other is None: problems.append(f"{n.name}.{p.name} -> {lnn} missing pin {lp}"); continue
            if (n.name, p.pin_id) not in other.links:
                problems.append(f"non-reciprocal: {n.name}.{p.name} -> {lnn}.{other.name}")

out = MOD + r"\.ccmod\graphs\stocker_3g.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"nodes: {len(g.nodes)}   wrote: {out}")
print(f"non-reciprocal / dangling problems: {len(problems)}")
for pr in problems: print("  !", pr)
