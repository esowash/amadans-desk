r"""Swap GetDisplayName -> GetBuildableName for the BenchDropdown populate loop.

Full pull+edit+repaste of the REAL live Construct graph (pulled fresh this session as
amadanmenu_full_for_benchnames.t3d, 24 nodes) -- needs to remove one real node
(K2Node_CallFunction_44, GetDisplayName) and rewire around it, so a self-contained fragment
with hand-wires isn't safe here (same reasoning as the RunSweep/AddKeepRule full-graph edits).

Real bug this fixes: BenchDropdown currently shows GetDisplayName's output, which in a COOKED
build returns the raw internal object name ("BP_PL_CraftingStation_Metal_C_2147466530") --
confirmed ugly in every playtest log this session. GetBuildableName (library brick, pure, self=
BuildableBase, real Conan function) returns the actual friendly buildable name instead.

GetBuildableName's self pin needs a BuildableBase reference, but ManagedStations is typed
Array<Actor> (deliberately generic, per design) -- so this needs a DynamicCast(Actor ->
BuildableBase) in front of it, same idiom AddKeepRule's own body already uses for its own
Cast-to-BP_Master_Placeables. DynamicCast is impure (execute/then/CastFailed), unlike the pure
GetDisplayName it replaces -- changes the LoopBody exec target from directly hitting AddOption to
going through the cast first.

GENUINELY UNVERIFIED, flagged rather than assumed: DynamicCast's auto-generated output pin name
for a native BuildableBase cast (built here as "AsBuildable Base", following the same "As<Class
Display Name>" pattern confirmed on a real BaseGameModeInterface cast elsewhere in this project's
captures) -- this is cosmetic and unlikely to be compiler-checked the way a real UFUNCTION
parameter name is (which is what broke GetDataTableRowNames/GetArrayItem earlier), but it's a
guess, not a captured example. Proofread after compile, same as everything else tonight.

CastFailed is left dangling (silent skip) -- every managed station should be a real BuildableBase
subtype in practice, and a silent skip from a display list is a low-stakes failure mode if that
assumption is ever wrong.
"""
import copy
import sys

CCMOD = r"<CCMOD_HOME>"
sys.path.insert(0, CCMOD)
from ccmod import db
from ccmod.t3d import parse, connect, connect_exec
from ccmod.t3d.generator import instantiate
from ccmod.t3d.model import Graph
from ccmod.workspace import Workspace

MOD = r"<MOD_ROOT>"
LIB = CCMOD + r"\library"

ws = Workspace.resolve()
conn = db.connect(ws.cache_db)
row = db.get_graph(conn, "amadanmenu_full_for_benchnames")
assert row, "run `ccmod pull --save amadanmenu_full_for_benchnames` first"
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


BUILDABLEBASE_CLASS = "\"/Script/CoreUObject.Class'/Script/ConanSandbox.BuildableBase'\""

GETBUILDABLENAME_T = tmpl_file(LIB + r"\actor\get_buildable_name.t3d")
CONV_TEXT_TO_STRING_T = tmpl_file(LIB + r"\actor\conv_text_to_string.t3d")

RAW_DYNAMICCAST = f'''Begin Object Class=/Script/BlueprintGraph.K2Node_DynamicCast Name="K2Node_DynamicCast_Bench"
   TargetType={BUILDABLEBASE_CLASS}
   NodeGuid=00000000000000000000000000000000
   CustomProperties Pin (PinId=00000000000000000000000000000060,PinName="execute",PinType.PinCategory="exec",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000061,PinName="then",Direction="EGPD_Output",PinType.PinCategory="exec",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000062,PinName="CastFailed",Direction="EGPD_Output",PinType.PinCategory="exec",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000063,PinName="Object",PinType.PinCategory="object",PinType.PinSubCategory="",PinType.PinSubCategoryObject="/Script/CoreUObject.Class'/Script/CoreUObject.Object'",PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000064,PinName="AsBuildable Base",Direction="EGPD_Output",PinType.PinCategory="object",PinType.PinSubCategory="",PinType.PinSubCategoryObject={BUILDABLEBASE_CLASS},PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000065,PinName="bSuccess",Direction="EGPD_Output",PinType.PinCategory="bool",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=True,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
End Object'''
DYNCAST_T = parse(RAW_DYNAMICCAST)

feach = by_name("K2Node_MacroInstance_2")     # ForEachLoop(ManagedStations)
oldGetDisplayName = by_name("K2Node_CallFunction_44")
addOpt = by_name("K2Node_CallFunction_23")    # AddOption(BenchDropdown)

# --- remove the old GetDisplayName node entirely --------------------------------------------
g.nodes = [n for n in g.nodes if n is not oldGetDisplayName]

# --- new cast + friendly-name chain -----------------------------------------------------------
dynCast = add(DYNCAST_T)
pin(feach, "Array Element", output=True).links = []  # clear the stale link to the deleted node
connect(feach, "Array Element", dynCast, "Object")

getName = add(GETBUILDABLENAME_T)
setf(getName, "self", "PinType.PinSubCategoryObject", BUILDABLEBASE_CLASS, output=False)
connect(dynCast, "AsBuildable Base", getName, "self")
setf(getName, "ignoreCustomName", "DefaultValue", '"false"')

t2s = add(CONV_TEXT_TO_STRING_T)
connect(getName, "ReturnValue", t2s, "InText")

# --- rewire: LoopBody now goes through the cast first, then into AddOption -----------------------
loopBodyPin = pin(feach, "LoopBody", output=True)
loopBodyPin.links = []
addOptExecPin = pin(addOpt, "execute", output=False)
addOptExecPin.links = []
optionPin = pin(addOpt, "Option", output=False)
optionPin.links = []

connect_exec(feach, dynCast, "LoopBody", "execute")
connect_exec(dynCast, addOpt, "then", "execute")
connect(t2s, "ReturnValue", addOpt, "Option")

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

out = MOD + r"\.ccmod\graphs\amadanmenu_benchnames_fix.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"nodes: {len(g.nodes)}   wrote: {out}")
print(f"problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
