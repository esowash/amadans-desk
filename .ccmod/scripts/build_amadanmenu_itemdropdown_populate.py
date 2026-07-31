r"""W_AmadanMenu Construct: populate ItemDropdown from the whole ItemTable.

Self-contained fragment, ONE hand-wire needed: the Menu_ModController GetAllActorsOfClass call's
`then` pin (K2Node_CallFunction_11 in the live Construct graph) went dangling once the legacy
SetText/AmadanText chain was deleted earlier this session -- confirmed dangling in the last full
proofread pull. Wire that dangling `then` -> this fragment's entry knot.

Chain:
  [[hand: CallFunction_11.then]] -> knot -> GetDataTableRowNames(ItemTable)
    -> ForEachLoop(RowNames) as RowName:
         Conv_NameToString(RowName) -> Conv_StringToInt -> TemplateID
         GetNameFromTemplateID(TemplateID) -> Conv_TextToString -> AddOption(ItemDropdown)
         Array_Add(ItemTemplateIDs, TemplateID)   -- parallel array, same index as the dropdown
           option that was just added, so OnClicked can resolve GetSelectedIndex -> TemplateID
           later exactly like BenchDropdown -> ManagedStations already does for Station.

Real precedent reused: GetNameFromTemplateID (library/inventory/get_name_from_template_id.t3d --
impure, has execute/then, self=SurvivalFunctionLibrary, __WorldContext left unwired same as
ApplyKeepRule's own __WorldContext, which is dangling in the live, working, playtest-confirmed
graph). Conv_TextToString / Array_Add are real bricks. Conv_NameToString / Conv_StringToInt clone
the same proven KismetStringLibrary pure-conversion shape used 4 times already this session.
AddOption / ForEachLoop / knot are the same real shapes used for BenchDropdown.

GENUINELY UNVERIFIED, flagged rather than silently assumed: GetDataTableRowNames's exact shape
(pure vs impure, exact self-class) has no capture anywhere in this project -- built here as PURE
(self hidden + Table input + ReturnValue output, no exec), the standard stock-UE convention for
this function, but this is the one node in this fragment most likely to need a fix after a first
compile attempt. Proofread via `ccmod pull` before trusting, same as every other first-time shape.
"""
import copy
import sys

import os, pathlib
CCMOD = os.environ.get("CCMOD_HOME") or str(pathlib.Path(__file__).resolve().parents[3] / "claude-conan-modder")
sys.path.insert(0, CCMOD)
from ccmod.t3d import parse, connect, connect_exec
from ccmod.t3d.generator import instantiate
from ccmod.t3d.model import Graph

import pathlib
MOD = str(pathlib.Path(__file__).resolve().parents[2])
LIB = CCMOD + r"\library"
EVENTGRAPH_SRC = MOD + r"\.ccmod\graphs\menu_w_amadanmenu_eventgraph.t3d"

COMBOBOX_CLASS = "\"/Script/CoreUObject.Class'/Script/UMG.ComboBoxString'\""
KISMET_STRING_LIB = "\"/Script/CoreUObject.Class'/Script/Engine.KismetStringLibrary'\""
DATATABLE_CLASS = "\"/Script/CoreUObject.Class'/Script/Engine.DataTable'\""
ITEMTABLE_ASSET = "\"/Game/Items/ItemTable.ItemTable\""


def tmpl_file(path):
    t = parse(open(path, encoding="utf-8-sig").read())
    for n in t.nodes:
        for p in n.pins:
            p.links = []
    return t


def tmpl_from(graph, name):
    n = copy.deepcopy(graph.by_name(name))
    for p in n.pins:
        p.links = []
    return Graph(nodes=[n])


eventgraph_src = parse(open(EVENTGRAPH_SRC, encoding="utf-8-sig").read())

SELFGET_T = tmpl_from(eventgraph_src, "K2Node_VariableGet_0")   # self-get shape (was MultiLineEditableTextBox_74)
SETTEXT_T = None  # placeholder, replaced below by loading from construct_src for AddOption shape
CONSTRUCT_SRC = MOD + r"\.ccmod\graphs\amadanmenu_construct_v2_full.t3d"
construct_src = parse(open(CONSTRUCT_SRC, encoding="utf-8-sig").read())
SETTEXT_T = tmpl_from(construct_src, "K2Node_CallFunction_7")   # impure 1-param call skeleton (was SetText)

FEACH_T = tmpl_file(LIB + r"\flow\foreach.t3d")
KNOT_T = tmpl_file(LIB + r"\flow\knot.t3d")
CONV_TEXT_TO_STRING_T = tmpl_file(LIB + r"\actor\conv_text_to_string.t3d")
CONV_UID_TO_STRING_T = tmpl_file(LIB + r"\actor\conv_uniqueid_to_string.t3d")
ARRAY_ADD_T = tmpl_file(LIB + r"\array\array_add.t3d")

