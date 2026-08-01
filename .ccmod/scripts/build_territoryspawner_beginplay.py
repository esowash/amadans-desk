"""Wire Amadan_TerritorySpawner's BeginPlay so it points itself at our camp.

Why this graph exists (session 22): NPCTerritorySpawner::BeginPlay has TWO modes.

    if SpawnFromTriggerEvent            -> skip
    else if (Color == NewEnumerator27)  -> FindStaticNavigationOverride(Camp)
                                           -> InitializeSpawners          [CAMP MODE]
         else                           -> RegisterNPCTerritorySpawner    [territory-volume mode]

Camp mode is the one that reads spawn points, via
Camp -> BP_CampOwner -> BP_CampComponent (implements StaticNavigationProviderInterface)
     -> GetSpawnPoints() -> CachedSpawnPoints -> built from CampActors.

`Camp` cannot be a Class Default: it is a reference to a specific world actor, and our camp owner
is spawned at runtime. So the subclass resolves it in its own BeginPlay and assigns it BEFORE
calling Parent: BeginPlay, because the parent reads Camp immediately.

Setting Camp from inside our own subclass (rather than from Menu_ModController) also sidesteps any
question about whether the inherited property is externally writable.

Node shapes are NOT synthesized - all five come from a real hand-placed probe the user captured
(amadan_territoryspawner_probe_s22), per the standing rule that retargeting a VariableSet to an
inherited variable on another class reliably produces "pin no longer exists" errors.

Note `Camp`'s pin is typed Actor (not BP_CampOwner), so Amadan_CampOwner_C upcasts into it with no
cast node. GetAllActorsOfClass is impure - it carries exec pins and must sit in the exec chain.
"""
import pathlib, sys

MOD = pathlib.Path(__file__).resolve().parents[2]
CCMOD = MOD.parent / "claude-conan-modder"
sys.path.insert(0, str(CCMOD))

from ccmod.t3d import parse, connect, connect_exec
from ccmod.t3d.generator import instantiate
from ccmod.t3d.model import Graph
import copy

G = MOD / ".ccmod" / "graphs"
SRC = G / "amadan_territoryspawner_probe_s22.t3d"
OUT = G / "amadan_territoryspawner_beginplay_s22.t3d"

g = parse(SRC.read_text(encoding="utf-8-sig"))

# The "unwired probe" was not actually unwired: UE auto-connects nodes dragged off an existing pin,
# so it arrived carrying event->gac->SetCamp->Parent and OutActors->Array. parse() preserves those
# links (only the tmpl() helper strips them), so wiring on top of a parsed graph silently ADDS to
# whatever it already had - which produced a second exec link out of GetAllActorsOfClass.then, i.e.
# exec fan-out, which this DevKit rejects outright. Strip everything and wire deliberately.
for _n in g.nodes:
    for _p in _n.pins:
        _p.links = []

event = g.by_name("K2Node_Event_0")            # ReceiveBeginPlay
parent = g.by_name("K2Node_CallParentFunction_0")  # Parent: BeginPlay
gac = g.by_name("K2Node_CallFunction_0")       # GetAllActorsOfClass(Amadan_CampOwner)
item = g.by_name("K2Node_GetArrayItem_0")      # Get (a copy)
setcamp = g.by_name("K2Node_VariableSet_0")    # Set Camp

# --- debug checkpoint ------------------------------------------------------
# The single most valuable diagnostic in this whole build: it proves whether the camp owner already
# existed when this spawner's BeginPlay ran. SpawnAmadan spawns the camp owner first and this
# spawner last, but that ordering is an assumption until a log line confirms it. If this prints 0,
# Camp is null, the parent takes the RegisterNPCTerritorySpawner branch, and nothing spawns - which
# is exactly the silent failure session 21 hit and could not explain.
def tmpl(graph, name):
    n = copy.deepcopy(next(x for x in graph.nodes if x.name == name))
    for p in n.pins:
        p.links = []
    return Graph(nodes=[n])


src_mc = parse((G / "modcontroller_beginplay_live_s21.t3d").read_text(encoding="utf-8-sig"))
src_old = parse((G / "spawnamadan_revert2_verify_s21.t3d").read_text(encoding="utf-8-sig"))

lit = instantiate(tmpl(src_mc, "K2Node_CallFunction_26"), g)[0]
val = instantiate(tmpl(src_mc, "K2Node_CallFunction_27"), g)[0]
conv = instantiate(tmpl(src_mc, "K2Node_CallFunction_33"), g)[0]
arrlen = instantiate(tmpl(src_old, "K2Node_CallArrayFunction_Len"), g)[0]

LABEL = "MENU_CAMP: spawner BeginPlay, camp owners found:"
lit.pin_by_name("InString")._set("DefaultValue", f'"{LABEL}"')
assert f'DefaultValue="{LABEL}"' in lit.pin_by_name("InString").render(), "gotcha #17"
val.pin_by_name("InString")._set("DefaultValue", '""')  # gotcha #13: blank the inherited literal
arrlen.pin_by_name("TargetArray")._set(
    "PinType.PinSubCategoryObject",
    '''"/Script/Engine.BlueprintGeneratedClass'/Game/Mods/Menu/Amadan_CampOwner.Amadan_CampOwner_C'"''')

# exec: BeginPlay -> GetAllActorsOfClass -> print label -> print count -> Set Camp -> Parent
connect_exec(event, gac, src_pin="then", dst_pin="execute")
connect_exec(gac, lit)
connect_exec(lit, val)
connect_exec(val, setcamp)
connect_exec(setcamp, parent)

# data: OutActors -> Array -> [0] -> Camp ; OutActors -> Length -> string -> print
connect(gac, "OutActors", item, "Array")
connect(item, "Output", setcamp, "Camp")
connect(gac, "OutActors", arrlen, "TargetArray")
connect(arrlen, "ReturnValue", conv, "InInt")
connect(conv, "ReturnValue", val, "InString")

# lay it out left-to-right so the pasted result is readable
for node, x, y in [
    (event,   -1080, 0),
    (gac,      -860, 0),
    (arrlen,   -660, 260),
    (conv,     -440, 260),
    (lit,      -600, 0),
    (val,      -360, 0),
    (item,     -120, 200),
    (setcamp,   -80, 0),
    (parent,    180, 0),
]:
    node.set_position(x, y)

t3d = g.render()
OUT.write_text(t3d, encoding="utf-8")

# proofread: every link must be reciprocal, keyed on (node, pin) not pin id alone
links = {}
for n in g.nodes:
    for p in n.pins:
        for tgt_node, tgt_pin in p.links:
            links.setdefault((n.name, p.pin_id), []).append((tgt_node, tgt_pin))
problems = []
for n in g.nodes:
    for p in n.pins:
        for tgt_node, tgt_pin in p.links:
            back = links.get((tgt_node, tgt_pin), [])
            if (n.name, p.pin_id) not in back:
                problems.append(f"{n.name}.{p.name} -> {tgt_node} {tgt_pin} not reciprocated")
print(f"wrote {OUT.name}: {len(g.nodes)} nodes, {sum(len(v) for v in links.values())} link-ends")
print("pin-reciprocity problems:", problems or "none")
