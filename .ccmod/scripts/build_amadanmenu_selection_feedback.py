r"""Selection visual feedback: echo the chosen item's name into the search box and collapse the
results list on click; reopen the results list when the player resumes typing.

Addresses the session-18 gap: the 8 click handlers work (SelectedTemplateID is set correctly,
confirmed by playtest), but nothing visible happens on click, which read as "not clickable" even
though it was. Fix is purely additive to two existing live chains, both edited via full
pull+edit+repaste of the combined region (amadanmenu_itemsearch_full_with_clicks, 136 nodes,
pulled this session):

Per-row click handler (K2Node_VariableSet_0..7 = "Set SelectedTemplateID"), appended after .then:
  GetNameFromTemplateID(same ItemResultIDs[i] value, fanned out from the existing GetArrayItem)
  -> ItemSearchInput.SetText -> ItemResultsBox.SetVisibility(Collapsed)

OnTextChanged chain (K2Node_ComponentBoundEvent_8), spliced between .then and the existing first
step (K2Node_CallArrayFunction_13, Array_Clear on ItemResultIDs):
  ItemResultsBox.SetVisibility(Visible) -- so results reappear when the player types again after
  a previous selection collapsed the list.

SetVisibility built directly with the CONFIRMED-correct shape this time (InVisibility pin, not
Visibility) -- no guessing, this was nailed down for good earlier this session (see
fix_amadanmenu_setvis_invisibility.py / [[stocker-menu-pivot]]). ItemResultsBox's real class
(UMG.VerticalBox) confirmed from amadanmenu_itemsearch_widget.t3d (the original widget-tree build).
SetText's real shape reused from construct_src's TextBlock::SetText call (K2Node_CallFunction_7),
retargeted to EditableTextBox -- same clone-and-retarget technique as everywhere else in this
project when no dedicated capture exists for the new target class.
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
from ccmod.t3d.guid import new_guid
from ccmod.workspace import Workspace

import pathlib
MOD = str(pathlib.Path(__file__).resolve().parents[2])
CONSTRUCT_SRC = MOD + r"\.ccmod\graphs\amadanmenu_construct_v2_full.t3d"

W_AMADANMENU_BGC = '''"/Script/UMG.WidgetBlueprintGeneratedClass'/Game/Mods/Menu/W_AmadanMenu.W_AmadanMenu_C'"'''
UMG_EDITABLETEXTBOX = '''"/Script/CoreUObject.Class'/Script/UMG.EditableTextBox'"'''
UMG_VERTICALBOX = '''"/Script/CoreUObject.Class'/Script/UMG.VerticalBox'"'''

ws = Workspace.resolve()
conn = db.connect(ws.cache_db)
row = db.get_graph(conn, "amadanmenu_itemsearch_full_with_clicks")
assert row, "run `ccmod pull --save amadanmenu_itemsearch_full_with_clicks` first"
g = parse(row["t3d"])

construct_src = parse(open(CONSTRUCT_SRC, encoding="utf-8-sig").read())


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


def tmpl_from(graph, name):
    n = copy.deepcopy(graph.by_name(name))
    for p in n.pins:
        p.links = []
    return Graph(nodes=[n])


SELFGET_T = tmpl_from(g, "K2Node_VariableGet_0")             # real, live self-get shape (ItemResultIDs)
SETTEXT_T = tmpl_from(construct_src, "K2Node_CallFunction_7")  # impure 1-text-param call skeleton (was TextBlock::SetText)

RAW_GNFT = '''Begin Object Class=/Script/BlueprintGraph.K2Node_CallFunction Name="K2Node_CallFunction_GNFT_fb"
   FunctionReference=(MemberParent="/Script/Engine.BlueprintGeneratedClass'/Game/Characters/SurvivalFunctionLibrary.SurvivalFunctionLibrary_C'",MemberName="GetNameFromTemplateID",MemberGuid=1F295A374DD6B5BFD32801949A612B13)
   NodeGuid=00000000000000000000000000000000
   CustomProperties Pin (PinId=00000000000000000000000000000100,PinName="execute",PinType.PinCategory="exec",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000101,PinName="then",Direction="EGPD_Output",PinType.PinCategory="exec",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000102,PinName="self",PinFriendlyName=NSLOCTEXT("K2Node", "Target", "Target"),PinType.PinCategory="object",PinType.PinSubCategory="",PinType.PinSubCategoryObject="/Script/Engine.BlueprintGeneratedClass'/Game/Characters/SurvivalFunctionLibrary.SurvivalFunctionLibrary_C'",PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,DefaultObject="/Game/Characters/SurvivalFunctionLibrary.Default__SurvivalFunctionLibrary_C",PersistentGuid=00000000000000000000000000000000,bHidden=True,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000103,PinName="templateID",PinType.PinCategory="int",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,DefaultValue="0",AutogeneratedDefaultValue="0",PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000104,PinName="__WorldContext",PinType.PinCategory="object",PinType.PinSubCategory="",PinType.PinSubCategoryObject="/Script/CoreUObject.Class'/Script/CoreUObject.Object'",PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000105,PinName="Name",Direction="EGPD_Output",PinType.PinCategory="text",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
End Object'''


def raw_setvis(tag, target_class, default_value):
    return f'''Begin Object Class=/Script/BlueprintGraph.K2Node_CallFunction Name="K2Node_CallFunction_SetVis_{tag}"
   FunctionReference=(MemberName="SetVisibility",bSelfContext=True)
   NodeGuid=00000000000000000000000000000000
   CustomProperties Pin (PinId={new_guid()},PinName="execute",PinType.PinCategory="exec",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId={new_guid()},PinName="then",Direction="EGPD_Output",PinType.PinCategory="exec",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId={new_guid()},PinName="self",PinFriendlyName=NSLOCTEXT("K2Node", "Target", "Target"),PinType.PinCategory="object",PinType.PinSubCategory="",PinType.PinSubCategoryObject={target_class},PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId={new_guid()},PinName="InVisibility",PinType.PinCategory="byte",PinType.PinSubCategory="",PinType.PinSubCategoryObject="/Script/CoreUObject.Enum'/Script/UMG.ESlateVisibility'",PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,DefaultValue="{default_value}",PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
End Object'''


def selfget(member_name, pin_category, pin_subcat_object, container="None"):
    n = add(SELFGET_T)
    n._replace_prop("VariableReference", f'(MemberName="{member_name}",bSelfContext=True)')
    p = pin(n, "ItemResultIDs", output=True)
    p._set("PinName", f'"{member_name}"')
    p._set("PinType.PinCategory", f'"{pin_category}"')
    p._set("PinType.PinSubCategoryObject", pin_subcat_object)
    p._set("PinType.ContainerType", container)
    return n, p.name.strip('"')


# --- Part A: per-row click-handler extension ----------------------------------------------------
for i in range(8):
    varSet = by_name(f"K2Node_VariableSet_{i}")
    idPin = pin(varSet, "SelectedTemplateID", output=False)
    (srcNode, srcPinId) = idPin.links[0]
    idItem = by_name(srcNode)

    gnft = add(parse(RAW_GNFT))
    connect(idItem, "Output", gnft, "templateID")

    setText = add(SETTEXT_T)
    setText._replace_prop("FunctionReference", '(MemberParent="/Script/CoreUObject.Class\'/Script/UMG.EditableTextBox\'",MemberName="SetText")')
    setf(setText, "self", "PinType.PinSubCategoryObject", UMG_EDITABLETEXTBOX, output=False)
    connect(gnft, "Name", setText, "InText")

    searchGet, searchPinName = selfget("ItemSearchInput", "object", UMG_EDITABLETEXTBOX)
    connect(searchGet, searchPinName, setText, "self")

    setVisCollapse = add(parse(raw_setvis(f"row{i}_collapse", UMG_VERTICALBOX, "Collapsed")))
    boxGet, boxPinName = selfget("ItemResultsBox", "object", UMG_VERTICALBOX)
    connect(boxGet, boxPinName, setVisCollapse, "self")

    connect_exec(varSet, gnft, "then", "execute")
    connect_exec(gnft, setText, "then", "execute")
    connect_exec(setText, setVisCollapse, "then", "execute")

    gnft.set_position(9200, 16400 + i * 260)
    setText.set_position(9500, 16400 + i * 260)
    searchGet.set_position(9500, 16300 + i * 260)
    setVisCollapse.set_position(9800, 16400 + i * 260)
    boxGet.set_position(9800, 16300 + i * 260)

# --- Part B: reopen results box on OnTextChanged --------------------------------------------------
boundEvent = by_name("K2Node_ComponentBoundEvent_8")
firstStep = by_name("K2Node_CallArrayFunction_13")

thenPin = pin(boundEvent, "then", output=True)
execPin = pin(firstStep, "execute", output=False)
oldLink = (firstStep.name, execPin.pin_id)
assert oldLink in thenPin.links, "unexpected: boundEvent.then does not link to firstStep.execute"

setVisOpen = add(parse(raw_setvis("ontextchanged_open", UMG_VERTICALBOX, "Visible")))
boxGet2, boxPinName2 = selfget("ItemResultsBox", "object", UMG_VERTICALBOX)
connect(boxGet2, boxPinName2, setVisOpen, "self")

thenPin.links = [l for l in thenPin.links if l != oldLink]
execPin.links = [l for l in execPin.links if l[0] != boundEvent.name]
connect_exec(boundEvent, setVisOpen, "then", "execute")
connect_exec(setVisOpen, firstStep, "then", "execute")

setVisOpen.set_position(7550, 15296)
boxGet2.set_position(7550, 15200)

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

out = MOD + r"\.ccmod\graphs\amadanmenu_selection_feedback_full.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"total nodes: {len(g.nodes)}   wrote: {out}")
print(f"problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
