"""Add the actual missing registration step to SpawnAmadan: GenerateUniqueID -> SetUniqueID,
chained between FinishAsyncTrySpawnNPCFromSpawnTableLowLevel and ConfigureSpawnedNPC.

Root cause confirmed empirically by querying the live save DB directly: Amadan Cnoic has NO row in
the `characters` table at all (only the player character does), even after both prior finalization
fixes - he's a live "ghost" actor that was never registered as a real, persistent, DB-tracked
character. This likely explains both the earlier Smart-Object "no valid UID" errors AND why the
native appearance/mesh-application pipeline (probably gated on the character being a real registered
entity) never fires for him - the log shows zero "Recreating Clothing Actors" lines for him, ever,
across the whole session, unlike every other character.

Real chain cloned verbatim from Corpse.uasset's own EventGraph (a base-game character that legitimately
needs a fresh UID at creation time, same situation as us): GenerateUniqueID(WorldContextObject,
auto-hidden) -> ReturnValue -> SetUniqueID(actor=<the character>, uid=ReturnValue). actor wired from
FinishAsyncTrySpawnNPCFromSpawnTableLowLevel's own NPC output (ConanCharacter, upcasts cleanly to
SetUniqueID's Actor-typed actor param, no cast node needed).
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


def pin(n, name, output=None):
    p = n.pin_by_name(name, output=output)
    assert p, f"{n.name} has no pin {name}"
    return p


raw = open(MOD + r"\.ccmod\graphs\spawnamadan_configurenpc_live_s20.t3d", encoding="utf-8-sig").read()
g = parse(raw)

corpse_src = parse(open(MOD + r"\.ccmod\graphs\corpse_live_s20.t3d", encoding="utf-8-sig").read())
generate_src = [n for n in corpse_src.nodes if n.name == "K2Node_CallFunction_324"][0]
setid_src = [n for n in corpse_src.nodes if n.name == "K2Node_CallFunction_322"][0]

gen_template_node = copy.deepcopy(generate_src)
for p in gen_template_node.pins:
    p.links = []
[generate] = instantiate(Graph(nodes=[gen_template_node]), g)

setid_template_node = copy.deepcopy(setid_src)
for p in setid_template_node.pins:
    p.links = []
[setid] = instantiate(Graph(nodes=[setid_template_node]), g)

finish = [n for n in g.nodes if n.name == "K2Node_CallFunction_1447"][0]
configure = [n for n in g.nodes if n.name == "K2Node_CallFunction_1439"][0]

finish_then = pin(finish, "then", output=True)
configure_exec = pin(configure, "execute", output=False)
finish_then.links = [l for l in finish_then.links if l[0] != configure.name]
configure_exec.links = [l for l in configure_exec.links if l[0] != finish.name]

connect(finish, "then", generate, "execute")
connect(generate, "then", setid, "execute")
connect(setid, "then", configure, "execute")
connect(finish, "NPC", setid, "actor")
connect(generate, "ReturnValue", setid, "uid")

out_path = MOD + r"\.ccmod\graphs\spawnamadan_uniqueid_body.t3d"
open(out_path, "w", encoding="utf-8").write(g.render())
print("wrote", out_path, "-", len(g.nodes), "nodes")
