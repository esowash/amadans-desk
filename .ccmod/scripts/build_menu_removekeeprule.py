r"""Author RemoveKeepRule(Station: Actor, TemplateID: int) -> void on Menu_ModController.

Body-only fragment (K2Node_FunctionEntry can't be pasted, same limitation as every other
function built this project) -- 3 dangling input knots (exec, Station, TemplateID) at the start,
needs 3 hand-wires from the real, already-created FunctionEntry after paste:
  Entry.then -> knot_exec.InputPin
  Entry.Station -> knot_station.InputPin
  Entry.TemplateID -> knot_templateid.InputPin

Structure: same resolve-and-compare idiom as TidyManagedStations (session 15,
build_menu_tidy_stations.py) -- GetGameMode -> Cast(BaseGameModeInterface) ->
GetActorByUniqueID(Rule.Container) -> ResolvedActor, playtest-proven correct, reused verbatim
rather than the (partially unclear) resolve chain found in the AddKeepRule upsert capture.

  ForEachLoop(KeepRulesV2) as Rule, Index:
    LoopBody:
      Break Rule -> Container/TemplateID_e/Keep/KeepAll
      GetGameMode -> Cast(BaseGameModeInterface) -> GetActorByUniqueID(Container) -> ResolvedActor
      IfThenElse(NotEqual(ResolvedActor, Station)):
        different station (then): no-op
        same station (else):
          IfThenElse(EqualEqual(TemplateID_e, TemplateID)):
            no match (else): no-op
            match (then): Set FoundIndex = Index
    Completed:
      IfThenElse(Greater(FoundIndex, -1)):
        found (then): Array_RemoveIndex(KeepRulesV2, FoundIndex) -> print "rule removed"
        not found (else): print "no matching rule found"

Reuses the existing "FoundIndex" member (int, already present on Menu_ModController --
confirmed via the AddKeepRule upsert capture, MemberName="FoundIndex") as scratch state, same as
that function's own search loop -- no new variable needed.

Array_RemoveIndex has no captured precedent anywhere in this project: cloned from the real
Array_Add template (library/array/array_add.t3d, wildcard-array shape, same
KismetArrayLibrary self-context-object pattern already proven for Array_Add/Array_Clear/
Array_Contains), retargeted MemberName + dropped NewItem/ReturnValue (RemoveIndex takes Index:int
instead, returns void). GENUINELY UNVERIFIED shape, flagged for proofread same as any other
first-time node in this project -- watch for it specifically when the pasted result is pulled.

EqualEqual_IntInt cloned from a REAL captured node (the AddKeepRule upsert graph's own
K2Node_CallFunction_260, menu_addkeeprule_upsert_full.t3d) rather than hand-typed from scratch.
"""
import copy
import sys

CCMOD = r"<CCMOD_HOME>"
sys.path.insert(0, CCMOD)
from ccmod.t3d import parse, connect, connect_exec, auto_layout
from ccmod.t3d.generator import instantiate
from ccmod.t3d.model import Graph

MOD = r"<MOD_ROOT>"
LIB = CCMOD + r"\library"
WLIB = MOD + r"\.ccmod\library"
UPSERT_SRC = MOD + r"\.ccmod\graphs\menu_addkeeprule_upsert_full.t3d"

KEEPRULE_STRUCT = '''"/Script/CoreUObject.UserDefinedStruct'/Game/Mods/Menu/S_KeepRule.S_KeepRule'"'''
MENU_MC_BGC = '''"/Script/Engine.BlueprintGeneratedClass'/Game/Mods/Menu/Menu_ModController.Menu_ModController_C'"'''
ACTOR_CLASS = '''"/Script/CoreUObject.Class'/Script/Engine.Actor'"'''


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


IFTHENELSE_RAW = '''Begin Object Class=/Script/BlueprintGraph.K2Node_IfThenElse Name="K2Node_IfThenElse_0"
   NodeGuid=00000000000000000000000000000000
   CustomProperties Pin (PinId=00000000000000000000000000000001,PinName="execute",PinType.PinCategory="exec",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000002,PinName="Condition",PinType.PinCategory="bool",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,DefaultValue="true",AutogeneratedDefaultValue="true",PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000003,PinName="then",PinFriendlyName=NSLOCTEXT("K2Node", "true", "true"),Direction="EGPD_Output",PinType.PinCategory="exec",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000004,PinName="else",PinFriendlyName=NSLOCTEXT("K2Node", "false", "false"),Direction="EGPD_Output",PinType.PinCategory="exec",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
End Object'''
IFTHENELSE_T = parse(IFTHENELSE_RAW)

