"""Transform stocker_3b.t3d -> stocker_3d.t3d.

Identical to 3C except MoveItemsByTemplateId now uses quantity=50 (3C used the
brick default quantity=0, which — with bMoveAllAvailable=true meaning "move UP TO
quantity, partial OK" — moved 0). Barest move-primitive test: does one stack move
and persist. Source = fuller Large chest by content (holds 12515), dest = other.
"""
import sys, re
import os, pathlib
CCMOD = os.environ.get("CCMOD_HOME") or str(pathlib.Path(__file__).resolve().parents[3] / "claude-conan-modder")
sys.path.insert(0, CCMOD)
from ccmod.t3d import parse, instantiate, connect, connect_exec

import pathlib
MOD = str(pathlib.Path(__file__).resolve().parents[2])
LIB = CCMOD + r"\library\inventory"
TEMPLATE_ID = "12515"   # held by owner 59 (the fuller chest -> source)
QUANTITY    = "50"      # 3D fix: real quantity instead of 0

g       = parse(open(MOD + r"\.ccmod\graphs\stocker_3b.t3d", encoding="utf-8").read())
gibt_t  = parse(open(LIB + r"\get_inventory_by_type.t3d", encoding="utf-8").read())
move_t  = parse(open(LIB + r"\move_items_by_template.t3d", encoding="utf-8").read())

def N(name):
    n = g.by_name(name)
    assert n, f"missing node {name}"
    return n

# --- existing nodes we hook into -----------------------------------------
ga0, ga1   = N("K2Node_GetArrayItem_0"), N("K2Node_GetArrayItem_1")
gpc0, gpc1 = N("K2Node_CallFunction_20"), N("K2Node_CallFunction_21")   # GetPopulatedItemCount
ps30, ps33 = N("K2Node_CallFunction_30"), N("K2Node_CallFunction_33")   # then-branch prints
ps40, ps43 = N("K2Node_CallFunction_40"), N("K2Node_CallFunction_43")   # else-branch prints
conv32, conv42 = N("K2Node_CallFunction_32"), N("K2Node_CallFunction_42")  # Conv_IntToString

# --- nodes to delete (old proxy + move mechanism) ------------------------
remove = {"K2Node_VariableGet_0", "K2Node_VariableGet_1",   # PlaceableInventory proxies
          "K2Node_CallFunction_2", "K2Node_CallFunction_3", # MoveAndStackItems
          "K2Node_VariableGet_2", "K2Node_VariableGet_3"}    # ItemDistributor gets

# --- instantiate the four new brick nodes --------------------------------
gibt0 = instantiate(gibt_t, g)[0]
gibt1 = instantiate(gibt_t, g)[0]
move_then = instantiate(move_t, g)[0]
move_else = instantiate(move_t, g)[0]
new_nodes = [gibt0, gibt1, move_then, move_else]

def clear_links(n):
    for p in n.pins:
        p.links = []

# brick nodes carry dangling links to their source graph -> scrub them all
for n in new_nodes:
    clear_links(n)

# --- remove old nodes, then scrub every dangling ref to them -------------
g.nodes = [n for n in g.nodes if n.name not in remove]
for n in g.nodes:
    for p in n.pins:
        kept = [(ln, lp) for (ln, lp) in p.links if ln not in remove]
        if kept != p.links:
            p.links = kept

# --- set pin defaults -----------------------------------------------------
def set_default(node, pin, value):
    p = node.pin_by_name(pin)
    p._set("DefaultValue", f'"{value}"')

set_default(gibt0, "inventoryType", "PlaceableInventory")
set_default(gibt1, "inventoryType", "PlaceableInventory")
for mv in (move_then, move_else):
    set_default(mv, "templateID", TEMPLATE_ID)
    set_default(mv, "quantity", QUANTITY)   # 3D: 50, not 0
    # bMoveAllAvailable / ignoreSizeLimit already default "true" in the brick

# --- log banners: mark 3D (pak-grep sentinel) ----------------------------
set_default(N("K2Node_CallFunction_0"),  "InString", "STOCKER_3D begin")
set_default(ps30, "InString", "STOCKER_3D src=chest0 (MIBT q50 12515 -> chest1)")
set_default(ps40, "InString", "STOCKER_3D src=chest1 (MIBT q50 12515 -> chest0)")

# --- positions (readability only) ----------------------------------------
gibt0.set_position(2950, -1620)
gibt1.set_position(2950, -1300)
move_then.set_position(3792, -1568)
move_else.set_position(4492, -1168)

# --- wire data ------------------------------------------------------------
connect(gibt0, "owner", ga0, "Output")
connect(gibt1, "owner", ga1, "Output")
connect(gibt0, "ReturnValue", gpc0, "self")      # count reads off the real inventory
connect(gibt1, "ReturnValue", gpc1, "self")
# then-branch: chest0 is fuller -> source=chest0(gibt0), dest=chest1(gibt1)
connect(move_then, "self", gibt0, "ReturnValue")
connect(move_then, "targetInventory", gibt1, "ReturnValue")
connect(move_then, "ReturnValue", conv32, "InInt")
# else-branch: chest1 fuller -> source=chest1(gibt1), dest=chest0(gibt0)
connect(move_else, "self", gibt1, "ReturnValue")
connect(move_else, "targetInventory", gibt0, "ReturnValue")
connect(move_else, "ReturnValue", conv42, "InInt")

# --- wire exec ------------------------------------------------------------
connect_exec(ps30, move_then)     # then: PrintString -> move
connect_exec(move_then, ps33)     # move  -> PrintString
connect_exec(ps40, move_else)
connect_exec(move_else, ps43)

# --- validate reciprocity -------------------------------------------------
problems = []
names = {n.name for n in g.nodes}
for n in g.nodes:
    for p in n.pins:
        for (ln, lp) in p.links:
            if ln not in names:
                problems.append(f"{n.name}.{p.name} -> missing node {ln}")
                continue
            other = g.by_name(ln).pin_by_id(lp)
            if other is None:
                problems.append(f"{n.name}.{p.name} -> {ln} missing pin {lp}")
                continue
            if (n.name, p.pin_id) not in other.links:
                problems.append(f"non-reciprocal: {n.name}.{p.name} -> {ln}.{other.name}")

out = MOD + r"\.ccmod\graphs\stocker_3d.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"nodes: {len(g.nodes)}   wrote: {out}")
print(f"non-reciprocal / dangling problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
