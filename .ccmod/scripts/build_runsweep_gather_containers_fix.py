r"""Fix the real bug behind Round 1-4's uniform Moved=0/Outcome=0: GatherNearbyStorageContainers
has ZERO callers anywhere in the live graph. Built in session 15, proven via the debug harness,
then orphaned when the harness was stripped in session 16 -- GatherNearbyBenches got a permanent
home in Construct, its ManagedContainers counterpart never did. ManagedContainers has stayed
empty this whole time, so every ApplyKeepRule candidate search has had nothing to search.

Full pull+edit+repaste of the REAL live RunSweep (pulled fresh this session as runsweep_live.t3d,
confirmed 3 nodes: FunctionEntry -> TidyManagedStations -> RestockManagedStations, nothing else)
-- not a self-contained fragment, since this needs to rewire FunctionEntry's existing `then` link.

Adds, at the very top of RunSweep, before Tidy/Restock run (both read ManagedContainers as their
Candidates source):
  FunctionEntry.then -> GetAllActorsOfClass(BP_PL_Table_Strategy_Amadan, the Menu Desk) -> [0]
    -> GatherNearbyStorageContainers(AnchorActor=Desk, Range=3000.0) -> then -> TidyManagedStations
       (rewires FunctionEntry.then, which used to go straight to TidyManagedStations)

Node shapes, both cloned from real precedent rather than typed from scratch:
  - The self-context call shape (execute/then/self) is cloned VERBATIM from TidyManagedStations'
    own real call site in this exact function (K2Node_CallFunction_2) -- same
    same-class-self-call risk flagged in [[stocker-menu-pivot]] (doesn't survive a from-scratch
    clipboard paste), same fix (clone a real live example). MemberGuid intentionally omitted --
    same technique already proven for RunSweep's own construction in session 16 and for this
    session's AddKeepRule external call (both self-healed a real GUID on first compile).
  - The AnchorActor/Range data pins are cloned VERBATIM from the real, live, working
    GatherNearbyBenches call in W_AmadanMenu's Construct (amadanmenu_construct_v2_full.t3d),
    same Range=3000.0 default already proven in that context.
  - The Desk lookup (GetAllActorsOfClass + GetArrayItem[0]) is the same real pattern already used
    twice this session (Construct's own Desk lookup for GatherNearbyBenches' AnchorActor).
"""
import copy
import sys

import os, pathlib
CCMOD = os.environ.get("CCMOD_HOME") or str(pathlib.Path(__file__).resolve().parents[3] / "claude-conan-modder")
sys.path.insert(0, CCMOD)
from ccmod import db
from ccmod.t3d import parse, connect, connect_exec
from ccmod.t3d.generator import instantiate
from ccmod.t3d.guid import new_guid
from ccmod.t3d.model import Graph
from ccmod.workspace import Workspace

import pathlib
MOD = str(pathlib.Path(__file__).resolve().parents[2])
CONSTRUCT_SRC = MOD + r"\.ccmod\graphs\amadanmenu_construct_v2_full.t3d"

ws = Workspace.resolve()
conn = db.connect(ws.cache_db)
row = db.get_graph(conn, "runsweep_live")
assert row, "run `ccmod pull --save runsweep_live` first"
g = parse(row["t3d"])

construct_src = parse(open(CONSTRUCT_SRC, encoding="utf-8-sig").read())


def by_name(name):
    n = g.by_name(name)
    assert n, f"missing node {name}"
    return n


def tmpl_from(graph, name):
    n = copy.deepcopy(graph.by_name(name))
    for p in n.pins:
        p.links = []
    return Graph(nodes=[n])


def pin(n, name, output=None):
    p = n.pin_by_name(name, output=output)
    assert p, f"{n.name} has no pin {name}"
    return p


def setf(n, pn, k, raw, output=None):
    pin(n, pn, output=output)._set(k, raw)


def add(t):
    return instantiate(t, g)[0]


