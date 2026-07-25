"""Replace the whole hand-rolled CreateWidget/AddToViewport/SetShowMouseCursor/
SetInputMode/IgnoreMoveInput/IgnoreLookInput chain with the real native idiom:
GetGUIModuleController -> ActivateModule("StockerHouseRules"). Three rounds of
generic-Engine patching (focus stolen by crafting menu, then movement, then
cursor) all trace back to Conan's own GUI Module system handling camera-lock/
cursor/focus atomically based on the module's DT_UIModuleTable row (Category=
Modal) -- registering our own module (mirrored off the real SignTextInput row,
see stocker-datatable-workflow-style DataTable merge, this session) should get
all three for free instead of us discovering a fourth override next round.

GetGUIModuleController/ActivateModule node shapes lifted verbatim from a real
capture off BP_PL_Sign_Master's own interact handler (signmaster_activatemodule_
idiom.t3d) -- not hand-authored, per this project's standing verify-via-a-real-
node discipline. Sign's own DynamicCast+SetContent steps are dropped: those
exist only so Sign can pass itself as context into its OWN widget-specific
SetContent function; W_StockerTestPanel needs no such injection (its Save
button already resolves its target station directly), so ActivateModule's
return value is simply left unused.

Base: amadan_interact_ignoreinput.t3d (10 nodes, currently live on the desk's
InteractableActivate override) -- keep Event_0 and the two STOCKER_INTERACT
begin/done banners, drop everything in between.
"""
import sys
import copy

CCMOD = r"<CCMOD_HOME>"
sys.path.insert(0, CCMOD)
from ccmod import db
from ccmod.t3d import parse, connect, connect_exec
from ccmod.t3d.generator import instantiate
from ccmod.t3d.model import Graph
from ccmod.workspace import Workspace

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


def add(t, g):
    return instantiate(t, g)[0]


# --- base: the graph currently live on the desk's InteractableActivate --------
g = parse(open(MOD + r"\.ccmod\graphs\amadan_interact_ignoreinput.t3d", encoding="utf-8").read())
print("base graph nodes:", len(g.nodes))

event = g.by_name("K2Node_Event_0")
printBegin = g.by_name("K2Node_CallFunction_21")
printDone = g.by_name("K2Node_CallFunction_22")

# --- everything between the two banners is being replaced ----------------------
keep = {event.name, printBegin.name, printDone.name}
old_middle = [n for n in g.nodes if n.name not in keep]
print(f"dropping {len(old_middle)} nodes from the old hand-rolled chain:")
for n in old_middle:
    print("  -", n.name)

event_then = event.pin_by_name("then")
assert event_then.links == [(printBegin.name, printBegin.pin_by_name("execute").pin_id)]
printBegin_then = printBegin.pin_by_name("then")
old_target = printBegin_then.links[0][0]

# detach printBegin.then from whatever it fed into (the old chain's head)
old_head = g.by_name(old_target)
old_head.pin_by_name("execute").links = []
printBegin_then.links = []

# printDone.execute's old incoming link (from the old chain's tail) -- just clear it,
# the old tail node is being dropped anyway
printDone.pin_by_name("execute").links = []

g.nodes = [n for n in g.nodes if n.name in keep]

# --- templates, lifted verbatim from the real Sign Master capture --------------
signSrc = parse(open(MOD + r"\.ccmod\graphs\signmaster_activatemodule_idiom.t3d", encoding="utf-8").read())
GETGUI_T = tmpl_from(signSrc, "K2Node_CallFunction_4")
ACTIVATE_T = tmpl_from(signSrc, "K2Node_CallFunction_5")

getGui = add(GETGUI_T, g)
activate = add(ACTIVATE_T, g)

connect(getGui, "ReturnValue", activate, "self")
pin(activate, "moduleName")._set("DefaultValue", '"StockerHouseRules"')

connect_exec(printBegin, activate, "then", "execute")
connect_exec(activate, printDone, "then", "execute")

# --- layout ----------------------------------------------------------------------
getGui.set_position(900, -150)
activate.set_position(1300, 0)
printDone.set_position(1750, 0)

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

for nn, pn in [(event.name, "then"), (printBegin.name, "then"),
               (activate.name, "execute"), (activate.name, "then"),
               (printDone.name, "execute")]:
    p = g.by_name(nn).pin_by_name(pn)
    if len(p.links) != 1:
        problems.append(f"{nn}.{pn} has {len(p.links)} links, expected exactly 1")

wilds = [(n.name, p.name) for n in g.nodes for p in n.pins
         if p._get("PinType.PinCategory") == '"wildcard"']
assert not wilds, f"unresolved wildcards: {wilds}"

out = MOD + r"\.ccmod\graphs\amadan_interact_activatemodule.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"\nnodes: {len(g.nodes)}   wrote: {out}")
print(f"problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
