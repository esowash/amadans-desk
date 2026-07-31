"""Fix the invisible-Amadan/no-nameplate bug: his own class BeginPlay calls StartEmote(SleepOnGround)
immediately on ReceiveBeginPlay, but the async spawn pipeline (AsyncSpawnNPCFromWeightedTable) hasn't
finished applying his CharacterLayout/mesh/AnimInstance by that point yet - confirmed via the real
log error "No animation instance found on skeletal mesh component: CharacterMesh0 on character:
Amadan when starting emote: 55". Same category of race that started this whole detour
(SpawnActorFromClass+SetCharacterSpawnTableID timing), just one step later in the pipeline.

Fix: insert a short Delay between ReceiveBeginPlay and StartEmote, giving mesh/anim setup time to
land first - same "deferred delay dodges a native setup race" workaround this project has used
before (amadan_delayhack_* precedents from the Stocker era interact-menu investigation).
"""
import sys
import copy

import os, pathlib
CCMOD = os.environ.get("CCMOD_HOME") or str(pathlib.Path(__file__).resolve().parents[3] / "claude-conan-modder")
sys.path.insert(0, CCMOD)
from ccmod.t3d import parse, connect
from ccmod.t3d.generator import instantiate
from ccmod.t3d.model import Graph

import pathlib
MOD = str(pathlib.Path(__file__).resolve().parents[2])


def find_template_by_raw(src_graph, needle):
    for n in src_graph.nodes:
        raw = " ".join(t for k, t in n.body if k == "raw")
        if needle in raw:
            nn = copy.deepcopy(n)
            for p in nn.pins:
                p.links = []
            return Graph(nodes=[nn])
    raise KeyError(needle)


def pin(n, name, output=None):
    p = n.pin_by_name(name, output=output)
    assert p, f"{n.name} has no pin {name}"
    return p


def setf(n, pn, k, raw, output=None):
    pin(n, pn, output=output)._set(k, raw)


live_src = parse(open(MOD + r"\.ccmod\graphs\amadan_class_beginplay_s20.t3d", encoding="utf-8-sig").read())
delay_src = parse(open(MOD + r"\.ccmod\graphs\amadan_beginplay_current.t3d", encoding="utf-8-sig").read())

DELAY_T = find_template_by_raw(delay_src, 'MemberName="Delay"')

g = parse(open(MOD + r"\.ccmod\graphs\amadan_class_beginplay_s20.t3d", encoding="utf-8-sig").read())

event = [n for n in g.nodes if "ReceiveBeginPlay" in " ".join(t for k, t in n.body if k == "raw")][0]
startemote = [n for n in g.nodes if "MemberName=\"StartEmote\"" in " ".join(t for k, t in n.body if k == "raw")][0]

# Sever the direct ReceiveBeginPlay -> StartEmote link before splicing the Delay in between.
event_then = pin(event, "then", output=True)
startemote_exec = pin(startemote, "execute", output=False)
event_then.links = [l for l in event_then.links if l[0] != startemote.name]
startemote_exec.links = [l for l in startemote_exec.links if l[0] != event.name]

[delay] = instantiate(DELAY_T, g)
setf(delay, "Duration", "DefaultValue", '"0.500000"')

connect(event, "then", delay, "execute")
connect(delay, "then", startemote, "execute")

out_path = MOD + r"\.ccmod\graphs\amadan_startemote_delay_body.t3d"
open(out_path, "w", encoding="utf-8").write(g.render())
print("wrote", out_path, "-", len(g.nodes), "nodes")
