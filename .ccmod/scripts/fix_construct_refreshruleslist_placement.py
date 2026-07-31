r"""Fix Construct: the user's hand-added RefreshRulesList() call landed inside the item-table
populate loop's per-iteration body (fed by an Array_Add that fires once per ItemTable row --
thousands of times), not after the bench-populate loop finishes. Rebuilds the whole Construct
chain (26 nodes, pulled fresh as amadanmenu_construct_wrong_refresh -- this particular copy
predates the bad add entirely, so nothing to remove) with a NEW RefreshRulesList call correctly
wired to K2Node_MacroInstance_2's Completed pin (the ManagedStations/bench-populate loop's real,
once-only branch tail).

RefreshRulesList call node cloned from a REAL, already-working, already-compiled instance
(K2Node_CallFunction_339, the SaveButton's copy, pulled from amadanmenu_eventgraph_full_s18end)
-- carries the real MemberGuid, so no name-resolution risk at all this time.

Includes K2Node_Event_0 (the Construct override) in the repaste -- confirmed safe in this project
(unlike K2Node_FunctionEntry/FunctionResult, event overrides paste fine; this project has done
full Construct-chain delete+repaste before, e.g. testpanel_construct_stripped_postpaste.t3d).
"""
import copy
import sys

import os, pathlib
CCMOD = os.environ.get("CCMOD_HOME") or str(pathlib.Path(__file__).resolve().parents[3] / "claude-conan-modder")
sys.path.insert(0, CCMOD)
from ccmod import db
from ccmod.t3d import parse, connect_exec
from ccmod.t3d.generator import instantiate
from ccmod.t3d.model import Graph
from ccmod.workspace import Workspace

import pathlib
MOD = str(pathlib.Path(__file__).resolve().parents[2])

ws = Workspace.resolve()
conn = db.connect(ws.cache_db)

row = db.get_graph(conn, "amadanmenu_construct_wrong_refresh")
assert row, "run the pull first"
g = parse(row["t3d"])

real_row = db.get_graph(conn, "amadanmenu_eventgraph_full_s18end")
assert real_row
real_g = parse(real_row["t3d"])


def by_name(name):
    n = g.by_name(name)
    assert n, f"missing {name}"
    return n


real_call = copy.deepcopy(real_g.by_name("K2Node_CallFunction_339"))
for p in real_call.pins:
    p.links = []
newRefresh = instantiate(Graph(nodes=[real_call]), g)[0]
newRefresh.set_position(-200, 2600)

macroInst2 = by_name("K2Node_MacroInstance_2")
connect_exec(macroInst2, newRefresh, "Completed", "execute")

# --- validate --------------------------------------------------------------------------------
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

out = MOD + r"\.ccmod\graphs\amadanmenu_construct_with_refresh_fixed.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"nodes: {len(g.nodes)}   wrote: {out}")
print(f"problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
