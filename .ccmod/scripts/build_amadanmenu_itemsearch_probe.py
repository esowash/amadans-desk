r"""Minimal probe: does OnTextChanged bind the way I expect, and what pin carries the new text?

No precedent anywhere in this project for a delegate-with-parameters ComponentBoundEvent (every
prior one -- OnClicked x4 -- carries no data). Built on the same real Button_634 OnClicked shape,
guessing: DelegatePropertyName="OnTextChanged", the UMG.EditableTextBox delegate signature name,
and that the new Text value appears as an extra OUTPUT pin (guessed name "Text") on the event
node itself, the same way any K2Node_Event with parameters exposes them.

Deliberately minimal -- just the bound event -> Conv_TextToString -> PrintString, so a wrong
guess is cheap to diagnose and fix before building the full filter loop on top of it.
"""
import sys

CCMOD = r"<CCMOD_HOME>"
sys.path.insert(0, CCMOD)
from ccmod.t3d import parse, connect, connect_exec
from ccmod.t3d.generator import instantiate
from ccmod.t3d.model import Graph

MOD = r"<MOD_ROOT>"
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


BOUND_EVENT_T = tmpl_from(eventgraph_src, "K2Node_ComponentBoundEvent_0")   # real Button_634 OnClicked shape
CONV_TEXT_TO_STRING_T = tmpl_file(LIB + r"\actor\conv_text_to_string.t3d")

RAW_PRINT = '''Begin Object Class=/Script/BlueprintGraph.K2Node_CallFunction Name="K2Node_CallFunction_Print"
   FunctionReference=(MemberParent=Class'"/Script/Engine.KismetSystemLibrary"',MemberName="PrintString")
   NodeGuid=00000000000000000000000000000000
   CustomProperties Pin (PinId=00000000000000000000000000000020,PinName="execute",PinType.PinCategory="exec",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000021,PinName="InString",PinType.PinCategory="string",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,DefaultValue="",PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000022,PinName="then",Direction="EGPD_Output",PinType.PinCategory="exec",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
End Object'''
PRINT_T = parse(RAW_PRINT)

g = Graph(nodes=[])


def add(t):
    return instantiate(t, g)[0]


def pin(n, name, output=None):
    p = n.pin_by_name(name, output=output)
    assert p, f"{n.name} has no pin {name}"
    return p


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
    '"BndEvt__W_AmadanMenu_ItemSearchInput_K2Node_ComponentBoundEvent_5_OnEditableTextBoxTextChangedEvent__DelegateSignature"',
)
# Add the guessed data output pin (the new Text value) directly onto the cloned node -- a real
# Pin object, not raw text (same lesson as the RunSweep AnchorActor/Range fix earlier tonight).
RAW_TEXT_PIN = '''Begin Object Class=/Script/BlueprintGraph.K2Node_CallFunction Name="K2Node_Scratch2"
   CustomProperties Pin (PinId=00000000000000000000000000000070,PinName="Text",Direction="EGPD_Output",PinType.PinCategory="text",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
End Object'''
scratch = parse(RAW_TEXT_PIN).nodes[0]
from ccmod.t3d.guid import new_guid
textPin = scratch.pins[0]
textPin.pin_id = new_guid()
boundEvent.body.append(("pin", textPin))

t2s = add(CONV_TEXT_TO_STRING_T)
connect(boundEvent, "Text", t2s, "InText")

printNode = add(PRINT_T)
connect(t2s, "ReturnValue", printNode, "InString")
connect_exec(boundEvent, printNode, "then", "execute")

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

out = MOD + r"\.ccmod\graphs\amadanmenu_itemsearch_probe.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"nodes: {len(g.nodes)}   wrote: {out}")
print(f"problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
