r"""W_AmadanMenu SaveButton::OnClicked -> AddKeepRule, WITH diagnostic prints.

Round 1 playtest: log confirmed MENU_RESTOCK found 1 rule to process, but NOTHING in the entire
lab moved (verified via full save-DB diff across all 5 stations + 15 storage containers -- zero
change anywhere, not even at the intended bench/item). No runtime errors logged either (no
Accessed None, no array-bounds warnings, no cast-failure prints) -- the chain ran clean but
produced a rule that didn't do anything, or a rule that didn't target what was intended. Can't
tell which from the log alone, since nothing echoes the actual resolved values.

Added here: 4 label+value print pairs (matching the SAME pattern MENU_TIDY/MENU_RESTOCK already
use -- literal-text label PrintString immediately followed by a wired-value PrintString, not a
single concatenated string) between the ModController lookup and the AddKeepRule call, so the
next Save click logs exactly what got resolved:
  SAVECLICK: Station     -> GetDisplayName(Station)
  SAVECLICK: TemplateID  -> Conv_IntToString(TemplateID)
  SAVECLICK: Keep        -> Conv_IntToString(Keep)
  SAVECLICK: KeepAll     -> Conv_BoolToString(KeepAll)
Compare this against the separate diagnostic being added inside RestockManagedStations (needs a
live pull, done separately) to see whether what's INPUT matches what's STORED/processed -- if
they match, the bug is inside ApplyKeepRule itself (out of scope to edit, ported verbatim from
Stocker); if they don't match, the bug is somewhere in this OnClicked chain or the upsert.

This is a full replacement for the existing SaveButton OnClicked (delete the old
ComponentBoundEvent + its whole chain first, then paste this) -- simpler and lower-risk than
hand-splicing 8 new nodes into an already-live wire under time pressure.

Self-contained fragment, same technique as build_amadanmenu_construct_populate.py and the earlier
build_widget_onclicked.py: does its own independent GetAllActorsOfClass(Menu_ModController)->[0]
lookup rather than tapping Construct's already-computed instance. ZERO hand-wires needed -- the
whole chain, including the OnClicked bound event itself, is generated; just paste into
W_AmadanMenu's EventGraph.

Chain:
  SaveButton.OnClicked (K2Node_ComponentBoundEvent) -> GetAllActorsOfClass(Menu_ModController)->[0]
    -> BenchDropdown.GetSelectedIndex -> ManagedStations[idx] -> Station
    -> TemplateIDInput.GetText -> Conv_TextToString -> Conv_StringToInt -> TemplateID
    -> KeepInput.GetText -> Conv_TextToString -> Conv_StringToInt -> Keep
    -> KeepAllCheckbox.IsChecked -> KeepAll
    -> Menu_ModController.AddKeepRule(Station, TemplateID, Keep, KeepAll)

Real precedent reused:
  - K2Node_ComponentBoundEvent cloned from Button_634's real, LIVE, working "Close" OnClicked
    (menu_w_amadanmenu_eventgraph.t3d K2Node_ComponentBoundEvent_0) -- same clone-a-real-example
    technique already proven for same-class self-calls in session 16 (see [[stocker-menu-pivot]]:
    "if a real working example already exists in the graph... clone it, swap the identifying
    field"). CustomFunctionName only needs to be a unique valid identifier, not match the node's
    own internal Name -- HIGHEST-UNCERTAINTY piece of this whole build, no other ComponentBoundEvent
    has ever been freshly minted (vs. captured-as-already-live) in this project. Proofread via
    `ccmod pull` after pasting + compiling, same as every other never-before-tried node shape.
  - GetAllActorsOfClass / GetArrayItem / ManagedStations external VariableGet: identical templates
    to build_amadanmenu_construct_populate.py (same real precedent, same MemberGuid).
  - BenchDropdown/TemplateIDInput/KeepInput/KeepAllCheckbox self-gets: same self-get shape as
    BenchDropdown's in the Construct fragment (MultiLineEditableTextBox_74's self-get), just a
    different MemberName/output class each time.
  - GetSelectedIndex / EditableTextBox::GetText / IsChecked: all clone the SAME real pure-function
    skeleton (MultiLineEditableTextBox::GetText, self hidden + ReturnValue only, no other input --
    K2Node_CallFunction_1 in menu_w_amadanmenu_eventgraph.t3d), retargeting FunctionReference +
    self pin type + ReturnValue pin type per call. Same "clone nearest same-shape real node"
    technique as everywhere else in this project when no dedicated capture exists.
  - Conv_TextToString: real shared library brick (actor/conv_text_to_string.t3d).
  - Conv_StringToInt: hand-typed, cloning Conv_UniqueIDToString's real pure-conversion-function
    shape (actor/conv_uniqueid_to_string.t3d), retargeted to KismetStringLibrary::Conv_StringToInt.
  - AddKeepRule call: hand-typed raw node (RAW_ADDKEEPRULE_CALL below), self+execute+then pin
    shape copied verbatim from GatherNearbyBenches's real external-call node (already proven live
    since session 16 -- amadanmenu_construct_v2_full.t3d K2Node_CallFunction_0), the 4 param pins
    built from AddKeepRule's REAL, CONFIRMED FunctionEntry pin types (pulled directly from
    menu_addkeeprule_live_s16.t3d: Station=object/Actor, TemplateID=int, Keep=int, KeepAll=bool).
    MemberGuid intentionally omitted -- AddKeepRule currently has zero callers anywhere, so no
    real MemberGuid has ever been captured for it; per the session-16-established technique,
    name+class resolution without a GUID is proven to work for external target-pin calls
    (GatherNearbyBenches' own capture is the proof: this exact shape, just with its real GUID).
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
CONSTRUCT_SRC = MOD + r"\.ccmod\graphs\amadanmenu_construct_v2_full.t3d"
EVENTGRAPH_SRC = MOD + r"\.ccmod\graphs\menu_w_amadanmenu_eventgraph.t3d"

MENU_MC_BGC = '''"/Script/Engine.BlueprintGeneratedClass'/Game/Mods/Menu/Menu_ModController.Menu_ModController_C'"'''
ACTOR_CLASS = '''"/Script/CoreUObject.Class'/Script/Engine.Actor'"'''
ACTOR_CLASS_UOBJ = '''"/Script/CoreUObject.Class'/Script/Engine.Actor'"'''
COMBOBOX_CLASS = '''"/Script/CoreUObject.Class'/Script/UMG.ComboBoxString'"'''
EDITABLETEXTBOX_CLASS = '''"/Script/CoreUObject.Class'/Script/UMG.EditableTextBox'"'''
CHECKBOX_CLASS = '''"/Script/CoreUObject.Class'/Script/UMG.CheckBox'"'''


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


construct_src = parse(open(CONSTRUCT_SRC, encoding="utf-8-sig").read())
eventgraph_src = parse(open(EVENTGRAPH_SRC, encoding="utf-8-sig").read())

BOUND_EVENT_T = tmpl_from(eventgraph_src, "K2Node_ComponentBoundEvent_0")  # Button_634 OnClicked, real+live
GAC_T = tmpl_from(construct_src, "K2Node_CallFunction_6")                 # GetAllActorsOfClass(Menu_ModController)
ITEM_T = tmpl_from(construct_src, "K2Node_GetArrayItem_0")                # generic GetArrayItem shape, reused 2x
MANAGEDSTATIONS_GET_T = tmpl_from(construct_src, "K2Node_VariableGet_1")  # external get shape (was AmadanText)
SELFGET_T = tmpl_from(eventgraph_src, "K2Node_VariableGet_0")             # self-get shape (was MultiLineEditableTextBox_74)
PUREGETTER_T = tmpl_from(eventgraph_src, "K2Node_CallFunction_1")         # pure self+ReturnValue-only shape (was GetText)

CONV_TEXT_TO_STRING_T = tmpl_file(LIB + r"\actor\conv_text_to_string.t3d")
CONV_UID_TO_STRING_T = tmpl_file(LIB + r"\actor\conv_uniqueid_to_string.t3d")

RAW_ADDKEEPRULE_CALL = '''Begin Object Class=/Script/BlueprintGraph.K2Node_CallFunction Name="K2Node_CallFunction_AddKeepRule"
   FunctionReference=(MemberParent="/Script/Engine.BlueprintGeneratedClass'/Game/Mods/Menu/Menu_ModController.Menu_ModController_C'",MemberName="AddKeepRule")
   NodeGuid=00000000000000000000000000000000
   CustomProperties Pin (PinId=00000000000000000000000000000001,PinName="execute",PinType.PinCategory="exec",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000002,PinName="then",Direction="EGPD_Output",PinType.PinCategory="exec",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000003,PinName="self",PinFriendlyName=NSLOCTEXT("K2Node", "Target", "Target"),PinType.PinCategory="object",PinType.PinSubCategory="",PinType.PinSubCategoryObject="/Script/Engine.BlueprintGeneratedClass'/Game/Mods/Menu/Menu_ModController.Menu_ModController_C'",PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000004,PinName="Station",PinType.PinCategory="object",PinType.PinSubCategory="",PinType.PinSubCategoryObject="/Script/CoreUObject.Class'/Script/Engine.Actor'",PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000005,PinName="TemplateID",PinType.PinCategory="int",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,DefaultValue="0",PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000006,PinName="Keep",PinType.PinCategory="int",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,DefaultValue="0",PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000007,PinName="KeepAll",PinType.PinCategory="bool",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,DefaultValue="false",PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
End Object'''
ADDKEEPRULE_CALL_T = parse(RAW_ADDKEEPRULE_CALL)

# Cloned verbatim from Button_634's real, original, working Close node (self pin visible but
# intentionally left unwired -- see build_amadanmenu_saveandclose_onclicked.py for the full note).
RAW_CLOSE_CALL = '''Begin Object Class=/Script/BlueprintGraph.K2Node_CallFunction Name="K2Node_CallFunction_Close"
   FunctionReference=(MemberName="Close",bSelfContext=True)
   NodeGuid=00000000000000000000000000000000
   CustomProperties Pin (PinId=00000000000000000000000000000010,PinName="execute",PinType.PinCategory="exec",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000011,PinName="then",Direction="EGPD_Output",PinType.PinCategory="exec",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000012,PinName="self",PinFriendlyName=NSLOCTEXT("K2Node", "Target", "Target"),PinToolTip="Target\\nWindow Root Object Reference",PinType.PinCategory="object",PinType.PinSubCategory="",PinType.PinSubCategoryObject="/Script/CoreUObject.Class'/Script/ConanSandbox.WindowRoot'",PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000013,PinName="force",PinToolTip="Force\\nBoolean",PinType.PinCategory="bool",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,DefaultValue="false",AutogeneratedDefaultValue="false",PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
End Object'''
CLOSE_CALL_T = parse(RAW_CLOSE_CALL)

GETDISPLAYNAME_T = tmpl_file(LIB + r"\call\get_display_name.t3d")

# Cloned verbatim from AddKeepRule's own real, live, PROVEN PrintString ("STOCKER_ADDRULE: rule
# added" -- confirmed firing in the actual playtest log) -- same minimal shape (execute/InString/
# then only, other PrintString params left at engine default), same MemberParent encoding
# (Class'"..."' rather than the "/Script/CoreUObject.Class'...'" form used elsewhere -- both are
# real, this is just the exact form THIS node already compiled and ran with, not worth normalizing).
RAW_PRINT = '''Begin Object Class=/Script/BlueprintGraph.K2Node_CallFunction Name="K2Node_CallFunction_Print"
   FunctionReference=(MemberParent=Class'"/Script/Engine.KismetSystemLibrary"',MemberName="PrintString")
   NodeGuid=00000000000000000000000000000000
   CustomProperties Pin (PinId=00000000000000000000000000000020,PinName="execute",PinType.PinCategory="exec",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000021,PinName="InString",PinType.PinCategory="string",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,DefaultValue="",PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000022,PinName="then",Direction="EGPD_Output",PinType.PinCategory="exec",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
End Object'''
PRINT_T = parse(RAW_PRINT)

g = Graph(nodes=[])


def make_print(label_text):
    n = add(PRINT_T)
    pin(n, "InString")._set("DefaultValue", f'"{label_text}"')
    return n


def make_print_wired(source_node, source_pin):
    n = add(PRINT_T)
    connect(source_node, source_pin, n, "InString")
    return n


def add(t):
    return instantiate(t, g)[0]


def pin(n, name, output=None):
    p = n.pin_by_name(name, output=output)
    assert p, f"{n.name} has no pin {name}"
    return p


def setf(n, pn, k, raw, output=None):
    pin(n, pn, output=output)._set(k, raw)


def selfget(member_name, out_pin_class):
    n = add(SELFGET_T)
    n._replace_prop("VariableReference", f'(MemberName="{member_name}",bSelfContext=True)')
    outpin = pin(n, "MultiLineEditableTextBox_74", output=True)
    outpin._set("PinName", f'"{member_name}"')
    outpin._set("PinType.PinSubCategoryObject", out_pin_class)
    return n


def puregetter(member_parent_class, member_name, self_class, return_category, return_subcat="None"):
    n = add(PUREGETTER_T)
    n._replace_prop("FunctionReference", f'(MemberParent={member_parent_class},MemberName="{member_name}")')
    setf(n, "self", "PinType.PinSubCategoryObject", self_class, output=False)
    outpin = pin(n, "ReturnValue", output=True)
    outpin._set("PinType.PinCategory", f'"{return_category}"')
    outpin._set("PinType.PinSubCategoryObject", return_subcat)
    return n


UMG_COMBOBOXSTRING = "\"/Script/CoreUObject.Class'/Script/UMG.ComboBoxString'\""
UMG_EDITABLETEXTBOX = "\"/Script/CoreUObject.Class'/Script/UMG.EditableTextBox'\""
UMG_CHECKBOX = "\"/Script/CoreUObject.Class'/Script/UMG.CheckBox'\""
KISMET_STRING_LIB = "\"/Script/CoreUObject.Class'/Script/Engine.KismetStringLibrary'\""

# --- bound event -------------------------------------------------------------------------------
boundEvent = add(BOUND_EVENT_T)
boundEvent._replace_prop("ComponentPropertyName", '"SaveAndCloseButton"')
boundEvent._replace_prop(
    "CustomFunctionName",
    '"BndEvt__W_AmadanMenu_SaveAndCloseButton_K2Node_ComponentBoundEvent_4_OnButtonClickedEvent__DelegateSignature"',
)

# --- resolve Menu_ModController instance --------------------------------------------------------
gac = add(GAC_T)
item0 = add(ITEM_T)
setf(item0, "Array", "PinType.PinSubCategoryObject", MENU_MC_BGC)
setf(item0, "Output", "PinType.PinSubCategoryObject", MENU_MC_BGC, output=True)
connect(gac, "OutActors", item0, "Array")
connect_exec(boundEvent, gac, "then", "execute")

# --- resolve Station via BenchDropdown.GetSelectedIndex + ManagedStations[idx] -------------------
stationsGet = add(MANAGEDSTATIONS_GET_T)
stationsGet._replace_prop(
    "VariableReference",
    f'(MemberParent={MENU_MC_BGC},MemberName="ManagedStations",MemberGuid=2BDF1DC24EB358615BDA2CB84789A1B5)',
)
setf(stationsGet, "self", "PinType.PinSubCategoryObject", MENU_MC_BGC, output=False)
outpin = pin(stationsGet, "AmadanText", output=True)
outpin._set("PinName", '"ManagedStations"')
outpin._set("PinType.PinCategory", '"object"')
outpin._set("PinType.PinSubCategoryObject", ACTOR_CLASS)
outpin._set("PinType.ContainerType", "Array")
connect(item0, "Output", stationsGet, "self")

dropdownGet = selfget("BenchDropdown", UMG_COMBOBOXSTRING)
selIdx = puregetter(UMG_COMBOBOXSTRING, "GetSelectedIndex", UMG_COMBOBOXSTRING, "int")
connect(dropdownGet, "BenchDropdown", selIdx, "self")

stationItem = add(ITEM_T)
setf(stationItem, "Array", "PinType.PinSubCategoryObject", ACTOR_CLASS)
setf(stationItem, "Output", "PinType.PinSubCategoryObject", ACTOR_CLASS, output=True)
connect(stationsGet, "ManagedStations", stationItem, "Array")
connect(selIdx, "ReturnValue", stationItem, "Dimension 1")

# --- TemplateID: SelectedTemplateID (set by whichever result row was clicked) -------------------
selectedIdGet = add(SELFGET_T)
selectedIdGet._replace_prop("VariableReference", '(MemberName="SelectedTemplateID",bSelfContext=True)')
p = pin(selectedIdGet, "MultiLineEditableTextBox_74", output=True)
p._set("PinName", '"SelectedTemplateID"')
p._set("PinType.PinCategory", '"int"')
p._set("PinType.PinSubCategoryObject", "None")

# --- Keep: KeepInput.GetText -> Conv_TextToString -> Conv_StringToInt ----------------------------
keepGet = selfget("KeepInput", UMG_EDITABLETEXTBOX)
getText2 = puregetter(UMG_EDITABLETEXTBOX, "GetText", UMG_EDITABLETEXTBOX, "text")
connect(keepGet, "KeepInput", getText2, "self")

t2s2 = add(CONV_TEXT_TO_STRING_T)
connect(getText2, "ReturnValue", t2s2, "InText")

s2i2 = add(CONV_UID_TO_STRING_T)
s2i2._replace_prop(
    "FunctionReference",
    f'(MemberParent={KISMET_STRING_LIB},MemberName="Conv_StringToInt")',
)
setf(s2i2, "self", "PinType.PinSubCategoryObject", KISMET_STRING_LIB, output=False)
inpin2 = pin(s2i2, "uid")
inpin2._set("PinName", '"InString"')
inpin2._set("PinType.PinCategory", '"string"')
inpin2._set("PinType.PinSubCategoryObject", "None")
outpin2 = pin(s2i2, "ReturnValue", output=True)
outpin2._set("PinType.PinCategory", '"int"')
connect(t2s2, "ReturnValue", s2i2, "InString")

# --- KeepAll: KeepAllCheckbox.IsChecked ----------------------------------------------------------
keepAllGet = selfget("KeepAllCheckbox", UMG_CHECKBOX)
isChecked = puregetter(UMG_CHECKBOX, "IsChecked", UMG_CHECKBOX, "bool")
connect(keepAllGet, "KeepAllCheckbox", isChecked, "self")

# --- diagnostic: echo the resolved values before AddKeepRule fires ------------------------------
dispName = add(GETDISPLAYNAME_T)
connect(stationItem, "Output", dispName, "Object")

idToStr = add(CONV_UID_TO_STRING_T)
idToStr._replace_prop("FunctionReference", f'(MemberParent={KISMET_STRING_LIB},MemberName="Conv_IntToString")')
setf(idToStr, "self", "PinType.PinSubCategoryObject", KISMET_STRING_LIB, output=False)
p = pin(idToStr, "uid"); p._set("PinName", '"InInt"'); p._set("PinType.PinCategory", '"int"'); p._set("PinType.PinSubCategoryObject", "None")
pin(idToStr, "ReturnValue", output=True)._set("PinType.PinCategory", '"string"')
connect(selectedIdGet, "SelectedTemplateID", idToStr, "InInt")

keepToStr = add(CONV_UID_TO_STRING_T)
keepToStr._replace_prop("FunctionReference", f'(MemberParent={KISMET_STRING_LIB},MemberName="Conv_IntToString")')
setf(keepToStr, "self", "PinType.PinSubCategoryObject", KISMET_STRING_LIB, output=False)
p = pin(keepToStr, "uid"); p._set("PinName", '"InInt"'); p._set("PinType.PinCategory", '"int"'); p._set("PinType.PinSubCategoryObject", "None")
pin(keepToStr, "ReturnValue", output=True)._set("PinType.PinCategory", '"string"')
connect(s2i2, "ReturnValue", keepToStr, "InInt")

boolToStr = add(CONV_UID_TO_STRING_T)
boolToStr._replace_prop("FunctionReference", f'(MemberParent={KISMET_STRING_LIB},MemberName="Conv_BoolToString")')
setf(boolToStr, "self", "PinType.PinSubCategoryObject", KISMET_STRING_LIB, output=False)
p = pin(boolToStr, "uid"); p._set("PinName", '"InBool"'); p._set("PinType.PinCategory", '"bool"'); p._set("PinType.PinSubCategoryObject", "None")
pin(boolToStr, "ReturnValue", output=True)._set("PinType.PinCategory", '"string"')
connect(isChecked, "ReturnValue", boolToStr, "InBool")

lbl1 = make_print("SAVECLICK: Station")
val1 = make_print_wired(dispName, "ReturnValue")
lbl2 = make_print("SAVECLICK: TemplateID")
val2 = make_print_wired(idToStr, "ReturnValue")
lbl3 = make_print("SAVECLICK: Keep")
val3 = make_print_wired(keepToStr, "ReturnValue")
lbl4 = make_print("SAVECLICK: KeepAll")
val4 = make_print_wired(boolToStr, "ReturnValue")

diag_chain = [lbl1, val1, lbl2, val2, lbl3, val3, lbl4, val4]
connect_exec(gac, diag_chain[0], "then", "execute")
for a, b in zip(diag_chain, diag_chain[1:]):
    connect_exec(a, b, "then", "execute")

# --- AddKeepRule call -----------------------------------------------------------------------------
callAddRule = add(ADDKEEPRULE_CALL_T)
connect(item0, "Output", callAddRule, "self")
connect(stationItem, "Output", callAddRule, "Station")
connect(selectedIdGet, "SelectedTemplateID", callAddRule, "TemplateID")
connect(s2i2, "ReturnValue", callAddRule, "Keep")
connect(isChecked, "ReturnValue", callAddRule, "KeepAll")
connect_exec(diag_chain[-1], callAddRule, "then", "execute")

# --- Close (chained after AddKeepRule) --------------------------------------------------------
closeCall = add(CLOSE_CALL_T)
connect_exec(callAddRule, closeCall, "then", "execute")

# --- layout -----------------------------------------------------------------------------------
boundEvent.set_position(-100, 0)
gac.set_position(250, 0)
item0.set_position(600, 0)
stationsGet.set_position(600, 200)
dropdownGet.set_position(600, 400)
selIdx.set_position(900, 400)
stationItem.set_position(1200, 200)
selectedIdGet.set_position(600, 600)
selectedIdGet.set_position(1500, 600)
keepGet.set_position(600, 800)
getText2.set_position(900, 800)
t2s2.set_position(1200, 800)
s2i2.set_position(1500, 800)
keepAllGet.set_position(600, 1000)
isChecked.set_position(900, 1000)
callAddRule.set_position(1800, 300)

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
print("intentionally dangling (hidden default pins + then/no-downstream-needed):")
for nn, pn in dangling:
    print(f"  {nn}.{pn}")

out = MOD + r"\.ccmod\graphs\amadanmenu_saveandclosebutton_v3_body.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"\nnodes: {len(g.nodes)}   wrote: {out}")
print(f"problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
