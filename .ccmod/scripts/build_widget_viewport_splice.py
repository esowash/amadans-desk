"""Splice Create Widget -> Add to Viewport onto Stocker_ModController's BeginPlay.

Full pull-edit-repaste of the whole EventGraph (155 nodes) -- NOT a hand-wired
delta. Reason: this requires fanning BeginPlay.then out to a SECOND
destination while its existing link (into the gather/tidy chain) stays
untouched. This project already got burned once doing that as a manual GUI
drag (it replaced the existing link instead of adding alongside it -- see the
session-7 note in stocker-current-state.md) so the fan-out is done here, in
code, as an explicit pin.links.append -- unambiguous, no GUI risk.

The 3 new nodes (K2Node_CreateWidget, AddToViewport call, GetPlayerController)
were captured live from THIS exact graph, so their auto-generated names are
already guaranteed unique within it -- safe to merge in directly, no renaming.
CreateWidget.then -> AddToViewport.execute was already wired by the user at
capture time and is kept untouched; this script only adds the 2 missing data
wires (OwningPlayer, AddToViewport.self) plus the BeginPlay fan-out.
"""
import sys

CCMOD = r"<CCMOD_HOME>"
sys.path.insert(0, CCMOD)
from ccmod import db
from ccmod.t3d import parse, connect
from ccmod.workspace import Workspace

MOD = r"<MOD_ROOT>"

ws = Workspace.resolve()
conn = db.connect(ws.cache_db)


def load_graph(name):
    row = db.get_graph(conn, name)
    assert row, f"no saved graph '{name}'"
    return parse(row["t3d"])


g = load_graph("stocker/modcontroller_eventgraph_full")
print("base graph nodes:", len(g.nodes))

# The 3 new nodes are already live in this pull (placed before the user copied
# the whole graph) -- no merge needed, just look them up.
createWidget = g.by_name("K2Node_CreateWidget_0")
addToViewport = g.by_name("K2Node_CallFunction_238")
gpc = g.by_name("K2Node_CallFunction_239")
beginPlay = g.by_name("K2Node_Event_0")
assert beginPlay.pin_by_name("then").links == [("K2Node_CallFunction_25", "D8FAB3EA147446279A60A7288A9EA314")], \
    "BeginPlay.then no longer points where expected -- re-check topology before fanning out"

# --- the 2 missing data wires ------------------------------------------------
connect(gpc, "ReturnValue", createWidget, "OwningPlayer")
connect(createWidget, "ReturnValue", addToViewport, "self")

# --- the fan-out: BeginPlay.then gets a SECOND destination, existing one kept -
# (Pin.links is a property that re-parses from raw text each access -- must use
# add_link(), which does get -> mutate -> set-back, not list.append() on the
# throwaway list a bare `.links` read returns.)
bp_then = beginPlay.pin_by_name("then")
cw_exec = createWidget.pin_by_name("execute")
bp_then.add_link(createWidget.name, cw_exec.pin_id)
cw_exec.add_link(beginPlay.name, bp_then.pin_id)

# --- layout: tuck the new chain near where the user placed it already --------
# (positions already set from capture; no repositioning needed)

# --- validate ------------------------------------------------------------------
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

assert beginPlay.pin_by_name("then").links == [
    ("K2Node_CallFunction_25", "D8FAB3EA147446279A60A7288A9EA314"),
    (createWidget.name, cw_exec.pin_id),
], "fan-out didn't land as expected"

out = MOD + r"\.ccmod\graphs\modcontroller_widget_viewport_splice.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"nodes: {len(g.nodes)}   wrote: {out}")
print(f"problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
