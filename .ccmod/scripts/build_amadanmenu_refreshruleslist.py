r"""RefreshRulesList() on W_AmadanMenu -- clears RulesListBox, rebuilds it from the live
KeepRulesV2, one dynamically-created W_RuleRowEntry per rule. Body-only fragment (FunctionEntry
can't be pasted) -- this function takes no params, so only ONE hand-wire needed: Entry.then ->
the returned knot.

Structure:
  ClearChildren(RulesListBox)
  -> GetAllActorsOfClass(Menu_ModController) -> [0] -> MC -> Get MC.KeepRulesV2
  -> ForEachLoop(KeepRulesV2) as Rule, Index:
       Break Rule -> Container/TemplateID/Keep/KeepAll
       GetGameMode -> Cast(BaseGameModeInterface):
         CastFailed -> print, skip this rule (dead end, same pattern as TidyManagedStations)
         then -> GetActorByUniqueID(Container) -> ResolvedActor
                 -> Cast(ResolvedActor -> BuildableBase):
                      CastFailed -> print, skip this rule (bench no longer exists)
                      then -> GetBuildableName(ignoreCustomName=false) -> Conv_TextToString -> BenchStr
                              GetNameFromTemplateID(TemplateID) -> Conv_TextToString -> ItemStr
                              Conv_IntToString(Keep) -> KeepStr
                              Concat(BenchStr, " - ") -> Concat(+ItemStr) -> Concat(": ") -> Concat(+KeepStr)
                              -> Conv_StringToText -> FinalText
                              CreateWidget(W_RuleRowEntry, OwningPlayer=GetOwningPlayer) -> NewRow
                              Set NewRow.RuleIndex = Index
                              Set NewRow.OwningMenu = Self
                              Get NewRow.RuleText -> SetText(FinalText)
                              AddChild(RulesListBox, NewRow)

Real precedent reused: GetGameMode/Cast(BaseGameModeInterface)/GetActorByUniqueID (proven in
TidyManagedStations), Cast(->BuildableBase)/GetBuildableName/Conv_TextToString (proven in this
session's bench-names fix, amadanmenu_benchnames_fix.t3d), GetNameFromTemplateID (RAW_GNFT, used
repeatedly this session), GetOwningPlayer (real capture, testpanel_tick_reassert.t3d),
CreateWidget (real capture, modcontroller_simpletest_90s_realfix.t3d), AddChild/ClearChildren
(real, hand-added by the user this session specifically because no precedent existed),
NotSelfContext VariableSet with a wired (not DefaultObject) self pin (real capture,
menu_ac_menu_eventgraph.t3d), K2Node_Self (real capture, menu_runsweep_timer_body.t3d).

GENUINELY UNVERIFIED, flagged: Concat_StrStr and Conv_StringToText have no captured precedent
anywhere in this project. Both are extremely standard, unambiguous KismetString/TextLibrary
functions (unlike SetVisibility/Array_RemoveIndex, which turned out to have non-obvious real
names) -- built by direct analogy to Conv_TextToString's real captured shape (same
KismetTextLibrary self-context pure-function pattern), risk accepted rather than spending
another hand-add round-trip. Proofread via pull before trusting a compile.
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
CONSTRUCT_SRC = MOD + r"\.ccmod\graphs\amadanmenu_construct_v2_full.t3d"
EVENTGRAPH_SRC = MOD + r"\.ccmod\graphs\menu_w_amadanmenu_eventgraph.t3d"
BENCHNAMES_SRC = MOD + r"\.ccmod\graphs\amadanmenu_benchnames_fix.t3d"
TICKREASSERT_SRC = MOD + r"\.ccmod\graphs\testpanel_tick_reassert.t3d"
CREATEWIDGET_SRC = MOD + r"\.ccmod\graphs\modcontroller_simpletest_90s_realfix.t3d"
ACMENU_SRC = MOD + r"\.ccmod\graphs\menu_ac_menu_eventgraph.t3d"
RUNSWEEPTIMER_SRC = MOD + r"\.ccmod\graphs\menu_runsweep_timer_body.t3d"
UPSERT_SRC = MOD + r"\.ccmod\graphs\menu_addkeeprule_upsert_full.t3d"

MENU_MC_BGC = '''"/Script/Engine.BlueprintGeneratedClass'/Game/Mods/Menu/Menu_ModController.Menu_ModController_C'"'''
ACTOR_CLASS = '''"/Script/CoreUObject.Class'/Script/Engine.Actor'"'''
KEEPRULE_STRUCT = '''"/Script/CoreUObject.UserDefinedStruct'/Game/Mods/Menu/S_KeepRule.S_KeepRule'"'''
W_AMADANMENU_BGC = '''"/Script/UMG.WidgetBlueprintGeneratedClass'/Game/Mods/Menu/W_AmadanMenu.W_AmadanMenu_C'"'''
W_RULEROWENTRY_BGC = '''"/Script/UMG.WidgetBlueprintGeneratedClass'/Game/Mods/Menu/W_RuleRowEntry.W_RuleRowEntry_C'"'''
UMG_VERTICALBOX = '''"/Script/CoreUObject.Class'/Script/UMG.VerticalBox'"'''
UMG_TEXTBLOCK = '''"/Script/CoreUObject.Class'/Script/UMG.TextBlock'"'''
KISMET_TEXT_LIB = '''"/Script/CoreUObject.Class'/Script/Engine.KismetTextLibrary'"'''
KISMET_STRING_LIB = '''"/Script/CoreUObject.Class'/Script/Engine.KismetStringLibrary'"'''


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


ws = Workspace.resolve()
conn = db.connect(ws.cache_db)
addchild_row = db.get_graph(conn, "ruleslistbox_addchild_clearchildren_real")
assert addchild_row, "run `ccmod pull --save ruleslistbox_addchild_clearchildren_real` first"
addchild_src = parse(addchild_row["t3d"])

construct_src = parse(open(CONSTRUCT_SRC, encoding="utf-8-sig").read())
eventgraph_src = parse(open(EVENTGRAPH_SRC, encoding="utf-8-sig").read())
benchnames_src = parse(open(BENCHNAMES_SRC, encoding="utf-8-sig").read())
tickreassert_src = parse(open(TICKREASSERT_SRC, encoding="utf-8-sig").read())
createwidget_src = parse(open(CREATEWIDGET_SRC, encoding="utf-8-sig").read())
acmenu_src = parse(open(ACMENU_SRC, encoding="utf-8-sig").read())
runsweeptimer_src = parse(open(RUNSWEEPTIMER_SRC, encoding="utf-8-sig").read())
upsert_src = parse(open(UPSERT_SRC, encoding="utf-8-sig").read())

KNOT_T = tmpl_file(LIB + r"\flow\knot.t3d")
FEACH_T = tmpl_file(LIB + r"\flow\foreach.t3d")
GETGAMEMODE_T = tmpl_file(LIB + r"\actor\get_game_mode.t3d")
CAST_BGM_T = tmpl_file(LIB + r"\actor\cast_to_basegamemode_interface.t3d")
GETACTOR_T = tmpl_file(LIB + r"\actor\get_actor_by_unique_id.t3d")

GAC_T = tmpl_from(construct_src, "K2Node_CallFunction_6")   # GetAllActorsOfClass
ITEM_T = tmpl_from(construct_src, "K2Node_GetArrayItem_0")  # generic GetArrayItem
SELFGET_T = tmpl_from(eventgraph_src, "K2Node_VariableGet_0")  # self-get shape

CAST_BENCH_T = tmpl_from(benchnames_src, "K2Node_DynamicCast_Bench")
GETBUILDABLENAME_T = find_by_raw(benchnames_src, 'MemberName="GetBuildableName"', want_class="K2Node_CallFunction")
CONV_TEXT_TO_STRING_T = find_by_raw(benchnames_src, 'MemberName="Conv_TextToString"', want_class="K2Node_CallFunction")

GETOWNINGPLAYER_T = find_by_raw(tickreassert_src, 'MemberName="GetOwningPlayer"', want_class="K2Node_CallFunction")
CREATEWIDGET_T = tmpl_from(createwidget_src, "K2Node_CreateWidget_0")

NOTSELF_VARSET_T = tmpl_from(acmenu_src, "K2Node_VariableSet_0")  # NotSelfContext, self pin WIRED (not DefaultObject)
SELF_NODE_T = find_by_raw(runsweeptimer_src, "", want_class="K2Node_Self")

ADDCHILD_T = tmpl_from(addchild_src, "K2Node_CallFunction_0")
CLEARCHILDREN_T = tmpl_from(addchild_src, "K2Node_CallFunction_1")

RAW_GNFT = '''Begin Object Class=/Script/BlueprintGraph.K2Node_CallFunction Name="K2Node_CallFunction_GNFT_rr"
   FunctionReference=(MemberParent="/Script/Engine.BlueprintGeneratedClass'/Game/Characters/SurvivalFunctionLibrary.SurvivalFunctionLibrary_C'",MemberName="GetNameFromTemplateID",MemberGuid=1F295A374DD6B5BFD32801949A612B13)
   NodeGuid=00000000000000000000000000000000
   CustomProperties Pin (PinId=00000000000000000000000000000100,PinName="execute",PinType.PinCategory="exec",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000101,PinName="then",Direction="EGPD_Output",PinType.PinCategory="exec",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000102,PinName="self",PinFriendlyName=NSLOCTEXT("K2Node", "Target", "Target"),PinType.PinCategory="object",PinType.PinSubCategory="",PinType.PinSubCategoryObject="/Script/Engine.BlueprintGeneratedClass'/Game/Characters/SurvivalFunctionLibrary.SurvivalFunctionLibrary_C'",PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,DefaultObject="/Game/Characters/SurvivalFunctionLibrary.Default__SurvivalFunctionLibrary_C",PersistentGuid=00000000000000000000000000000000,bHidden=True,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000103,PinName="templateID",PinType.PinCategory="int",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,DefaultValue="0",AutogeneratedDefaultValue="0",PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000104,PinName="__WorldContext",PinType.PinCategory="object",PinType.PinSubCategory="",PinType.PinSubCategoryObject="/Script/CoreUObject.Class'/Script/CoreUObject.Object'",PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000105,PinName="Name",Direction="EGPD_Output",PinType.PinCategory="text",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
End Object'''


def raw_concat(tag):
    return f'''Begin Object Class=/Script/BlueprintGraph.K2Node_CallFunction Name="K2Node_CallFunction_Concat_{tag}"
   bDefaultsToPureFunc=True
   FunctionReference=(MemberParent={KISMET_STRING_LIB},MemberName="Concat_StrStr")
   NodeGuid=00000000000000000000000000000000
   CustomProperties Pin (PinId=00000000000000000000000000000001,PinName="self",PinFriendlyName=NSLOCTEXT("K2Node", "Target", "Target"),PinType.PinCategory="object",PinType.PinSubCategory="",PinType.PinSubCategoryObject={KISMET_STRING_LIB},PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=True,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000002,PinName="A",PinType.PinCategory="string",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000003,PinName="B",PinType.PinCategory="string",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000004,PinName="ReturnValue",Direction="EGPD_Output",PinType.PinCategory="string",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
End Object'''


RAW_CONV_STRING_TO_TEXT = f'''Begin Object Class=/Script/BlueprintGraph.K2Node_CallFunction Name="K2Node_CallFunction_ConvS2T"
   bDefaultsToPureFunc=True
   FunctionReference=(MemberParent={KISMET_TEXT_LIB},MemberName="Conv_StringToText")
   NodeGuid=00000000000000000000000000000000
   CustomProperties Pin (PinId=00000000000000000000000000000001,PinName="self",PinFriendlyName=NSLOCTEXT("K2Node", "Target", "Target"),PinType.PinCategory="object",PinType.PinSubCategory="",PinType.PinSubCategoryObject={KISMET_TEXT_LIB},PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=True,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000002,PinName="InString",PinType.PinCategory="string",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000003,PinName="ReturnValue",Direction="EGPD_Output",PinType.PinCategory="text",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
End Object'''

RAW_CONV_INT_TO_STRING = '''Begin Object Class=/Script/BlueprintGraph.K2Node_CallFunction Name="K2Node_CallFunction_ConvI2S"
   bDefaultsToPureFunc=True
   FunctionReference=(MemberParent="/Script/CoreUObject.Class'/Script/Engine.KismetStringLibrary'",MemberName="Conv_IntToString")
   NodeGuid=00000000000000000000000000000000
   CustomProperties Pin (PinId=00000000000000000000000000000001,PinName="self",PinFriendlyName=NSLOCTEXT("K2Node", "Target", "Target"),PinType.PinCategory="object",PinType.PinSubCategory="",PinType.PinSubCategoryObject="/Script/CoreUObject.Class'/Script/Engine.KismetStringLibrary'",PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=True,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000002,PinName="InInt",PinType.PinCategory="int",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000003,PinName="ReturnValue",Direction="EGPD_Output",PinType.PinCategory="string",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
End Object'''

RAW_BREAKSTRUCT = f'''Begin Object Class=/Script/BlueprintGraph.K2Node_BreakStruct Name="K2Node_BreakStruct_rr"
   bMadeAfterOverridePinRemoval=True
   ShowPinForProperties(0)=(PropertyName="Container_4_62E0F0614C1CC5F95CAE6B97F57E9504",PropertyFriendlyName="Container",bShowPin=True,bCanToggleVisibility=True)
   ShowPinForProperties(1)=(PropertyName="TemplateID_6_7331DAFA4369B9E2C105A59FAAA510CD",PropertyFriendlyName="TemplateID",bShowPin=True,bCanToggleVisibility=True)
   ShowPinForProperties(2)=(PropertyName="Keep_8_5132904E4CC17522C07075A43E93B26E",PropertyFriendlyName="Keep",bShowPin=True,bCanToggleVisibility=True)
   StructType={KEEPRULE_STRUCT}
   NodeGuid=00000000000000000000000000000000
   CustomProperties Pin (PinId=00000000000000000000000000000001,PinName="S_KeepRule",PinType.PinCategory="struct",PinType.PinSubCategory="",PinType.PinSubCategoryObject={KEEPRULE_STRUCT},PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=True,PinType.bIsConst=True,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000002,PinName="Container_4_62E0F0614C1CC5F95CAE6B97F57E9504",PinFriendlyName=INVTEXT("Container"),Direction="EGPD_Output",PinType.PinCategory="object",PinType.PinSubCategory="",PinType.PinSubCategoryObject="/Script/CoreUObject.Class'/Script/UE4Dreamworld.UniqueID'",PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=62E0F0614C1CC5F95CAE6B97F57E9504,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000003,PinName="TemplateID_6_7331DAFA4369B9E2C105A59FAAA510CD",PinFriendlyName=INVTEXT("TemplateID"),Direction="EGPD_Output",PinType.PinCategory="int",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=7331DAFA4369B9E2C105A59FAAA510CD,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000004,PinName="Keep_8_5132904E4CC17522C07075A43E93B26E",PinFriendlyName=INVTEXT("Keep"),Direction="EGPD_Output",PinType.PinCategory="int",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=5132904E4CC17522C07075A43E93B26E,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
End Object'''


g = Graph()


def add(t):
    return instantiate(t, g)[0]


def pin(n, name, output=None):
    p = n.pin_by_name(name, output=output)
    assert p, f"{n.name} has no pin {name}"
    return p


def setf(n, pn, k, raw, output=None):
    pin(n, pn, output=output)._set(k, raw)


PRINT_T = find_by_raw(upsert_src, 'MemberName="PrintString"', want_class="K2Node_CallFunction")


def real_print(text):
    n = add(PRINT_T)
    setf(n, "InString", "DefaultValue", f'"{text}"')
    return n


def selfget_widget(member_name, pin_category, pin_subcat_object, self_class, container_type="None"):
    n = add(SELFGET_T)
    n._replace_prop("VariableReference", f'(MemberName="{member_name}",bSelfContext=True)')
    outpin = pin(n, "MultiLineEditableTextBox_74", output=True)
    outpin._set("PinName", f'"{member_name}"')
    outpin._set("PinType.PinCategory", f'"{pin_category}"')
    outpin._set("PinType.PinSubCategoryObject", pin_subcat_object)
    outpin._set("PinType.ContainerType", container_type)
    setf(n, "self", "PinType.PinSubCategoryObject", self_class, output=False)
    return n


def notself_varset(member_name, value_category, value_subcat_object, target_class):
    """NotSelfContext VariableSet with self pin left to be wired by the caller."""
    n = add(NOTSELF_VARSET_T)
    n._replace_prop("VariableReference", f'(MemberParent={target_class},MemberName="{member_name}")')
    valpin = pin(n, "AmadanText", output=False)
    valpin._set("PinName", f'"{member_name}"')
    valpin._set("PinType.PinCategory", f'"{value_category}"')
    valpin._set("PinType.PinSubCategoryObject", value_subcat_object)
    outgetpin = pin(n, "Output_Get", output=True)
    outgetpin._set("PinType.PinCategory", f'"{value_category}"')
    outgetpin._set("PinType.PinSubCategoryObject", value_subcat_object)
    setf(n, "self", "PinType.PinSubCategoryObject", target_class, output=False)
    return n


# --- entry hand-wire (only one: no params) ------------------------------------------------------
knot_entry = add(KNOT_T)
setf(knot_entry, "InputPin", "PinType.PinCategory", '"exec"')
setf(knot_entry, "OutputPin", "PinType.PinCategory", '"exec"')

# --- clear + resolve KeepRulesV2 ------------------------------------------------------------------
rulesBoxGet1 = selfget_widget("RulesListBox", "object", UMG_VERTICALBOX, W_AMADANMENU_BGC)
clearChildren = add(CLEARCHILDREN_T)
connect(rulesBoxGet1, "RulesListBox", clearChildren, "self")

gac = add(GAC_T)
item0 = add(ITEM_T)
setf(item0, "Array", "PinType.PinSubCategoryObject", MENU_MC_BGC)
setf(item0, "Output", "PinType.PinSubCategoryObject", MENU_MC_BGC, output=True)
connect(gac, "OutActors", item0, "Array")

KEEPRULES_GET_T = tmpl_from(acmenu_src, "K2Node_VariableGet_0")  # NotSelfContext get shape (was PersistenceComponent)
keeprulesGet = add(KEEPRULES_GET_T)
keeprulesGet._replace_prop("VariableReference", f'(MemberParent={MENU_MC_BGC},MemberName="KeepRulesV2")')
kg_out = pin(keeprulesGet, "PersistenceComponent", output=True)
kg_out._set("PinName", '"KeepRulesV2"')
kg_out._set("PinType.PinCategory", '"struct"')
kg_out._set("PinType.PinSubCategoryObject", KEEPRULE_STRUCT)
kg_out._set("PinType.ContainerType", "Array")
setf(keeprulesGet, "self", "PinType.PinSubCategoryObject", MENU_MC_BGC, output=False)
connect(item0, "Output", keeprulesGet, "self")

feach = add(FEACH_T)
setf(feach, "Array", "PinType.PinCategory", '"struct"')
setf(feach, "Array", "PinType.PinSubCategoryObject", KEEPRULE_STRUCT)
setf(feach, "Array", "PinType.ContainerType", "Array")
setf(feach, "Array Element", "PinType.PinCategory", '"struct"', output=True)
setf(feach, "Array Element", "PinType.PinSubCategoryObject", KEEPRULE_STRUCT, output=True)
connect(keeprulesGet, "KeepRulesV2", feach, "Array")

# --- per-rule: break + resolve station actor -------------------------------------------------
breakRule = add(parse(RAW_BREAKSTRUCT))
connect(feach, "Array Element", breakRule, "S_KeepRule")

gamemodeGet = add(GETGAMEMODE_T)
castGM = add(CAST_BGM_T)
print_gmFail = real_print("MENU_RULESLIST: GetGameMode cast failed, skipping row")
connect_exec(castGM, print_gmFail, "CastFailed", "execute")
connect(gamemodeGet, "ReturnValue", castGM, "Object")

getActor = add(GETACTOR_T)
connect_exec(castGM, getActor, "then", "execute")
connect(castGM, "AsBase Game Mode Interface", getActor, "self")
connect(breakRule, "Container_4_62E0F0614C1CC5F95CAE6B97F57E9504", getActor, "UniqueID")

castBench = add(CAST_BENCH_T)
connect_exec(getActor, castBench, "then", "execute")
connect(getActor, "Actor", castBench, "Object")
print_benchFail = real_print("MENU_RULESLIST: bench actor invalid, skipping row")
connect_exec(castBench, print_benchFail, "CastFailed", "execute")

# --- name/keep resolution ------------------------------------------------------------------------
getBuildableName = add(GETBUILDABLENAME_T)
connect(castBench, "AsBuildable Base", getBuildableName, "self")

convBenchS = add(CONV_TEXT_TO_STRING_T)
connect(getBuildableName, "ReturnValue", convBenchS, "InText")

gnft = add(parse(RAW_GNFT))
connect(breakRule, "TemplateID_6_7331DAFA4369B9E2C105A59FAAA510CD", gnft, "templateID")
convItemS = add(CONV_TEXT_TO_STRING_T)
connect(gnft, "Name", convItemS, "InText")
connect_exec(castBench, gnft, "then", "execute")

convKeepS = add(parse(RAW_CONV_INT_TO_STRING))
connect(breakRule, "Keep_8_5132904E4CC17522C07075A43E93B26E", convKeepS, "InInt")

c1 = add(parse(raw_concat("1")))
connect(convBenchS, "ReturnValue", c1, "A")
setf(c1, "B", "DefaultValue", '" - "')
c2 = add(parse(raw_concat("2")))
connect(c1, "ReturnValue", c2, "A")
connect(convItemS, "ReturnValue", c2, "B")
c3 = add(parse(raw_concat("3")))
connect(c2, "ReturnValue", c3, "A")
setf(c3, "B", "DefaultValue", '": "')
c4 = add(parse(raw_concat("4")))
connect(c3, "ReturnValue", c4, "A")
connect(convKeepS, "ReturnValue", c4, "B")

convFinalText = add(parse(RAW_CONV_STRING_TO_TEXT))
connect(c4, "ReturnValue", convFinalText, "InString")

# --- create + populate the row widget -------------------------------------------------------------
getOwningPlayer = add(GETOWNINGPLAYER_T)

createRow = add(CREATEWIDGET_T)
classPin = pin(createRow, "Class")
classPin._set("DefaultObject", '"/Game/Mods/Menu/W_RuleRowEntry.W_RuleRowEntry_C"')
retPin = pin(createRow, "ReturnValue", output=True)
retPin._set("PinType.PinSubCategoryObject", W_RULEROWENTRY_BGC)
connect(getOwningPlayer, "ReturnValue", createRow, "OwningPlayer")
connect_exec(gnft, createRow, "then", "execute")

setIndex = notself_varset("RuleIndex", "int", "None", W_RULEROWENTRY_BGC)
connect(createRow, "ReturnValue", setIndex, "self")
connect(feach, "Array Index", setIndex, "RuleIndex")
connect_exec(createRow, setIndex, "then", "execute")

selfNode = add(SELF_NODE_T)
setOwning = notself_varset("OwningMenu", "object", W_AMADANMENU_BGC, W_RULEROWENTRY_BGC)
connect(createRow, "ReturnValue", setOwning, "self")
connect(selfNode, "self", setOwning, "OwningMenu")
connect_exec(setIndex, setOwning, "then", "execute")

# external get of NewRow.RuleText -- clone the same NotSelfContext get shape, retarget
ruleTextGet = add(tmpl_from(acmenu_src, "K2Node_VariableGet_0"))
ruleTextGet._replace_prop("VariableReference", f'(MemberParent={W_RULEROWENTRY_BGC},MemberName="RuleText")')
rtg_out = pin(ruleTextGet, "PersistenceComponent", output=True)
rtg_out._set("PinName", '"RuleText"')
rtg_out._set("PinType.PinCategory", '"object"')
rtg_out._set("PinType.PinSubCategoryObject", UMG_TEXTBLOCK)
setf(ruleTextGet, "self", "PinType.PinSubCategoryObject", W_RULEROWENTRY_BGC, output=False)
connect(createRow, "ReturnValue", ruleTextGet, "self")

SETTEXT_T = tmpl_from(construct_src, "K2Node_CallFunction_7")
setRowText = add(SETTEXT_T)
setRowText._replace_prop("FunctionReference", '(MemberParent="/Script/CoreUObject.Class\'/Script/UMG.TextBlock\'",MemberName="SetText")')
setf(setRowText, "self", "PinType.PinSubCategoryObject", UMG_TEXTBLOCK, output=False)
connect(ruleTextGet, "RuleText", setRowText, "self")
connect(convFinalText, "ReturnValue", setRowText, "InText")
connect_exec(setOwning, setRowText, "then", "execute")

addChild = add(ADDCHILD_T)
rulesBoxGet2 = selfget_widget("RulesListBox", "object", UMG_VERTICALBOX, W_AMADANMENU_BGC)
connect(rulesBoxGet2, "RulesListBox", addChild, "self")
connect(createRow, "ReturnValue", addChild, "Content")
connect_exec(setRowText, addChild, "then", "execute")

# =====================  top-level exec wiring  ====================================================
connect_exec(knot_entry, clearChildren, "OutputPin", "execute")
connect_exec(clearChildren, feach, "then", "Exec")
connect_exec(feach, castGM, "LoopBody", "execute")

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

out = MOD + r"\.ccmod\graphs\amadanmenu_refreshruleslist_body.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"nodes: {len(g.nodes)}   wrote: {out}")
print(f"problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
print("wildcards:", wilds)
print()
print("hand-wire needed after paste: Entry.then ->", knot_entry.name)
