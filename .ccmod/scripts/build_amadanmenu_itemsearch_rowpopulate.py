r"""Populate the 8 visible result rows from ItemResultIDs, chained after the existing match-count
diagnostic print. For each row N (0-7): if Array_Length(ItemResultIDs) > N, resolve that entry's
friendly name and show the row; otherwise collapse it.

Full pull+edit+repaste of the REAL live OnTextChanged graph (pulled fresh this session as
amadanmenu_full_for_rowpopulate.t3d, 16 nodes -- exactly the filter cluster already built and
confirmed compiling). Reuses the EXISTING Array_Length call (K2Node_CallArrayFunction_Len) as the
shared length value for all 8 comparisons rather than recomputing it 8 times (pure node, fan-out
is free). Chains the new logic after the existing Print_1 (match-count value print)'s `then`,
currently dangling.

GENUINELY UNVERIFIED, flagged: UWidget::SetVisibility's exact parameter name ("InVisibility") and
whether the ESlateVisibility enum literal serializes as a bare name string ("Visible"/"Collapsed")
-- no captured precedent anywhere in this project. Same risk class as SetVisibility/Contains/
GetDataTableRowNames earlier -- built from general UE knowledge, flagged for proofread.
"""
import sys

CCMOD = r"<CCMOD_HOME>"
sys.path.insert(0, CCMOD)
from ccmod import db
from ccmod.t3d import parse, connect, connect_exec
from ccmod.t3d.generator import instantiate
from ccmod.t3d.model import Graph
from ccmod.t3d.guid import new_guid
from ccmod.workspace import Workspace

MOD = r"<MOD_ROOT>"
LIB = CCMOD + r"\library"
CONSTRUCT_SRC = MOD + r"\.ccmod\graphs\amadanmenu_construct_v2_full.t3d"

ws = Workspace.resolve()
conn = db.connect(ws.cache_db)
row = db.get_graph(conn, "amadanmenu_full_for_rowpopulate")
assert row, "run `ccmod pull --save amadanmenu_full_for_rowpopulate` first"
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


def tmpl_file(path):
    t = parse(open(path, encoding="utf-8-sig").read())
    for n in t.nodes:
        for p in n.pins:
            p.links = []
    return t


import copy as _copy
def tmpl_from(graph, name):
    n = _copy.deepcopy(graph.by_name(name))
    for p in n.pins:
        p.links = []
    return Graph(nodes=[n])


GREATER_T = tmpl_file(LIB + r"\math\greater_int.t3d")
ITEM_T = tmpl_from(construct_src, "K2Node_GetArrayItem_0")
SETTEXT_T = tmpl_from(construct_src, "K2Node_CallFunction_7")   # impure 1-text-param call skeleton

RAW_GNFT = '''Begin Object Class=/Script/BlueprintGraph.K2Node_CallFunction Name="K2Node_CallFunction_GNFT_row"
   FunctionReference=(MemberParent="/Script/Engine.BlueprintGeneratedClass'/Game/Characters/SurvivalFunctionLibrary.SurvivalFunctionLibrary_C'",MemberName="GetNameFromTemplateID",MemberGuid=1F295A374DD6B5BFD32801949A612B13)
   NodeGuid=00000000000000000000000000000000
   CustomProperties Pin (PinId=00000000000000000000000000000100,PinName="execute",PinType.PinCategory="exec",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000101,PinName="then",Direction="EGPD_Output",PinType.PinCategory="exec",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000102,PinName="self",PinFriendlyName=NSLOCTEXT("K2Node", "Target", "Target"),PinType.PinCategory="object",PinType.PinSubCategory="",PinType.PinSubCategoryObject="/Script/Engine.BlueprintGeneratedClass'/Game/Characters/SurvivalFunctionLibrary.SurvivalFunctionLibrary_C'",PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,DefaultObject="/Game/Characters/SurvivalFunctionLibrary.Default__SurvivalFunctionLibrary_C",PersistentGuid=00000000000000000000000000000000,bHidden=True,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000103,PinName="templateID",PinType.PinCategory="int",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,DefaultValue="0",AutogeneratedDefaultValue="0",PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000104,PinName="__WorldContext",PinType.PinCategory="object",PinType.PinSubCategory="",PinType.PinSubCategoryObject="/Script/CoreUObject.Class'/Script/CoreUObject.Object'",PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000105,PinName="Name",Direction="EGPD_Output",PinType.PinCategory="text",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
End Object'''

