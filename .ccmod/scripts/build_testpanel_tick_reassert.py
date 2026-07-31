"""Fight back every frame: bind Event Tick to keep re-forcing bShowMouseCursor
true for as long as W_StockerTestPanel is open, in case Conan's own camera/
pawn Tick resets it every frame (confirmed via ccmod's whole-game index that
NO real asset manually manages SetInputMode/ShowMouseCursor at all -- this is
uncharted territory the shipped game never does by hand, so no real idiom to
copy; this is a deliberate workaround, not a proven pattern).

Base: the pulled W_StockerTestPanel graph (20 nodes) -- user already added
Event Tick, GetOwningPlayer (pure, ReturnValue already wired to the new
VariableSet's self), and Set bShowMouseCursor, all via Context Sensitive
search. GetOwningPlayer needs no exec wiring (pure). Only wiring needed:
Tick.then -> VariableSet.execute, plus set the bool value to true.

Pre-existing SignalClicked -> AddKeepRule chain (via K2Node_ComponentBoundEvent_0
-> Knot_623 -> ...) is untouched -- confirmed by inspection before editing.
"""
import sys

import os, pathlib
CCMOD = os.environ.get("CCMOD_HOME") or str(pathlib.Path(__file__).resolve().parents[3] / "claude-conan-modder")
sys.path.insert(0, CCMOD)
from ccmod.t3d import parse, connect_exec

import pathlib
MOD = str(pathlib.Path(__file__).resolve().parents[2])


def pin(n, name):
    p = n.pin_by_name(name)
    assert p, f"{n.name} has no pin {name}"
    return p


g = parse(open(MOD + r"\.ccmod\graphs\testpanel_with_tick_pieces.t3d", encoding="utf-8").read())
print("base graph nodes:", len(g.nodes))

tick = g.by_name("K2Node_Event_3")
getOwningPlayer = g.by_name("K2Node_CallFunction_3")
setShowMouse = g.by_name("K2Node_VariableSet_0")
signalClicked = g.by_name("K2Node_ComponentBoundEvent_0")

# --- sanity: confirm the existing button chain is untouched ---------------------
assert pin(signalClicked, "then").links, "expected SignalClicked.then already wired -- did something change?"
assert pin(tick, "then").links == [], "expected Tick.then dangling"
assert pin(setShowMouse, "execute").links == [], "expected VariableSet execute dangling"
assert pin(getOwningPlayer, "ReturnValue").links == [
    (setShowMouse.name, pin(setShowMouse, "self").pin_id)], "expected GetOwningPlayer already feeding VariableSet.self"

# --- wire: Tick.then -> Set bShowMouseCursor(true) ------------------------------
connect_exec(tick, setShowMouse, "then", "execute")
pin(setShowMouse, "bShowMouseCursor")._set("DefaultValue", '"true"')

# --- validate --------------------------------------------------------------------
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

for nn, pn in [(tick.name, "then"), (setShowMouse.name, "execute")]:
    p = g.by_name(nn).pin_by_name(pn)
    if len(p.links) != 1:
        problems.append(f"{nn}.{pn} has {len(p.links)} links, expected exactly 1")

out = MOD + r"\.ccmod\graphs\testpanel_tick_reassert.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"\nnodes: {len(g.nodes)}   wrote: {out}")
print(f"problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