# self-context VariableSet/Get for a plain int member -- shape confirmed correct earlier this
# session (SelectedTemplateID build): MemberName only, bSelfContext=True, no SelfContextInfo
# line, hidden unlinked self pin.
RAW_SELFSET_INT = '''Begin Object Class=/Script/BlueprintGraph.K2Node_VariableSet Name="K2Node_VariableSet_foundidx"
   VariableReference=(MemberName="FoundIndex",bSelfContext=True)
   NodeGuid=00000000000000000000000000000000
   CustomProperties Pin (PinId=00000000000000000000000000000001,PinName="execute",PinType.PinCategory="exec",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000002,PinName="then",Direction="EGPD_Output",PinType.PinCategory="exec",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000003,PinName="FoundIndex",PinType.PinCategory="int",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,DefaultValue="0",PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000004,PinName="Output_Get",Direction="EGPD_Output",PinType.PinCategory="int",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000005,PinName="self",PinFriendlyName=NSLOCTEXT("K2Node", "Target", "Target"),PinType.PinCategory="object",PinType.PinSubCategory="",PinType.PinSubCategoryObject=%s,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=True,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
End Object''' % MENU_MC_BGC

RAW_SELFGET_INT = '''Begin Object Class=/Script/BlueprintGraph.K2Node_VariableGet Name="K2Node_VariableGet_foundidx"
   VariableReference=(MemberName="FoundIndex",bSelfContext=True)
   NodeGuid=00000000000000000000000000000000
   CustomProperties Pin (PinId=00000000000000000000000000000001,PinName="FoundIndex",Direction="EGPD_Output",PinType.PinCategory="int",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000002,PinName="self",PinFriendlyName=NSLOCTEXT("K2Node", "Target", "Target"),PinType.PinCategory="object",PinType.PinSubCategory="",PinType.PinSubCategoryObject=%s,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=True,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
End Object''' % MENU_MC_BGC

upsert_src = parse(open(UPSERT_SRC, encoding="utf-8-sig").read())

KNOT_T = tmpl_file(LIB + r"\flow\knot.t3d")
FEACH_T = tmpl_file(LIB + r"\flow\foreach.t3d")
GREATER_T = tmpl_file(LIB + r"\math\greater_int.t3d")
NOTEQUAL_T = tmpl_file(LIB + r"\math\not_equal_object.t3d")
GETGAMEMODE_T = tmpl_file(LIB + r"\actor\get_game_mode.t3d")
CAST_T = tmpl_file(LIB + r"\actor\cast_to_basegamemode_interface.t3d")
GETACTOR_T = tmpl_file(LIB + r"\actor\get_actor_by_unique_id.t3d")
ADD_T = tmpl_file(LIB + r"\array\array_add.t3d")
GET_KEEPRULESV2_T = tmpl_file(WLIB + r"\stocker\get_keeprules_v2.t3d")

BREAKSTRUCT_T = find_by_raw(upsert_src, "S_KeepRule.S_KeepRule", want_class="K2Node_BreakStruct")
EQUALEQUAL_T = find_by_raw(upsert_src, 'MemberName="EqualEqual_IntInt"', want_class="K2Node_CallFunction")
PRINT_T = find_by_raw(upsert_src, 'MemberName="PrintString"', want_class="K2Node_CallFunction")


def make_print(text):
    n = add(PRINT_T)
    setf(n, "InString", "DefaultValue", f'"{text}"')
    return n


def type_knot(n, category, subcat_obj="None", container="None"):
    for pn in ("InputPin", "OutputPin"):
        setf(n, pn, "PinType.PinCategory", f'"{category}"')
        setf(n, pn, "PinType.PinSubCategoryObject", subcat_obj)
        setf(n, pn, "PinType.ContainerType", container)


g = Graph()


def add(t):
    return instantiate(t, g)[0]


# ---- entry hand-wires (3: exec, Station, TemplateID) -------------------------------------------
knot_exec = add(KNOT_T)
type_knot(knot_exec, "exec")
knot_station = add(KNOT_T)
type_knot(knot_station, "object", ACTOR_CLASS)
knot_templateid = add(KNOT_T)
type_knot(knot_templateid, "int")

# ---- Array_RemoveIndex: cloned from the real Array_Add template, retargeted --------------------
removeindex_call = add(ADD_T)
removeindex_call._replace_prop(
    "FunctionReference",
    '(MemberParent="/Script/CoreUObject.Class\'/Script/Engine.KismetArrayLibrary\'",MemberName="Array_RemoveIndex")',
)
setf(removeindex_call, "TargetArray", "PinType.PinCategory", '"struct"')
setf(removeindex_call, "TargetArray", "PinType.PinSubCategoryObject", KEEPRULE_STRUCT)
setf(removeindex_call, "TargetArray", "PinType.ContainerType", "Array")
newitem_pin = pin(removeindex_call, "NewItem")
newitem_pin._set("PinName", '"IndexToRemove"')
newitem_pin._set("PinType.PinCategory", '"int"')
newitem_pin._set("PinType.PinSubCategoryObject", "None")
newitem_pin._set("PinType.bIsReference", "False")
newitem_pin._set("PinType.bIsConst", "False")
returnvalue_pin = pin(removeindex_call, "ReturnValue", output=True)
removeindex_call.body = [(k, it) for (k, it) in removeindex_call.body if not (k == "pin" and it is returnvalue_pin)]

