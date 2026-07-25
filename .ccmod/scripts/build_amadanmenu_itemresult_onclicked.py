r"""W_AmadanMenu ItemResult_0..7::OnClicked -> Set SelectedTemplateID = ItemResultIDs[N].

This is the confirmed blocking gap from the session-17/18 playtest: search filtering works
(log-verified), but clicking a result row never sets SelectedTemplateID, so both Save buttons
read TemplateID=0. Fix is 8 independent, near-identical bound-event chains, one per row -- no
wiring to the existing OnTextChanged/filter chain needed, this is a brand new set of event
entry points into the same EventGraph.

Chain per row N:
  ItemResult_N.OnClicked (K2Node_ComponentBoundEvent) -> Get ItemResultIDs -> [N] -> Set SelectedTemplateID

Real precedent reused:
  - K2Node_ComponentBoundEvent: same clone-a-real-example technique as
    build_amadanmenu_saverule_onclicked.py -- cloned from Button_634's real, live "Close"
    OnClicked (menu_w_amadanmenu_eventgraph.t3d K2Node_ComponentBoundEvent_0), already proven to
    paste/compile/fire correctly for a freshly-minted ComponentPropertyName+CustomFunctionName
    (SaveButton's OnClicked chain is playtest-confirmed working, session 17).
  - Self-get (ItemResultIDs) and GetArrayItem: same SELFGET_T/ITEM_T shapes already used
    identically in build_amadanmenu_itemsearch_rowpopulate.py for the same array.

GENUINELY UNVERIFIED, flagged: the self-context K2Node_VariableSet shape below has no captured
precedent anywhere in this project (only a NotSelfContext example exists, menu_ac_menu_eventgraph
.t3d's K2Node_VariableSet_0, setting Menu_ModController's AmadanText). Built by analogy to how
this project's self-context K2Node_VariableGet nodes differ from NotSelfContext ones (drop
MemberParent, add bSelfContext=True, omit the SelfContextInfo line entirely, hide+unlink the
`self` pin) -- consistent across every VariableGet example checked, but never confirmed for
VariableSet specifically. Same risk class as SetVisibility/Contains before it: proofread via
`ccmod pull` before trusting a compile; if the DevKit rejects it, fall back to having the user
hand-add ONE `Set SelectedTemplateID` node via GUI drag-from-My-Blueprint, pull it, and use the
real shape for the remaining 7.
"""
import copy
import sys

CCMOD = r"<CCMOD_HOME>"
sys.path.insert(0, CCMOD)
from ccmod.t3d import parse, connect, connect_exec
from ccmod.t3d.generator import instantiate
from ccmod.t3d.model import Graph

MOD = r"<MOD_ROOT>"
CONSTRUCT_SRC = MOD + r"\.ccmod\graphs\amadanmenu_construct_v2_full.t3d"
EVENTGRAPH_SRC = MOD + r"\.ccmod\graphs\menu_w_amadanmenu_eventgraph.t3d"
AC_MENU_SRC = MOD + r"\.ccmod\graphs\menu_ac_menu_eventgraph.t3d"

W_AMADANMENU_BGC = '''"/Script/UMG.WidgetBlueprintGeneratedClass'/Game/Mods/Menu/W_AmadanMenu.W_AmadanMenu_C'"'''


def tmpl_from(graph, name):
    n = copy.deepcopy(graph.by_name(name))
    for p in n.pins:
        p.links = []
    return Graph(nodes=[n])


construct_src = parse(open(CONSTRUCT_SRC, encoding="utf-8-sig").read())
eventgraph_src = parse(open(EVENTGRAPH_SRC, encoding="utf-8-sig").read())
ac_menu_src = parse(open(AC_MENU_SRC, encoding="utf-8-sig").read())

BOUND_EVENT_T = tmpl_from(eventgraph_src, "K2Node_ComponentBoundEvent_0")  # Button_634 OnClicked, real+live
SELFGET_T = tmpl_from(eventgraph_src, "K2Node_VariableGet_0")             # self-get shape (was MultiLineEditableTextBox_74)
ITEM_T = tmpl_from(construct_src, "K2Node_GetArrayItem_0")                # generic GetArrayItem shape
VARSET_T = tmpl_from(ac_menu_src, "K2Node_VariableSet_0")                 # NotSelfContext VariableSet (was AmadanText) -- adapted to self-context below

