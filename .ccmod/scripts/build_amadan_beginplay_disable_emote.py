"""Diagnostic: temporarily strip HumanoidNPC_Character_Amadan's BeginPlay down to a bare
ReceiveBeginPlay event with nothing wired - disables the Delay(0.5s)->StartEmote(SleepOnGround)
chain entirely, to test whether forcing that emote on a character with no resolved anim instance
is what's causing full invisibility (session 21 finding: today's playtest was invisible while
alive, whereas session 19's playtest of the same plain SpawnActorFromClass spawn - before this
emote-forcing BeginPlay existed - was visible with default appearance). Not a permanent removal;
StartEmote logic stays on file in amadan_class_beginplay_live_s21.t3d to re-add once appearance
is fixed for real.
"""
import sys, copy, pathlib

CCMOD = str(pathlib.Path(__file__).resolve().parents[3] / "claude-conan-modder")
sys.path.insert(0, CCMOD)
from ccmod.t3d import parse
from ccmod.t3d.model import Graph

MOD = str(pathlib.Path(__file__).resolve().parents[2])

SRC_PATH = MOD + r"\.ccmod\graphs\amadan_class_beginplay_live_s21.t3d"
src = parse(open(SRC_PATH, encoding="utf-8-sig").read())

event = copy.deepcopy(next(n for n in src.nodes if n.name == "K2Node_Event_3"))
event.pin_by_name("then", output=True).links = []

g = Graph(nodes=[event])

out_path = MOD + r"\.ccmod\graphs\amadan_beginplay_emote_disabled_s21.t3d"
open(out_path, "w", encoding="utf-8").write(g.render())
print("wrote", out_path, "-", len(g.nodes), "nodes")
