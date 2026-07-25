"""Swap Set Input Mode UI Only for Set Input Mode Game And UI, chasing the
missing mouse cursor. Real captured signature (not assumed -- it has BOTH
bHideCursorDuringCapture AND bFlushInput, a superset of UIOnlyEx's params,
which I'd have gotten wrong if I'd hand-authored from the UIOnlyEx shape):
SetInputMode_GameAndUIEx(PlayerController, InWidgetToFocus, InMouseLockMode,
bHideCursorDuringCapture=true, bFlushInput=false).

bHideCursorDuringCapture defaults to true -- set it explicitly false, since
that's plausibly the exact flag suppressing our cursor (GameAndUI balances
game-capture vs UI, and this flag governs whether the cursor hides during
that capture; UIOnlyEx has no equivalent parameter at all, which may be part
of why it wasn't giving us a working cursor).

Base: amadan_gameandui_capture.t3d (11 nodes -- the current 10-node
hand-rolled chain plus the freshly captured, still-unconnected GameAndUIEx
node). Splice point: VariableSet_0 (Set Show Mouse Cursor).then, currently ->
CallFunction_417 (SetInputMode_UIOnlyEx); rewire to the new node instead and
drop the old one entirely.
"""
import sys

CCMOD = r"<CCMOD_HOME>"
sys.path.insert(0, CCMOD)
from ccmod.t3d import parse, connect, connect_exec

MOD = r"<MOD_ROOT>"


def pin(n, name):
    p = n.pin_by_name(name)
    assert p, f"{n.name} has no pin {name}"
    return p


g = parse(open(MOD + r"\.ccmod\graphs\amadan_gameandui_capture.t3d", encoding="utf-8").read())
print("base graph nodes:", len(g.nodes))

setShowMouse = g.by_name("K2Node_VariableSet_0")
oldInputMode = g.by_name("K2Node_CallFunction_417")
newInputMode = g.by_name("K2Node_CallFunction_2")
ignoreMove = g.by_name("K2Node_CallFunction_8")
createWidget = g.by_name("K2Node_CreateWidget_0")

showMouse_then = pin(setShowMouse, "then")
assert showMouse_then.links == [(oldInputMode.name, pin(oldInputMode, "execute").pin_id)]
oldInputMode_then = pin(oldInputMode, "then")
assert oldInputMode_then.links == [(ignoreMove.name, pin(ignoreMove, "execute").pin_id)]

# --- disconnect the old node from both sides, drop it entirely -----------------
showMouse_then.links = []
pin(oldInputMode, "execute").links = []
oldInputMode_then.links = []
pin(ignoreMove, "execute").links = []
pin(oldInputMode, "PlayerController").links = []
pin(oldInputMode, "InWidgetToFocus").links = []
# clear the reciprocal ends on the shared upstream nodes too
pin_pc = g.by_name("K2Node_CallFunction_239").pin_by_name("ReturnValue")
pin_pc.links = [lk for lk in pin_pc.links if lk[0] != oldInputMode.name]
pin_cw = createWidget.pin_by_name("ReturnValue")
pin_cw.links = [lk for lk in pin_cw.links if lk[0] != oldInputMode.name]

g.nodes = [n for n in g.nodes if n.name != oldInputMode.name]

# --- wire in the new node -------------------------------------------------------
connect_exec(setShowMouse, newInputMode, "then", "execute")
connect_exec(newInputMode, ignoreMove, "then", "execute")
connect(g.by_name("K2Node_CallFunction_239"), "ReturnValue", newInputMode, "PlayerController")
connect(createWidget, "ReturnValue", newInputMode, "InWidgetToFocus")
pin(newInputMode, "bHideCursorDuringCapture")._set("DefaultValue", '"false"')

newInputMode.set_position(1750, 0)

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

for nn, pn in [(setShowMouse.name, "then"), (newInputMode.name, "execute"),
               (newInputMode.name, "then"), (ignoreMove.name, "execute")]:
    p = g.by_name(nn).pin_by_name(pn)
    if len(p.links) != 1:
        problems.append(f"{nn}.{pn} has {len(p.links)} links, expected exactly 1")

out = MOD + r"\.ccmod\graphs\amadan_interact_gameandui.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"\nnodes: {len(g.nodes)}   wrote: {out}")
print(f"problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