# ---- init FoundIndex = -1 -----------------------------------------------------------------------
init_found = add(parse(RAW_SELFSET_INT))
setf(init_found, "FoundIndex", "DefaultValue", '"-1"')

# ---- outer loop: KeepRulesV2 as Rule --------------------------------------------------------------
keeprules_get = add(GET_KEEPRULESV2_T)
setf(keeprules_get, "self", "PinType.PinSubCategoryObject", MENU_MC_BGC, output=False)
feach_rules = add(FEACH_T)
setf(feach_rules, "Array", "PinType.PinCategory", '"struct"')
setf(feach_rules, "Array", "PinType.PinSubCategoryObject", KEEPRULE_STRUCT)
setf(feach_rules, "Array", "PinType.ContainerType", "Array")
setf(feach_rules, "Array Element", "PinType.PinCategory", '"struct"', output=True)
setf(feach_rules, "Array Element", "PinType.PinSubCategoryObject", KEEPRULE_STRUCT, output=True)

break_rule = add(BREAKSTRUCT_T)
break_rule._replace_prop("StructType", KEEPRULE_STRUCT)
setf(break_rule, "S_KeepRule", "PinType.PinSubCategoryObject", KEEPRULE_STRUCT)

gamemode_get = add(GETGAMEMODE_T)
cast_gm = add(CAST_T)
getactor = add(GETACTOR_T)
notequal_station = add(NOTEQUAL_T)
ite_station = add(IFTHENELSE_T)
equal_template = add(EQUALEQUAL_T)
ite_template = add(IFTHENELSE_T)
set_found = add(parse(RAW_SELFSET_INT))

# ---- after loop: remove if found -------------------------------------------------------------
get_found = add(parse(RAW_SELFGET_INT))
greater_found = add(GREATER_T)
ite_found = add(IFTHENELSE_T)
print_removed = make_print("MENU_RULESLIST: rule removed")
print_notfound = make_print("MENU_RULESLIST: no matching rule found")

# =====================  WIRING  ==================================================================

connect_exec(knot_exec, init_found, "OutputPin", "execute")
connect_exec(init_found, feach_rules, "then", "Exec")
connect(keeprules_get, "KeepRulesV2", feach_rules, "Array")

connect(feach_rules, "Array Element", break_rule, "S_KeepRule")
connect_exec(feach_rules, cast_gm, "LoopBody", "execute")
connect(gamemode_get, "ReturnValue", cast_gm, "Object")
connect_exec(cast_gm, getactor, "then", "execute")
connect(cast_gm, "AsBase Game Mode Interface", getactor, "self")
connect(break_rule, "Container_4_62E0F0614C1CC5F95CAE6B97F57E9504", getactor, "UniqueID")
connect_exec(getactor, ite_station, "then", "execute")
connect(getactor, "Actor", notequal_station, "A")
connect(knot_station, "InputPin", notequal_station, "B")
connect(notequal_station, "ReturnValue", ite_station, "Condition")

connect_exec(ite_station, ite_template, "else", "execute")
connect(break_rule, "TemplateID_6_7331DAFA4369B9E2C105A59FAAA510CD", equal_template, "A")
connect(knot_templateid, "InputPin", equal_template, "B")
connect(equal_template, "ReturnValue", ite_template, "Condition")
connect_exec(ite_template, set_found, "then", "execute")
connect(feach_rules, "Array Index", set_found, "FoundIndex")

connect_exec(feach_rules, ite_found, "Completed", "execute")
connect(get_found, "FoundIndex", greater_found, "A")
setf(greater_found, "B", "DefaultValue", '"-1"')
connect(greater_found, "ReturnValue", ite_found, "Condition")
connect_exec(ite_found, removeindex_call, "then", "execute")
connect(keeprules_get, "KeepRulesV2", removeindex_call, "TargetArray")
connect(get_found, "FoundIndex", removeindex_call, "IndexToRemove")
connect_exec(removeindex_call, print_removed, "then", "execute")
connect_exec(ite_found, print_notfound, "else", "execute")

auto_layout(g.nodes, origin=(0, 0), dx=260, dy=200, per_column=7)

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

out = MOD + r"\.ccmod\graphs\menu_removekeeprule_body.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"nodes: {len(g.nodes)}   wrote: {out}")
print(f"problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
print()
print("hand-wires needed after paste (from the REAL FunctionEntry):")
print(f"  Entry.then       -> {knot_exec.name}.InputPin")
print(f"  Entry.Station    -> {knot_station.name}.InputPin")
print(f"  Entry.TemplateID -> {knot_templateid.name}.InputPin")
