r"""Splice diagnostic prints into the REAL, LIVE RestockManagedStations graph (pulled fresh this
session as restockmanagedstations_live.t3d -- full pull+edit+repaste, not a self-contained
fragment, since this needs to tap ApplyKeepRule's own actual output pins (Moved, Outcome) on the
one real call site that already exists -- can't re-derive those by re-calling the function again,
that would double-move items).

Real structure confirmed by the pull: ForEachLoop(KeepRulesV2) -> DynamicCast(GetGameMode as
BaseGameModeInterface) -> Get Actor By UniqueID Interface (resolves Rule.Container -> Station
actor) -> ApplyKeepRule(Station, TemplateID, Keep, Candidates=ManagedContainers, KeepAll) ->
[then: DANGLING -- nothing downstream, nothing ever reads Moved or Outcome]. That's the real gap:
the function's own return values (an int count actually moved, and an E_Stocker_Outcome enum)
have never been surfaced anywhere, in this build or historically.

Adds 6 label+value print pairs, chained off ApplyKeepRule (K2Node_CallFunction_120)'s currently-
dangling `then` pin, echoing exactly what was fed in AND what came back:
  MENU_RESTOCK_DIAG: Station     -> GetDisplayName(the resolved actor, same one ApplyKeepRule got)
  MENU_RESTOCK_DIAG: TemplateID  -> Conv_IntToString(BreakStruct's TemplateID output)
  MENU_RESTOCK_DIAG: Keep        -> Conv_IntToString(BreakStruct's Keep output)
  MENU_RESTOCK_DIAG: KeepAll     -> Conv_BoolToString(BreakStruct's KeepAll output)
  MENU_RESTOCK_DIAG: Moved       -> Conv_IntToString(ApplyKeepRule's own Moved output)
  MENU_RESTOCK_DIAG: Outcome     -> Conv_ByteToString(ApplyKeepRule's own Outcome output, raw
                                     enum ordinal -- E_Stocker_Outcome's member names aren't
                                     captured anywhere in this project as symbolic strings, only
                                     the raw byte is available cheaply; cross-reference by hand
                                     against the enum asset if the value needs a name)

This is the single most valuable diagnostic of this whole debugging pass: Moved/Outcome are
ApplyKeepRule's own report of what it did, straight from the source, not inferred from a save-DB
diff. If Moved=0 and Outcome is consistently the SAME non-success value, that's a direct pointer
at which failure mode (e.g. matches the known NoDestination gap in [[stocker-orphan-plan]]) rather
than another round of blind guessing.
"""
import copy
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
row = db.get_graph(conn, "restockmanagedstations_live")
assert row, "run `ccmod pull --save restockmanagedstations_live` first"
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


applyRule = by_name("K2Node_CallFunction_120")   # ApplyKeepRule
getActor = by_name("K2Node_CallFunction_524")    # Get Actor By UniqueID Interface
breakRule = by_name("K2Node_BreakStruct_0")      # S_KeepRule fields

TEMPLATEID_PIN = "TemplateID_6_7331DAFA4369B9E2C105A59FAAA510CD"
KEEP_PIN = "Keep_8_5132904E4CC17522C07075A43E93B26E"
KEEPALL_PIN = "KeepAll_10_A6025F204FE4948B8C46EE8626A13B30"

dispName = add(GETDISPLAYNAME_T)
connect(getActor, "Actor", dispName, "Object")

templateIdStr = conv("Conv_IntToString", "InInt", "int", breakRule, TEMPLATEID_PIN)
keepStr = conv("Conv_IntToString", "InInt", "int", breakRule, KEEP_PIN)
keepAllStr = conv("Conv_BoolToString", "InBool", "bool", breakRule, KEEPALL_PIN)
movedStr = conv("Conv_IntToString", "InInt", "int", applyRule, "Moved")
outcomeStr = conv("Conv_ByteToString", "InByte", "byte", applyRule, "Outcome")

pairs = [
    ("MENU_RESTOCK_DIAG: Station", dispName, "ReturnValue"),
    ("MENU_RESTOCK_DIAG: TemplateID", templateIdStr, "ReturnValue"),
    ("MENU_RESTOCK_DIAG: Keep", keepStr, "ReturnValue"),
    ("MENU_RESTOCK_DIAG: KeepAll", keepAllStr, "ReturnValue"),
    ("MENU_RESTOCK_DIAG: Moved", movedStr, "ReturnValue"),
    ("MENU_RESTOCK_DIAG: Outcome", outcomeStr, "ReturnValue"),
]

chain = []
for label, src, srcpin in pairs:
    chain.append(make_print(label))
    chain.append(make_print_wired(src, srcpin))

connect_exec(applyRule, chain[0], "then", "execute")
for a, b in zip(chain, chain[1:]):
    connect_exec(a, b, "then", "execute")

# --- layout: nudge the new nodes below the existing graph, avoid overlap -----------------------
base_y = 1400
for i, n in enumerate([dispName, templateIdStr, keepStr, keepAllStr, movedStr, outcomeStr]):
    n.set_position(400 + i * 300, base_y)
for i, n in enumerate(chain):
    n.set_position(400 + i * 180, base_y + 250)

# --- validate ------------------------------------------------------------------------------------
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

out = MOD + r"\.ccmod\graphs\restockmanagedstations_diag.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"nodes: {len(g.nodes)}   wrote: {out}")
print(f"problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
