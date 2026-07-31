r"""W_AmadanMenu Construct: populate BenchDropdown from ManagedStations.

Self-contained fragment (same technique as build_widget_onclicked.py): does its own
GetAllActorsOfClass(Menu_ModController)->[0] lookup rather than tapping the existing Construct
graph's already-computed instance -- avoids needing a fresh live pull to find that node's exact
current NodeGuid/PinId, trivial extra cost since Construct runs once. One hand-wire: the existing
GatherNearbyBenches call's dangling `then` pin (confirmed dangling in amadanmenu_construct_v2_full.t3d)
-> this fragment's entry knot, so the dropdown fills in AFTER ManagedStations is actually populated.

Chain:
  [[hand: GatherNearbyBenches.then]] -> knot -> GetAllActorsOfClass(Menu_ModController) -> [0]
    -> VariableGet(ManagedStations, external, self=above)
    -> ForEachLoop(Station):
         GetDisplayName(Station) -> AddOption(BenchDropdown, that string)

Real precedent reused: GetAllActorsOfClass + GetArrayItem cloned from amadanmenu_construct_v2_full.t3d
(K2Node_CallFunction_6 / K2Node_GetArrayItem_0 -- the SAME lookup already live and working in this
exact widget's Construct). ManagedStations external VariableGet clones AmadanText's external-get
shape (K2Node_VariableGet_1 in the same file), with ManagedStations' real MemberGuid
(996311EC4F3077BB4F2AFAADB1BC959D, confirmed live in menu_modcontroller_eventgraph_live_s16.t3d).
BenchDropdown self-get clones MultiLineEditableTextBox_74's self-get shape (K2Node_VariableGet_3).
GetDisplayName is the real shared library brick (call/get_display_name.t3d). ForEachLoop is the
real shared library brick (flow/foreach.t3d). AddOption has no precedent anywhere in this project
-- hand-typed from the standard UComboBoxString::AddOption(FString) signature, same
CallFunction/exec-pin shape already proven dozens of times elsewhere (e.g. AddOption is the same
family of impure single-String-param call as SetText on MultiLineEditableTextBox_74, just a
different target class/function -- cloned from THAT shape, not typed fully from scratch).
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
CONSTRUCT_SRC = MOD + r"\.ccmod\graphs\amadanmenu_construct_v2_full.t3d"
EVENTGRAPH_SRC = MOD + r"\.ccmod\graphs\menu_w_amadanmenu_eventgraph.t3d"

MENU_MC_BGC = '''"/Script/Engine.BlueprintGeneratedClass'/Game/Mods/Menu/Menu_ModController.Menu_ModController_C'"'''
ACTOR_CLASS = '''"/Script/CoreUObject.Class'/Script/Engine.Actor'"'''
COMBOBOX_CLASS = '''"/Script/CoreUObject.Class'/Script/UMG.ComboBoxString'"'''


def tmpl_file(path):
    t = parse(open(path, encoding="utf-8-sig").read())
    for n in t.nodes:
        for p in n.pins:
            p.links = []
    return t


construct_src = parse(open(CONSTRUCT_SRC, encoding="utf-8-sig").read())
eventgraph_src = parse(open(EVENTGRAPH_SRC, encoding="utf-8-sig").read())

def tmpl_from(graph, name):
    n = copy.deepcopy(graph.by_name(name))
    for p in n.pins:
        p.links = []
    return Graph(nodes=[n])


GAC_T = tmpl_from(construct_src, "K2Node_CallFunction_6")          # GetAllActorsOfClass(Menu_ModController)
ITEM_T = tmpl_from(construct_src, "K2Node_GetArrayItem_0")         # [0]
MANAGEDSTATIONS_GET_T = tmpl_from(construct_src, "K2Node_VariableGet_1")   # external get shape (was AmadanText)
DROPDOWN_SELFGET_T = tmpl_from(eventgraph_src, "K2Node_VariableGet_0")     # self-get shape (was MultiLineEditableTextBox_74)
SETTEXT_T = tmpl_from(construct_src, "K2Node_CallFunction_7")             # impure 1-text-param call shape (was SetText -- reused only for its CallFunction/exec pin skeleton)

GETDISPLAYNAME_T = tmpl_file(LIB + r"\call\get_display_name.t3d")
FEACH_T = tmpl_file(LIB + r"\flow\foreach.t3d")
KNOT_T = tmpl_file(LIB + r"\flow\knot.t3d")

g = Graph(nodes=[])


def add(t):
    return instantiate(t, g)[0]


def pin(n, name, output=None):
    p = n.pin_by_name(name, output=output)
    assert p, f"{n.name} has no pin {name}"
    return p


def setf(n, pn, k, raw, output=None):
    pin(n, pn, output=output)._set(k, raw)


def setd(n, pn, v, output=None):
    setf(n, pn, "DefaultValue", f'"{v}"', output=output)


# --- build ---------------------------------------------------------------------------------
knotExec = add(KNOT_T)
setf(knotExec, "InputPin", "PinType.PinCategory", '"exec"')
setf(knotExec, "InputPin", "PinType.PinSubCategoryObject", "None")
setf(knotExec, "OutputPin", "PinType.PinCategory", '"exec"')
setf(knotExec, "OutputPin", "PinType.PinSubCategoryObject", "None")

gac = add(GAC_T)   # already targets Menu_ModController_C, no retyping needed
item0 = add(ITEM_T)
setf(item0, "Array", "PinType.PinSubCategoryObject", MENU_MC_BGC)
setf(item0, "Output", "PinType.PinSubCategoryObject", MENU_MC_BGC, output=True)
connect(gac, "OutActors", item0, "Array")
connect_exec(knotExec, gac, "OutputPin", "execute")

stationsGet = add(MANAGEDSTATIONS_GET_T)
stationsGet._replace_prop(
    "VariableReference",
    f'(MemberParent={MENU_MC_BGC},MemberName="ManagedStations",MemberGuid=996311EC4F3077BB4F2AFAADB1BC959D)',
)
setf(stationsGet, "self", "PinType.PinSubCategoryObject", MENU_MC_BGC, output=False)
outpin = pin(stationsGet, "AmadanText", output=True)
outpin._set("PinName", '"ManagedStations"')
outpin._set("PinType.PinCategory", '"object"')
outpin._set("PinType.PinSubCategoryObject", ACTOR_CLASS)
outpin._set("PinType.ContainerType", "Array")
connect(item0, "Output", stationsGet, "self")

feach = add(FEACH_T)
setf(feach, "Array", "PinType.PinCategory", '"object"')
setf(feach, "Array", "PinType.PinSubCategoryObject", ACTOR_CLASS)
setf(feach, "Array", "PinType.ContainerType", "Array")
setf(feach, "Array Element", "PinType.PinCategory", '"object"', output=True)
setf(feach, "Array Element", "PinType.PinSubCategoryObject", ACTOR_CLASS, output=True)
setf(feach, "Array Element", "PinType.ContainerType", "None", output=True)
connect(stationsGet, "ManagedStations", feach, "Array")
connect_exec(gac, feach, "then", "Exec")

disp = add(GETDISPLAYNAME_T)
connect(feach, "Array Element", disp, "Object")

dropdownGet = add(DROPDOWN_SELFGET_T)
dropdownGet._replace_prop("VariableReference", '(MemberName="BenchDropdown",bSelfContext=True)')
outpin2 = pin(dropdownGet, "MultiLineEditableTextBox_74", output=True)
outpin2._set("PinName", '"BenchDropdown"')
outpin2._set("PinType.PinSubCategoryObject", COMBOBOX_CLASS)

# AddOption: cloned from SetText's impure-1-param-call skeleton, retargeted to
# UComboBoxString::AddOption(FString Option). SetText's own data (InText/self target class) gets
# fully overwritten below -- only the node's CallFunction/exec-pin shape is reused.
addOpt = add(SETTEXT_T)
addOpt._replace_prop(
    "FunctionReference",
    '(MemberParent="/Script/CoreUObject.Class\'/Script/UMG.ComboBoxString\'",MemberName="AddOption")',
)
setf(addOpt, "self", "PinType.PinSubCategoryObject", COMBOBOX_CLASS, output=False)
inpin = pin(addOpt, "InText")
inpin._set("PinName", '"Option"')
inpin._set("PinType.PinCategory", '"string"')
inpin._set("PinType.PinSubCategoryObject", "None")

connect(dropdownGet, "BenchDropdown", addOpt, "self")
connect(disp, "ReturnValue", addOpt, "Option")
connect_exec(feach, addOpt, "LoopBody", "execute")

# --- layout ----------------------------------------------------------------------------------
knotExec.set_position(-100, 0)
gac.set_position(150, 0)
item0.set_position(500, 0)
stationsGet.set_position(500, 200)
feach.set_position(850, 0)
disp.set_position(1150, 150)
dropdownGet.set_position(1150, 350)
addOpt.set_position(1450, 150)

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
print("intentionally dangling (hand-wire landing point + loop Completed, no downstream needed):")
for nn, pn in dangling:
    print(f"  {nn}.{pn}")

out = MOD + r"\.ccmod\graphs\amadanmenu_construct_populate_body.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"\nnodes: {len(g.nodes)}   wrote: {out}")
print(f"problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
