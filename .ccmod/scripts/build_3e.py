"""Transform stocker_3d.t3d -> stocker_3e.t3d.

3E is the first *honest* move test. Root cause of 3A-3D no-ops: the graph
enumerated BP_PL_Chest_Medium (two empty chests 2.6 km away), so the source
never held the item it was told to move. 3E fixes that and does a DIRECTED,
cross-class move:

    source = Blacksmith  (BP_PL_CraftingStation_Metal, owner 57, holds Iron Bar)
    dest   = Large Chest (BP_PL_Chest_Large,            owner 59, ALSO holds Iron Bar)
    item   = 11501 (Iron Bar), move ALL (bMoveAllAvailable=true, quantity=999)

Only ONE Metal station and ONE Large chest exist in the save, so index [0] of
each GetAllActorsOfClass is unambiguous (no far-away pollution). The dest already
holds Iron Bar, so the "merge-into-existing-stack?" question is also controlled.

Structural change from 3D: drop the pick-the-fuller branch entirely (Branch +
2x GetPopulatedItemCount + Greater + the whole else path). It becomes a straight
line: BeginPlay -> Delay -> GAC(station) -> GAC(chest) -> Print begin ->
Print src -> MoveItemsByTemplateId -> Print result.
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
STA = "/Game/Systems/Building/Placeables/BP_PL_CraftingStation_Metal.BP_PL_CraftingStation_Metal_C"
LRG = "/Game/Systems/Building/Placeables/BP_PL_Chest_Large.BP_PL_Chest_Large_C"
TEMPLATE_ID = "11501"   # Iron Bar
QUANTITY    = "999"     # "move all" ceiling; bMoveAllAvailable=true keeps partial OK

g = parse(open(MOD + r"\.ccmod\graphs\stocker_3d.t3d", encoding="utf-8").read())

def N(name):
    n = g.by_name(name); assert n, f"missing node {name}"; return n

# --- existing nodes we keep -------------------------------------------------
delay     = N("K2Node_CallFunction_1")     # Delay 8s
gac_sta   = N("K2Node_CallFunction_8")     # GetAllActorsOfClass -> repurpose to Metal station
begin     = N("K2Node_CallFunction_0")     # PrintString "begin"
gai0      = N("K2Node_GetArrayItem_0")     # station[0]
gai1      = N("K2Node_GetArrayItem_1")     # chest[0]
gibt_src  = N("K2Node_CallFunction_1757")  # GetInventoryByType(station) = srcInv
gibt_dst  = N("K2Node_CallFunction_1758")  # GetInventoryByType(chest)   = dstInv
print_src = N("K2Node_CallFunction_30")    # PrintString src banner (then-branch print)
move      = N("K2Node_CallFunction_1129")  # MoveItemsByTemplateId (then-branch move)
# conv 32 -> print_res 33 tail stays wired to the move already

# --- clone the station GAC into a second GAC for the Large chest ------------
gac_chest = instantiate(Graph(nodes=[copy.deepcopy(gac_sta)]), g)[0]
for p in gac_chest.pins:            # scrub links copied from the source graph
    p.links = []
gac_chest.set_position(1344, -1120)

# --- delete the pick-the-fuller branch + the whole else path ----------------
remove = {"K2Node_IfThenElse_0",
          "K2Node_CallFunction_20", "K2Node_CallFunction_21",   # GetPopulatedItemCount
          "K2Node_PromotableOperator_0",                        # Greater_IntInt
          "K2Node_CallFunction_1130",                           # else move
          "K2Node_CallFunction_40", "K2Node_CallFunction_42", "K2Node_CallFunction_43"}
g.nodes = [n for n in g.nodes if n.name not in remove]
for n in g.nodes:                   # scrub every dangling ref to a removed node
    for p in n.pins:
        kept = [(ln, lp) for (ln, lp) in p.links if ln not in remove]
        if kept != p.links:
            p.links = kept

# --- helpers ----------------------------------------------------------------
def pin(node, name):
    p = node.pin_by_name(name); assert p, f"{node.name} has no pin {name}"; return p
def set_field(node, pinname, key, raw):
    pin(node, pinname)._set(key, raw)
def set_default(node, pinname, value):
    set_field(node, pinname, "DefaultValue", f'"{value}"')
def dobj(path):  # ActorClass DefaultObject literal
    return f'"{path}"'
def bgc(path):   # PinType.PinSubCategoryObject BlueprintGeneratedClass literal
    return f'''"/Script/Engine.BlueprintGeneratedClass'{path}'"'''

# --- retarget the two enumerations to the right classes ---------------------
# station GAC (Metal) feeds only gai0
set_field(gac_sta, "ActorClass", "DefaultObject", dobj(STA))
set_field(gac_sta, "OutActors", "PinType.PinSubCategoryObject", bgc(STA))
pin(gac_sta, "OutActors").links = [(ln, lp) for (ln, lp) in pin(gac_sta, "OutActors").links
                                   if ln == "K2Node_GetArrayItem_0"]
set_field(gai0, "Array",  "PinType.PinSubCategoryObject", bgc(STA))
set_field(gai0, "Output", "PinType.PinSubCategoryObject", bgc(STA))

# chest GAC (Large) feeds gai1 at index 0
set_field(gac_chest, "ActorClass", "DefaultObject", dobj(LRG))
set_field(gac_chest, "OutActors", "PinType.PinSubCategoryObject", bgc(LRG))
set_field(gai1, "Array",  "PinType.PinSubCategoryObject", bgc(LRG))
set_field(gai1, "Output", "PinType.PinSubCategoryObject", bgc(LRG))
set_default(gai1, "Dimension 1", "0")            # index 1 -> 0
pin(gai1, "Array").links = []
connect(gac_chest, "OutActors", gai1, "Array")

# --- rewire exec into a straight line ---------------------------------------
# was: ... -> gac_sta -> begin -> Branch -> then/else
# now: ... -> gac_sta -> gac_chest -> begin -> print_src -> move -> print_res
pin(gac_sta, "then").links = []                  # drop gac_sta -> begin
pin(begin, "execute").links = []                 # drop begin <- gac_sta
connect_exec(gac_sta, gac_chest)                 # gac_sta -> gac_chest
connect_exec(gac_chest, begin)                   # gac_chest -> begin
pin(begin, "then").links = []                    # (Branch link already scrubbed)
connect_exec(begin, print_src)                   # begin -> print_src
# print_src -> move -> conv -> print_res tail is already intact from 3D

# --- params + banners -------------------------------------------------------
set_default(begin,     "InString", "STOCKER_3E begin")
set_default(print_src, "InString", "STOCKER_3E move ALL IronBar(11501) Blacksmith57 -> LargeChest59")
set_default(move, "templateID", TEMPLATE_ID)
set_default(move, "quantity",   QUANTITY)
set_default(move, "bMoveAllAvailable", "true")
set_default(move, "ignoreSizeLimit",   "true")

# --- validate reciprocity ---------------------------------------------------
problems = []
names = {n.name for n in g.nodes}
for n in g.nodes:
    for p in n.pins:
        for (ln, lp) in p.links:
            if ln not in names:
                problems.append(f"{n.name}.{p.name} -> missing node {ln}"); continue
            other = g.by_name(ln).pin_by_id(lp)
            if other is None:
                problems.append(f"{n.name}.{p.name} -> {ln} missing pin {lp}"); continue
            if (n.name, p.pin_id) not in other.links:
                problems.append(f"non-reciprocal: {n.name}.{p.name} -> {ln}.{other.name}")

out = MOD + r"\.ccmod\graphs\stocker_3e.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"nodes: {len(g.nodes)}   wrote: {out}")
print(f"non-reciprocal / dangling problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
