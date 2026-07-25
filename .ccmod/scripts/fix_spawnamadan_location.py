"""Fix SpawnAmadan's spawn location: it was anchored on the Desk (wrong - never confirmed with
the user), should be the Entertainer reference NPC's saved position instead (the notebook/journal
spot). Removes the whole Desk-anchor chain (GetAllActorsOfClass -> GetArrayItem ->
GetActorFeetLocation) and feeds the fixed coordinate straight into MakeTransform's Location pin.

Coordinate is actor 101's real saved position, extracted earlier this session from Game_0.db's
actor_position table: X=-99959.47512071289, Y=4180.127014764417, Z=-3758.6206208148874.
"""
import sys

CCMOD = r"<CCMOD_HOME>"
sys.path.insert(0, CCMOD)
from ccmod.t3d import parse

MOD = r"<MOD_ROOT>"

g = parse(open(MOD + r"\.ccmod\graphs\amadan_spawnamadan_live_v2.t3d", encoding="utf-8-sig").read())

DROP = {"K2Node_CallFunction_46", "K2Node_GetArrayItem_6", "K2Node_CallFunction_3"}
ite_node = next(n for n in g.nodes if n.name == "K2Node_IfThenElse_0")
spawn_node = next(n for n in g.nodes if n.name == "K2Node_SpawnActorFromClass_1")
maketransform_node = next(n for n in g.nodes if n.name == "K2Node_CallFunction_4")

ite_then = ite_node.pin_by_name("then", output=True)
spawn_exec = spawn_node.pin_by_name("execute", output=False)
location_pin = maketransform_node.pin_by_name("Location", output=False)

# rewire IfThenElse.then -> SpawnActorFromClass.execute directly (skip the removed Desk chain)
ite_then.links = [(spawn_node.name, spawn_exec.pin_id)]
spawn_exec.links = [(ite_node.name, ite_then.pin_id)]

# feed the fixed coordinate as a literal instead of the (now-removed) FeetLocation wire
location_pin.links = []
for i, (k, v) in enumerate(location_pin.fields):
    if k == "DefaultValue":
        location_pin.fields[i] = (k, '"-99959.475121, 4180.127015, -3758.620615"')

g.nodes = [n for n in g.nodes if n.name not in DROP]

out_path = MOD + r"\.ccmod\graphs\amadan_spawnamadan_fixed_location.t3d"
open(out_path, "w", encoding="utf-8").write(g.render())
print("wrote", out_path, "-", len(g.nodes), "nodes (dropped", len(DROP), ")")