IFTHENELSE_RAW = '''Begin Object Class=/Script/BlueprintGraph.K2Node_IfThenElse Name="K2Node_IfThenElse_row"
   NodeGuid=00000000000000000000000000000000
   CustomProperties Pin (PinId=00000000000000000000000000000001,PinName="execute",PinType.PinCategory="exec",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000002,PinName="Condition",PinType.PinCategory="bool",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,DefaultValue="true",AutogeneratedDefaultValue="true",PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000003,PinName="then",PinFriendlyName=NSLOCTEXT("K2Node", "true", "true"),Direction="EGPD_Output",PinType.PinCategory="exec",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId=00000000000000000000000000000004,PinName="else",PinFriendlyName=NSLOCTEXT("K2Node", "false", "false"),Direction="EGPD_Output",PinType.PinCategory="exec",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
End Object'''


def raw_setvis(button_name):
    return f'''Begin Object Class=/Script/BlueprintGraph.K2Node_CallFunction Name="K2Node_CallFunction_SetVis_{button_name}"
   FunctionReference=(MemberParent="/Script/CoreUObject.Class'/Script/UMG.Widget'",MemberName="SetVisibility")
   NodeGuid=00000000000000000000000000000000
   CustomProperties Pin (PinId={new_guid()},PinName="execute",PinType.PinCategory="exec",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId={new_guid()},PinName="then",Direction="EGPD_Output",PinType.PinCategory="exec",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId={new_guid()},PinName="self",PinFriendlyName=NSLOCTEXT("K2Node", "Target", "Target"),PinType.PinCategory="object",PinType.PinSubCategory="",PinType.PinSubCategoryObject="/Script/UMG.WidgetBlueprintGeneratedClass'/Game/Mods/Menu/W_AmadanMenu.W_AmadanMenu_C'",PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
   CustomProperties Pin (PinId={new_guid()},PinName="Visibility",PinType.PinCategory="byte",PinType.PinSubCategory="ESlateVisibility",PinType.PinSubCategoryObject="/Script/UMG.ESlateVisibility",PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,DefaultValue="Visible",PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False)
End Object'''


UMG_BUTTON = "\"/Script/CoreUObject.Class'/Script/UMG.Button'\""
UMG_TEXTBLOCK = "\"/Script/CoreUObject.Class'/Script/UMG.TextBlock'\""

# self-context self-get shape, reused from the pulled OnTextChanged graph's own ItemNames get
SELFGET_T = tmpl_from(g, "K2Node_VariableGet_0")

lenNode = by_name("K2Node_CallArrayFunction_Len")
resultIdsGetForItem = by_name("K2Node_VariableGet_3")   # spare ItemResultIDs self-get already in the pull
chainTail = by_name("K2Node_CallFunction_Print_1")       # last node in the existing chain, .then dangling

prev_exec_node = chainTail
prev_exec_pin = "then"

