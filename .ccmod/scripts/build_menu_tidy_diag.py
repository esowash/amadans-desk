r"""Splice per-item diagnostic prints into the REAL, LIVE TidyManagedStations graph (pulled fresh
this session as tidymanagedstations_live_s19.t3d -- same discipline as build_restockmanagedstations_diag.py:
full pull+edit+repaste onto the actual live topology, not a re-derivation from the original build
script, so this taps ApplyKeepRule's own real Moved/Outcome output pins on the one real call site
that already exists.

Investigating: after a rule is DELETED mid-session, the very next tidy pass should treat that
item as unruled (opt-out design: "no rule = keep 0") and sweep it out entirely. A live playtest
showed 20 units of Star Metal Bar (TemplateID 18061) still sitting in the Metal crafting station
after TWO sweep passes following the rule's deletion, despite the station's own "rules matched"
count correctly dropping to exclude it. TidyManagedStations has no per-item print at all (only the
aggregate "stations to process"/"rules matched" counts already in the live graph) -- this build
adds two diagnostic points to see exactly what happens to each item:

1. K2Node_IfThenElse_2 (the ruled/unruled gate, Condition = Array_Contains(RuleTemplateID,
   Item.TemplateID)) `.then` (ruled/protected branch, currently a dead end -- ite_ruled.then never
   went anywhere) gets a print: "MENU_TIDY_ITEM: <TemplateID> RULED, skipped".
2. K2Node_CallFunction_118 (ApplyKeepRule, the unruled/opt-out-tidy branch)'s `.then` (also
   currently dangling, same gap RESTOCK_DIAG's own investigation found on the restock side) gets
   the full RESTOCK_DIAG-style block: Station (GetDisplayName), TemplateID, Moved, Outcome -- straight
   from ApplyKeepRule's own return values, not inferred from a save-DB diff.

If Star Metal Bar shows up in the UNRULED branch with Moved=0, that points at the known
NoDestination/orphan gap. If it shows up in the RULED branch, RuleTemplateID is somehow still
carrying a stale 18061 despite the aggregate count looking right (a real, different bug). If it
never shows up in EITHER branch, the item loop itself isn't seeing it (e.g. GetInventoryByType's
ItemList not including it) -- a third, more surprising possibility.
"""
import sys

import os, pathlib
CCMOD = os.environ.get("CCMOD_HOME") or str(pathlib.Path(__file__).resolve().parents[3] / "claude-conan-modder")
sys.path.insert(0, CCMOD)
from ccmod import db
from ccmod.t3d import parse, connect, connect_exec
from ccmod.t3d.generator import instantiate
from ccmod.t3d.model import Graph
from ccmod.workspace import Workspace

import pathlib
MOD = str(pathlib.Path(__file__).resolve().parents[2])
LIB = CCMOD + r"\library"

ws = Workspace.resolve()
conn = db.connect(ws.cache_db)
row = db.get_graph(conn, "tidymanagedstations_live_s19")
assert row, "run `ccmod pull --save tidymanagedstations_live_s19` first"
g = parse(row["t3d"])


def by_name(name):
    n = g.by_name(name)
    assert n, f"missing node {name}"
    return n


def pin(n, name, output=None):
    p = n.pin_by_name(name, output=output)
    assert p, f"{n.name} has no pin {name}"
    return p


def setf(n, pn, k, raw, output=None):
    pin(n, pn, output=output)._set(k, raw)


def add(t):
    return instantiate(t, g)[0]


def tmpl_file(path):
    t = parse(open(path, encoding="utf-8-sig").read())
    for n in t.nodes:
        for p in n.pins:
            p.links = []
    return t


GETDISPLAYNAME_T = tmpl_file(LIB + r"\call\get_display_name.t3d")
CONV_UID_TO_STRING_T = tmpl_file(LIB + r"\actor\conv_uniqueid_to_string.t3d")

RAW_PRINT = '''Begin Object Class=/Script/BlueprintGraph.K2Node_CallFunction Name="K2Node_CallFunction_Print"
   FunctionReference=(MemberParent=Class'"/Script/Engine.KismetSystemLibrary"',MemberName="PrintString")
   NodeGuid=00000000000000000000000000000000
   CustomProperties Pin (PinId=00000000000000000000000000000020,PinName="execute",PinType.PinCategory="exec",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000021,PinName="InString",PinType.PinCategory="string",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,DefaultValue="",PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000022,PinName="then",Direction="EGPD_Output",PinType.PinCategory="exec",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
End Object'''
PRINT_T = parse(RAW_PRINT)

