"""Stocker_ModController::ModDataTableOperations body.

Native override hook (already exists as an empty function on Stocker_ModController,
inherited from /Script/DreamworldMods.ModController) -- same shape Example_modcontroller
uses in its own ModDataTableOperations_FLX_TODO: 3 chained MergeDataTables calls,
one per table, merging OUR new mod-owned DataTables into the real base tables.

Self-contained fragment (entry untouched), 1 knot as the hand-wire landing point
per the user's standing feedback (route every entry hand-wire through a knot).
"""
import sys
import copy

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


def load_graph(name):
    row = db.get_graph(conn, name)
    assert row, f"no saved graph '{name}'"
    return parse(row["t3d"])


def tmpl_from(graph, name):
    n = copy.deepcopy(graph.by_name(name))
    for p in n.pins:
        p.links = []
    return Graph(nodes=[n])


def load_template(key):
    row = db.get_template(conn, key)
    assert row, f"no template '{key}'"
    graph = parse(row["t3d"])
    assert len(graph.nodes) == 1
    return tmpl_from(graph, graph.nodes[0].name)


g = Graph(nodes=[])


def add(t):
    return instantiate(t, g)[0]


def pin(n, name):
    p = n.pin_by_name(name)
    assert p, f"{n.name} has no pin {name}"
    return p


def setf(n, pn, k, raw):
    pin(n, pn)._set(k, raw)


exampleGraph = load_graph("stocker/example_modcontroller_full_merge_v2")
MERGE_T = tmpl_from(exampleGraph, "K2Node_CallFunction_1")   # the ItemTable merge call, as a shape template
KNOT_T = load_template("flow/knot")

# (MergeIntoDataTable stays the REAL base table; ToBeAddedDataTable is our new one)
TABLES = [
    ("/Game/Items/ItemTable.ItemTable", "/Game/Mods/Stocker/AmadanItem.AmadanItem"),
    ("/Game/Items/Recipes/RecipesTable.RecipesTable", "/Game/Mods/Stocker/AmadanRecipe.AmadanRecipe"),
    ("/Game/Items/Feats/FeatTable.FeatTable", "/Game/Mods/Stocker/AmadanFeat.AmadanFeat"),
]

calls = []
for base_path, mod_path in TABLES:
    call = add(MERGE_T)
    setf(call, "MergeIntoDataTable", "DefaultObject", f'"{base_path}"')
    setf(call, "ToBeAddedDataTable", "DefaultObject", f'"{mod_path}"')
    calls.append(call)

for a, b in zip(calls, calls[1:]):
    connect_exec(a, b, "then", "execute")

knot = add(KNOT_T)
setf(knot, "InputPin", "PinType.PinCategory", '"exec"')
setf(knot, "InputPin", "PinType.PinSubCategoryObject", "None")
setf(knot, "OutputPin", "PinType.PinCategory", '"exec"')
setf(knot, "OutputPin", "PinType.PinSubCategoryObject", "None")
connect_exec(knot, calls[0], "OutputPin", "execute")

# --- layout ------------------------------------------------------------------
knot.set_position(-150, 0)
for i, c in enumerate(calls):
    c.set_position(150 + i * 500, 0)

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

dangling = [(n.name, p.name) for n in g.nodes for p in n.pins if not p.links]
print("intentionally dangling (hand-wire point + hidden self pins):")
for nn, pn in dangling:
    print(f"  {nn}.{pn}")

out = MOD + r"\.ccmod\graphs\moddatatableoperations_body.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"\nnodes: {len(g.nodes)}   wrote: {out}")
print(f"problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
