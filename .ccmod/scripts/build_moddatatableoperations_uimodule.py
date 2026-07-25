"""Add a 4th MergeDataTables call to ModDataTableOperations, pairing the real
DT_UIModuleTable with our new AmadanUIModule (one row: StockerHouseRules ->
W_StockerTestPanel, Category=Modal, mirroring the real SignTextInput row).
Same mechanism already proven for Item/Recipe/Feat -- chain the new call
after the existing 3rd call's dangling `then`.

Base: moddatatableoperations_body.t3d (the function body already live on
Stocker_ModController). K2Node_CallFunction_3 (Feat merge) is the last of
the 3 existing calls; its `then` is currently dangling -- that's the splice
point. New node cloned from CallFunction_3's own shape (same FunctionReference,
same self-context pattern) with MergeIntoDataTable/ToBeAddedDataTable swapped.
"""
import sys
import copy

CCMOD = r"<CCMOD_HOME>"
sys.path.insert(0, CCMOD)
from ccmod.t3d import parse, connect_exec
from ccmod.t3d.generator import instantiate
from ccmod.t3d.model import Graph

MOD = r"<MOD_ROOT>"


def tmpl_from(graph, name):
    n = copy.deepcopy(graph.by_name(name))
    for p in n.pins:
        p.links = []
    return Graph(nodes=[n])


def pin(n, name):
    p = n.pin_by_name(name)
    assert p, f"{n.name} has no pin {name}"
    return p


g = parse(open(MOD + r"\.ccmod\graphs\moddatatableoperations_body.t3d", encoding="utf-8").read())
print("base graph nodes:", len(g.nodes))

feat_merge = g.by_name("K2Node_CallFunction_3")
assert pin(feat_merge, "then").links == [], "expected CallFunction_3.then dangling"

MERGE_T = tmpl_from(g, "K2Node_CallFunction_3")
uimodule_merge = instantiate(MERGE_T, g)[0]

pin(uimodule_merge, "MergeIntoDataTable")._set(
    "DefaultObject", '"/Game/UI/Data/DataTables/DT_UIModuleTable.DT_UIModuleTable"')
pin(uimodule_merge, "ToBeAddedDataTable")._set(
    "DefaultObject", '"/Game/Mods/Stocker/AmadanUIModule.AmadanUIModule"')

connect_exec(feat_merge, uimodule_merge, "then", "execute")
uimodule_merge.set_position(1650, 0)

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

for nn, pn in [(feat_merge.name, "then"), (uimodule_merge.name, "execute")]:
    p = g.by_name(nn).pin_by_name(pn)
    if len(p.links) != 1:
        problems.append(f"{nn}.{pn} has {len(p.links)} links, expected exactly 1")

out = MOD + r"\.ccmod\graphs\moddatatableoperations_with_uimodule.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"\nnodes: {len(g.nodes)}   wrote: {out}")
print(f"problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
