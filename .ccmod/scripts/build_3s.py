"""Author stocker_3s.t3d -- multi-station STEP A: gather ManagedStations.

Operates on the FULL live graph (pull-edit-repaste), per stocker-full-graph-edits.

Purely additive, read-only report -- does NOT touch pass 1, pass 2, or any
existing behaviour. The gather loop's storage-filter Branch (brStore) already
sorts every in-range container into two buckets; the `then` (is storage)
branch has fed ManagedContainers since 3N, but the `else` (NOT storage)
branch has been dangling the whole time. This just wires that dangling branch
into a NEW parallel array, ManagedStations -- benches/furnaces/forges/kilns,
naming-agnostic (per the multi-station design note: don't enumerate by class,
use the complement of the storage filter).

ManagedStations shares BP_PlaceableItemContainer's element type -- confirmed
via source-uasset ParentClass grep that BP_PL_CraftingStation_Wood and
BP_PL_CraftingStation_Furnace both descend through BP_PL_Crafting_Station,
whose own ParentClass IS BP_PlaceableItemContainer_C. Same type as
ManagedContainers, no new class needed.

Reports what it finds (count + display names) right before pass 1 begins, so
the log can be eyeballed for sanity (in particular: does it sweep up altars/
beds/the desk, and if so, does that look right?) BEFORE step B (restructuring
pass 1 to actually iterate this list) gets built on top of it.
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
WLIB = MOD + r"\.ccmod\library"

PRE = "/Game/Systems/Building/Placeables/"
BASE_CONTAINER = PRE + "BP_PlaceableItemContainer.BP_PlaceableItemContainer_C"

ws = Workspace.resolve()
conn = db.connect(ws.cache_db)
row = conn.execute("SELECT t3d FROM graphs WHERE name=?", ("stocker_3s_base",)).fetchone()
assert row, "run `ccmod pull --save stocker_3s_base` first"
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


brStore = g.by_name("K2Node_IfThenElse_1")
feGather = g.by_name("K2Node_MacroInstance_4")
arradd_containers = g.by_name("K2Node_CallArrayFunction_2")
gacWood = g.by_name("K2Node_CallFunction_10")

assert not pin(brStore, "else").links, "brStore.else not dangling -- already wired?"
assert pin(gacWood, "then").links[0][0] == "K2Node_CallFunction_6"

PRINT_T = None


def literal_print_template():
    n = find_by_text("STOCKER_3N begin (storage-only candidates; benches excluded)")
    import copy
    nn = copy.deepcopy(n)
    for p in nn.pins:
        p.links = []
    return Graph(nodes=[nn])


PRINT_T = literal_print_template()

FEACH_T = None
for n in g.nodes:
    if n.class_path.endswith("K2Node_MacroInstance"):
        arr = n.pin_by_name("Array")
        if arr and arr.category == "object":
            import copy
            nn = copy.deepcopy(n)
            for p in nn.pins:
                p.links = []
            FEACH_T = Graph(nodes=[nn])
            break
assert FEACH_T

CONV_T = None
for n in g.nodes:
    raw = " ".join(t for k, t in n.body if k == "raw")
    if 'MemberName="Conv_IntToString"' in raw:
        import copy
        nn = copy.deepcopy(n)
        for p in nn.pins:
            p.links = []
        CONV_T = Graph(nodes=[nn])
        break
assert CONV_T

LEN_T = None
for n in g.nodes:
    if n.class_path.endswith("K2Node_CallArrayFunction"):
        raw = " ".join(t for k, t in n.body if k == "raw")
        if "Array_Length" in raw:
            import copy
            nn = copy.deepcopy(n)
            for p in nn.pins:
                p.links = []
            LEN_T = Graph(nodes=[nn])
            break
assert LEN_T

ADD_T = tmpl_file(LIB + r"\array\array_add.t3d")
GDN_T = tmpl_file(LIB + r"\call\get_display_name.t3d")
GET_STATIONS_T = tmpl_file(WLIB + r"\stocker\get_managed_stations.t3d")

# --- wire the dangling else branch: Array_Add into ManagedStations ---------
stationsGet1 = add(GET_STATIONS_T)
arradd_stations = add(ADD_T)
connect(stationsGet1, "ManagedStations", arradd_stations, "TargetArray")
connect(feGather, "Array Element", arradd_stations, "NewItem")
connect_exec(brStore, arradd_stations, "else", "execute")

# --- report block: count + names, spliced before p1lbl ---------------------
pLbl = add(PRINT_T)
setd(pLbl, "InString", "STOCKER_3S ManagedStations found:")

stationsGet2 = add(GET_STATIONS_T)
alen = add(LEN_T)
setf(alen, "TargetArray", "PinType.PinSubCategoryObject", bgc(BASE_CONTAINER))
connect(stationsGet2, "ManagedStations", alen, "TargetArray")
convLen = add(CONV_T)
connect(alen, "ReturnValue", convLen, "InInt")
pCount = add(PRINT_T)
connect(convLen, "ReturnValue", pCount, "InString")

stationsGet3 = add(GET_STATIONS_T)
feNames2 = add(FEACH_T)
type_foreach(feNames2, bgc(BASE_CONTAINER))
connect(stationsGet3, "ManagedStations", feNames2, "Array")
gdn2 = add(GDN_T)
connect(feNames2, "Array Element", gdn2, "Object")
pName2 = add(PRINT_T)
connect(gdn2, "ReturnValue", pName2, "InString")

# --- splice: gacWood.then -> pLbl -> ... -> feNames2.Completed -> p1lbl ----
p1lbl = g.by_name("K2Node_CallFunction_6")
pin(gacWood, "then").links = []
pin(p1lbl, "execute").links = []
connect_exec(gacWood, pLbl)
connect_exec(pLbl, pCount)
connect_exec(pCount, feNames2, "then", "Exec")
connect_exec(feNames2, pName2, "LoopBody", "execute")
connect_exec(feNames2, p1lbl, "Completed", "execute")

# --- validate ---------------------------------------------------------------
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

out = MOD + r"\.ccmod\graphs\stocker_3s.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"nodes: {len(g.nodes)}   wrote: {out}")
print(f"non-reciprocal / dangling problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