RAW_GETDATATABLEROWNAMES = '''Begin Object Class=/Script/BlueprintGraph.K2Node_CallFunction Name="K2Node_CallFunction_GDTRN"
   FunctionReference=(MemberParent="/Script/CoreUObject.Class'/Script/Engine.DataTableFunctionLibrary'",MemberName="GetDataTableRowNames")
   NodeGuid=00000000000000000000000000000000
   CustomProperties Pin (PinId=00000000000000000000000000000043,PinName="execute",PinType.PinCategory="exec",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000044,PinName="then",Direction="EGPD_Output",PinType.PinCategory="exec",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000040,PinName="self",PinFriendlyName=NSLOCTEXT("K2Node", "Target", "Target"),PinType.PinCategory="object",PinType.PinSubCategory="",PinType.PinSubCategoryObject="/Script/CoreUObject.Class'/Script/Engine.DataTableFunctionLibrary'",PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,DefaultObject="/Script/Engine.Default__DataTableFunctionLibrary",PersistentGuid=00000000000000000000000000000000,bHidden=True,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000041,PinName="Table",PinType.PinCategory="object",PinType.PinSubCategory="",PinType.PinSubCategoryObject="/Script/CoreUObject.Class'/Script/Engine.DataTable'",PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,DefaultObject="/Game/Items/ItemTable.ItemTable",PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000042,PinName="OutRowNames",Direction="EGPD_Output",PinType.PinCategory="name",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=Array,PinType.bIsReference=True,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
End Object'''
GDTRN_T = parse(RAW_GETDATATABLEROWNAMES)

RAW_GETNAME_FROM_TEMPLATEID = '''Begin Object Class=/Script/BlueprintGraph.K2Node_CallFunction Name="K2Node_CallFunction_GNFT"
   FunctionReference=(MemberParent="/Script/Engine.BlueprintGeneratedClass'/Game/Characters/SurvivalFunctionLibrary.SurvivalFunctionLibrary_C'",MemberName="GetNameFromTemplateID",MemberGuid=1F295A374DD6B5BFD32801949A612B13)
   NodeGuid=00000000000000000000000000000000
   CustomProperties Pin (PinId=00000000000000000000000000000050,PinName="execute",PinType.PinCategory="exec",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000051,PinName="then",Direction="EGPD_Output",PinType.PinCategory="exec",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000052,PinName="self",PinFriendlyName=NSLOCTEXT("K2Node", "Target", "Target"),PinType.PinCategory="object",PinType.PinSubCategory="",PinType.PinSubCategoryObject="/Script/Engine.BlueprintGeneratedClass'/Game/Characters/SurvivalFunctionLibrary.SurvivalFunctionLibrary_C'",PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,DefaultObject="/Game/Characters/SurvivalFunctionLibrary.Default__SurvivalFunctionLibrary_C",PersistentGuid=00000000000000000000000000000000,bHidden=True,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000053,PinName="templateID",PinType.PinCategory="int",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,DefaultValue="0",AutogeneratedDefaultValue="0",PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000054,PinName="__WorldContext",PinType.PinCategory="object",PinType.PinSubCategory="",PinType.PinSubCategoryObject="/Script/CoreUObject.Class'/Script/CoreUObject.Object'",PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000055,PinName="Name",Direction="EGPD_Output",PinType.PinCategory="text",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
End Object'''
GNFT_T = parse(RAW_GETNAME_FROM_TEMPLATEID)

g = Graph(nodes=[])


def add(t):
    return instantiate(t, g)[0]


def pin(n, name, output=None):
    p = n.pin_by_name(name, output=output)
    assert p, f"{n.name} has no pin {name}"
    return p


def setf(n, pn, k, raw, output=None):
    pin(n, pn, output=output)._set(k, raw)


# --- entry knot (hand-wire landing point) ------------------------------------------------------
knotExec = add(KNOT_T)
setf(knotExec, "InputPin", "PinType.PinCategory", '"exec"')
setf(knotExec, "InputPin", "PinType.PinSubCategoryObject", "None")
setf(knotExec, "OutputPin", "PinType.PinCategory", '"exec"')
setf(knotExec, "OutputPin", "PinType.PinSubCategoryObject", "None")

# --- enumerate ItemTable ---------------------------------------------------------------------
gdtrn = add(GDTRN_T)

feach = add(FEACH_T)
setf(feach, "Array", "PinType.PinCategory", '"name"')
setf(feach, "Array", "PinType.ContainerType", "Array")
setf(feach, "Array Element", "PinType.PinCategory", '"name"', output=True)
setf(feach, "Array Element", "PinType.ContainerType", "None", output=True)
connect(gdtrn, "OutRowNames", feach, "Array")

# --- RowName -> TemplateID (int) -----------------------------------------------------------------
n2s = add(CONV_UID_TO_STRING_T)
n2s._replace_prop("FunctionReference", f'(MemberParent={KISMET_STRING_LIB},MemberName="Conv_NameToString")')
setf(n2s, "self", "PinType.PinSubCategoryObject", KISMET_STRING_LIB, output=False)
p = pin(n2s, "uid"); p._set("PinName", '"InName"'); p._set("PinType.PinCategory", '"name"'); p._set("PinType.PinSubCategoryObject", "None")
pin(n2s, "ReturnValue", output=True)._set("PinType.PinCategory", '"string"')
connect(feach, "Array Element", n2s, "InName")

