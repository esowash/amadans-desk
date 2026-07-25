"""Author the repeating RunSweep timer on Menu_ModController's BeginPlay (currently empty --
the debug harness was stripped out this session). This replaces the harness's one-shot
Delay(90s) with a real repeating Set Timer by Function Name, per the design note that the
sweep can no longer be a single BeginPlay shot once GatherNearbyStorageContainers runs on
every tick rather than once.

Set Timer by Function Name (K2_SetTimer) takes the target function's NAME AS A STRING, not a
self-call node reference -- so it sidesteps the same-class-self-call paste problem entirely
(same category as Delay: an ordinary KismetSystemLibrary call, ReturnValue unused). The exact
node shape (Object/FunctionName/Time/bLooping/bMaxOncePerFrame/InitialStartDelay* pins) is a
REAL capture this session from BP_PL_Door's vanilla ChangeNavMeshArea timer, not hand-typed,
after two hand-typing bugs earlier this session (a forgotten Range literal, an unquoted
DefaultObject) made a real capture worth the extra round-trip.

Sweep interval defaults to 300s (5 minutes) -- a placeholder until the real house-rules UI's
planned "sweep frequency, in minutes" text field exists to drive it.
"""
import sys

CCMOD = r"<CCMOD_HOME>"
sys.path.insert(0, CCMOD)
from ccmod.t3d import parse, connect, connect_exec
from ccmod.t3d.generator import instantiate
from ccmod.t3d.model import Graph

MOD = r"<MOD_ROOT>"
STOCKER_GRAPH = MOD + r"\.ccmod\graphs\stocker_modcontroller_probe_a_live.t3d"
SELF_GRAPH = MOD + r"\.ccmod\graphs\testpanel_review.t3d"
TIMER_GRAPH = MOD + r"\.ccmod\graphs\settimer_byfunctionname_real.t3d"


def tmpl_file_parsed(graph, want_class):
    for n in graph.nodes:
        if n.class_path.endswith(want_class):
            import copy
            nn = copy.deepcopy(n)
            for p in nn.pins:
                p.links = []
            return Graph(nodes=[nn])
    raise KeyError(want_class)


stocker_src = parse(open(STOCKER_GRAPH, encoding="utf-8-sig").read())
self_src = parse(open(SELF_GRAPH, encoding="utf-8-sig").read())
timer_src = parse(open(TIMER_GRAPH, encoding="utf-8-sig").read())

EVENT_T = tmpl_file_parsed(stocker_src, "K2Node_Event")
# stocker_src has multiple K2Node_Event nodes (ReceiveBeginPlay + interface overrides) --
# make sure we grab the ReceiveBeginPlay one specifically.
for n in stocker_src.nodes:
    if n.class_path.endswith("K2Node_Event"):
        raw = " ".join(t for k, t in n.body if k == "raw")
        if 'MemberName="ReceiveBeginPlay"' in raw:
            import copy
            nn = copy.deepcopy(n)
            for p in nn.pins:
                p.links = []
            EVENT_T = Graph(nodes=[nn])
            break

SELF_T = tmpl_file_parsed(self_src, "K2Node_Self")
TIMER_T = tmpl_file_parsed(timer_src, "K2Node_CallFunction")


def setf(n, pn, k, raw, output=None):
    p = n.pin_by_name(pn, output=output)
    assert p, f"{n.name} has no pin {pn}"
    p._set(k, raw)


g = Graph()


def add(t):
    return instantiate(t, g)[0]


ev = add(EVENT_T)
self_node = add(SELF_T)
timer = add(TIMER_T)

setf(timer, "FunctionName", "DefaultValue", '"RunSweep"')
setf(timer, "Time", "DefaultValue", '"300.000000"')
setf(timer, "bLooping", "DefaultValue", '"true"')

connect_exec(ev, timer, "then", "execute")
connect(self_node, "self", timer, "Object")

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

out = MOD + r"\.ccmod\graphs\menu_runsweep_timer_body.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"RunSweep timer: nodes={len(g.nodes)} wrote={out} problems={len(problems)}")
for pr in problems:
    print("  !", pr)
