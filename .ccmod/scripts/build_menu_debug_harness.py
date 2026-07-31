"""Author the temporary debug seed+sweep harness on Menu_ModController's EventGraph
(currently empty -- confirmed via a fresh ccmod pull, session 16). NOT a permanent feature:
remove once the real house-rules UI (menu-open call site for GatherNearbyBenches) and a
repeating sweep Timer (for RunSweep) exist.

Same-class self-calls (GatherNearbyBenches, AddKeepRule x2, GatherNearbyStorageContainers,
RunSweep) do NOT survive ccmod's clipboard paste -- confirmed session 15 when RunSweep's own
internal calls had to be hand-built in the GUI after a synthesized K2Node_CallFunction pasted
as nothing. So this script authors everything EXCEPT those 5 nodes; the user right-click-adds
those 5 and wires them per the printed recipe below.

Chain:
  ReceiveBeginPlay -> Delay(8s) -> GetAllActorsOfClass(BP_PL_Table_Strategy_Amadan) -> [0] -> Desk
  Desk --(hand)--> GatherNearbyBenches(AnchorActor=Desk, Range=3000) -> ReturnValue --(hand)--> [0] -> Station
  Station --(hand)--> AddKeepRule(Station, TemplateID=11501 /*Iron Bar*/, Keep=5, KeepAll=false)
                  --> AddKeepRule(Station, TemplateID=12515 /*Layered Silk*/, Keep=0, KeepAll=true)
  Desk --(hand)--> GatherNearbyStorageContainers(AnchorActor=Desk, Range=3000)
                  --> RunSweep()
                  --> PrintString("MENU_HARNESS: seed+sweep complete")
"""
import sys

import os, pathlib
CCMOD = os.environ.get("CCMOD_HOME") or str(pathlib.Path(__file__).resolve().parents[3] / "claude-conan-modder")
sys.path.insert(0, CCMOD)
from ccmod.t3d import parse, connect, connect_exec, auto_layout
from ccmod.t3d.generator import instantiate
from ccmod.t3d.model import Graph

import pathlib
MOD = str(pathlib.Path(__file__).resolve().parents[2])
LIB = CCMOD + r"\library"
SRC_GRAPH = MOD + r"\.ccmod\graphs\stocker_modcontroller_probe_a_live.t3d"

ACTOR_CLASS = '''"/Script/CoreUObject.Class'/Script/Engine.Actor'"'''


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


def find_by_raw(src_graph, needle, want_class=None, nth=0):
    hits = []
    for n in src_graph.nodes:
        if want_class and not n.class_path.endswith(want_class):
            continue
        raw = " ".join(t for k, t in n.body if k == "raw")
        if needle in raw:
            hits.append(n)
    import copy
    nn = copy.deepcopy(hits[nth])
    for p in nn.pins:
        p.links = []
    return Graph(nodes=[nn])


def find_by_pin_field(src_graph, pin_name, field, needle):
    import copy
    for n in src_graph.nodes:
        p = n.pin_by_name(pin_name)
        if p and needle in (p._get(field) or ""):
            nn = copy.deepcopy(n)
            for pp in nn.pins:
                pp.links = []
            return Graph(nodes=[nn])
    raise KeyError((pin_name, field, needle))


src = parse(open(SRC_GRAPH, encoding="utf-8-sig").read())

KNOT_T = tmpl_file(LIB + r"\flow\knot.t3d")
EVENT_T = find_by_raw(src, 'MemberName="ReceiveBeginPlay"', want_class="K2Node_Event")
DELAY_T = find_by_raw(src, 'MemberName="Delay"', want_class="K2Node_CallFunction", nth=0)
GAC_DESK_T = find_by_pin_field(src, "ActorClass", "DefaultObject", "BP_PL_Table_Strategy_Amadan")
GETARRAYITEM_T = find_by_raw(src, "", want_class="K2Node_GetArrayItem", nth=0)
PRINT_T = find_by_raw(src, 'MemberName="PrintString"', want_class="K2Node_CallFunction", nth=0)


def type_knot(n, category, subcat_obj="None", container="None"):
    for pn in ("InputPin", "OutputPin"):
        setf(n, pn, "PinType.PinCategory", f'"{category}"')
        setf(n, pn, "PinType.PinSubCategoryObject", subcat_obj)
        setf(n, pn, "PinType.ContainerType", container)


g = Graph()


def add(t):
    return instantiate(t, g)[0]


ev = add(EVENT_T)
delay = add(DELAY_T)
setf(delay, "Duration", "DefaultValue", '"8.000000"')

gac_desk = add(GAC_DESK_T)

getitem_desk = add(GETARRAYITEM_T)  # Array pin already typed to the Desk class from capture

knot_desk = add(KNOT_T)
type_knot(knot_desk, "object", ACTOR_CLASS)

getitem_station = add(GETARRAYITEM_T)
# retype: this one reads GatherNearbyBenches's Array<Actor> return, not the Desk array
setf(getitem_station, "Array", "PinType.PinCategory", '"object"')
setf(getitem_station, "Array", "PinType.PinSubCategoryObject", ACTOR_CLASS)
setf(getitem_station, "Array", "PinType.ContainerType", "Array")
setf(getitem_station, "Output", "PinType.PinCategory", '"object"', output=True)
setf(getitem_station, "Output", "PinType.PinSubCategoryObject", ACTOR_CLASS, output=True)
setf(getitem_station, "Output", "PinType.ContainerType", "None", output=True)

knot_station = add(KNOT_T)
type_knot(knot_station, "object", ACTOR_CLASS)

print_done = add(PRINT_T)
setf(print_done, "InString", "DefaultValue", '"MENU_HARNESS: seed+sweep complete"')

# --- ccmod-authored wiring only (boundary pins to hand-added nodes are left dangling) ---
connect_exec(ev, delay, "then", "execute")
connect_exec(delay, gac_desk, "then", "execute")
connect(gac_desk, "OutActors", getitem_desk, "Array")
connect(getitem_desk, "Output", knot_desk, "InputPin")
connect(getitem_station, "Output", knot_station, "InputPin")

auto_layout(g.nodes, origin=(0, 0), dx=260, dy=200, per_column=6)

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

out = MOD + r"\.ccmod\graphs\menu_debug_harness_body.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"DebugHarness: nodes={len(g.nodes)} wrote={out} problems={len(problems)}")
for pr in problems:
    print("  !", pr)
print()
print("Dangling pins that need a hand-wire after paste (per node, by ccmod-side name):")
print(f"  {gac_desk.name}.then                -> [hand-add] GatherNearbyBenches.execute")
print(f"  {knot_desk.name}.OutputPin           -> [hand-add] GatherNearbyBenches.AnchorActor")
print(f"  {knot_desk.name}.OutputPin           -> [hand-add] GatherNearbyStorageContainers.AnchorActor")
print(f"  {getitem_station.name}.Array (input) <- [hand-add] GatherNearbyBenches.ReturnValue")
print(f"  {knot_station.name}.OutputPin        -> [hand-add] AddKeepRule (rule 1).Station")
print(f"  {knot_station.name}.OutputPin        -> [hand-add] AddKeepRule (rule 2).Station")
print(f"  {print_done.name}.execute (input)    <- [hand-add] RunSweep.then")
