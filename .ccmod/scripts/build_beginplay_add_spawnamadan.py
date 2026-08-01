"""Re-add a SpawnAmadan() self-call into Menu_ModController::BeginPlay, chained in front of the
existing SpawnAmadanNotebook() self-call on the ExecutionSequence's 3rd branch (then_2) - the same
real slot SpawnAmadan used to occupy before it was deleted. Full pull+edit+repaste of the whole
BeginPlay graph (15 nodes -> 16), per this project's standing full-graph-edit rule.

New self-call node cloned from the ALREADY-LIVE SpawnAmadanNotebook self-call node in this same pull
(K2Node_CallFunction_SpawnAmadan_18135A4D_1) - same technique as gotcha #20: retarget MemberName only,
omit MemberGuid, let UE resolve by name.
"""
import sys, copy, pathlib

CCMOD = str(pathlib.Path(__file__).resolve().parents[3] / "claude-conan-modder")
sys.path.insert(0, CCMOD)
from ccmod.t3d import parse, connect, connect_exec
from ccmod.t3d.generator import instantiate
from ccmod.t3d.model import Graph

MOD = str(pathlib.Path(__file__).resolve().parents[2])

SRC_PATH = MOD + r"\.ccmod\graphs\modcontroller_beginplay_live_s21.t3d"
src = parse(open(SRC_PATH, encoding="utf-8-sig").read())

g = Graph(nodes=[copy.deepcopy(n) for n in src.nodes])

by_name = {n.name: n for n in g.nodes}
seq = by_name["K2Node_ExecutionSequence_0"]
notebook_call = by_name["K2Node_CallFunction_SpawnAmadan_18135A4D_1"]

# Clone the notebook self-call as a template for the new SpawnAmadan self-call.
tmpl = copy.deepcopy(notebook_call)
for p in tmpl.pins:
    p.links = []
TEMPLATE = Graph(nodes=[tmpl])

spawn_amadan = instantiate(TEMPLATE, g)[0]
# Retarget: MemberName only, no MemberGuid - resolves by name (gotcha #20).
for i, (kind, text) in enumerate(spawn_amadan.body):
    if kind == "raw" and text.strip().startswith("FunctionReference="):
        spawn_amadan.body[i] = (kind, 'FunctionReference=(MemberName="SpawnAmadan",bSelfContext=True)')

# --- rewire: seq.then_2 -> spawn_amadan.execute -> spawn_amadan.then -> notebook_call.execute ---
then2 = seq.pin_by_name("then_2")
assert then2, "ExecutionSequence has no then_2 pin"
then2.links = []
notebook_exec = notebook_call.pin_by_name("execute")
notebook_exec.links = []

connect_exec(seq, spawn_amadan, "then_2", "execute")
connect_exec(spawn_amadan, notebook_call, "then", "execute")

out_path = MOD + r"\.ccmod\graphs\beginplay_add_spawnamadan_s21.t3d"
open(out_path, "w", encoding="utf-8").write(g.render())
print("wrote", out_path, "-", len(g.nodes), "nodes")
