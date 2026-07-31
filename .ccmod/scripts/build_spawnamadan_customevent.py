"""Rebuild SpawnAmadan as a Custom Event (not a Function) directly in Menu_ModController's
EventGraph - Unreal restricts latent/async nodes (like AsyncSpawnNPCFromWeightedTable, a
K2Node_AsyncAction) to Event Graphs, never plain Functions. Confirmed empirically tonight: the
Function version silently dropped everything downstream of the guard's IfThenElse on paste (5 of 9
nodes landed), and the user confirmed AsyncSpawnNPCFromWeightedTable IS in the Context Sensitive
palette from BeginPlay's own EventGraph but was never found searching from a scratch Function.

Real K2Node_CustomEvent shape (CustomFunctionName, FunctionFlags, own `then` output pin that pastes
with working links - no FunctionEntry-style hand-wire needed) cloned from AC_Menu's own real
SaveVariableToMC event (menu_ac_menu_eventgraph.t3d). Everything downstream (guard/MakeTransform/
AsyncAction/prints) is the same body already proven pin-clean in the (rejected) Function attempt,
just re-spliced off the CustomEvent's own `then` pin instead of a knot.
"""
import sys
import copy

import os, pathlib
CCMOD = os.environ.get("CCMOD_HOME") or str(pathlib.Path(__file__).resolve().parents[3] / "claude-conan-modder")
sys.path.insert(0, CCMOD)
from ccmod.t3d import parse, connect, connect_exec
from ccmod.t3d.generator import instantiate
from ccmod.t3d.model import Graph

import pathlib
MOD = str(pathlib.Path(__file__).resolve().parents[2])


def pin(n, name, output=None):
    p = n.pin_by_name(name, output=output)
    assert p, f"{n.name} has no pin {name}"
    return p


def setf(n, pn, k, raw, output=None):
    pin(n, pn, output=output)._set(k, raw)


def find_node_by_class(src_graph, class_needle):
    for n in src_graph.nodes:
        if class_needle in n.begin_line:
            nn = copy.deepcopy(n)
            for p in nn.pins:
                p.links = []
            return Graph(nodes=[nn])
    raise KeyError(class_needle)


def find_template_by_raw(src_graph, needle):
    for n in src_graph.nodes:
        raw = " ".join(t for k, t in n.body if k == "raw")
        if needle in raw:
            nn = copy.deepcopy(n)
            for p in nn.pins:
                p.links = []
            return Graph(nodes=[nn])
    raise KeyError(needle)


live_src = parse(open(MOD + r"\.ccmod\graphs\spawnamadan_live_s20.t3d", encoding="utf-8-sig").read())
merc_src = parse(open(MOD + r"\.ccmod\graphs\mercenaryspawnpoint_live_s20.t3d", encoding="utf-8-sig").read())
beginplay_src = parse(open(MOD + r"\.ccmod\graphs\menu_beginplay_spawnnotebook_spliced.t3d", encoding="utf-8-sig").read())
acmenu_src = parse(open(MOD + r"\.ccmod\graphs\menu_ac_menu_eventgraph.t3d", encoding="utf-8-sig").read())

CUSTOMEVENT_T = find_node_by_class(acmenu_src, "K2Node_CustomEvent_0")
GAC_T = find_node_by_class(live_src, "K2Node_CallFunction_45")
ARRLEN_T = find_node_by_class(live_src, "K2Node_CallArrayFunction_Len")
EQ0_T = find_node_by_class(live_src, "K2Node_CallFunction_260")
ITE_T = find_node_by_class(live_src, "K2Node_IfThenElse_0")
MAKETRANSFORM_T = find_template_by_raw(live_src, 'MemberName="MakeTransform"')
ASYNCSPAWN_T = find_node_by_class(merc_src, "K2Node_AsyncAction_0")
PRINT_T = find_template_by_raw(beginplay_src, 'MemberName="PrintString"')

