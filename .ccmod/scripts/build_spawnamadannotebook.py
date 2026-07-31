"""Author Menu_ModController::SpawnAmadanNotebook - spawns the notebook placeable once at a
fixed spot beside Amadan, guarded so a relaunch doesn't spawn a second copy.

Pared down from build_spawnamadan.py's own precedent: no DynamicCast/SetCharacterSpawnTableID
needed here (the notebook isn't a character, its Feat-grant logic lives entirely on the
BP_interactable_clientside component already configured in the editor - nothing left to set from
code). Everything else (guard pattern, GetAllActorsOfClass/GetArrayItem/MakeTransform/
SpawnActorFromClass templates) reuses the exact real-captured pieces build_spawnamadan.py already
proved compile clean.

Spawn location is the REAL recorded position of BP_PL_PapyrusScroll_Journal already placed in this
save (~160 units from Amadan's own hardcoded spot), from stocker-amadan-npc memory - not guessed.
"""
import sys

import os, pathlib
CCMOD = os.environ.get("CCMOD_HOME") or str(pathlib.Path(__file__).resolve().parents[3] / "claude-conan-modder")
sys.path.insert(0, CCMOD)
from ccmod.t3d import parse, connect, connect_exec
from ccmod.t3d.generator import instantiate
from ccmod.t3d.model import Graph
import copy

import pathlib
MOD = str(pathlib.Path(__file__).resolve().parents[2])

# Confirmed by the user: Save-As clone of BP_interactable_teachmultipleemotes, named BP_AmadanNotebook,
# saved into Menu/Local, compiled clean.
NOTEBOOK_BGC = '''"/Script/Engine.BlueprintGeneratedClass'/Game/Mods/Menu/BP_AmadanNotebook.BP_AmadanNotebook_C'"'''
NOTEBOOK_CLASS_PATH = '"/Game/Mods/Menu/BP_AmadanNotebook.BP_AmadanNotebook_C"'

# Real recorded position of the journal prop already placed in this save (stocker-amadan-npc memory).
NOTEBOOK_LOCATION = '"-99862.15, 4269.24, -3856.33"'


def pin(n, name, output=None):
    p = n.pin_by_name(name, output=output)
    assert p, f"{n.name} has no pin {name}"
    return p


def setf(n, pn, k, raw, output=None):
    pin(n, pn, output=output)._set(k, raw)


def find_node_by_class(src_graph, class_needle):
    for n in src_graph.nodes:
        if class_needle in n.begin_line:
            nn = copy.deepcopy(n)
            for p in nn.pins:
                p.links = []
            return Graph(nodes=[nn])
    raise KeyError(class_needle)


def find_template_by_raw(src_graph, needle):
    for n in src_graph.nodes:
        raw = " ".join(t for k, t in n.body if k == "raw")
        if needle in raw:
            nn = copy.deepcopy(n)
            for p in nn.pins:
                p.links = []
            return Graph(nodes=[nn])
    raise KeyError(needle)


def find_template_by_pin_field(src_graph, pin_name, field, needle):
    for n in src_graph.nodes:
        p = n.pin_by_name(pin_name)
        if p and needle in (p._get(field) or ""):
            nn = copy.deepcopy(n)
            for pp in nn.pins:
                pp.links = []
            return Graph(nodes=[nn])
    raise KeyError((pin_name, field, needle))


bench_src = parse(open(MOD + r"\.ccmod\graphs\amadanmenu_benchnames_fix.t3d", encoding="utf-8-sig").read())
probe_src = parse(open(MOD + r"\.ccmod\graphs\amadan_spawntableid_probe.t3d", encoding="utf-8-sig").read())
filter_src = parse(open(MOD + r"\.ccmod\graphs\amadanmenu_itemsearch_filter.t3d", encoding="utf-8-sig").read())
addrule_src = parse(open(MOD + r"\.ccmod\graphs\addkeeprule_persist_save.t3d", encoding="utf-8-sig").read())
spawnamadan_src = parse(open(MOD + r"\.ccmod\graphs\amadan_spawnamadan_fixed_location.t3d", encoding="utf-8-sig").read())
beginplay_src = parse(open(MOD + r"\.ccmod\graphs\menu_beginplay_spawnamadan_spliced.t3d", encoding="utf-8-sig").read())

