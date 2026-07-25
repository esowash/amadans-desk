"""Rewrite AddKeepRule for upsert semantics, working on the REAL live function graph (pulled
session 16), not a from-scratch template -- preserves every existing real NodeGuid/PinId/
FunctionReference (including MakeStruct_0's real per-field PersistentGuids, which are specific
to the S_KeepRule asset and must not be re-derived).

Before: Cast -> GetActorUniqueID -> MakeStruct -> blind Array_Add -> print.
After:  Cast -> GetActorUniqueID -> [hand: Set FoundIndex=-1] -> MakeStruct (unchanged) ->
        ForEachLoop(KeepRulesV2) as Rule, Index:
          resolve Rule.Container -> ResolvedActor (same GetGameMode/Cast/GetActorByUniqueID idiom
          TidyManagedStations already uses) -> NotEqual(ResolvedActor, Station):
            same station -> EqualEqual_IntInt(Rule.TemplateID, TemplateID):
              match -> [hand: Set Array Element(KeepRulesV2, Index, NewRule)] ->
                       [hand: Set FoundIndex = Index]
        Completed -> Greater_IntInt(0, [hand: Get FoundIndex]) i.e. "FoundIndex still -1":
          not found -> Array_Add (existing node, reused) -> print (existing, reused)
          found     -> print (existing, reused) directly -- exec fan-IN onto the same node is
                       normal Blueprint (unlike fan-out, which needs a Sequence)

Requires a local int variable `FoundIndex` on AddKeepRule (user-created, per session convention
for anything ccmod can't originate) -- its Set/Get node shape has no precedent anywhere in this
project's captures, so those 2 Set nodes + the 1 Get node are left as hand-adds rather than guessed,
same as the Set Array Element node (also no precedent). Four hand-adds total.
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
SRC = MOD + r"\.ccmod\graphs\menu_addkeeprule_live_s16.t3d"
STOCKER_GRAPH = MOD + r"\.ccmod\graphs\stocker_modcontroller_probe_a_live.t3d"
WOODBENCH_GRAPH = MOD + r"\.ccmod\graphs\woodbench_chain_review.t3d"

KEEPRULE_STRUCT = '''"/Script/CoreUObject.UserDefinedStruct'/Game/Mods/Menu/S_KeepRule.S_KeepRule'"'''
MENU_MC_BGC = '''"/Script/Engine.BlueprintGeneratedClass'/Game/Mods/Menu/Menu_ModController.Menu_ModController_C'"'''

# FoundIndex is now a real MEMBER variable (user confirmed) rather than a local -- Get/Set for it
# use the same proven member-variable shape already used throughout this project (KeepRulesV2,
# ManagedStations, etc.), so these no longer need to be hand-added. MemberGuid is omitted (same
# name-only self-context resolution already proven working for RunSweep/GatherNearbyStorageContainers).

g = parse(open(SRC, encoding="utf-8-sig").read())
stocker_src = parse(open(STOCKER_GRAPH, encoding="utf-8-sig").read())
woodbench_src = parse(open(WOODBENCH_GRAPH, encoding="utf-8-sig").read())


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


def tmpl_file(path):
    t = parse(open(path, encoding="utf-8-sig").read())
    for n in t.nodes:
        for p in n.pins:
            p.links = []
    return t


def find_by_raw(src_graph, needle, want_class=None):
    for n in src_graph.nodes:
        if want_class and not n.class_path.endswith(want_class):
            continue
        raw = " ".join(t for k, t in n.body if k == "raw")
        if needle in raw:
            nn = copy.deepcopy(n)
            for p in nn.pins:
                p.links = []
            return Graph(nodes=[nn])
    raise KeyError(needle)


FEACH_T = tmpl_file(LIB + r"\flow\foreach.t3d")
GETGAMEMODE_T = tmpl_file(LIB + r"\actor\get_game_mode.t3d")
CAST_T = tmpl_file(LIB + r"\actor\cast_to_basegamemode_interface.t3d")
GETACTOR_T = tmpl_file(LIB + r"\actor\get_actor_by_unique_id.t3d")
NOTEQUAL_T = tmpl_file(LIB + r"\math\not_equal_object.t3d")
GREATER_T = tmpl_file(LIB + r"\math\greater_int.t3d")
KNOT_T = tmpl_file(LIB + r"\flow\knot.t3d")

BREAKSTRUCT_T = find_by_raw(stocker_src, "S_KeepRule.S_KeepRule", want_class="K2Node_BreakStruct")
VARSET_T = find_by_raw(woodbench_src, 'MemberName="ItemToModify"', want_class="K2Node_VariableSet")

IFTHENELSE_RAW = '''Begin Object Class=/Script/BlueprintGraph.K2Node_IfThenElse Name="K2Node_IfThenElse_0"
   NodeGuid=00000000000000000000000000000000
   CustomProperties Pin (PinId=00000000000000000000000000000001,PinName="execute",PinType.PinCategory="exec",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False,)
   CustomProperties Pin (PinId=00000000000000000000000000000002,PinName="Condition",PinType.PinCategory="bool",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,DefaultValue="true",AutogeneratedDefaultValue="true",PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False,)
   CustomProperties Pin (PinId=00000000000000000000000000000003,PinName="then",PinFriendlyName=NSLOCTEXT("K2Node", "true", "true"),Direction="EGPD_Output",PinType.PinCategory="exec",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False,)
   CustomProperties Pin (PinId=00000000000000000000000000000004,PinName="else",PinFriendlyName=NSLOCTEXT("K2Node", "false", "false"),Direction="EGPD_Output",PinType.PinCategory="exec",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False,)
End Object'''
IFTHENELSE_T = parse(IFTHENELSE_RAW)


def add(t):
    return instantiate(t, g)[0]


def clone_as_template(node):
    nn = copy.deepcopy(node)
    for p in nn.pins:
        p.links = []
    return Graph(nodes=[nn])


entry = by_name("K2Node_FunctionEntry_0")
getuid = by_name("K2Node_CallFunction_7")           # GetActorUniqueID
makestruct = by_name("K2Node_MakeStruct_0")
keeprules_get = by_name("K2Node_VariableGet_50")
array_add = by_name("K2Node_CallArrayFunction_2")
print_added = by_name("K2Node_CallFunction_0")       # "rule added"

GET_FOUNDINDEX_T = clone_as_template(keeprules_get)  # real member-Get shape, retyped below


def make_set_foundindex():
    n = add(VARSET_T)
    n._replace_prop("VariableReference", '(MemberName="FoundIndex",bSelfContext=True)')
    valpin = pin(n, "ItemToModify")
    valpin._set("PinName", '"FoundIndex"')
    valpin._set("PinType.PinCategory", '"int"')
    valpin._set("PinType.PinSubCategoryObject", "None")
    outpin = pin(n, "Output_Get", output=True)
    outpin._set("PinType.PinCategory", '"int"')
    outpin._set("PinType.PinSubCategoryObject", "None")
    setf(n, "self", "PinType.PinSubCategoryObject", MENU_MC_BGC, output=False)
    return n


def make_get_foundindex():
    n = add(GET_FOUNDINDEX_T)
    n._replace_prop("VariableReference", '(MemberName="FoundIndex",bSelfContext=True)')
    outpin = pin(n, "KeepRulesV2", output=True)
    outpin._set("PinName", '"FoundIndex"')
    outpin._set("PinType.PinCategory", '"int"')
    outpin._set("PinType.PinSubCategoryObject", "None")
    outpin._set("PinType.ContainerType", "None")
    return n

feach = add(FEACH_T)
setf(feach, "Array", "PinType.PinCategory", '"struct"')
setf(feach, "Array", "PinType.PinSubCategoryObject", KEEPRULE_STRUCT)
setf(feach, "Array", "PinType.ContainerType", "Array")
setf(feach, "Array Element", "PinType.PinCategory", '"struct"', output=True)
setf(feach, "Array Element", "PinType.PinSubCategoryObject", KEEPRULE_STRUCT, output=True)
setf(feach, "Array Element", "PinType.ContainerType", "None", output=True)

break_rule = add(BREAKSTRUCT_T)
break_rule._replace_prop("StructType", KEEPRULE_STRUCT)
setf(break_rule, "S_KeepRule", "PinType.PinSubCategoryObject", KEEPRULE_STRUCT)

gamemode_get = add(GETGAMEMODE_T)
cast_gm = add(CAST_T)
getactor = add(GETACTOR_T)
notequal = add(NOTEQUAL_T)
ite_station = add(IFTHENELSE_T)
ite_template = add(IFTHENELSE_T)
greater = add(GREATER_T)
ite_found = add(IFTHENELSE_T)

# EqualEqual_IntInt: clone Greater_IntInt's proven shape (same KismetMathLibrary int-comparison
# family, identical pin layout), just swap MemberName.
equalint_node = add(GREATER_T)
equalint_node._replace_prop(
    "FunctionReference",
    '(MemberParent="/Script/CoreUObject.Class\'/Script/Engine.KismetMathLibrary\'",MemberName="EqualEqual_IntInt")',
)

# --- exec spine -------------------------------------------------------------------------------
# GetActorUniqueID.then previously went straight to Array_Add; redirect it through the new
# "Set FoundIndex=-1" node first, then into the loop.
getuid_then = pin(getuid, "then", output=True)
getuid_then.links = []

array_add_exec = pin(array_add, "execute", output=False)
array_add_exec.links = []  # was fed by GetActorUniqueID.then; now fed from ite_found.then below

setidx_init = make_set_foundindex()
setf(setidx_init, "FoundIndex", "DefaultValue", '"-1"')
connect_exec(getuid, setidx_init, "then", "execute")
connect_exec(setidx_init, feach, "then", "Exec")

setidx_found = make_set_foundindex()
connect(feach, "Array Index", setidx_found, "FoundIndex")

getidx = make_get_foundindex()

connect_exec(feach, cast_gm, "LoopBody", "execute")
connect(gamemode_get, "ReturnValue", cast_gm, "Object")
connect(break_rule, "Container_4_62E0F0614C1CC5F95CAE6B97F57E9504", getactor, "UniqueID")
connect_exec(cast_gm, getactor, "then", "execute")
connect(cast_gm, "AsBase Game Mode Interface", getactor, "self")
connect(getactor, "Actor", notequal, "A")
connect(entry, "Station", notequal, "B", )
connect(notequal, "ReturnValue", ite_station, "Condition")
connect_exec(getactor, ite_station, "then", "execute")
connect_exec(ite_station, ite_template, "else", "execute")  # else = same station (NotEqual=false)
connect(break_rule, "TemplateID_6_7331DAFA4369B9E2C105A59FAAA510CD", equalint_node, "A")
connect(entry, "TemplateID", equalint_node, "B")
connect(equalint_node, "ReturnValue", ite_template, "Condition")
connect(feach, "Array Element", break_rule, "S_KeepRule")

connect_exec(feach, ite_found, "Completed", "execute")
setf(greater, "A", "DefaultValue", '"0"')
connect(getidx, "FoundIndex", greater, "B")
connect(greater, "ReturnValue", ite_found, "Condition")
connect_exec(ite_found, array_add, "then", "execute")   # then = 0 > FoundIndex, i.e. not found
connect_exec(ite_found, print_added, "else", "execute")  # else = found, replaced in-loop; fan-IN
connect(keeprules_get, "KeepRulesV2", feach, "Array")

out = MOD + r"\.ccmod\graphs\menu_addkeeprule_upsert_full.t3d"

# --- knots for the one remaining hand-add (Set Array Element), all grouped on the left so the
# user just drags each knot's OutputPin a short distance into the new node, instead of routing
# wires across the whole graph. Per this project's own convention, entry-side hand-wire knots
# always get a knot, even single-destination pins.
def type_knot(n, category, subcat_obj="None", container="None"):
    for pn in ("InputPin", "OutputPin"):
        setf(n, pn, "PinType.PinCategory", f'"{category}"')
        setf(n, pn, "PinType.PinSubCategoryObject", subcat_obj)
        setf(n, pn, "PinType.ContainerType", container)


knot_exec = add(KNOT_T)
type_knot(knot_exec, "exec")
connect_exec(ite_template, knot_exec, "then", "InputPin")

knot_array = add(KNOT_T)
type_knot(knot_array, "struct", KEEPRULE_STRUCT, "Array")
connect(keeprules_get, "KeepRulesV2", knot_array, "InputPin")

knot_index = add(KNOT_T)
type_knot(knot_index, "int")
connect(feach, "Array Index", knot_index, "InputPin")

knot_item = add(KNOT_T)
type_knot(knot_item, "struct", KEEPRULE_STRUCT)
connect(makestruct, "S_KeepRule", knot_item, "InputPin")

for kn, x, y in ((knot_exec, -260, -80), (knot_array, -260, 0), (knot_index, -260, 80), (knot_item, -260, 160)):
    kn.set_position(x, y)

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

open(out, "w", encoding="utf-8").write(g.render())
print(f"AddKeepRule upsert + knots: nodes={len(g.nodes)} problems={len(problems)}")
for pr in problems:
    print("  !", pr)
print()
print("ONLY ONE hand-add left (Set Array Element has no precedent anywhere in this project).")
print("Four knots now sit on the left, ready to drag into the new node's input pins:")
print(f"  {knot_exec.name}  -> [hand-add] Set Array Element . execute")
print(f"  {knot_array.name} -> [hand-add] Set Array Element . TargetArray/Array")
print(f"  {knot_index.name} -> [hand-add] Set Array Element . Index")
print(f"  {knot_item.name}  -> [hand-add] Set Array Element . Item")
print(f"  [hand-add SetArrayElement].then -> {setidx_found.name}.execute  (direct wire, no knot)")