DESK_CLASS = '''"/Script/Engine.BlueprintGeneratedClass'/Game/Mods/Menu/BP_PL_Table_Strategy_Amadan.BP_PL_Table_Strategy_Amadan_C'"'''

# Real desk-lookup pair, cloned from Construct's own GatherNearbyBenches AnchorActor resolution.
GAC_DESK_T = tmpl_from(construct_src, "K2Node_CallFunction_8")   # GetAllActorsOfClass(Desk)
ITEM_DESK_T = tmpl_from(construct_src, "K2Node_GetArrayItem_1")  # [0]

# Self-context call shape, cloned verbatim from TidyManagedStations' real call site in THIS
# function (execute/then/self, self visible-but-unwired, matches proven working precedent).
GATHER_CONTAINERS_T = tmpl_from(g, "K2Node_CallFunction_2")

entry = by_name("K2Node_FunctionEntry_0")
tidy = by_name("K2Node_CallFunction_2")

gacDesk = add(GAC_DESK_T)  # already targets BP_PL_Table_Strategy_Amadan_C, no retyping needed
itemDesk = add(ITEM_DESK_T)
setf(itemDesk, "Array", "PinType.PinSubCategoryObject", DESK_CLASS)
setf(itemDesk, "Output", "PinType.PinSubCategoryObject", DESK_CLASS, output=True)
connect(gacDesk, "OutActors", itemDesk, "Array")

gatherContainers = add(GATHER_CONTAINERS_T)
gatherContainers._replace_prop(
    "FunctionReference",
    '(MemberName="GatherNearbyStorageContainers",bSelfContext=True)',
)

# add the two data pins GatherNearbyStorageContainers actually takes -- TidyManagedStations (the
# node we cloned the shape from) has none, so these are new REAL Pin objects (not raw text --
# Node.pins only recognizes ("pin", Pin) body items, a raw string wouldn't be found by
# pin_by_name/connect()), built by parsing a tiny synthetic node carrying the real AnchorActor/
# Range pin text captured off the live GatherNearbyBenches call, then transplanting the two
# parsed Pin objects onto gatherContainers.
RAW_EXTRA_PINS = '''Begin Object Class=/Script/BlueprintGraph.K2Node_CallFunction Name="K2Node_Scratch"
   CustomProperties Pin (PinId=00000000000000000000000000000030,PinName="AnchorActor",PinType.PinCategory="object",PinType.PinSubCategory="",PinType.PinSubCategoryObject="/Script/CoreUObject.Class'/Script/Engine.Actor'",PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000031,PinName="Range",PinType.PinCategory="real",PinType.PinSubCategory="double",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,DefaultValue="3000.0",AutogeneratedDefaultValue="0.0",PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
End Object'''
scratch = parse(RAW_EXTRA_PINS).nodes[0]
for extra_pin in scratch.pins:
    extra_pin.pin_id = new_guid()
    gatherContainers.body.append(("pin", extra_pin))

connect(itemDesk, "Output", gatherContainers, "AnchorActor")

# --- rewire the exec spine -----------------------------------------------------------------------
entry_then = pin(entry, "then", output=True)
entry_then.links = []
tidy_execute = pin(tidy, "execute", output=False)
tidy_execute.links = []

connect_exec(entry, gacDesk, "then", "execute")
connect_exec(gacDesk, gatherContainers, "then", "execute")
connect_exec(gatherContainers, tidy, "then", "execute")

# --- layout ----------------------------------------------------------------------------------
gacDesk.set_position(0, 200)
itemDesk.set_position(300, 260)
gatherContainers.set_position(600, 200)
tidy.set_position(1000, -16)

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
assert not wilds, f"unresolved wildcards: {wilds}"

dangling = [(n.name, p.name) for n in g.nodes for p in n.pins if not p.links]
print("intentionally dangling (hidden default pins, self-context self pins):")
for nn, pn in dangling:
    print(f"  {nn}.{pn}")

out = MOD + r"\.ccmod\graphs\runsweep_gather_containers_fix.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"\nnodes: {len(g.nodes)}   wrote: {out}")
print(f"problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
