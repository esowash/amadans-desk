r"""Full item-search filter: OnTextChanged -> loop ItemNames, Contains-match against the typed
substring, collect matching TemplateIDs into ItemResultIDs. Ends with a diagnostic print of the
match count (same "add a checkpoint before trusting a cold function" discipline as every other
new piece tonight) -- doesn't populate the 8 visible rows yet, that's the next, separate step
(isolates the SetVisibility guess from this one).

Self-contained full replacement for the OnTextChanged probe (delete the probe, paste this) --
same event-binding shape already proven live by that probe (compiled clean), just built fresh
rather than edited in place since the probe wasn't worth a live pull for 3 trivial nodes.

GENUINELY UNVERIFIED, flagged: KismetStringLibrary::Contains's exact parameter names
("SearchIn"/"Substring"/"bCaseSensitive"/"bSearchFromEnd") -- no captured precedent anywhere in
this project or its harvested API index (13 real callers exist in the base game, none captured).
Built from general UE knowledge of the standard signature. Only SearchIn/Substring are wired;
the two bool params are left unwired to pick up their real defaults (bCaseSensitive=false,
bSearchFromEnd=false), same pattern already proven safe with PrintString's optional params.
"""
import sys

import os, pathlib
CCMOD = os.environ.get("CCMOD_HOME") or str(pathlib.Path(__file__).resolve().parents[3] / "claude-conan-modder")
sys.path.insert(0, CCMOD)
from ccmod.t3d import parse, connect, connect_exec
from ccmod.t3d.generator import instantiate
from ccmod.t3d.model import Graph
from ccmod.t3d.guid import new_guid

import pathlib
MOD = str(pathlib.Path(__file__).resolve().parents[2])
LIB = CCMOD + r"\library"
EVENTGRAPH_SRC = MOD + r"\.ccmod\graphs\menu_w_amadanmenu_eventgraph.t3d"

eventgraph_src = parse(open(EVENTGRAPH_SRC, encoding="utf-8-sig").read())


def tmpl_from(graph, name):
    import copy
    n = copy.deepcopy(graph.by_name(name))
    for p in n.pins:
        p.links = []
    return Graph(nodes=[n])


def tmpl_file(path):
    t = parse(open(path, encoding="utf-8-sig").read())
    for n in t.nodes:
        for p in n.pins:
            p.links = []
    return t


BOUND_EVENT_T = tmpl_from(eventgraph_src, "K2Node_ComponentBoundEvent_0")
SELFGET_T = tmpl_from(eventgraph_src, "K2Node_VariableGet_0")

CONV_TEXT_TO_STRING_T = tmpl_file(LIB + r"\actor\conv_text_to_string.t3d")
FEACH_T = tmpl_file(LIB + r"\flow\foreach.t3d")
ARRAY_CLEAR_T = tmpl_file(LIB + r"\actor\array_clear_int.t3d")
ARRAY_ADD_T = tmpl_file(LIB + r"\array\array_add.t3d")

RAW_PRINT = '''Begin Object Class=/Script/BlueprintGraph.K2Node_CallFunction Name="K2Node_CallFunction_Print"
   FunctionReference=(MemberParent=Class'"/Script/Engine.KismetSystemLibrary"',MemberName="PrintString")
   NodeGuid=00000000000000000000000000000000
   CustomProperties Pin (PinId=00000000000000000000000000000020,PinName="execute",PinType.PinCategory="exec",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000021,PinName="InString",PinType.PinCategory="string",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,DefaultValue="",PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000022,PinName="then",Direction="EGPD_Output",PinType.PinCategory="exec",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
End Object'''
PRINT_T = parse(RAW_PRINT)

RAW_CONTAINS = '''Begin Object Class=/Script/BlueprintGraph.K2Node_CallFunction Name="K2Node_CallFunction_Contains"
   bDefaultsToPureFunc=True
   FunctionReference=(MemberParent="/Script/CoreUObject.Class'/Script/Engine.KismetStringLibrary'",MemberName="Contains")
   NodeGuid=00000000000000000000000000000000
   CustomProperties Pin (PinId=00000000000000000000000000000080,PinName="self",PinFriendlyName=NSLOCTEXT("K2Node", "Target", "Target"),PinType.PinCategory="object",PinType.PinSubCategory="",PinType.PinSubCategoryObject="/Script/CoreUObject.Class'/Script/Engine.KismetStringLibrary'",PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,DefaultObject="/Script/Engine.Default__KismetStringLibrary",PersistentGuid=00000000000000000000000000000000,bHidden=True,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000081,PinName="SearchIn",PinType.PinCategory="string",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000082,PinName="Substring",PinType.PinCategory="string",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000083,PinName="ReturnValue",Direction="EGPD_Output",PinType.PinCategory="bool",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,DefaultValue="false",PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
End Object'''
CONTAINS_T = parse(RAW_CONTAINS)

