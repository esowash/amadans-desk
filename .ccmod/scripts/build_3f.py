"""Author stocker_3f.t3d — a DIAGNOSTIC (no move).

3E proved the move machinery works but the destination lookup
`GetAllActorsOfClass(BP_PL_Chest_Large)` returned an EMPTY array at runtime, even
though chest 59 exists, is loaded, and is exactly that class — while
`GetAllActorsOfClass(BP_PL_CraftingStation_Metal)` found the station. Timing,
graph, and DB are all ruled out. So: ask the engine directly.

For each candidate class this prints the COUNT GetAllActorsOfClass returns:
    STOCKER_3F <label>
    <count>
Classes: Metal station (known-good control), Large chest (the failing one),
Medium chest (worked in 3D; near chest 65 exists), and the shared base
BP_PlaceableItemContainer (the design end-state + candidate fix — if the base
sees the chest when the leaf class doesn't, switch the dest lookup to the base).

Structure: BeginPlay -> Delay(8s) -> Print "begin" -> for each class:
    GetAllActorsOfClass(class) -> Print "<label>" -> [Array_Length -> IntToString] -> Print count
"""
import sys, copy
CCMOD = r"<CCMOD_HOME>"
sys.path.insert(0, CCMOD)
from ccmod.t3d import parse, connect, connect_exec
from ccmod.t3d.generator import instantiate
from ccmod.t3d.model import Graph

MOD = r"<MOD_ROOT>"
PRE = "/Game/Systems/Building/Placeables/"
CLASSES = [
    ("Metal_ctrl",     PRE + "BP_PL_CraftingStation_Metal.BP_PL_CraftingStation_Metal_C"),
    ("Large",          PRE + "BP_PL_Chest_Large.BP_PL_Chest_Large_C"),
    ("Medium",         PRE + "BP_PL_Chest_Medium.BP_PL_Chest_Medium_C"),
    ("BaseContainer",  PRE + "BP_PlaceableItemContainer.BP_PlaceableItemContainer_C"),
]

# --- Array_Length template (hand-written; pure K2Node_CallArrayFunction) ------
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

src = parse(open(MOD + r"\.ccmod\graphs\stocker_3e.t3d", encoding="utf-8").read())

def template(name):
    n = copy.deepcopy(src.by_name(name))
    for p in n.pins:
        p.links = []
    return Graph(nodes=[n])

gac_tmpl   = template("K2Node_CallFunction_8")    # GetAllActorsOfClass
print_tmpl = template("K2Node_CallFunction_0")    # PrintString
conv_tmpl  = template("K2Node_CallFunction_32")   # Conv_IntToString
len_tmpl   = parse(ARRAY_LENGTH)

# --- helpers ----------------------------------------------------------------
def pin(node, name):
    p = node.pin_by_name(name); assert p, f"{node.name} has no pin {name}"; return p
def setf(node, pinname, key, raw):
    pin(node, pinname)._set(key, raw)
def set_default(node, pinname, value):
    setf(node, pinname, "DefaultValue", f'"{value}"')
def bgc(path):
    return f'''"/Script/Engine.BlueprintGeneratedClass'{path}'"'''

# --- new graph: keep Event + Delay as the entry -----------------------------
g = Graph(nodes=[])
event = copy.deepcopy(src.by_name("K2Node_Event_0"))
delay = copy.deepcopy(src.by_name("K2Node_CallFunction_1"))
g.nodes += [event, delay]
pin(delay, "then").links = []                     # drop delay -> old GAC

begin = instantiate(print_tmpl, g)[0]
set_default(begin, "InString", "STOCKER_3F begin")
begin.set_position(1700, -1900)
connect_exec(delay, begin)

prev = begin
row = 0
for label, path in CLASSES:
    gac  = instantiate(gac_tmpl,  g)[0]
    ln   = instantiate(len_tmpl,  g)[0]
    conv = instantiate(conv_tmpl, g)[0]
    plab = instantiate(print_tmpl, g)[0]
    pcnt = instantiate(print_tmpl, g)[0]
    for n in (gac, ln, conv, plab, pcnt):
        for p in n.pins:
            p.links = []                          # start clean, wire explicitly
    # class on the enumeration + the length pin's array element type
    setf(gac, "ActorClass", "DefaultObject", f'"{path}"')
    setf(gac, "OutActors", "PinType.PinSubCategoryObject", bgc(path))
    setf(ln,  "TargetArray", "PinType.PinSubCategoryObject", bgc(path))
    set_default(plab, "InString", f"STOCKER_3F {label}")
    # data: GAC.OutActors -> Array_Length -> IntToString -> count print
    connect(gac, "OutActors", ln, "TargetArray")
    connect(ln, "ReturnValue", conv, "InInt")
    connect(conv, "ReturnValue", pcnt, "InString")
    # exec: prev -> gac -> plab -> pcnt
    connect_exec(prev, gac)
    connect_exec(gac, plab)
    connect_exec(plab, pcnt)
    prev = pcnt
    # layout
    x = 2100 + row * 900
    gac.set_position(x, -1800); plab.set_position(x + 300, -1900)
    ln.set_position(x + 300, -1650); conv.set_position(x + 480, -1650)
    pcnt.set_position(x + 620, -1800)
    row += 1

# --- validate reciprocity ---------------------------------------------------
problems = []
names = {n.name for n in g.nodes}
for n in g.nodes:
    for p in n.pins:
        for (lnn, lp) in p.links:
            if lnn not in names:
                problems.append(f"{n.name}.{p.name} -> missing node {lnn}"); continue
            other = g.by_name(lnn).pin_by_id(lp)
            if other is None:
                problems.append(f"{n.name}.{p.name} -> {lnn} missing pin {lp}"); continue
            if (n.name, p.pin_id) not in other.links:
                problems.append(f"non-reciprocal: {n.name}.{p.name} -> {lnn}.{other.name}")

out = MOD + r"\.ccmod\graphs\stocker_3f.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"nodes: {len(g.nodes)}   classes: {len(CLASSES)}   wrote: {out}")
print(f"non-reciprocal / dangling problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
