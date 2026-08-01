"""Rebuild SpawnAmadan to stand up a real Conan camp instead of spawning the character directly.

Session 22. Conan does not spawn world NPCs by calling a spawn function on an actor; it uses a
three-actor camp system wired by array membership (docs/CAMP-SPAWNER-SYSTEM.md). Every attempt in
sessions 19-21 bypassed it, which is why the character existed but never rendered.

New body:

    SpawnAmadan
      guard: GetAllActorsOfClass(Amadan_CampOwner).Length == 0
        -> Spawn Amadan_CampOwner            (its BP_CampComponent::BeginPlay registers the camp
                                              against ConanWorldSettings' BP_CampSystemComponent)
        -> Spawn Amadan_ManualSpawnPoint     (carries SpawnTable="Amadan", EmoteState, IsGuardSpot)
        -> Array_Add(campOwner's BP_CampComponent.CampActors, spawnPoint)
        -> Spawn Amadan_TerritorySpawner     LAST

Ordering is load-bearing twice over:
  * the spawn-point cache is build-once-then-frozen (UpdateCachedWaypointsAndSpawnPoints early-outs
    on IsSpawnPointAndWaypointCacheValid?), so CampActors must be populated before the territory
    spawner's BeginPlay reaches GetSpawnPoints;
  * the territory spawner's own BeginPlay resolves Camp via GetAllActorsOfClass(Amadan_CampOwner),
    so the camp owner must already exist when it spawns.

All three are spawned at the same transform deliberately: NPCTerritorySpawner has a SpawnVolume
BoxComponent that is normally sized at edit time by the UpdateSpawnVolumeForManualSpawnPoints
editor button, which nothing performs at runtime. Co-locating keeps the spawn point inside any
plausible default extent.

The guard checks the camp owner rather than the character: once the camp stands, the territory
spawner owns respawn natively (AllowRespawn on the spawn point), so repeated calls from RunSweep
become no-ops instead of the old manual respawn.

Dropped from the old body: DynamicCast + SetCharacterSpawnTableID. The spawn table now lives on
the manual spawn point, which is where the base game puts it - a real working camp spawner has its
own NPCs/Human NPCs arrays empty.

Package paths: a mod's Local/ folder is mounted AS the mod package root, so these are
/Game/Mods/Menu/<Asset>, NOT /Game/Mods/Menu/Local/<Asset>, despite the on-disk layout. Verified
against live pulls; getting this wrong silently pastes a null class pin (test-loop gotcha #1).
"""
import copy, pathlib, sys

MOD = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(MOD.parent / "claude-conan-modder"))

from ccmod.t3d import parse, connect, connect_exec
from ccmod.t3d.generator import instantiate
from ccmod.t3d.model import Graph

G = MOD / ".ccmod" / "graphs"
src_old = parse((G / "spawnamadan_revert2_verify_s21.t3d").read_text(encoding="utf-8-sig"))
src_camp = parse((G / "campactors_probe2_s22.t3d").read_text(encoding="utf-8-sig"))
src_mc = parse((G / "modcontroller_beginplay_live_s21.t3d").read_text(encoding="utf-8-sig"))


def tmpl(graph, name):
    """A single-node Graph copied from `graph`, with all links stripped."""
    n = copy.deepcopy(next(x for x in graph.nodes if x.name == name))
    for p in n.pins:
        p.links = []
    return Graph(nodes=[n])


EVENT_T = tmpl(src_old, "K2Node_CustomEvent_0")
GAC_T = tmpl(src_old, "K2Node_CallFunction_45")
ARRLEN_T = tmpl(src_old, "K2Node_CallArrayFunction_Len")
EQ0_T = tmpl(src_old, "K2Node_CallFunction_260")
ITE_T = tmpl(src_old, "K2Node_IfThenElse_0")
XFORM_T = tmpl(src_old, "K2Node_CallFunction_4")
SPAWN_T = tmpl(src_old, "K2Node_SpawnActorFromClass_1")

