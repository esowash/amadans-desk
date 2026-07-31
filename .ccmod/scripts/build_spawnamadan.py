"""Author Menu_ModController::SpawnAmadan - spawns Amadan once at a fixed spot (anchored on
the Desk's location) and sets his SpawnTableID so his appearance resolves from the SpawnDataTable
row, guarded so a relaunch doesn't spawn a second copy.

All pieces below are cloned from REAL captures, not hand-typed guesses:
- GetAllActorsOfClass(BP_PL_Table_Strategy_Amadan) + GetArrayItem[0] -> lifted verbatim from
  W_AmadanMenu's own Desk-anchor pattern (amadanmenu_benchnames_fix.t3d), already correctly
  targeted, zero retargeting needed.
- SpawnActorFromClass, DynamicCast(->HumanoidNPC_Character_Amadan), GetActorFeetLocation,
  MakeTransform, SetCharacterSpawnTableID -> from the user's own hand-added probe capture
  (amadan_spawntableid_probe.t3d) - real pin shapes, not guessed.
- Array_Length / EqualEqual_IntInt / IfThenElse -> real precedent already used elsewhere in
  this project's captured graphs (or the same synthetic IfThenElse template
  build_menu_gather_functions.py already established as safe).
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

AMADAN_BGC = '''"/Script/Engine.BlueprintGeneratedClass'/Game/Mods/Menu/HumanoidNPC_Character_Amadan.HumanoidNPC_Character_Amadan_C'"'''
AMADAN_CLASS_PATH = '"/Game/Mods/Menu/HumanoidNPC_Character_Amadan.HumanoidNPC_Character_Amadan_C"'


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

GAC_DESK_T = find_template_by_pin_field(bench_src, "ActorClass", "DefaultObject", "BP_PL_Table_Strategy_Amadan")
GETITEM_DESK_T = find_template_by_pin_field(bench_src, "Array", "PinType.PinSubCategoryObject", "BP_PL_Table_Strategy_Amadan")

SPAWN_T = find_node_by_class(probe_src, "K2Node_SpawnActorFromClass")
CAST_T = find_node_by_class(probe_src, "K2Node_DynamicCast")
FEETLOC_T = find_template_by_raw(probe_src, 'MemberName="GetActorFeetLocation"')
MAKETRANSFORM_T = find_template_by_raw(probe_src, 'MemberName="MakeTransform"')
SETID_T = find_template_by_raw(probe_src, 'MemberName="SetCharacterSpawnTableID"')

ARRLEN_T = find_template_by_raw(filter_src, 'MemberName="Array_Length"')
EQ0_T = find_template_by_raw(addrule_src, 'MemberName="EqualEqual_IntInt"')

KNOT_T = parse(open(CCMOD + r"\library\flow\knot.t3d", encoding="utf-8-sig").read())

IFTHENELSE_RAW = '''Begin Object Class=/Script/BlueprintGraph.K2Node_IfThenElse Name="K2Node_IfThenElse_0"
   NodeGuid=00000000000000000000000000000000
   CustomProperties Pin (PinId=00000000000000000000000000000001,PinName="execute",PinType.PinCategory="exec",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False,)
   CustomProperties Pin (PinId=00000000000000000000000000000002,PinName="Condition",PinType.PinCategory="bool",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,DefaultValue="true",AutogeneratedDefaultValue="true",PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False,)
   CustomProperties Pin (PinId=00000000000000000000000000000003,PinName="then",PinFriendlyName=NSLOCTEXT("K2Node", "true", "true"),Direction="EGPD_Output",PinType.PinCategory="exec",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False,)
   CustomProperties Pin (PinId=00000000000000000000000000000004,PinName="else",PinFriendlyName=NSLOCTEXT("K2Node", "false", "false"),Direction="EGPD_Output",PinType.PinCategory="exec",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False,)
End Object'''
IFTHENELSE_T = parse(IFTHENELSE_RAW)

g = Graph()


def add(t):
    return instantiate(t, g)[0]


knot_exec = add(KNOT_T)
for pn in ("InputPin", "OutputPin"):
    setf(knot_exec, pn, "PinType.PinCategory", '"exec"')
    setf(knot_exec, pn, "PinType.PinSubCategoryObject", "None")

gac_check = add(GAC_DESK_T)
setf(gac_check, "ActorClass", "DefaultObject", AMADAN_CLASS_PATH)
setf(gac_check, "OutActors", "PinType.PinSubCategoryObject", AMADAN_BGC, output=True)

arrlen = add(ARRLEN_T)
setf(arrlen, "TargetArray", "PinType.PinCategory", '"object"')
setf(arrlen, "TargetArray", "PinType.PinSubCategoryObject", AMADAN_BGC)
setf(arrlen, "TargetArray", "PinType.ContainerType", "Array")

eq0 = add(EQ0_T)
ite = add(IFTHENELSE_T)

gac_desk = add(GAC_DESK_T)
getitem_desk = add(GETITEM_DESK_T)
feetloc = add(FEETLOC_T)
maketransform = add(MAKETRANSFORM_T)
spawn = add(SPAWN_T)
setf(spawn, "Class", "DefaultObject", AMADAN_CLASS_PATH)
setf(spawn, "CollisionHandlingOverride", "DefaultValue", '"AdjustIfPossibleButAlwaysSpawn"')

cast = add(CAST_T)
setid = add(SETID_T)
setf(setid, "SpawnTableID", "DefaultValue", '"Amadan"')

# --- exec spine ----------------------------------------------------------
connect(knot_exec, "OutputPin", gac_check, "execute")
connect_exec(gac_check, ite, "then", "execute")
connect_exec(ite, gac_desk, "then", "execute")
connect_exec(gac_desk, spawn, "then", "execute")
connect_exec(spawn, cast, "then", "execute")
connect_exec(cast, setid, "then", "execute")

# --- data ------------------------------------------------------------------
connect(gac_check, "OutActors", arrlen, "TargetArray")
connect(arrlen, "ReturnValue", eq0, "A")
connect(eq0, "ReturnValue", ite, "Condition")

connect(gac_desk, "OutActors", getitem_desk, "Array")
connect(getitem_desk, "Output", feetloc, "Actor")
connect(feetloc, "FeetLocation", maketransform, "Location")
connect(maketransform, "ReturnValue", spawn, "SpawnTransform")
connect(spawn, "ReturnValue", cast, "Object")
connect(cast, "AsHumanoid NPC Character Amadan", setid, "self")

out_path = MOD + r"\.ccmod\graphs\menu_spawnamadan_body.t3d"
open(out_path, "w", encoding="utf-8").write(g.render())
print("wrote", out_path, "-", len(g.nodes), "nodes")
