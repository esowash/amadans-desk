"""Chain AddToViewport -> Set Show Mouse Cursor -> Set Input Mode UI Only.

Plain linear extension of an EMPTY exec output pin (AddToViewport.then had no
existing link), so this is a single connection each step -- not the fan-out
pattern that needed a Sequence node last time.

Also: flip bShowMouseCursor's literal from false to true, and wire
InWidgetToFocus to CreateWidget's ReturnValue so keyboard input (typing into
KeepInput) routes to the panel, not just mouse clicks.
"""
import sys

CCMOD = r"<CCMOD_HOME>"
sys.path.insert(0, CCMOD)
from ccmod import db
from ccmod.t3d import parse, connect, connect_exec
from ccmod.workspace import Workspace

MOD = r"<MOD_ROOT>"

ws = Workspace.resolve()
conn = db.connect(ws.cache_db)


def load_graph(name):
    row = db.get_graph(conn, name)
    assert row, f"no saved graph '{name}'"
    return parse(row["t3d"])


g = load_graph("stocker/modcontroller_before_inputmode")
print("base graph nodes:", len(g.nodes))

addToViewport = g.by_name("K2Node_CallFunction_238")
createWidget = g.by_name("K2Node_CreateWidget_0")
setCursor = g.by_name("K2Node_VariableSet_0")
setInputMode = g.by_name("K2Node_CallFunction_417")

for n, pn in [(addToViewport, "then"), (setCursor, "execute"), (setInputMode, "execute")]:
    assert n.pin_by_name(pn).links == [], f"{n.name}.{pn} not empty as expected -- re-check topology"

connect_exec(addToViewport, setCursor, "then", "execute")
connect_exec(setCursor, setInputMode, "then", "execute")
connect(createWidget, "ReturnValue", setInputMode, "InWidgetToFocus")

cursorPin = setCursor.pin_by_name("bShowMouseCursor")
cursorPin._set("DefaultValue", '"true"')

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

out = MOD + r"\.ccmod\graphs\modcontroller_input_mode_splice.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"nodes: {len(g.nodes)}   wrote: {out}")
print(f"problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