s2i = add(CONV_UID_TO_STRING_T)
s2i._replace_prop("FunctionReference", f'(MemberParent={KISMET_STRING_LIB},MemberName="Conv_StringToInt")')
setf(s2i, "self", "PinType.PinSubCategoryObject", KISMET_STRING_LIB, output=False)
p = pin(s2i, "uid"); p._set("PinName", '"InString"'); p._set("PinType.PinCategory", '"string"'); p._set("PinType.PinSubCategoryObject", "None")
pin(s2i, "ReturnValue", output=True)._set("PinType.PinCategory", '"int"')
connect(n2s, "ReturnValue", s2i, "InString")

# --- TemplateID -> friendly Name (impure, needs exec) ----------------------------------------
gnft = add(GNFT_T)
connect(s2i, "ReturnValue", gnft, "templateID")

t2s = add(CONV_TEXT_TO_STRING_T)
connect(gnft, "Name", t2s, "InText")

# --- AddOption(ItemDropdown, friendly string) ------------------------------------------------
addOpt = add(SETTEXT_T)
addOpt._replace_prop("FunctionReference", '(MemberParent="/Script/CoreUObject.Class\'/Script/UMG.ComboBoxString\'",MemberName="AddOption")')
setf(addOpt, "self", "PinType.PinSubCategoryObject", COMBOBOX_CLASS, output=False)
inpin = pin(addOpt, "InText")
inpin._set("PinName", '"Option"')
inpin._set("PinType.PinCategory", '"string"')
inpin._set("PinType.PinSubCategoryObject", "None")

dropdownGet = add(SELFGET_T)
dropdownGet._replace_prop("VariableReference", '(MemberName="ItemDropdown",bSelfContext=True)')
outpin2 = pin(dropdownGet, "MultiLineEditableTextBox_74", output=True)
outpin2._set("PinName", '"ItemDropdown"')
outpin2._set("PinType.PinSubCategoryObject", COMBOBOX_CLASS)

connect(dropdownGet, "ItemDropdown", addOpt, "self")
connect(t2s, "ReturnValue", addOpt, "Option")

# --- Array_Add(ItemTemplateIDs, TemplateID) --------------------------------------------------
idsGet = add(SELFGET_T)
idsGet._replace_prop("VariableReference", '(MemberName="ItemTemplateIDs",bSelfContext=True)')
outpin3 = pin(idsGet, "MultiLineEditableTextBox_74", output=True)
outpin3._set("PinName", '"ItemTemplateIDs"')
outpin3._set("PinType.PinCategory", '"int"')
outpin3._set("PinType.PinSubCategoryObject", "None")
outpin3._set("PinType.ContainerType", "Array")

arrAdd = add(ARRAY_ADD_T)
setf(arrAdd, "TargetArray", "PinType.PinCategory", '"int"')
setf(arrAdd, "TargetArray", "PinType.PinSubCategoryObject", "None")
setf(arrAdd, "TargetArray", "PinType.ContainerType", "Array")
setf(arrAdd, "NewItem", "PinType.PinCategory", '"int"')
setf(arrAdd, "NewItem", "PinType.PinSubCategoryObject", "None")
connect(idsGet, "ItemTemplateIDs", arrAdd, "TargetArray")
connect(s2i, "ReturnValue", arrAdd, "NewItem")

# --- exec spine ---------------------------------------------------------------------------------
# GetDataTableRowNames is impure (real UE signature -- confirmed the hard way: compiling it as
# pure got it silently pruned, output read as empty/default). Needs a real exec chain.
connect_exec(knotExec, gdtrn, "OutputPin", "execute")
connect_exec(gdtrn, feach, "then", "Exec")
connect_exec(feach, gnft, "LoopBody", "execute")
connect_exec(gnft, addOpt, "then", "execute")
connect_exec(addOpt, arrAdd, "then", "execute")

# --- layout ----------------------------------------------------------------------------------
knotExec.set_position(-100, 1400)
gdtrn.set_position(150, 1400)
feach.set_position(450, 1400)
n2s.set_position(750, 1600)
s2i.set_position(1000, 1600)
gnft.set_position(750, 1400)
t2s.set_position(1050, 1400)
dropdownGet.set_position(1350, 1550)
addOpt.set_position(1650, 1400)
idsGet.set_position(1350, 1750)
arrAdd.set_position(1950, 1400)

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
print("intentionally dangling (hand-wire landing point + hidden default pins):")
for nn, pn in dangling:
    print(f"  {nn}.{pn}")

out = MOD + r"\.ccmod\graphs\amadanmenu_itemdropdown_populate_body.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"\nnodes: {len(g.nodes)}   wrote: {out}")
print(f"problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