GETCOMP_T = tmpl(src_camp, "K2Node_CallFunction_0")        # GetComponentByClass (pure)
CAMPACTORS_T = tmpl(src_camp, "K2Node_VariableGet_0")      # external Get CampActors
ARRAYADD_T = tmpl(src_camp, "K2Node_CallArrayFunction_0")  # Array_Add

# Debug prints follow this mod's existing MENU_TIMER_SETUP idiom exactly: a PrintString carrying a
# LITERAL label, immediately followed by a second PrintString whose InString is WIRED to a
# Conv_IntToString. No Concat_StrStr involved - the label and the number are two separate lines.
PRINT_LIT_T = tmpl(src_mc, "K2Node_CallFunction_26")   # literal-InString PrintString
PRINT_VAL_T = tmpl(src_mc, "K2Node_CallFunction_27")   # PrintString with InString wired
CONV_T = tmpl(src_mc, "K2Node_CallFunction_33")        # Conv_IntToString


def paths(asset):
    return (f'"/Game/Mods/Menu/{asset}.{asset}_C"',
            f'''"/Script/Engine.BlueprintGeneratedClass'/Game/Mods/Menu/{asset}.{asset}_C'"''')


CAMPOWNER, CAMPOWNER_BGC = paths("Amadan_CampOwner")
SPAWNPOINT, SPAWNPOINT_BGC = paths("Amadan_ManualSpawnPoint")
TERRITORY, TERRITORY_BGC = paths("Amadan_TerritorySpawner")

g = Graph()
add = lambda t: instantiate(t, g)[0]


def setf(n, pin_name, key, raw, output=None):
    p = n.pin_by_name(pin_name, output=output)
    assert p, f"{n.name} has no pin {pin_name}"
    p._set(key, raw)


event = add(EVENT_T)
for i, (kind, text) in enumerate(event.body):
    if kind == "raw" and text.strip().startswith("CustomFunctionName="):
        event.body[i] = (kind, 'CustomFunctionName="SpawnAmadan"')

# --- guard: no camp owner in the world yet? --------------------------------
gac = add(GAC_T)
setf(gac, "ActorClass", "DefaultObject", CAMPOWNER)
setf(gac, "OutActors", "PinType.PinSubCategoryObject", CAMPOWNER_BGC, output=True)
arrlen = add(ARRLEN_T)
setf(arrlen, "TargetArray", "PinType.PinSubCategoryObject", CAMPOWNER_BGC)
eq0 = add(EQ0_T)
ite = add(ITE_T)

# --- one shared transform at Amadan's real coordinate ----------------------
# (Location default is carried verbatim from the cloned source node.)
xform = add(XFORM_T)


def spawner(class_path, bgc):
    n = add(SPAWN_T)
    setf(n, "Class", "DefaultObject", class_path)
    setf(n, "CollisionHandlingOverride", "DefaultValue", '"AdjustIfPossibleButAlwaysSpawn"')
    setf(n, "ReturnValue", "PinType.PinSubCategoryObject", bgc, output=True)
    connect(xform, "ReturnValue", n, "SpawnTransform")
    # Drop the hidden advanced Instigator pin. Its value is None (the default anyway), but if the
    # node reconstructs on paste - which it does whenever the Class pin fails to resolve - the
    # advanced pins are not recreated and the carried value orphans into
    # "Input pin Instigator ... no longer exists on node". Omitting it costs nothing: Unreal
    # recreates the pin at its default. Same reasoning would apply to Owner, but Owner carries no
    # value in the source template so it is harmless.
    n.body[:] = [(k, v) for k, v in n.body
                 if not (k == "pin" and v.name == "Instigator")]
    return n


spawn_camp = spawner(CAMPOWNER, CAMPOWNER_BGC)
spawn_point = spawner(SPAWNPOINT, SPAWNPOINT_BGC)
spawn_terr = spawner(TERRITORY, TERRITORY_BGC)

# --- register the spawn point into the camp --------------------------------
getcomp = add(GETCOMP_T)
campactors = add(CAMPACTORS_T)
arrayadd = add(ARRAYADD_T)