IFTHENELSE_RAW = '''Begin Object Class=/Script/BlueprintGraph.K2Node_IfThenElse Name="K2Node_IfThenElse_0"
   NodeGuid=00000000000000000000000000000000
   CustomProperties Pin (PinId=00000000000000000000000000000001,PinName="execute",PinType.PinCategory="exec",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000002,PinName="Condition",PinType.PinCategory="bool",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,DefaultValue="true",AutogeneratedDefaultValue="true",PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000003,PinName="then",PinFriendlyName=NSLOCTEXT("K2Node", "true", "true"),Direction="EGPD_Output",PinType.PinCategory="exec",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000004,PinName="else",PinFriendlyName=NSLOCTEXT("K2Node", "false", "false"),Direction="EGPD_Output",PinType.PinCategory="exec",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
End Object'''
IFTHENELSE_T = parse(IFTHENELSE_RAW)

KISMET_STRING_LIB = "\"/Script/CoreUObject.Class'/Script/Engine.KismetStringLibrary'\""
KISMET_ARRAY_LIB = "\"/Script/CoreUObject.Class'/Script/Engine.KismetArrayLibrary'\""

g = Graph(nodes=[])


def add(t):
    return instantiate(t, g)[0]


def pin(n, name, output=None):
    p = n.pin_by_name(name, output=output)
    assert p, f"{n.name} has no pin {name}"
    return p


def setf(n, pn, k, raw, output=None):
    pin(n, pn, output=output)._set(k, raw)


def selfget_array(member_name, category):
    n = add(SELFGET_T)
    n._replace_prop("VariableReference", f'(MemberName="{member_name}",bSelfContext=True)')
    p = pin(n, "MultiLineEditableTextBox_74", output=True)
    p._set("PinName", f'"{member_name}"')
    p._set("PinType.PinCategory", f'"{category}"')
    p._set("PinType.PinSubCategoryObject", "None")
    p._set("PinType.ContainerType", "Array")
    return n


# --- bound event ---------------------------------------------------------------------------------
boundEvent = add(BOUND_EVENT_T)
boundEvent._replace_prop("DelegatePropertyName", '"OnTextChanged"')
boundEvent._replace_prop("DelegateOwnerClass", "\"/Script/CoreUObject.Class'/Script/UMG.EditableTextBox'\"")
boundEvent._replace_prop("ComponentPropertyName", '"ItemSearchInput"')
boundEvent._replace_prop(
    "EventReference",
    '(MemberParent="/Script/CoreUObject.Package\'/Script/UMG\'",MemberName="OnEditableTextBoxTextChangedEvent__DelegateSignature")',
)
boundEvent._replace_prop(
    "CustomFunctionName",
    '"BndEvt__W_AmadanMenu_ItemSearchInput_K2Node_ComponentBoundEvent_6_OnEditableTextBoxTextChangedEvent__DelegateSignature"',
)
RAW_TEXT_PIN = '''Begin Object Class=/Script/BlueprintGraph.K2Node_CallFunction Name="K2Node_Scratch3"
   CustomProperties Pin (PinId=00000000000000000000000000000070,PinName="Text",Direction="EGPD_Output",PinType.PinCategory="text",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
End Object'''
scratch = parse(RAW_TEXT_PIN).nodes[0]
textPin = scratch.pins[0]
textPin.pin_id = new_guid()
boundEvent.body.append(("pin", textPin))

t2s = add(CONV_TEXT_TO_STRING_T)
connect(boundEvent, "Text", t2s, "InText")

# --- caches ----------------------------------------------------------------------------------
namesGet = selfget_array("ItemNames", "string")
idsGet = selfget_array("ItemTemplateIDs", "int")
resultsGet1 = selfget_array("ItemResultIDs", "int")   # for Array_Clear
resultsGet2 = selfget_array("ItemResultIDs", "int")   # for Array_Add inside the loop

clearResults = add(ARRAY_CLEAR_T)
connect(resultsGet1, "ItemResultIDs", clearResults, "TargetArray")

# --- loop + filter -----------------------------------------------------------------------------
feach = add(FEACH_T)
setf(feach, "Array", "PinType.PinCategory", '"string"')
setf(feach, "Array", "PinType.ContainerType", "Array")
setf(feach, "Array Element", "PinType.PinCategory", '"string"', output=True)
setf(feach, "Array Element", "PinType.ContainerType", "None", output=True)
connect(namesGet, "ItemNames", feach, "Array")

contains = add(CONTAINS_T)
connect(feach, "Array Element", contains, "SearchIn")
connect(t2s, "ReturnValue", contains, "Substring")

ite = add(IFTHENELSE_T)
connect(contains, "ReturnValue", ite, "Condition")

# GetArrayItem(ItemTemplateIDs, Array Index) -- real shape cloned from Construct's own precedent
CONSTRUCT_SRC = MOD + r"\.ccmod\graphs\amadanmenu_construct_v2_full.t3d"
construct_src = parse(open(CONSTRUCT_SRC, encoding="utf-8-sig").read())
ITEM_T = tmpl_from(construct_src, "K2Node_GetArrayItem_0")

