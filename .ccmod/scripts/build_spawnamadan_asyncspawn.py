"""Rebuild Menu_ModController::SpawnAmadan to use the REAL async spawn pipeline
(AsyncSpawnNPCFromWeightedTable, a K2Node_AsyncAction wrapping native AsyncSpawnNPCProxy) instead
of SpawnActorFromClass+SetCharacterSpawnTableID - the combined-node timing bug that made Amadan
spawn with default appearance/no gear (SetCharacterSpawnTableID fired after construction already
resolved an empty appearance).

Real precedent cloned verbatim from BP_MercenarySpawnpoint's own live EventGraph (captured this
session as mercenaryspawnpoint_live_s20.t3d) - the K2Node_AsyncAction node itself
(ProxyFactoryFunctionName="AsyncSpawnNPCFromWeightedTable", ProxyClass=
/Script/ConanSandbox.AsyncSpawnNPCProxy), confirmed via a real hand-add-and-pull probe attempt that
failed (not in the Context Sensitive palette from an unrelated Blueprint - it's a K2Node_AsyncAction,
discovered differently), so cloned from a real caller instead. FinishSpawn (BP_MercenarySpawnpoint's
OWN same-class self-call, not part of the pipeline itself) is deliberately NOT replicated - the
async node's own SpawnSucceeded/TargetLayout/SpawnedPawn outputs are the actual pipeline surface.

Guard (GetAllActorsOfClass count==0) and MakeTransform (hardcoded Amadan coordinate) are unchanged,
cloned from SpawnAmadan's own current live body (spawnamadan_live_s20.t3d, pulled fresh this
session, not assumed).
"""
import sys
import copy

CCMOD = r"<CCMOD_HOME>"
sys.path.insert(0, CCMOD)
from ccmod.t3d import parse, connect, connect_exec
from ccmod.t3d.generator import instantiate
from ccmod.t3d.model import Graph

MOD = r"<MOD_ROOT>"


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
    # ccmod bug workaround: instantiate() renames Name="..." on collision but leaves the
    # ExportPath's own trailing "...GraphPath.<OldName>'" stale - only bites when the same
    # template is instantiated more than once into one target graph (first time all night).
    import re as _re
    n.begin_line = _re.sub(
        r"([:.])[A-Za-z0-9_]+(' *\")$",
        lambda m: m.group(1) + n.name + m.group(2),
        n.begin_line,
    )
    return n


KNOT_T = parse(open(CCMOD + r"\library\flow\knot.t3d", encoding="utf-8-sig").read())
knot_entry = add(KNOT_T)
for pn in ("InputPin", "OutputPin"):
    setf(knot_entry, pn, "PinType.PinCategory", '"exec"')
    setf(knot_entry, pn, "PinType.PinSubCategoryObject", "None")

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
# Location already carries the real Amadan coordinate verbatim from the cloned source, untouched.

asyncspawn = add(ASYNCSPAWN_T)
setf(asyncspawn, "WeightedTableID", "DefaultValue", '"Amadan"')

print_ok = add(PRINT_T)
setf(print_ok, "InString", "DefaultValue", '"AMADAN_ASYNCSPAWN: SpawnSucceeded"')
print_fail = add(PRINT_T)
setf(print_fail, "InString", "DefaultValue", '"AMADAN_ASYNCSPAWN: SpawnFailed"')

# --- exec spine ------------------------------------------------------------
connect(knot_entry, "OutputPin", gac, "execute")
connect_exec(gac, ite, "then", "execute")
connect_exec(ite, asyncspawn, "then", "execute")
connect_exec(asyncspawn, print_ok, "SpawnSucceeded", "execute")
connect_exec(asyncspawn, print_fail, "SpawnFailed", "execute")

# --- data --------------------------------------------------------------
connect(gac, "OutActors", arrlen, "TargetArray")
connect(arrlen, "ReturnValue", eq0, "A")
connect(eq0, "ReturnValue", ite, "Condition")
connect(maketransform, "ReturnValue", asyncspawn, "SpawnTransform")

out_path = MOD + r"\.ccmod\graphs\spawnamadan_asyncspawn_body.t3d"
open(out_path, "w", encoding="utf-8").write(g.render())
print("wrote", out_path, "-", len(g.nodes), "nodes")