for i in range(8):
    btn = f"ItemResult_{i}"
    lbl = f"ItemResultText_{i}"

    greater = add(GREATER_T)
    setf(greater, "B", "DefaultValue", f'"{i}"')
    connect(lenNode, "ReturnValue", greater, "A")

    ite = add(parse(IFTHENELSE_RAW))
    connect(greater, "ReturnValue", ite, "Condition")
    connect_exec(prev_exec_node, ite, prev_exec_pin, "execute")

    # --- true branch: resolve + show -----------------------------------------------------------
    idsGet = add(SELFGET_T)
    idsGet._replace_prop("VariableReference", '(MemberName="ItemResultIDs",bSelfContext=True)')
    p = pin(idsGet, "ItemNames", output=True)
    p._set("PinName", '"ItemResultIDs"')
    p._set("PinType.PinCategory", '"int"')
    p._set("PinType.PinSubCategoryObject", "None")
    p._set("PinType.ContainerType", "Array")

    idItem = add(ITEM_T)
    setf(idItem, "Array", "PinType.PinCategory", '"int"')
    setf(idItem, "Array", "PinType.PinSubCategoryObject", "None")
    setf(idItem, "Array", "PinType.ContainerType", "Array")
    outp = pin(idItem, "Output", output=True)
    outp._set("PinType.PinCategory", '"int"')
    outp._set("PinType.PinSubCategoryObject", "None")
    setf(idItem, "Dimension 1", "DefaultValue", f'"{i}"')
    connect(idsGet, "ItemResultIDs", idItem, "Array")

    gnft = add(parse(RAW_GNFT))
    connect(idItem, "Output", gnft, "templateID")

    setText = add(SETTEXT_T)
    setText._replace_prop("FunctionReference", '(MemberParent="/Script/CoreUObject.Class\'/Script/UMG.TextBlock\'",MemberName="SetText")')
    setf(setText, "self", "PinType.PinSubCategoryObject", UMG_TEXTBLOCK, output=False)
    connect(gnft, "Name", setText, "InText")

    lblGet = add(SELFGET_T)
    lblGet._replace_prop("VariableReference", f'(MemberName="{lbl}",bSelfContext=True)')
    p = pin(lblGet, "ItemNames", output=True)
    p._set("PinName", f'"{lbl}"')
    p._set("PinType.PinCategory", '"object"')
    p._set("PinType.PinSubCategoryObject", UMG_TEXTBLOCK)
    p._set("PinType.ContainerType", "None")
    connect(lblGet, lbl, setText, "self")

    setVisTrue = add(parse(raw_setvis(btn + "_t")))
    btnGetT = add(SELFGET_T)
    btnGetT._replace_prop("VariableReference", f'(MemberName="{btn}",bSelfContext=True)')
    p = pin(btnGetT, "ItemNames", output=True)
    p._set("PinName", f'"{btn}"')
    p._set("PinType.PinCategory", '"object"')
    p._set("PinType.PinSubCategoryObject", UMG_BUTTON)
    p._set("PinType.ContainerType", "None")
    setf(setVisTrue, "self", "PinType.PinSubCategoryObject", UMG_BUTTON, output=False)
    connect(btnGetT, btn, setVisTrue, "self")
    setf(setVisTrue, "Visibility", "DefaultValue", '"Visible"')

    connect_exec(ite, gnft, "then", "execute")
    connect_exec(gnft, setText, "then", "execute")
    connect_exec(setText, setVisTrue, "then", "execute")

    # --- false branch: collapse -----------------------------------------------------------------
    setVisFalse = add(parse(raw_setvis(btn + "_f")))
    btnGetF = add(SELFGET_T)
    btnGetF._replace_prop("VariableReference", f'(MemberName="{btn}",bSelfContext=True)')
    p = pin(btnGetF, "ItemNames", output=True)
    p._set("PinName", f'"{btn}"')
    p._set("PinType.PinCategory", '"object"')
    p._set("PinType.PinSubCategoryObject", UMG_BUTTON)
    p._set("PinType.ContainerType", "None")
    setf(setVisFalse, "self", "PinType.PinSubCategoryObject", UMG_BUTTON, output=False)
    connect(btnGetF, btn, setVisFalse, "self")
    setf(setVisFalse, "Visibility", "DefaultValue", '"Collapsed"')

    connect_exec(ite, setVisFalse, "else", "execute")

    # --- layout ------------------------------------------------------------------------------
    base_y = 1400 + i * 220
    greater.set_position(0, base_y)
    ite.set_position(250, base_y)
    idsGet.set_position(500, base_y - 60)
    idItem.set_position(750, base_y - 60)
    gnft.set_position(1000, base_y - 60)
    lblGet.set_position(1250, base_y - 60)
    setText.set_position(1500, base_y - 60)
    btnGetT.set_position(1750, base_y - 60)
    setVisTrue.set_position(2000, base_y - 60)
    btnGetF.set_position(500, base_y + 60)
    setVisFalse.set_position(750, base_y + 60)

    # next row chains off this row's true-branch tail (setVisTrue.then); the false branch is a
    # dead end (nothing needs to happen after collapsing a row).
    prev_exec_node = setVisTrue
    prev_exec_pin = "then"

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

out = MOD + r"\.ccmod\graphs\amadanmenu_itemsearch_rowpopulate.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"nodes: {len(g.nodes)}   wrote: {out}")
print(f"problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