# --- debug checkpoints -----------------------------------------------------
# Every failure mode in this chain is SILENT: a null spawn, a null component, an Array_Add that
# no-ops, a camp that never registers - all look identical in a log ("nothing happened"). These two
# checkpoints distinguish them. The second is the decisive one: CampActors length AFTER the add is
# what the territory spawner will later read via GetSpawnPoints.
def checkpoint(label, int_source_node, int_source_pin):
    lit = add(PRINT_LIT_T)
    lit.pin_by_name("InString")._set("DefaultValue", f'"{label}"')
    assert f'DefaultValue="{label}"' in lit.pin_by_name("InString").render(), \
        "gotcha #17: DefaultValue must render wrapped in quotes"
    val = add(PRINT_VAL_T)
    # gotcha #13: this template was cloned from a real PrintString whose own literal InString text
    # ("MENU_PERSISTENCE: data loaded, rules restored:") is still sitting on the pin. Once InString
    # is wired that text is dead cosmetic cruft, but the DevKit still DISPLAYS it - which is
    # precisely the trap that caused a wrong hand-wire once already. Blank it so the node can't lie.
    val.pin_by_name("InString")._set("DefaultValue", '""')
    conv = add(CONV_T)
    connect(int_source_node, int_source_pin, conv, "InInt")
    connect(conv, "ReturnValue", val, "InString")
    connect_exec(lit, val)
    return lit, val


cp1_a, cp1_b = checkpoint("MENU_CAMP: SpawnAmadan entry, existing camp owners:", arrlen, "ReturnValue")

# Length of CampActors read back AFTER the add, via a second pure Array_Length on the same Get.
arrlen2 = add(ARRLEN_T)
setf(arrlen2, "TargetArray", "PinType.PinSubCategoryObject",
     '''"/Script/CoreUObject.Class'/Script/Engine.Actor'"''')
connect(campactors, "CampActors", arrlen2, "TargetArray")
cp2_a, cp2_b = checkpoint("MENU_CAMP: registered spawn point, CampActors now:", arrlen2, "ReturnValue")

# --- exec spine ------------------------------------------------------------
connect_exec(event, gac, "then", "execute")
connect_exec(gac, cp1_a, "then", "execute")
connect_exec(cp1_b, ite)
connect_exec(ite, spawn_camp, "then", "execute")
connect_exec(spawn_camp, spawn_point)
connect_exec(spawn_point, arrayadd)
connect_exec(arrayadd, cp2_a)
connect_exec(cp2_b, spawn_terr)

# --- data ------------------------------------------------------------------
connect(gac, "OutActors", arrlen, "TargetArray")
connect(arrlen, "ReturnValue", eq0, "A")
connect(eq0, "ReturnValue", ite, "Condition")
connect(spawn_camp, "ReturnValue", getcomp, "self")
connect(getcomp, "ReturnValue", campactors, "self")
connect(campactors, "CampActors", arrayadd, "TargetArray")
connect(spawn_point, "ReturnValue", arrayadd, "NewItem")

for n, x, y in [
    (event, -1900, 0), (gac, -1680, 0), (arrlen, -1500, 240), (eq0, -1140, 240),
    (cp1_a, -1440, 0), (cp1_b, -1200, 0), (ite, -940, 0), (xform, -940, 460),
    (spawn_camp, -680, 0), (getcomp, -420, 320), (spawn_point, -400, 0),
    (campactors, -180, 320), (arrayadd, 60, 0), (arrlen2, 60, 320),
    (cp2_a, 300, 0), (cp2_b, 540, 0), (spawn_terr, 800, 0),
]:
    n.set_position(x, y)

out = G / "spawnamadan_camp_trio_s22.t3d"
out.write_text(g.render(), encoding="utf-8")

links = {}
for n in g.nodes:
    for p in n.pins:
        for tn, tp in p.links:
            links.setdefault((n.name, p.pin_id), []).append((tn, tp))
problems = [f"{n.name}.{p.name} -> {tn} {tp}"
            for n in g.nodes for p in n.pins for tn, tp in p.links
            if (n.name, p.pin_id) not in links.get((tn, tp), [])]
print(f"wrote {out.name}: {len(g.nodes)} nodes, {sum(len(v) for v in links.values())} link-ends")
print("pin-reciprocity problems:", problems or "none")
