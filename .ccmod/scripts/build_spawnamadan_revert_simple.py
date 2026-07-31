"""Revert SpawnAmadan back to the simple, proven SpawnActorFromClass approach - the whole
async-spawn/finalization-chain detour (AsyncSpawnNPC, FinishAsyncTrySpawnNPCFromSpawnTableLowLevel,
ConfigureSpawnedNPC, GenerateUniqueID/SetUniqueID, SetCharacterLayout) never fixed the invisible-mesh
symptom across five real, evidence-based attempts. Pivoting: spawn via the simple, crash-free,
already-proven SpawnActorFromClass+SetCharacterSpawnTableID chain, then hand-add SetCharacterLayout
separately afterward (K2Node_Message crashes the DevKit on clipboard paste, confirmed twice - must be
hand-added via GUI, not built here) to self-apply Amadan's real extracted appearance directly, instead
of relying on the SpawnDataTable/native-registration pipeline that never worked.

Guard/MakeTransform/SpawnActorFromClass/DynamicCast/SetCharacterSpawnTableID nodes cloned from the
original working capture (amadan_spawnamadan_fixed_location.t3d), CustomEvent trigger cloned from the
same real precedent already used successfully for this exact conversion (AC_Menu's SaveVariableToMC).
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


orig_src = parse(open(MOD + r"\.ccmod\graphs\amadan_spawnamadan_fixed_location.t3d", encoding="utf-8-sig").read())
acmenu_src = parse(open(MOD + r"\.ccmod\graphs\menu_ac_menu_eventgraph.t3d", encoding="utf-8-sig").read())

CUSTOMEVENT_T = find_node_by_class(acmenu_src, "K2Node_CustomEvent_0")
GAC_T = find_node_by_class(orig_src, "K2Node_CallFunction_45")
ARRLEN_T = find_node_by_class(orig_src, "K2Node_CallArrayFunction_Len")
EQ0_T = find_node_by_class(orig_src, "K2Node_CallFunction_260")
ITE_T = find_node_by_class(orig_src, "K2Node_IfThenElse_0")
MAKETRANSFORM_T = find_template_by_raw(orig_src, 'MemberName="MakeTransform"')
SPAWN_T = find_node_by_class(orig_src, "K2Node_SpawnActorFromClass")
CAST_T = find_node_by_class(orig_src, "K2Node_DynamicCast")
SETID_T = find_template_by_raw(orig_src, 'MemberName="SetCharacterSpawnTableID"')

AMADAN_CLASS_PATH = '"/Game/Mods/Menu/HumanoidNPC_Character_Amadan.HumanoidNPC_Character_Amadan_C"'
AMADAN_BGC = '''"/Script/Engine.BlueprintGeneratedClass'/Game/Mods/Menu/HumanoidNPC_Character_Amadan.HumanoidNPC_Character_Amadan_C'"'''

g = Graph()


def add(t):
    return instantiate(t, g)[0]


event = add(CUSTOMEVENT_T)
for i, (kind, text) in enumerate(event.body):
    if kind == "raw" and text.strip().startswith("CustomFunctionName="):
        event.body[i] = (kind, 'CustomFunctionName="SpawnAmadan"')
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

spawn = add(SPAWN_T)
setf(spawn, "Class", "DefaultObject", AMADAN_CLASS_PATH)
setf(spawn, "CollisionHandlingOverride", "DefaultValue", '"AdjustIfPossibleButAlwaysSpawn"')

cast = add(CAST_T)
setid = add(SETID_T)
setf(setid, "SpawnTableID", "DefaultValue", '"Amadan"')

# --- exec spine ----------------------------------------------------------
connect_exec(event, gac, "then", "execute")
connect_exec(gac, ite, "then", "execute")
connect_exec(ite, spawn, "then", "execute")
connect_exec(spawn, cast, "then", "execute")
connect_exec(cast, setid, "then", "execute")

# --- data ------------------------------------------------------------------
connect(gac, "OutActors", arrlen, "TargetArray")
connect(arrlen, "ReturnValue", eq0, "A")
connect(eq0, "ReturnValue", ite, "Condition")
connect(maketransform, "ReturnValue", spawn, "SpawnTransform")
connect(spawn, "ReturnValue", cast, "Object")
connect(cast, "AsHumanoid NPC Character Amadan", setid, "self")

out_path = MOD + r"\.ccmod\graphs\spawnamadan_revert_simple_body.t3d"
open(out_path, "w", encoding="utf-8").write(g.render())
print("wrote", out_path, "-", len(g.nodes), "nodes")
