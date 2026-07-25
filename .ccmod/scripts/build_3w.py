"""Author stocker_3w.t3d -- custom-name spike: GetBuildableName for each
managed container.

Operates on the FULL live graph (pull-edit-repaste), per stocker-full-graph-edits.

Tests whether GetBuildableName(ignoreCustomName=false) returns a player's
custom container name (e.g. a chest renamed to "Seeds" via its own in-game
UI) -- discovered by examining the save DB's `properties` table for a
newly-placed, renamed test chest (actor 85). Read-only, purely additive,
appended after 3V's true tail.
"""
import sys
import copy as _copy

CCMOD = r"<CCMOD_HOME>"
sys.path.insert(0, CCMOD)
from ccmod import db
from ccmod.t3d import parse, connect, connect_exec
from ccmod.t3d.generator import instantiate
from ccmod.t3d.model import Graph
from ccmod.workspace import Workspace

MOD = r"<MOD_ROOT>"
LIB = CCMOD + r"\library"
WLIB = MOD + r"\.ccmod\library"

PRE = "/Game/Systems/Building/Placeables/"
BASE_CONTAINER = PRE + "BP_PlaceableItemContainer.BP_PlaceableItemContainer_C"

ws = Workspace.resolve()
conn = db.connect(ws.cache_db)
row = conn.execute("SELECT t3d FROM graphs WHERE name=?", ("stocker_3w_base",)).fetchone()
assert row, "run `ccmod pull --save stocker_3w_base` first"
g = parse(row[0])
print("pulled nodes:", len(g.nodes))


def pin(n, name):
    p = n.pin_by_name(name)
    assert p, f"{n.name} has no pin {name}"
    return p


def tmpl_file(path):
    t = parse(open(path, encoding="utf-8-sig").read())
    for n in t.nodes:
        for p in n.pins:
            p.links = []
    return t


def add(t):
    return instantiate(t, g)[0]


def setf(n, pn, k, raw):
    pin(n, pn)._set(k, raw)


def setd(n, pn, v):
    setf(n, pn, "DefaultValue", f'"{v}"')


def bgc(path):
    return f'''"/Script/Engine.BlueprintGeneratedClass'{path}'"'''


def type_foreach(node, subobj_raw):
    setf(node, "Array", "PinType.PinCategory", '"object"')
    setf(node, "Array", "PinType.PinSubCategoryObject", subobj_raw)
    setf(node, "Array", "PinType.ContainerType", "Array")
    setf(node, "Array Element", "PinType.PinCategory", '"object"')
    setf(node, "Array Element", "PinType.PinSubCategoryObject", subobj_raw)
    setf(node, "Array Element", "PinType.ContainerType", "None")


def find_by_text(text):
    for n in g.nodes:
        isp = n.pin_by_name("InString")
        if isp and isp._get("DefaultValue") == f'"{text}"' and not isp.links:
            return n
    raise KeyError(text)


def literal_print_template():
    n = find_by_text("STOCKER_3N begin (storage-only candidates; benches excluded)")
    nn = _copy.deepcopy(n)
    for p in nn.pins:
        p.links = []
    return Graph(nodes=[nn])


PRINT_T = literal_print_template()

FEACH_T = None
for n in g.nodes:
    if n.class_path.endswith("K2Node_MacroInstance"):
        arr = n.pin_by_name("Array")
        if arr and arr.category == "object":
            nn = _copy.deepcopy(n)
            for p in nn.pins:
                p.links = []
            FEACH_T = Graph(nodes=[nn])
            break
assert FEACH_T

GDN_T = tmpl_file(LIB + r"\call\get_display_name.t3d")
GBN_T = tmpl_file(LIB + r"\actor\get_buildable_name.t3d")
C2S_T = tmpl_file(LIB + r"\actor\conv_text_to_string.t3d")
MCGET_T = tmpl_file(WLIB + r"\stocker\get_managed_containers.t3d")

tail = find_by_text("STOCKER_3V done")
assert not pin(tail, "then").links, "STOCKER_3V done.then not dangling -- already spliced?"

pLbl = add(PRINT_T)
setd(pLbl, "InString", "STOCKER_3W begin (custom-name spike)")

mcGet = add(MCGET_T)
fe = add(FEACH_T)
type_foreach(fe, bgc(BASE_CONTAINER))
connect(mcGet, "ManagedContainers", fe, "Array")

gdn = add(GDN_T)
connect(fe, "Array Element", gdn, "Object")
pInternal = add(PRINT_T)
setd(pInternal, "InString", "STOCKER_3W internal=")
connect(gdn, "ReturnValue", pInternal, "InString")

gbn = add(GBN_T)
connect(fe, "Array Element", gbn, "self")
setd(gbn, "ignoreCustomName", "false")
c2s = add(C2S_T)
connect(gbn, "ReturnValue", c2s, "InText")
pName = add(PRINT_T)
setd(pName, "InString", "STOCKER_3W name=")
connect(c2s, "ReturnValue", pName, "InString")

pDone = add(PRINT_T)
setd(pDone, "InString", "STOCKER_3W done")

connect_exec(tail, pLbl)
connect_exec(pLbl, fe, "then", "Exec")
connect_exec(fe, pInternal, "LoopBody", "execute")
connect_exec(pInternal, pName)
connect_exec(fe, pDone, "Completed", "execute")

pLbl.set_position(2400, 2500)
mcGet.set_position(2400, 2650)
fe.set_position(2660, 2500)
gdn.set_position(2920, 2350); pInternal.set_position(3180, 2350)
gbn.set_position(2920, 2650); c2s.set_position(3180, 2650); pName.set_position(3440, 2650)
pDone.set_position(2660, 2800)

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
         if p._get("PinType.PinCategory") == '"wildcard"'
         and not n.class_path.endswith("K2Node_CallArrayFunction")]
assert not wilds, f"unresolved wildcards: {wilds}"

out = MOD + r"\.ccmod\graphs\stocker_3w.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"nodes: {len(g.nodes)}   wrote: {out}")
print(f"non-reciprocal / dangling problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
