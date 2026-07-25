"""First retest of the interact-event hookup was inconclusive from the log:
the desk showed the inherited Artisan crafting menu (expected -- that's the
Parent call's default behavior, deliberately preserved), but there is no
banner anywhere in the chain to confirm our own Create Widget -> AddToViewport
-> SetInputMode branch actually ran at all. User's own hypothesis: our panel
may have opened BEHIND the crafting menu and never gotten focus, possibly
left stuck in the viewport if the player backs out via the vanilla menu
instead of our own Save button.

Two changes to amadan_interact_splice.t3d (the graph already pasted into
BP_PL_WorkStation_Amadan's InteractableActivate override this session):
1. Bracket the chain with STOCKER_INTERACT begin/done PrintStrings (same
   banner convention as every STOCKER_3X spike) -- begin fires right after
   the Parent call, before CreateWidget, so a retest will show conclusively
   whether the override path is even reached; done fires after SetInputMode,
   the end of the existing chain.
2. Bump AddToViewport's ZOrder from the default 0 to 1000 -- attacks the
   most likely cause of "presented the Artisan default menu" directly: if
   the inherited crafting UI uses a higher/non-zero ZOrder of its own, two
   ZOrder=0 widgets stack by add-order and ours (added second) SHOULD win,
   but if the base UI reserves a high ZOrder for full-screen menus ours would
   lose regardless of order. Cheap, safe, and the begin/done banners will
   tell us next test whether this alone was sufficient or whether the panel
   fires but still needs something else (e.g. explicit focus).

PrintString template lifted from the live ModController graph (K2Node_
CallFunction_21, one of the existing STOCKER_3N banners) -- generic function,
no per-asset specialization, safe to reuse in the desk's own graph.
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


def setd(n, pn, v):
    pin(n, pn)._set("DefaultValue", f'"{v}"')


# --- base: the graph already live on the desk's InteractableActivate override ---
g = parse(open(MOD + r"\.ccmod\graphs\amadan_interact_splice.t3d", encoding="utf-8").read())
print("base graph nodes:", len(g.nodes))

callParent = g.by_name("K2Node_CallParentFunction_0")
createWidget = g.by_name("K2Node_CreateWidget_0")
addToViewport = g.by_name("K2Node_CallFunction_238")
setInputMode = g.by_name("K2Node_CallFunction_417")

# --- PrintString template, lifted from the live ModController graph -----------
mcSrc = parse(open(MOD + r"\.ccmod\graphs\modcontroller_anchor_repointed.t3d", encoding="utf-8").read())
PRINT_T = tmpl_from(mcSrc, "K2Node_CallFunction_21")


def add(t):
    return instantiate(t, g)[0]


printBegin = add(PRINT_T)
printDone = add(PRINT_T)
setd(printBegin, "InString", "STOCKER_INTERACT begin (desk widget hookup)")
setd(printDone, "InString", "STOCKER_INTERACT done (widget + input mode set)")

# --- splice begin banner: CallParentFunction.then -> printBegin -> CreateWidget ---
old_then = pin(callParent, "then")
assert old_then.links == [(createWidget.name, pin(createWidget, "execute").pin_id)], \
    f"unexpected pre-state on CallParentFunction.then: {old_then.links}"

# clear both sides of the old link before rewiring -- connect_exec only appends
old_then.links = []
pin(createWidget, "execute").links = []

connect_exec(callParent, printBegin, "then", "execute")
connect_exec(printBegin, createWidget, "then", "execute")

# --- splice done banner onto the existing chain's dangling tail -----------------
old_setinputmode_then = pin(setInputMode, "then")
assert old_setinputmode_then.links == [], "expected SetInputMode.then dangling"
connect_exec(setInputMode, printDone, "then", "execute")

# --- attack the likely Z-order cause: force our panel above the default menu ----
before_zorder = pin(addToViewport, "ZOrder")._get("DefaultValue")
pin(addToViewport, "ZOrder")._set("DefaultValue", '"1000"')
print(f"AddToViewport.ZOrder: {before_zorder} -> \"1000\"")

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

for nn, pn in [(callParent.name, "then"), (printBegin.name, "execute"), (printBegin.name, "then"),
               (createWidget.name, "execute"), (setInputMode.name, "then"),
               (printDone.name, "execute")]:
    p = g.by_name(nn).pin_by_name(pn)
    if len(p.links) != 1:
        problems.append(f"{nn}.{pn} has {len(p.links)} links, expected exactly 1")

# --- layout: nudge the two new prints out of the way, no overlap ---------------
printBegin.set_position(525, -200)
printDone.set_position(2100, 200)

out = MOD + r"\.ccmod\graphs\amadan_interact_splice_v2.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"\nnodes: {len(g.nodes)}   wrote: {out}")
print(f"problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