KISMET_STRING_LIB = "\"/Script/CoreUObject.Class'/Script/Engine.KismetStringLibrary'\""


def make_print(label_text):
    n = add(PRINT_T)
    pin(n, "InString")._set("DefaultValue", f'"{label_text}"')
    return n


def make_print_wired(source_node, source_pin):
    n = add(PRINT_T)
    connect(source_node, source_pin, n, "InString")
    return n


def conv(member_name, in_pin_name, in_category, source_node, source_pin):
    n = add(CONV_UID_TO_STRING_T)
    n._replace_prop("FunctionReference", f'(MemberParent={KISMET_STRING_LIB},MemberName="{member_name}")')
    setf(n, "self", "PinType.PinSubCategoryObject", KISMET_STRING_LIB, output=False)
    p = pin(n, "uid")
    p._set("PinName", f'"{in_pin_name}"')
    p._set("PinType.PinCategory", f'"{in_category}"')
    p._set("PinType.PinSubCategoryObject", "None")
    pin(n, "ReturnValue", output=True)._set("PinType.PinCategory", '"string"')
    connect(source_node, source_pin, n, in_pin_name)
    return n


applyRule = by_name("K2Node_CallFunction_118")   # ApplyKeepRule (unruled/opt-out-tidy branch)
iteRuled = by_name("K2Node_IfThenElse_2")        # ruled/unruled gate
stationLoop = by_name("K2Node_MacroInstance_0")  # ForEachLoop(ManagedStations)
itemTemplateGet = by_name("K2Node_VariableGet_4")  # current item's TemplateID

# --- chain 1: unruled branch (ApplyKeepRule.then, dangling) -> full result dump ------------------
dispName = add(GETDISPLAYNAME_T)
connect(stationLoop, "Array Element", dispName, "Object")

templateIdStr = conv("Conv_IntToString", "InInt", "int", itemTemplateGet, "TemplateID")
movedStr = conv("Conv_IntToString", "InInt", "int", applyRule, "Moved")
outcomeStr = conv("Conv_ByteToString", "InByte", "byte", applyRule, "Outcome")

pairs = [
    ("MENU_TIDY_DIAG: Station", dispName, "ReturnValue"),
    ("MENU_TIDY_DIAG: TemplateID", templateIdStr, "ReturnValue"),
    ("MENU_TIDY_DIAG: Moved", movedStr, "ReturnValue"),
    ("MENU_TIDY_DIAG: Outcome", outcomeStr, "ReturnValue"),
]

chain = []
for label, src, srcpin in pairs:
    chain.append(make_print(label))
    chain.append(make_print_wired(src, srcpin))

connect_exec(applyRule, chain[0], "then", "execute")
for a, b in zip(chain, chain[1:]):
    connect_exec(a, b, "then", "execute")

# --- chain 2: ruled/protected branch (ite_ruled.then, dead end) -> TemplateID + label -------------
ruledTemplateIdStr = conv("Conv_IntToString", "InInt", "int", itemTemplateGet, "TemplateID")
ruled_chain = [
    make_print("MENU_TIDY_ITEM: RULED, skipped, TemplateID"),
    make_print_wired(ruledTemplateIdStr, "ReturnValue"),
]
connect_exec(iteRuled, ruled_chain[0], "then", "execute")
connect_exec(ruled_chain[0], ruled_chain[1], "then", "execute")

# --- layout: nudge new nodes below the existing graph -----------------------------------------
base_y = 1800
for i, n in enumerate([dispName, templateIdStr, movedStr, outcomeStr]):
    n.set_position(400 + i * 300, base_y)
for i, n in enumerate(chain):
    n.set_position(400 + i * 180, base_y + 250)
ruledTemplateIdStr.set_position(2200, base_y)
for i, n in enumerate(ruled_chain):
    n.set_position(2200 + i * 180, base_y + 250)

# --- validate --------------------------------------------------------------------------------
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

out = MOD + r"\.ccmod\graphs\menu_tidymanagedstations_diag.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"nodes: {len(g.nodes)}   wrote: {out}")
print(f"problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
print("wildcards:", wilds)