idItem = add(ITEM_T)
setf(idItem, "Array", "PinType.PinCategory", '"int"')
setf(idItem, "Array", "PinType.PinSubCategoryObject", "None")
setf(idItem, "Array", "PinType.ContainerType", "Array")
p = pin(idItem, "Output", output=True)
p._set("PinType.PinCategory", '"int"')
p._set("PinType.PinSubCategoryObject", "None")
connect(idsGet, "ItemTemplateIDs", idItem, "Array")
connect(feach, "Array Index", idItem, "Dimension 1")

arrAddResult = add(ARRAY_ADD_T)
setf(arrAddResult, "TargetArray", "PinType.PinCategory", '"int"')
setf(arrAddResult, "TargetArray", "PinType.PinSubCategoryObject", "None")
setf(arrAddResult, "TargetArray", "PinType.ContainerType", "Array")
setf(arrAddResult, "NewItem", "PinType.PinCategory", '"int"')
setf(arrAddResult, "NewItem", "PinType.PinSubCategoryObject", "None")
connect(resultsGet2, "ItemResultIDs", arrAddResult, "TargetArray")
connect(idItem, "Output", arrAddResult, "NewItem")

# --- match-count diagnostic --------------------------------------------------------------------
# Array_Length: real shape confirmed from an earlier live pull this session (RestockManagedStations'
# own "rules to process" diagnostic) -- pure, no exec pins at all, self hidden + TargetArray + ReturnValue.
RAW_ARRAY_LENGTH = '''Begin Object Class=/Script/BlueprintGraph.K2Node_CallArrayFunction Name="K2Node_CallArrayFunction_Len"
   bDefaultsToPureFunc=True
   FunctionReference=(MemberParent="/Script/CoreUObject.Class'/Script/Engine.KismetArrayLibrary'",MemberName="Array_Length")
   NodeGuid=00000000000000000000000000000000
   CustomProperties Pin (PinId=00000000000000000000000000000091,PinName="self",PinFriendlyName=NSLOCTEXT("K2Node", "Target", "Target"),PinType.PinCategory="object",PinType.PinSubCategory="",PinType.PinSubCategoryObject="/Script/CoreUObject.Class'/Script/Engine.KismetArrayLibrary'",PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,DefaultObject="/Script/Engine.Default__KismetArrayLibrary",PersistentGuid=00000000000000000000000000000000,bHidden=True,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000092,PinName="TargetArray",PinType.PinCategory="int",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=Array,PinType.bIsReference=True,PinType.bIsConst=True,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=True,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000093,PinName="ReturnValue",Direction="EGPD_Output",PinType.PinCategory="int",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,DefaultValue="0",PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
End Object'''
countLen = add(parse(RAW_ARRAY_LENGTH))
connect(resultsGet1, "ItemResultIDs", countLen, "TargetArray")

countToStr = add(tmpl_file(CCMOD + "/library/actor/conv_uniqueid_to_string.t3d"))
countToStr._replace_prop("FunctionReference", f'(MemberParent={KISMET_STRING_LIB},MemberName="Conv_IntToString")')
setf(countToStr, "self", "PinType.PinSubCategoryObject", KISMET_STRING_LIB, output=False)
p = pin(countToStr, "uid"); p._set("PinName", '"InInt"'); p._set("PinType.PinCategory", '"int"'); p._set("PinType.PinSubCategoryObject", "None")
pin(countToStr, "ReturnValue", output=True)._set("PinType.PinCategory", '"string"')
connect(countLen, "ReturnValue", countToStr, "InInt")

lbl = add(PRINT_T)
pin(lbl, "InString")._set("DefaultValue", '"ITEMSEARCH: matches found"')
val = add(PRINT_T)
connect(countToStr, "ReturnValue", val, "InString")

# --- exec spine -----------------------------------------------------------------------------
connect_exec(boundEvent, clearResults, "then", "execute")
connect_exec(clearResults, feach, "then", "Exec")
connect_exec(feach, ite, "LoopBody", "execute")
connect_exec(ite, arrAddResult, "then", "execute")
connect_exec(feach, lbl, "Completed", "execute")
connect_exec(lbl, val, "then", "execute")

# --- layout ----------------------------------------------------------------------------------
boundEvent.set_position(-100, 0)
t2s.set_position(250, 0)
namesGet.set_position(-100, 300)
idsGet.set_position(-100, 450)
resultsGet1.set_position(-100, 600)
resultsGet2.set_position(1200, 600)
clearResults.set_position(250, 600)
feach.set_position(600, 300)
contains.set_position(950, 100)
ite.set_position(1200, 300)
idItem.set_position(1200, 450)
arrAddResult.set_position(1500, 300)
countLen.set_position(600, 900)
countToStr.set_position(900, 900)
lbl.set_position(600, 1100)
val.set_position(900, 1100)

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

out = MOD + r"\.ccmod\graphs\amadanmenu_itemsearch_filter.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"nodes: {len(g.nodes)}   wrote: {out}")
print(f"problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
