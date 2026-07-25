"""Full pull+edit+repaste of Menu_ModController's BeginPlay: add a third parallel branch off
the existing K2Node_ExecutionSequence_0 (same node that already forks into the RunSweep timer
setup and the persistence IsDataDoneLoading poll) that calls SpawnAmadan() once.

Per this project's own standing rule (session 18's Construct-placement bug): never ask the user
to hand-place a node near an internal T3D node name they can't see in the GUI - always repaste the
whole edited region instead. This edits the LIVE pulled BeginPlay graph directly (not a fresh
synthesis) and hands back the complete 14-node graph for a full select-all-delete-paste.

The new self-call node is cloned from a REAL self-call already captured this session
(ModDataTableOperations' own MergeDataTables self-calls, amadan_moddatatableops.t3d) - same
bSelfContext=True pattern already proven to compile clean - with its two data pins (which
SpawnAmadan doesn't have) stripped, retargeted to call "SpawnAmadan" instead.
"""
import sys
import uuid
import copy

CCMOD = r"<CCMOD_HOME>"
sys.path.insert(0, CCMOD)
from ccmod.t3d import parse
from ccmod.t3d.model import Node

MOD = r"<MOD_ROOT>"

MENU_MC_BGC = '''"/Script/Engine.BlueprintGeneratedClass'/Game/Mods/Menu/Menu_ModController.Menu_ModController_C'"'''


def new_guid():
    return uuid.uuid4().hex.upper()


beginplay = parse(open(MOD + r"\.ccmod\graphs\amadan_beginplay_current.t3d", encoding="utf-8-sig").read())
moddt = parse(open(MOD + r"\.ccmod\graphs\menu_moddatatableops_s19.t3d", encoding="utf-8-sig").read())

# --- find the ExecutionSequence and its then_1 pin (template for the new then_2) -------------
seq_node = None
for n in beginplay.nodes:
    if "K2Node_ExecutionSequence" in n.begin_line:
        seq_node = n
        break
assert seq_node, "ExecutionSequence not found"

then1 = seq_node.pin_by_name("then_1")
assert then1, "then_1 pin not found"

then2 = copy.deepcopy(then1)
then2.pin_id = new_guid()
then2.links = []
for i, (k, v) in enumerate(then2.fields):
    if k == "PinName":
        then2.fields[i] = (k, '"then_2"')

seq_node.body.append(("pin", then2))

# --- clone a real self-call node (MergeDataTables) and retarget to SpawnAmadan ---------------
src_call = None
for n in moddt.nodes:
    raw_text = " ".join(t for k, t in n.body if k == "raw")
    if 'MemberName="MergeDataTables"' in raw_text:
        src_call = copy.deepcopy(n)
        break
assert src_call, "MergeDataTables self-call not found"

new_node_name = f"K2Node_CallFunction_SpawnAmadan_{new_guid()[:8]}"
src_call.name = new_node_name
src_call.begin_line = (
    f'Begin Object Class=/Script/BlueprintGraph.K2Node_CallFunction Name="{new_node_name}" '
    f'ExportPath="/Script/BlueprintGraph.K2Node_CallFunction\'/Game/Mods/Menu/Menu_ModController.'
    f"Menu_ModController:EventGraph.{new_node_name}'\""
)

# retarget the function reference
new_body = []
for k, v in src_call.body:
    if k == "raw" and v.strip().startswith("FunctionReference="):
        new_body.append((k, '   FunctionReference=(MemberName="SpawnAmadan",bSelfContext=True)'))
    elif k == "raw" and v.strip().startswith("NodeGuid="):
        new_body.append((k, f"   NodeGuid={new_guid()}"))
    elif k == "pin":
        if v.name in ("execute", "then", "self"):
            new_body.append((k, v))
        # drop MergeIntoDataTable / ToBeAddedDataTable - SpawnAmadan takes no params
    else:
        new_body.append((k, v))
src_call.body = new_body

for p in src_call.pins:
    p.links = []
    p.pin_id = new_guid()
    if p.name == "self":
        for i, (k, v) in enumerate(p.fields):
            if k == "PinType.PinSubCategoryObject":
                p.fields[i] = (k, MENU_MC_BGC)

exec_pin = src_call.pin_by_name("execute")

# --- wire then_2 -> new node's execute ---------------------------------------------------------
then2.add_link(new_node_name, exec_pin.pin_id)
exec_pin.add_link("K2Node_ExecutionSequence_0", then2.pin_id)

beginplay.nodes.append(src_call)

out_path = MOD + r"\.ccmod\graphs\menu_beginplay_spawnamadan_spliced.t3d"
open(out_path, "w", encoding="utf-8").write(beginplay.render())
print("wrote", out_path, "-", len(beginplay.nodes), "nodes")
