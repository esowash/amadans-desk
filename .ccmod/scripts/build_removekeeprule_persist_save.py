r"""Add a persistence Save() call to RemoveKeepRule, right after its one success terminal.

Full pull+edit+repaste onto the live graph (removekeeprule_live_s19_persist.t3d), traced
this session: FunctionEntry -> IsValidIndex gate -> then: Array_Remove -> CallFunction_0
("MENU_RULESLIST: rule removed", dangling .then -- the correct splice point) / else:
CallFunction_1 ("invalid index, nothing removed", a FAILURE path, correctly gets no Save()).

Same real captured precedent as AddKeepRule's persistence fix: persistence_dragoff_s19.t3d
(self-context PersistenceComponent VariableGet + parameterless Save() call).
"""
import copy
import sys

import os, pathlib
CCMOD = os.environ.get("CCMOD_HOME") or str(pathlib.Path(__file__).resolve().parents[3] / "claude-conan-modder")
sys.path.insert(0, CCMOD)
from ccmod.t3d import parse, connect, connect_exec
from ccmod.t3d.generator import instantiate
from ccmod.t3d.model import Graph

import pathlib
MOD = str(pathlib.Path(__file__).resolve().parents[2])

g = parse(open(MOD + r"\.ccmod\graphs\removekeeprule_live_s19_persist.t3d", encoding="utf-8-sig").read())
persist_src = parse(open(MOD + r"\.ccmod\graphs\persistence_dragoff_s19.t3d", encoding="utf-8-sig").read())


def pin(n, name, output=None):
    p = n.pin_by_name(name, output=output)
    assert p, f"{n.name} has no pin {name}"
    return p


def add(t):
    return instantiate(t, g)[0]


def clone_from(src_graph, name):
    n = copy.deepcopy(src_graph.by_name(name))
    for p in n.pins:
        p.links = []
    return Graph(nodes=[n])


successPrint = g.by_name("K2Node_CallFunction_0")  # "MENU_RULESLIST: rule removed"
assert pin(successPrint, "then", output=True).links == [], "expected this to still be dangling"

persistGet = add(clone_from(persist_src, "K2Node_VariableGet_0"))
saveCall = add(clone_from(persist_src, "K2Node_CallFunction_1"))

connect(persistGet, "PersistenceComponent", saveCall, "self")
connect_exec(successPrint, saveCall, "then", "execute")

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

out = MOD + r"\.ccmod\graphs\removekeeprule_persist_save.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"nodes: {len(g.nodes)}   wrote: {out}")
print(f"problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
