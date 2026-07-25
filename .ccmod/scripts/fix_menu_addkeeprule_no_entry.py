"""AddKeepRule is a FUNCTION graph, not an EventGraph -- its FunctionEntry node can't be deleted
by the user and can't be included in a paste (this project hit that exact limit before; every
other function body here -- the original AddKeepRule, RunSweep, Tidy/RestockManagedStations --
was always built as an interior-only paste plus ONE hand-wire from the real Entry node). This
script strips FunctionEntry_1 out of the already-fixed graph and replaces every pin it fed with
a knot, so the paste never touches the graph's real, protected entry point.
"""
import sys

CCMOD = r"<CCMOD_HOME>"
sys.path.insert(0, CCMOD)
from ccmod.t3d import parse, connect, connect_exec
from ccmod.t3d.generator import instantiate

MOD = r"<MOD_ROOT>"
LIB = CCMOD + r"\library"
SRC = MOD + r"\.ccmod\graphs\menu_addkeeprule_fixed.t3d"

g = parse(open(SRC, encoding="utf-8-sig").read())


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


def tmpl_file(path):
    t = parse(open(path, encoding="utf-8-sig").read())
    for n in t.nodes:
        for p in n.pins:
            p.links = []
    return t


def add(t):
    return instantiate(t, g)[0]


def type_knot(n, category, subcat_obj="None", container="None"):
    for pn in ("InputPin", "OutputPin"):
        setf(n, pn, "PinType.PinCategory", f'"{category}"')
        setf(n, pn, "PinType.PinSubCategoryObject", subcat_obj)
        setf(n, pn, "PinType.ContainerType", container)


KNOT_T = tmpl_file(LIB + r"\flow\knot.t3d")
ACTOR_CLASS = '''"/Script/CoreUObject.Class'/Script/Engine.Actor'"'''

entry = by_name("K2Node_FunctionEntry_1")
dyncast = by_name("K2Node_DynamicCast_0")
makestruct = by_name("K2Node_MakeStruct_0")
notequal = by_name("K2Node_CallFunction_242")
equalint = by_name("K2Node_CallFunction_260")  # NOT 259 -- that's the Greater_IntInt final check

# Verified by inspection (menu_addkeeprule_fixed.t3d): pasting a synthesized FunctionEntry
# silently dropped every custom-parameter pin's fan-out (Station/TemplateID/Keep/KeepAll all
# came through completely dangling on every consumer) while the plain exec "then" pin happened
# to still resolve. So there is nothing real to "capture and redirect" here -- these consumer
# pins are simply unconnected right now. Wire fresh knots directly to the known targets instead.
exec_consumers = list(pin(entry, "then", output=True).links)
station_consumers = [(dyncast.name, pin(dyncast, "Object", output=False).pin_id),
                      (notequal.name, pin(notequal, "B", output=False).pin_id)]
templateid_consumers = [(makestruct.name, pin(makestruct, "TemplateID_6_7331DAFA4369B9E2C105A59FAAA510CD", output=False).pin_id),
                         (equalint.name, pin(equalint, "B", output=False).pin_id)]
keep_consumers = [(makestruct.name, pin(makestruct, "Keep_8_5132904E4CC17522C07075A43E93B26E", output=False).pin_id)]
keepall_consumers = [(makestruct.name, pin(makestruct, "KeepAll_10_A6025F204FE4948B8C46EE8626A13B30", output=False).pin_id)]

# Clear the stale reciprocal link on DynamicCast_0.execute (currently pointing at entry, which
# is about to be removed) before rewiring it fresh from knot_exec.
pin(dyncast, "execute", output=False).links = []

g.nodes.remove(entry)

# --- knots, replacing FunctionEntry as the source for each of its 5 pins -----------------------
knot_exec = add(KNOT_T)
type_knot(knot_exec, "exec")
knot_station = add(KNOT_T)
type_knot(knot_station, "object", ACTOR_CLASS)
knot_templateid = add(KNOT_T)
type_knot(knot_templateid, "int")
knot_keep = add(KNOT_T)
type_knot(knot_keep, "int")
knot_keepall = add(KNOT_T)
type_knot(knot_keepall, "bool")

for kn, x, y in ((knot_exec, -640, -160), (knot_station, -640, -80),
                 (knot_templateid, -640, 0), (knot_keep, -640, 80), (knot_keepall, -640, 160)):
    kn.set_position(x, y)

assert len(exec_consumers) == 1
connect_exec(knot_exec, dyncast, "OutputPin", "execute")

for (nn, pid) in station_consumers:
    other_node = g.by_name(nn)
    other_pin = other_node.pin_by_id(pid)
    connect(knot_station, "OutputPin", other_node, other_pin.name)

for (nn, pid) in templateid_consumers:
    other_node = g.by_name(nn)
    other_pin = other_node.pin_by_id(pid)
    connect(knot_templateid, "OutputPin", other_node, other_pin.name)

for (nn, pid) in keep_consumers:
    other_node = g.by_name(nn)
    other_pin = other_node.pin_by_id(pid)
    connect(knot_keep, "OutputPin", other_node, other_pin.name)

for (nn, pid) in keepall_consumers:
    other_node = g.by_name(nn)
    other_pin = other_node.pin_by_id(pid)
    connect(knot_keepall, "OutputPin", other_node, other_pin.name)

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

out = MOD + r"\.ccmod\graphs\menu_addkeeprule_bodyonly.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"AddKeepRule body-only: nodes={len(g.nodes)} wrote={out} problems={len(problems)}")
for pr in problems:
    print("  !", pr)
print()
print("Hand-wire from the REAL FunctionEntry (do not delete or paste over it):")
print(f"  Entry.then     -> {knot_exec.name}.InputPin")
print(f"  Entry.Station  -> {knot_station.name}.InputPin")
print(f"  Entry.TemplateID -> {knot_templateid.name}.InputPin")
print(f"  Entry.Keep     -> {knot_keep.name}.InputPin")
print(f"  Entry.KeepAll  -> {knot_keepall.name}.InputPin")
