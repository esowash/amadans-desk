"""Add the real menu-open call site for GatherNearbyBenches to W_AmadanMenu's Construct
event, working on the REAL live graph (pulled session 16) rather than a from-scratch template.

Existing chain (untouched): Construct -> GetAllActorsOfClass(Menu_ModController)[0] ->
Get(AmadanText) -> SetText(placeholder textbox). This already proves the "get the one
ModController instance" pattern works via GAC+[0] (safe: Conan spawns exactly one
ModController per mod).

New chain, added via a Sequence off Construct.then (never fan out an exec pin directly --
see stocker-exec-fanout-gotcha): the second branch gets the Desk the same way (GAC on the
Menu-namespaced BP_PL_Table_Strategy_Amadan, not the legacy Stocker one -- see session 16's
finding that the harness had been anchored to the wrong/invisible Desk), then calls
GatherNearbyBenches on the SAME ModController reference the existing branch already fetched
(fan out that data pin, not a duplicate GAC).

This is NOT a same-class self-call (the caller is the widget, not the ModController), so it
does not hit the "self-call synthesis fails" gotcha at all -- it's an ordinary external
function call via an explicit Target pin, the same shape as every ApplyKeepRule call already
built successfully in this project. Uses GatherNearbyBenches's real, already-known MemberGuid
(CCF54CFD4BC437159B5892A2EF0EC0C4, captured session 16 from the user's own hand-added node)
so this isn't even a best-effort reconstruction -- it's the actual correct reference.
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
SRC = MOD + r"\.ccmod\graphs\amadanmenu_construct_live_s16.t3d"
STOCKER_GRAPH = MOD + r"\.ccmod\graphs\stocker_modcontroller_probe_a_live.t3d"
HARNESS_GRAPH = MOD + r"\.ccmod\graphs\menu_debug_harness_postpaste.t3d"

MENU_MC_BGC = '''"/Script/Engine.BlueprintGeneratedClass'/Game/Mods/Menu/Menu_ModController.Menu_ModController_C'"'''
MENU_MC_CLASS = "/Game/Mods/Menu/Menu_ModController.Menu_ModController_C"
MENU_DESK_BGC = '''"/Script/Engine.BlueprintGeneratedClass'/Game/Mods/Menu/BP_PL_Table_Strategy_Amadan.BP_PL_Table_Strategy_Amadan_C'"'''
MENU_DESK_CLASS = "/Game/Mods/Menu/BP_PL_Table_Strategy_Amadan.BP_PL_Table_Strategy_Amadan_C"
ACTOR_CLASS = '''"/Script/CoreUObject.Class'/Script/Engine.Actor'"'''

g = parse(open(SRC, encoding="utf-8-sig").read())
stocker_src = parse(open(STOCKER_GRAPH, encoding="utf-8-sig").read())
harness_src = parse(open(HARNESS_GRAPH, encoding="utf-8-sig").read())


def by_name(graph, name):
    n = graph.by_name(name)
    assert n, f"missing node {name}"
    return n


def setf(n, pn, k, raw, output=None):
    p = n.pin_by_name(pn, output=output)
    assert p, f"{n.name} has no pin {pn}"
    p._set(k, raw)


def tmpl_file(path):
    t = parse(open(path, encoding="utf-8-sig").read())
    for n in t.nodes:
        for p in n.pins:
            p.links = []
    return t


def find_by_pin_field(src_graph, pin_name, field, needle):
    for n in src_graph.nodes:
        p = n.pin_by_name(pin_name)
        if p and needle in (p._get(field) or ""):
            nn = copy.deepcopy(n)
            for pp in nn.pins:
                pp.links = []
            return Graph(nodes=[nn])
    raise KeyError((pin_name, field, needle))


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


KNOT_T = tmpl_file(LIB + r"\flow\knot.t3d")
SEQ_T = find_by_raw(stocker_src, "", want_class="K2Node_ExecutionSequence")
# The Desk GAC template was captured targeting the Stocker Desk; clone + retarget to Menu's.
GAC_DESK_T = find_by_pin_field(stocker_src, "ActorClass", "DefaultObject", "BP_PL_Table_Strategy_Amadan")
GETARRAYITEM_T = find_by_raw(stocker_src, "", want_class="K2Node_GetArrayItem")
# GatherNearbyBenches's real self-call node, captured from the debug harness -- reshape its
# "self" pin from implicit-self to an explicit Target pin for this external call.
GATHER_BENCHES_T = find_by_raw(harness_src, 'MemberName="GatherNearbyBenches"', want_class="K2Node_CallFunction")


def add(t):
    return instantiate(t, g)[0]


construct = by_name(g, "K2Node_Event_3")
old_first = by_name(g, "K2Node_CallFunction_6")  # GAC(Menu_ModController), existing chain head
modctrl_getarrayitem = by_name(g, "K2Node_GetArrayItem_0")  # existing ModController ref

# --- retarget the Desk GAC clone from Stocker's namespace to Menu's -------------------------
gac_desk = add(GAC_DESK_T)
setf(gac_desk, "ActorClass", "DefaultObject", f'"{MENU_DESK_CLASS}"')
setf(gac_desk, "OutActors", "PinType.PinSubCategoryObject", MENU_DESK_BGC, output=True)

getitem_desk = add(GETARRAYITEM_T)
setf(getitem_desk, "Array", "PinType.PinCategory", '"object"')
setf(getitem_desk, "Array", "PinType.PinSubCategoryObject", MENU_DESK_BGC)
setf(getitem_desk, "Array", "PinType.ContainerType", "Array")
setf(getitem_desk, "Output", "PinType.PinCategory", '"object"', output=True)
setf(getitem_desk, "Output", "PinType.PinSubCategoryObject", MENU_DESK_BGC, output=True)

knot_desk = add(KNOT_T)
setf(knot_desk, "InputPin", "PinType.PinCategory", '"object"')
setf(knot_desk, "InputPin", "PinType.PinSubCategoryObject", ACTOR_CLASS)
setf(knot_desk, "InputPin", "PinType.ContainerType", "None")
setf(knot_desk, "OutputPin", "PinType.PinCategory", '"object"', output=True)
setf(knot_desk, "OutputPin", "PinType.PinSubCategoryObject", ACTOR_CLASS, output=True)
setf(knot_desk, "OutputPin", "PinType.ContainerType", "None", output=True)

# --- GatherNearbyBenches as an EXTERNAL call (Target pin, not self-context) -----------------
gather = add(GATHER_BENCHES_T)
gather._replace_prop(
    "FunctionReference",
    f'(MemberParent={MENU_MC_BGC},MemberName="GatherNearbyBenches",MemberGuid=CCF54CFD4BC437159B5892A2EF0EC0C4)',
)
self_pin = gather.pin_by_name("self", output=False)
self_pin._set("PinType.PinSubCategory", '""')
self_pin._set("PinType.PinSubCategoryObject", MENU_MC_BGC)
setf(gather, "Range", "DefaultValue", '"3000.0"')

# --- sequence splice: Construct.then -> Seq -> {old chain, new chain} -----------------------
seq = add(SEQ_T)
construct_then = construct.pin_by_name("then", output=True)
old_first_exec = old_first.pin_by_name("execute", output=False)
construct_then.links = []
old_first_exec.links = []
connect_exec(construct, seq, "then", "execute")
connect_exec(seq, old_first, "then_0", "execute")
connect_exec(seq, gac_desk, "then_1", "execute")
connect_exec(gac_desk, gather, "then", "execute")

# --- data wiring -----------------------------------------------------------------------------
connect(gac_desk, "OutActors", getitem_desk, "Array")
connect(getitem_desk, "Output", knot_desk, "InputPin")
connect(knot_desk, "OutputPin", gather, "AnchorActor")
connect(modctrl_getarrayitem, "Output", gather, "self")

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

out = MOD + r"\.ccmod\graphs\amadanmenu_construct_v2_full.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"AmadanMenu Construct v2: nodes={len(g.nodes)} wrote={out} problems={len(problems)}")
for pr in problems:
    print("  !", pr)