# Reuse the already-proven GetAllActorsOfClass / GetArrayItem shape (retargeted below) and the
# real MakeTransform + SpawnActorFromClass node shapes straight from SpawnAmadan's own body.
GAC_T = find_template_by_pin_field(bench_src, "ActorClass", "DefaultObject", "BP_PL_Table_Strategy_Amadan")
ARRLEN_T = find_template_by_raw(filter_src, 'MemberName="Array_Length"')
EQ0_T = find_template_by_raw(addrule_src, 'MemberName="EqualEqual_IntInt"')
MAKETRANSFORM_T = find_template_by_raw(spawnamadan_src, 'MemberName="MakeTransform"')
SPAWN_T = find_node_by_class(spawnamadan_src, "K2Node_SpawnActorFromClass")
PRINT_T = find_template_by_raw(beginplay_src, 'MemberName="PrintString"')

IFTHENELSE_RAW = '''Begin Object Class=/Script/BlueprintGraph.K2Node_IfThenElse Name="K2Node_IfThenElse_0"
   NodeGuid=00000000000000000000000000000000
   CustomProperties Pin (PinId=00000000000000000000000000000001,PinName="execute",PinType.PinCategory="exec",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False,)
   CustomProperties Pin (PinId=00000000000000000000000000000002,PinName="Condition",PinType.PinCategory="bool",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,DefaultValue="true",AutogeneratedDefaultValue="true",PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False,)
   CustomProperties Pin (PinId=00000000000000000000000000000003,PinName="then",PinFriendlyName=NSLOCTEXT("K2Node", "true", "true"),Direction="EGPD_Output",PinType.PinCategory="exec",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False,)
   CustomProperties Pin (PinId=00000000000000000000000000000004,PinName="else",PinFriendlyName=NSLOCTEXT("K2Node", "false", "false"),Direction="EGPD_Output",PinType.PinCategory="exec",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False,)
End Object'''
IFTHENELSE_T = parse(IFTHENELSE_RAW)

KNOT_T = parse(open(CCMOD + r"\library\flow\knot.t3d", encoding="utf-8-sig").read())

g = Graph()


def add(t):
    return instantiate(t, g)[0]


# Entry knot - the function's own FunctionEntry can't be pasted (standing project rule), so this
# knot is the real splice point: after paste, hand-wire FunctionEntry.then -> this knot's InputPin.
knot_entry = add(KNOT_T)
for pn in ("InputPin", "OutputPin"):
    setf(knot_entry, pn, "PinType.PinCategory", '"exec"')
    setf(knot_entry, pn, "PinType.PinSubCategoryObject", "None")

# --- guard: don't spawn a second copy on relaunch ---------------------------
gac_check = add(GAC_T)
setf(gac_check, "ActorClass", "DefaultObject", NOTEBOOK_CLASS_PATH)
setf(gac_check, "OutActors", "PinType.PinSubCategoryObject", NOTEBOOK_BGC, output=True)

arrlen = add(ARRLEN_T)
setf(arrlen, "TargetArray", "PinType.PinCategory", '"object"')
setf(arrlen, "TargetArray", "PinType.PinSubCategoryObject", NOTEBOOK_BGC)
setf(arrlen, "TargetArray", "PinType.ContainerType", "Array")

eq0 = add(EQ0_T)
ite = add(IFTHENELSE_T)

# --- spawn --------------------------------------------------------------
maketransform = add(MAKETRANSFORM_T)
setf(maketransform, "Location", "DefaultValue", NOTEBOOK_LOCATION)

spawn = add(SPAWN_T)
setf(spawn, "Class", "DefaultObject", NOTEBOOK_CLASS_PATH)
setf(spawn, "ReturnValue", "PinType.PinSubCategoryObject", NOTEBOOK_BGC, output=True)
setf(spawn, "CollisionHandlingOverride", "DefaultValue", '"AdjustIfPossibleButAlwaysSpawn"')

# Debug checkpoint - first-ever playtest of this function, per this project's own standing rule
# (never debug a cold function blind after a multi-minute cook cycle).
print_spawned = add(PRINT_T)
setf(print_spawned, "InString", "DefaultValue", '"NOTEBOOK_SPAWN: notebook placed at fixed location"')

# --- exec spine ----------------------------------------------------------
connect(knot_entry, "OutputPin", gac_check, "execute")
connect_exec(gac_check, ite, "then", "execute")
connect_exec(ite, spawn, "then", "execute")
connect_exec(spawn, print_spawned, "then", "execute")

# --- data ------------------------------------------------------------------
connect(gac_check, "OutActors", arrlen, "TargetArray")
connect(arrlen, "ReturnValue", eq0, "A")
connect(eq0, "ReturnValue", ite, "Condition")
connect(maketransform, "ReturnValue", spawn, "SpawnTransform")

out_path = MOD + r"\.ccmod\graphs\menu_spawnamadannotebook_body.t3d"
open(out_path, "w", encoding="utf-8").write(g.render())
print("wrote", out_path, "-", len(g.nodes), "nodes")
