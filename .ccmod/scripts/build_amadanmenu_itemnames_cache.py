r"""Swap the item-populate loop's AddOption(ItemDropdown) call for Array_Add(ItemNames, name) --
ItemDropdown is going away (replaced by the search box + 8 result rows), but the friendly-name
resolution work the loop already does per row is exactly what the type-ahead filter needs cached.

Full pull+edit+repaste of the REAL live Construct graph (pulled fresh this session as
amadanmenu_for_typeahead.t3d, 26 nodes) -- removes K2Node_CallFunction_123 (AddOption) and
K2Node_VariableGet_43 (ItemDropdown self-get) entirely, replaces with a second Array_Add call
(ItemNames) chained where AddOption used to be, feeding the SAME Conv_TextToString output that
used to go into AddOption.Option. The existing Array_Add(ItemTemplateIDs) call right after is
untouched, just now chained from the new node instead of the deleted AddOption.

Order deliberately kept safe: this graph edit removes the reference to ItemDropdown BEFORE the
widget itself gets deleted from the tree (paste this, compile clean with ItemDropdown now just an
unused orphaned widget, THEN delete the old widget and paste the search-box replacement -- never
the other order, which would leave the graph referencing a deleted variable).
"""
import sys

CCMOD = r"<CCMOD_HOME>"
sys.path.insert(0, CCMOD)
from ccmod import db
from ccmod.t3d import parse, connect, connect_exec
from ccmod.t3d.generator import instantiate
from ccmod.t3d.model import Graph
from ccmod.workspace import Workspace

MOD = r"<MOD_ROOT>"
LIB = CCMOD + r"\library"

ws = Workspace.resolve()
conn = db.connect(ws.cache_db)
row = db.get_graph(conn, "amadanmenu_for_typeahead")
assert row, "run `ccmod pull --save amadanmenu_for_typeahead` first"
g = parse(row["t3d"])


def by_name(name):
    n = g.by_name(name)
    assert n, f"missing node {name}"
    return n


def pin(n, name, output=None):
    p = n.pin_by_name(name, output=output)
    assert p, f"{n.name} has no pin {name}"
    return p


def setf(n, pn, k, raw, output=None):
    pin(n, pn, output=output)._set(k, raw)


def add(t):
    return instantiate(t, g)[0]


def tmpl_file(path):
    t = parse(open(path, encoding="utf-8-sig").read())
    for n in t.nodes:
        for p in n.pins:
            p.links = []
    return t


ARRAY_ADD_T = tmpl_file(LIB + r"\array\array_add.t3d")

gnft = by_name("K2Node_CallFunction_GNFT")
t2s = by_name("K2Node_CallFunction_119")            # Conv_TextToString (friendly name -> string)
oldAddOpt = by_name("K2Node_CallFunction_123")       # AddOption(ItemDropdown) -- being removed
oldDropdownGet = by_name("K2Node_VariableGet_43")    # ItemDropdown self-get -- being removed
arrAddIDs = by_name("K2Node_CallArrayFunction_2")    # Array_Add(ItemTemplateIDs) -- kept as-is

# --- remove the two dead nodes -----------------------------------------------------------------
g.nodes = [n for n in g.nodes if n is not oldAddOpt and n is not oldDropdownGet]

# --- new: ItemNames self-get + Array_Add ---------------------------------------------------------
# (reuse the same self-get shape already proven this session -- pull it from the same eventgraph
# capture used for every other self-context widget/array get tonight)
EVENTGRAPH_SRC = MOD + r"\.ccmod\graphs\menu_w_amadanmenu_eventgraph.t3d"
eventgraph_src = parse(open(EVENTGRAPH_SRC, encoding="utf-8-sig").read())
import copy as _copy
def tmpl_from(graph, name):
    n = _copy.deepcopy(graph.by_name(name))
    for p in n.pins:
        p.links = []
    return Graph(nodes=[n])
SELFGET_T = tmpl_from(eventgraph_src, "K2Node_VariableGet_0")

namesGet = add(SELFGET_T)
namesGet._replace_prop("VariableReference", '(MemberName="ItemNames",bSelfContext=True)')
p = pin(namesGet, "MultiLineEditableTextBox_74", output=True)
p._set("PinName", '"ItemNames"')
p._set("PinType.PinCategory", '"string"')
p._set("PinType.PinSubCategoryObject", "None")
p._set("PinType.ContainerType", "Array")

arrAddNames = add(ARRAY_ADD_T)
setf(arrAddNames, "TargetArray", "PinType.PinCategory", '"string"')
setf(arrAddNames, "TargetArray", "PinType.PinSubCategoryObject", "None")
setf(arrAddNames, "TargetArray", "PinType.ContainerType", "Array")
setf(arrAddNames, "NewItem", "PinType.PinCategory", '"string"')
setf(arrAddNames, "NewItem", "PinType.PinSubCategoryObject", "None")
connect(namesGet, "ItemNames", arrAddNames, "TargetArray")
pin(t2s, "ReturnValue", output=True).links = []  # clear the stale link to the deleted AddOption node
connect(t2s, "ReturnValue", arrAddNames, "NewItem")

# --- rewire exec: GNFT.then -> arrAddNames.execute -> then -> arrAddIDs.execute -----------------
pin(gnft, "then", output=True).links = []
pin(arrAddIDs, "execute", output=False).links = []
connect_exec(gnft, arrAddNames, "then", "execute")
connect_exec(arrAddNames, arrAddIDs, "then", "execute")

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

wilds = [(n.name, p.name) for n in g.nodes for p in n.pins
         if p._get("PinType.PinCategory") == '"wildcard"']
assert not wilds, f"unresolved wildcards: {wilds}"

out = MOD + r"\.ccmod\graphs\amadanmenu_itemnames_cache.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"nodes: {len(g.nodes)}   wrote: {out}")
print(f"problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