AMADAN_CLASS_PATH = '"/Game/Mods/Menu/HumanoidNPC_Character_Amadan.HumanoidNPC_Character_Amadan_C"'
AMADAN_BGC = '''"/Script/Engine.BlueprintGeneratedClass'/Game/Mods/Menu/HumanoidNPC_Character_Amadan.HumanoidNPC_Character_Amadan_C'"'''

g = Graph()


def add(t):
    n = instantiate(t, g)[0]
    # ccmod bug workaround (fixed upstream too, kept here for belt-and-suspenders): ExportPath's
    # trailing "...GraphPath.<OldName>'" must track a rename, same as Name= does.
    import re as _re
    n.begin_line = _re.sub(
        r"([:.])[A-Za-z0-9_]+(' *\")$", lambda m: m.group(1) + n.name + m.group(2), n.begin_line,
    )
    return n


event = add(CUSTOMEVENT_T)
for i, (kind, text) in enumerate(event.body):
    if kind == "raw" and text.strip().startswith("CustomFunctionName="):
        event.body[i] = (kind, 'CustomFunctionName="SpawnAmadan"')
# Strip SaveVariableToMC's own "Text" parameter (both its pin and UserDefinedPin declaration) -
# SpawnAmadan takes no parameters, same as the old Function's signature. .pins is a read-only
# property computed from .body, so filter .body directly for both the pin tuple and the raw line.
event.body = [
    (kind, item) for (kind, item) in event.body
    if not (kind == "raw" and "UserDefinedPin" in item)
    and not (kind == "pin" and item.name == "Text")
]

gac = add(GAC_T)
setf(gac, "ActorClass", "DefaultObject", AMADAN_CLASS_PATH)
setf(gac, "OutActors", "PinType.PinSubCategoryObject", AMADAN_BGC, output=True)

arrlen = add(ARRLEN_T)
setf(arrlen, "TargetArray", "PinType.PinCategory", '"object"')
setf(arrlen, "TargetArray", "PinType.PinSubCategoryObject", AMADAN_BGC)
setf(arrlen, "TargetArray", "PinType.ContainerType", "Array")

eq0 = add(EQ0_T)
ite = add(ITE_T)

maketransform = add(MAKETRANSFORM_T)
# Location pin already carries the real Amadan coordinate verbatim from the cloned source.

asyncspawn = add(ASYNCSPAWN_T)
setf(asyncspawn, "WeightedTableID", "DefaultValue", '"Amadan"')

print_ok = add(PRINT_T)
setf(print_ok, "InString", "DefaultValue", '"AMADAN_ASYNCSPAWN: SpawnSucceeded"')
print_fail = add(PRINT_T)
setf(print_fail, "InString", "DefaultValue", '"AMADAN_ASYNCSPAWN: SpawnFailed"')

# --- exec spine ------------------------------------------------------------
connect_exec(event, gac, "then", "execute")
connect_exec(gac, ite, "then", "execute")
connect_exec(ite, asyncspawn, "then", "execute")
connect_exec(asyncspawn, print_ok, "SpawnSucceeded", "execute")
connect_exec(asyncspawn, print_fail, "SpawnFailed", "execute")

# --- data --------------------------------------------------------------
connect(gac, "OutActors", arrlen, "TargetArray")
connect(arrlen, "ReturnValue", eq0, "A")
connect(eq0, "ReturnValue", ite, "Condition")
connect(maketransform, "ReturnValue", asyncspawn, "SpawnTransform")

out_path = MOD + r"\.ccmod\graphs\spawnamadan_customevent_body.t3d"
open(out_path, "w", encoding="utf-8").write(g.render())
print("wrote", out_path, "-", len(g.nodes), "nodes")
for k, t in event.body:
    if k == "raw" and t.strip().startswith("NodeGuid="):
        print("CustomEvent", t.strip())
print("event pins now:", [p.name for p in event.pins])
