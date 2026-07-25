"""Remove the always-visible BeginPlay widget (superseded by the desk's
InteractableActivate hookup -- see amadan_interact_splice) from the live
Stocker_ModController EventGraph, and compact the whole graph's layout while
we're in here (the user can no longer zoom out far enough to see it all --
sessions of additive splices left huge unused gaps between sections).

Base: the LIVE graph as it stands right now, pulled fresh
('stocker/modcontroller_live_pre_widget_removal', 156 nodes) -- confirmed
exactly ONE K2Node_Event (BeginPlay), so a reachability sweep from it is safe
(no other entry point's subgraph can be mistaken for garbage).

Removal: BeginPlay.then currently fans into a Sequence (then_0 -> the real
gather/tidy/restock pipeline via CallFunction_25, then_1 -> CreateWidget ->
AddToViewport -> Set bShowMouseCursor -> SetInputMode_UIOnlyEx -> GetPlayerController).
Rewire BeginPlay.then straight to CallFunction_25 (single destination again,
Sequence no longer earns its keep) then mark-and-sweep from BeginPlay --
same method as build 3R's map retirement, safer than hand-enumerating the
~6 orphaned nodes, and it also catches any pre-existing zero-link scratch
orphans for free (reported separately below, not conflated with the
intentional removal).

Layout: coordinate-compression squeeze, independently on X and Y -- sort the
distinct positions used, walk them in order, clamp each gap to a max (big
gaps from session-to-session splices collapse; genuine local spacing within
a section is preserved almost as-is since those gaps are already small).
"""
import sys
import re

CCMOD = r"<CCMOD_HOME>"
sys.path.insert(0, CCMOD)
from ccmod import db
from ccmod.t3d import parse, connect_exec
from ccmod.workspace import Workspace

MOD = r"<MOD_ROOT>"

ws = Workspace.resolve()
conn = db.connect(ws.cache_db)


def load_graph(name):
    row = db.get_graph(conn, name)
    assert row, f"no saved graph '{name}'"
    return parse(row["t3d"])


def get_pos(n):
    x = y = None
    for kind, text in n.body:
        if kind != "raw":
            continue
        t = text.strip()
        if t.startswith("NodePosX="):
            x = int(t.split("=", 1)[1])
        elif t.startswith("NodePosY="):
            y = int(t.split("=", 1)[1])
    return x, y


g = load_graph("stocker/modcontroller_live_pre_widget_removal")
print("base graph nodes:", len(g.nodes))

event = g.by_name("K2Node_Event_0")
seq = g.by_name("K2Node_ExecutionSequence_0")
createWidget = g.by_name("K2Node_CreateWidget_0")
gatherChain = g.by_name("K2Node_CallFunction_25")

bp_then = event.pin_by_name("then")
seq_execute = seq.pin_by_name("execute")
seq_then0 = seq.pin_by_name("then_0")
seq_then1 = seq.pin_by_name("then_1")
gather_exec = gatherChain.pin_by_name("execute")

assert bp_then.links == [(seq.name, seq_execute.pin_id)]
assert seq_then0.links == [(gatherChain.name, gather_exec.pin_id)]
assert seq_then1.links == [(createWidget.name, createWidget.pin_by_name("execute").pin_id)]

# --- rewire: BeginPlay.then -> gather chain directly, Sequence drops out --------
bp_then.links = [(gatherChain.name, gather_exec.pin_id)]
gather_exec.links = [(event.name, bp_then.pin_id)]

# --- mark-and-sweep from BeginPlay: only reachable nodes survive ---------------
names = {n.name for n in g.nodes}
reachable = set()
stack = [event.name]
while stack:
    nn = stack.pop()
    if nn in reachable:
        continue
    reachable.add(nn)
    node = g.by_name(nn)
    for p in node.pins:
        for (lnn, _lp) in p.links:
            if lnn in names and lnn not in reachable:
                stack.append(lnn)

swept = [n for n in g.nodes if n.name not in reachable]
swept_names = {n.name for n in swept}
expected_widget_branch = {
    "K2Node_ExecutionSequence_0", "K2Node_CreateWidget_0",
}
already_zero_link_orphans = [
    n.name for n in swept
    if n.name not in expected_widget_branch
    and all(not p.links for p in n.pins)
]
print(f"swept {len(swept)} node(s):")
for n in swept:
    tag = "widget-branch" if n.name in expected_widget_branch else (
        "pre-existing zero-link orphan" if n.name in already_zero_link_orphans else "swept (reachable only via widget branch)")
    print(f"  - {n.name} ({tag})")

g.nodes = [n for n in g.nodes if n.name in reachable]

# --- validate before layout ------------------------------------------------------
problems = []
kept_names = {n.name for n in g.nodes}
for n in g.nodes:
    for p in n.pins:
        for (lnn, lp) in p.links:
            if lnn not in kept_names:
                problems.append(f"{n.name}.{p.name} -> missing {lnn} (was it swept incorrectly?)")
                continue
            other = g.by_name(lnn).pin_by_id(lp)
            if other is None:
                problems.append(f"{n.name}.{p.name} -> {lnn} missing pin {lp}")
                continue
            if (n.name, p.pin_id) not in other.links:
                problems.append(f"non-reciprocal: {n.name}.{p.name} -> {lnn}.{other.name}")

p = event.pin_by_name("then")
if len(p.links) != 1:
    problems.append(f"BeginPlay.then has {len(p.links)} links, expected exactly 1")

# --- layout: coordinate-compression squeeze, X and Y independently -------------
MAX_GAP = 500

def squeeze(get, set_):
    vals = sorted({get(n) for n in g.nodes})
    remap = {}
    cursor = vals[0]
    remap[vals[0]] = cursor
    for prev, cur in zip(vals, vals[1:]):
        cursor += min(cur - prev, MAX_GAP)
        remap[cur] = cursor
    for n in g.nodes:
        set_(n, remap[get(n)])

xs = {n.name: get_pos(n)[0] for n in g.nodes}
ys = {n.name: get_pos(n)[1] for n in g.nodes}
squeeze(lambda n: xs[n.name], lambda n, v: n.set_position(v, get_pos(n)[1]))
# recompute Y after set_position may have touched the raw prop ordering
ys = {n.name: get_pos(n)[1] for n in g.nodes}
squeeze(lambda n: ys[n.name], lambda n, v: n.set_position(get_pos(n)[0], v))

xs_after = [get_pos(n)[0] for n in g.nodes]
ys_after = [get_pos(n)[1] for n in g.nodes]
print(f"bounding box before: x[{min(xs.values())},{max(xs.values())}] y[{min(ys.values())},{max(ys.values())}]")
print(f"bounding box after:  x[{min(xs_after)},{max(xs_after)}] y[{min(ys_after)},{max(ys_after)}]")

out = MOD + r"\.ccmod\graphs\modcontroller_widget_removed_compact.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"\nnodes: {len(g.nodes)}   wrote: {out}")
print(f"problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