g = Graph(nodes=[])


def add(t):
    return instantiate(t, g)[0]


def pin(n, name, output=None):
    p = n.pin_by_name(name, output=output)
    assert p, f"{n.name} has no pin {name}"
    return p


def setf(n, pn, k, raw, output=None):
    pin(n, pn, output=output)._set(k, raw)


def del_prop(n, key):
    needle = key + "="
    n.body = [(kind, text) for (kind, text) in n.body
              if not (kind == "raw" and text.lstrip().startswith(needle))]


rows = []
for i in range(8):
    btn = f"ItemResult_{i}"

    # --- bound event ---------------------------------------------------------------------------
    boundEvent = add(BOUND_EVENT_T)
    boundEvent._replace_prop("ComponentPropertyName", f'"{btn}"')
    boundEvent._replace_prop(
        "CustomFunctionName",
        f'"BndEvt__W_AmadanMenu_{btn}_K2Node_ComponentBoundEvent_Row{i}_OnButtonClickedEvent__DelegateSignature"',
    )

    # --- Get ItemResultIDs (self, Array<Integer>) -----------------------------------------------
    idsGet = add(SELFGET_T)
    idsGet._replace_prop("VariableReference", '(MemberName="ItemResultIDs",bSelfContext=True)')
    p = pin(idsGet, "MultiLineEditableTextBox_74", output=True)
    p._set("PinName", '"ItemResultIDs"')
    p._set("PinType.PinCategory", '"int"')
    p._set("PinType.PinSubCategoryObject", "None")
    p._set("PinType.ContainerType", "Array")

    # --- ItemResultIDs[i] ------------------------------------------------------------------------
    idItem = add(ITEM_T)
    setf(idItem, "Array", "PinType.PinCategory", '"int"')
    setf(idItem, "Array", "PinType.PinSubCategoryObject", "None")
    setf(idItem, "Array", "PinType.ContainerType", "Array")
    outp = pin(idItem, "Output", output=True)
    outp._set("PinType.PinCategory", '"int"')
    outp._set("PinType.PinSubCategoryObject", "None")
    setf(idItem, "Dimension 1", "DefaultValue", f'"{i}"')
    connect(idsGet, "ItemResultIDs", idItem, "Array")

    # --- Set SelectedTemplateID (self-context) ----------------------------------------------------
    varSet = add(VARSET_T)
    varSet._replace_prop("VariableReference", '(MemberName="SelectedTemplateID",bSelfContext=True)')
    del_prop(varSet, "SelfContextInfo")

    valuePin = pin(varSet, "AmadanText", output=False)
    valuePin._set("PinName", '"SelectedTemplateID"')
    valuePin._set("PinType.PinCategory", '"int"')
    valuePin._set("PinType.PinSubCategoryObject", "None")
    connect(idItem, "Output", varSet, "SelectedTemplateID")

    outGetPin = pin(varSet, "Output_Get", output=True)
    outGetPin._set("PinType.PinCategory", '"int"')
    outGetPin._set("PinType.PinSubCategoryObject", "None")

    selfPin = pin(varSet, "self", output=False)
    selfPin._set("PinType.PinSubCategoryObject", W_AMADANMENU_BGC)
    selfPin._set("bHidden", "True")
    selfPin.links = []

    connect_exec(boundEvent, varSet, "then", "execute")

    # --- layout ------------------------------------------------------------------------------
    base_y = i * 220
    boundEvent.set_position(-100, base_y)
    idsGet.set_position(300, base_y - 40)
    idItem.set_position(600, base_y - 40)
    varSet.set_position(900, base_y)

    rows.append((boundEvent, idsGet, idItem, varSet))

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
print("intentionally dangling (hidden self pins + Output_Get, unused):")
for nn, pn in dangling:
    print(f"  {nn}.{pn}")

out = MOD + r"\.ccmod\graphs\amadanmenu_itemresult_onclicked.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"\nnodes: {len(g.nodes)}   wrote: {out}")
print(f"problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
