"""Second retest: STOCKER_INTERACT begin/done both fired and the ZOrder=1000
bump landed (confirmed via the MouseCaptureMode log line), but the Save
button didn't register a click. User's diagnosis: the inherited Artisan
crafting menu (still opened by the Parent: InteractableActivate call we
deliberately preserved) is still grabbing input focus underneath our panel,
even though ours renders on top.

Fix: stop calling Parent at all. Amadan's Desk was only ever built off
BP_PL_WorkStation_Artisan to inherit real placement/recipe/feat machinery
(see stocker-datatable-workflow/stocker-placeable-saveas-gotcha) -- it was
never meant to actually function as a crafting station. There's no reason to
open the inherited crafting menu on interact at all; skipping the Parent
call removes the whole underlying-menu-focus-stealing problem at the root
instead of fighting it with z-order/focus tricks.

Base: amadan_interact_splice_v2.t3d (9 nodes, currently live on the desk's
InteractableActivate override) -- rewire Event.then straight to the
STOCKER_INTERACT begin print (previously Parent's job), then drop
K2Node_CallParentFunction_0 entirely (fully unreachable once its exec inputs/
outputs are disconnected; removing it outright rather than leaving a dead
node, per this project's own hygiene practice).
"""
import sys

CCMOD = r"<CCMOD_HOME>"
sys.path.insert(0, CCMOD)
from ccmod.t3d import parse, connect_exec

MOD = r"<MOD_ROOT>"

g = parse(open(MOD + r"\.ccmod\graphs\amadan_interact_splice_v2.t3d", encoding="utf-8").read())
print("base graph nodes:", len(g.nodes))

event = g.by_name("K2Node_Event_0")
callParent = g.by_name("K2Node_CallParentFunction_0")
printBegin = g.by_name("K2Node_CallFunction_21")

event_then = event.pin_by_name("then")
assert event_then.links == [(callParent.name, callParent.pin_by_name("execute").pin_id)]
assert callParent.pin_by_name("then").links == [
    (printBegin.name, printBegin.pin_by_name("execute").pin_id)]

# --- rewire: Event.then -> STOCKER_INTERACT begin directly, Parent drops out ---
event_then.links = []
callParent.pin_by_name("execute").links = []
connect_exec(event, printBegin, "then", "execute")

# --- drop the Parent-call node: clear its remaining data-pin links (Event's own
# Component/Instigator/HitIndex/TriggeredFromRadialWheel outputs only ever fed
# this node) so nothing is left pointing at a node about to disappear -----------
for p in callParent.pins:
    for (lnn, lp) in p.links:
        other = g.by_name(lnn).pin_by_id(lp)
        if other is not None:
            other.links = [lk for lk in other.links if lk != (callParent.name, p.pin_id)]
    p.links = []

g.nodes = [n for n in g.nodes if n.name != callParent.name]

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

p = event.pin_by_name("then")
if len(p.links) != 1:
    problems.append(f"Event.then has {len(p.links)} links, expected exactly 1")

out = MOD + r"\.ccmod\graphs\amadan_interact_no_craftmenu.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"\nnodes: {len(g.nodes)}   wrote: {out}")
print(f"problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
