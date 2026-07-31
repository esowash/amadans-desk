r"""W_RuleRowEntry DeleteButton::OnClicked -> Menu_ModController.RemoveKeepRule(RuleIndex) ->
OwningMenu.RefreshRulesList().

Self-contained fragment, zero hand-wires -- same technique as build_amadanmenu_saverule_onclicked.py
and build_amadanmenu_itemresult_onclicked.py: the bound event itself is generated too.

Chain:
  DeleteButton.OnClicked (K2Node_ComponentBoundEvent)
    -> GetAllActorsOfClass(Menu_ModController) -> [0] -> RemoveKeepRule(Index=self.RuleIndex)
    -> self.OwningMenu -> RefreshRulesList()

Real precedent reused:
  - K2Node_ComponentBoundEvent: same clone-a-real-example technique as every other bound event
    this project (cloned from Button_634's live "Close" OnClicked).
  - GetAllActorsOfClass / GetArrayItem: same real templates as build_amadanmenu_saverule_onclicked.py.
  - Self-gets (RuleIndex: int, OwningMenu: object->W_AmadanMenu): same self-get shape used
    throughout this session, self-context on W_RuleRowEntry this time.
  - RemoveKeepRule call: hand-typed raw node, self+execute+then shape copied from a real
    external-call precedent (AddKeepRule's own zero-caller build), Index:int pin built from
    RemoveKeepRule's REAL, CONFIRMED FunctionEntry pin (pulled from menu_removekeeprule_final_v2:
    PinCategory="int", no subcategory). MemberGuid intentionally omitted -- zero real callers
    exist yet for RemoveKeepRule either, same as AddKeepRule's first caller build.
  - RefreshRulesList call: hand-typed raw node, same self+execute+then shape, no params/return
    (void). Also zero real callers yet -- MemberGuid omitted, name+class resolution technique
    already proven repeatedly in this project.
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
CONSTRUCT_SRC = MOD + r"\.ccmod\graphs\amadanmenu_construct_v2_full.t3d"
EVENTGRAPH_SRC = MOD + r"\.ccmod\graphs\menu_w_amadanmenu_eventgraph.t3d"

MENU_MC_BGC = '''"/Script/Engine.BlueprintGeneratedClass'/Game/Mods/Menu/Menu_ModController.Menu_ModController_C'"'''
W_RULEROWENTRY_BGC = '''"/Script/UMG.WidgetBlueprintGeneratedClass'/Game/Mods/Menu/W_RuleRowEntry.W_RuleRowEntry_C'"'''
W_AMADANMENU_BGC = '''"/Script/UMG.WidgetBlueprintGeneratedClass'/Game/Mods/Menu/W_AmadanMenu.W_AmadanMenu_C'"'''


def tmpl_from(graph, name):
    n = copy.deepcopy(graph.by_name(name))
    for p in n.pins:
        p.links = []
    return Graph(nodes=[n])


construct_src = parse(open(CONSTRUCT_SRC, encoding="utf-8-sig").read())
eventgraph_src = parse(open(EVENTGRAPH_SRC, encoding="utf-8-sig").read())

BOUND_EVENT_T = tmpl_from(eventgraph_src, "K2Node_ComponentBoundEvent_0")  # Button_634 OnClicked, real+live
GAC_T = tmpl_from(construct_src, "K2Node_CallFunction_6")                 # GetAllActorsOfClass(Menu_ModController)
ITEM_T = tmpl_from(construct_src, "K2Node_GetArrayItem_0")                # generic GetArrayItem shape
SELFGET_T = tmpl_from(eventgraph_src, "K2Node_VariableGet_0")             # self-get shape

RAW_REMOVEKEEPRULE_CALL = '''Begin Object Class=/Script/BlueprintGraph.K2Node_CallFunction Name="K2Node_CallFunction_RemoveKeepRule"
   FunctionReference=(MemberParent="/Script/Engine.BlueprintGeneratedClass'/Game/Mods/Menu/Menu_ModController.Menu_ModController_C'",MemberName="RemoveKeepRule")
   NodeGuid=00000000000000000000000000000000
   CustomProperties Pin (PinId=00000000000000000000000000000001,PinName="execute",PinType.PinCategory="exec",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000002,PinName="then",Direction="EGPD_Output",PinType.PinCategory="exec",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000003,PinName="self",PinFriendlyName=NSLOCTEXT("K2Node", "Target", "Target"),PinType.PinCategory="object",PinType.PinSubCategory="",PinType.PinSubCategoryObject="/Script/Engine.BlueprintGeneratedClass'/Game/Mods/Menu/Menu_ModController.Menu_ModController_C'",PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000004,PinName="Index",PinType.PinCategory="int",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,DefaultValue="0",PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
End Object'''

RAW_REFRESHRULESLIST_CALL = '''Begin Object Class=/Script/BlueprintGraph.K2Node_CallFunction Name="K2Node_CallFunction_RefreshRulesList"
   FunctionReference=(MemberParent="/Script/UMG.WidgetBlueprintGeneratedClass'/Game/Mods/Menu/W_AmadanMenu.W_AmadanMenu_C'",MemberName="RefreshRulesList")
   NodeGuid=00000000000000000000000000000000
   CustomProperties Pin (PinId=00000000000000000000000000000001,PinName="execute",PinType.PinCategory="exec",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000002,PinName="then",Direction="EGPD_Output",PinType.PinCategory="exec",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000003,PinName="self",PinFriendlyName=NSLOCTEXT("K2Node", "Target", "Target"),PinType.PinCategory="object",PinType.PinSubCategory="",PinType.PinSubCategoryObject="/Script/UMG.WidgetBlueprintGeneratedClass'/Game/Mods/Menu/W_AmadanMenu.W_AmadanMenu_C'",PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
End Object'''

g = Graph(nodes=[])


def add(t):
    return instantiate(t, g)[0]


def pin(n, name, output=None):
    p = n.pin_by_name(name, output=output)
    assert p, f"{n.name} has no pin {name}"
    return p


def setf(n, pn, k, raw, output=None):
    pin(n, pn, output=output)._set(k, raw)


def selfget(member_name, pin_category, pin_subcat_object, container_type="None"):
    n = add(SELFGET_T)
    n._replace_prop("VariableReference", f'(MemberName="{member_name}",bSelfContext=True)')
    outpin = pin(n, "MultiLineEditableTextBox_74", output=True)
    outpin._set("PinName", f'"{member_name}"')
    outpin._set("PinType.PinCategory", f'"{pin_category}"')
    outpin._set("PinType.PinSubCategoryObject", pin_subcat_object)
    outpin._set("PinType.ContainerType", container_type)
    # self pin of this widget's own self-get must point at W_RuleRowEntry, not the source's class
    setf(n, "self", "PinType.PinSubCategoryObject", W_RULEROWENTRY_BGC, output=False)
    return n


# --- bound event -------------------------------------------------------------------------------
boundEvent = add(BOUND_EVENT_T)
boundEvent._replace_prop("ComponentPropertyName", '"DeleteButton"')
boundEvent._replace_prop(
    "CustomFunctionName",
    '"BndEvt__W_RuleRowEntry_DeleteButton_K2Node_ComponentBoundEvent_0_OnButtonClickedEvent__DelegateSignature"',
)

# --- resolve Menu_ModController instance --------------------------------------------------------
gac = add(GAC_T)
item0 = add(ITEM_T)
setf(item0, "Array", "PinType.PinSubCategoryObject", MENU_MC_BGC)
setf(item0, "Output", "PinType.PinSubCategoryObject", MENU_MC_BGC, output=True)
connect(gac, "OutActors", item0, "Array")
connect_exec(boundEvent, gac, "then", "execute")

# --- RemoveKeepRule(RuleIndex) --------------------------------------------------------------------
ruleIndexGet = selfget("RuleIndex", "int", "None")
callRemove = add(parse(RAW_REMOVEKEEPRULE_CALL))
connect(item0, "Output", callRemove, "self")
connect(ruleIndexGet, "RuleIndex", callRemove, "Index")
connect_exec(gac, callRemove, "then", "execute")

# --- OwningMenu.RefreshRulesList() ----------------------------------------------------------------
owningMenuGet = selfget("OwningMenu", "object", W_AMADANMENU_BGC)
callRefresh = add(parse(RAW_REFRESHRULESLIST_CALL))
connect(owningMenuGet, "OwningMenu", callRefresh, "self")
connect_exec(callRemove, callRefresh, "then", "execute")

# --- layout -----------------------------------------------------------------------------------
boundEvent.set_position(-100, 0)
gac.set_position(250, 0)
item0.set_position(600, 0)
ruleIndexGet.set_position(600, 200)
callRemove.set_position(900, 100)
owningMenuGet.set_position(1200, 200)
callRefresh.set_position(1500, 100)

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

out = MOD + r"\.ccmod\graphs\ruleRowEntry_deletebutton_body.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"nodes: {len(g.nodes)}   wrote: {out}")
print(f"problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
