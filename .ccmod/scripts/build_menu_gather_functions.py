"""Author the two independent sweep-gather function bodies for Menu_ModController:
GatherNearbyStorageContainers (keeps the storage-component branch -> ManagedContainers)
GatherNearbyBenches (keeps the complement branch -> ManagedStations).

Each is a fresh, self-contained GetAllActorsOfClass(BP_PlaceableItemContainer) + ForEachLoop +
range-gate + storage-component-gate, mirroring the traced Stocker_ModController BeginPlay sweep
(session 15 data-pin trace) but as two independent functions per the user's explicit "separate
functions, full stop" call, each with its own Array_Clear so repeated calls (menu-open / sweep
tick) don't accumulate duplicates.

Entry/Result nodes can't be pasted (K2Node_FunctionEntry / K2Node_FunctionResult), so every pin
that must hand-wire to a real one goes through a Knot -- per the user's ask this session, knots at
EVERY hand-wire point, not just fan-out, matching the established convention.
"""
import copy
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
WLIB = MOD + r"\.ccmod\library"
SRC_GRAPH = MOD + r"\.ccmod\graphs\stocker_modcontroller_probe_a_live.t3d"

PLACEABLE_BGC = '''"/Script/Engine.BlueprintGeneratedClass'/Game/Systems/Building/Placeables/BP_PlaceableItemContainer.BP_PlaceableItemContainer_C'"'''
STORAGE_BGC = '''"/Script/Engine.BlueprintGeneratedClass'/Game/Systems/Building/BuildingActorComponents/BP_BAC_Storage.BP_BAC_Storage_C'"'''
MENU_MC_BGC = '''"/Script/Engine.BlueprintGeneratedClass'/Game/Mods/Menu/Menu_ModController.Menu_ModController_C'"'''


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


src = parse(open(SRC_GRAPH, encoding="utf-8-sig").read())

KNOT_T = tmpl_file(LIB + r"\flow\knot.t3d")
FEACH_T = tmpl_file(LIB + r"\flow\foreach.t3d")
ADD_T = tmpl_file(LIB + r"\array\array_add.t3d")
CLEAR_T = tmpl_file(LIB + r"\actor\array_clear_int.t3d")
GDT_T = tmpl_file(LIB + r"\actor\get_distance_to.t3d")
GCBC_T = tmpl_file(LIB + r"\actor\get_component_by_class.t3d")
ISVALID_T = tmpl_file(LIB + r"\call\is_valid.t3d")
GET_CONTAINERS_T = tmpl_file(WLIB + r"\stocker\get_managed_containers.t3d")
GET_STATIONS_T = tmpl_file(WLIB + r"\stocker\get_managed_stations.t3d")

# Extracted directly from the traced live graph -- the one GetAllActorsOfClass whose
# ActorClass filter is BP_PlaceableItemContainer (not the Desk/Wood/Furnace ones), and the
# Less_DoubleDouble used for the range gate. No dedicated shared-library template exists yet.
GAC_T = find_template_by_pin_field(src, "ActorClass", "DefaultObject", "BP_PlaceableItemContainer.BP_PlaceableItemContainer_C")
LESSD_T = find_template_by_raw(src, 'MemberName="Less_DoubleDouble"')

IFTHENELSE_RAW = '''Begin Object Class=/Script/BlueprintGraph.K2Node_IfThenElse Name="K2Node_IfThenElse_0"
   NodeGuid=00000000000000000000000000000000
   CustomProperties Pin (PinId=00000000000000000000000000000001,PinName="execute",PinType.PinCategory="exec",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False,)
   CustomProperties Pin (PinId=00000000000000000000000000000002,PinName="Condition",PinType.PinCategory="bool",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,DefaultValue="true",AutogeneratedDefaultValue="true",PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False,)
   CustomProperties Pin (PinId=00000000000000000000000000000003,PinName="then",PinFriendlyName=NSLOCTEXT("K2Node", "true", "true"),Direction="EGPD_Output",PinType.PinCategory="exec",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False,)
   CustomProperties Pin (PinId=00000000000000000000000000000004,PinName="else",PinFriendlyName=NSLOCTEXT("K2Node", "false", "false"),Direction="EGPD_Output",PinType.PinCategory="exec",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False,)
End Object'''
IFTHENELSE_T = parse(IFTHENELSE_RAW)


def type_knot(n, category, subcat_obj="None", container="None"):
    for pn in ("InputPin", "OutputPin"):
        setf(n, pn, "PinType.PinCategory", f'"{category}"')
        setf(n, pn, "PinType.PinSubCategoryObject", subcat_obj)
        setf(n, pn, "PinType.ContainerType", container)


def type_array_pin(n, pn, subobj_raw, container, output=None):
    setf(n, pn, "PinType.PinCategory", '"object"', output=output)
    setf(n, pn, "PinType.PinSubCategoryObject", subobj_raw, output=output)
    setf(n, pn, "PinType.ContainerType", container, output=output)


def build(member_name, keep_branch, func_name, out_path):
    g = Graph()

    def add(t):
        return instantiate(t, g)[0]

    # Input-side knots (land under the real FunctionEntry, left edge of the graph).
    knot_exec = add(KNOT_T)
    knot_anchor = add(KNOT_T)
    knot_range = add(KNOT_T)

    type_knot(knot_exec, "exec")
    type_knot(knot_anchor, "object", '''"/Script/CoreUObject.Class'/Script/Engine.Actor'"''')
    type_knot(knot_range, "real", "None")
    setf(knot_range, "InputPin", "PinType.PinSubCategory", '"double"')
    setf(knot_range, "OutputPin", "PinType.PinSubCategory", '"double"')

    clear_get = add(GET_CONTAINERS_T if member_name == "ManagedContainers" else GET_STATIONS_T)
    clear_call = add(CLEAR_T)
    gac = add(GAC_T)
    feach = add(FEACH_T)
    gdt = add(GDT_T)
    lessd = add(LESSD_T)
    ite_range = add(IFTHENELSE_T)
    gcbc = add(GCBC_T)
    isvalid = add(ISVALID_T)
    ite_storage = add(IFTHENELSE_T)
    add_get = add(GET_CONTAINERS_T if member_name == "ManagedContainers" else GET_STATIONS_T)
    add_call = add(ADD_T)
    return_get = add(GET_CONTAINERS_T if member_name == "ManagedContainers" else GET_STATIONS_T)

    # Output-side knots (land next to the real Return node) -- added last so
    # auto_layout's column-wrap naturally places them at the right edge of the
    # graph, not stacked with the input knots on the left (user feedback,
    # session 15: output knots belong on the right, inputs stay on the left).
    knot_completed = add(KNOT_T)
    knot_return = add(KNOT_T)
    type_knot(knot_completed, "exec")
    type_knot(knot_return, "object", PLACEABLE_BGC, "Array")

    # retype the wildcard/int templates to BP_PlaceableItemContainer
    type_array_pin(feach, "Array", PLACEABLE_BGC, "Array")
    setf(feach, "Array Element", "PinType.PinCategory", '"object"', output=True)
    setf(feach, "Array Element", "PinType.PinSubCategoryObject", PLACEABLE_BGC, output=True)
    type_array_pin(clear_call, "TargetArray", PLACEABLE_BGC, "Array")
    type_array_pin(add_call, "TargetArray", PLACEABLE_BGC, "Array")
    setf(add_call, "NewItem", "PinType.PinCategory", '"object"')
    setf(add_call, "NewItem", "PinType.PinSubCategoryObject", PLACEABLE_BGC)
    setf(gcbc, "ComponentClass", "DefaultObject", STORAGE_BGC)

    # retarget the hidden self pins on the two ModController variable-getters to Menu
    for n in (clear_get, add_get, return_get):
        setf(n, "self", "PinType.PinSubCategoryObject", MENU_MC_BGC, output=False)

    # --- exec spine --------------------------------------------------------
    connect(knot_exec, "OutputPin", clear_call, "execute")
    connect_exec(clear_call, gac)
    connect_exec(gac, feach, "then", "Exec")
    connect(gac, "OutActors", feach, "Array")
    connect_exec(feach, ite_range, "LoopBody", "execute")
    connect_exec(ite_range, ite_storage, "then", "execute")
    connect_exec(ite_storage, add_call, keep_branch, "execute")
    connect(feach, "Completed", knot_completed, "InputPin")

    # --- data: range gate ----------------------------------------------------
    connect(feach, "Array Element", gdt, "self")
    connect(knot_anchor, "OutputPin", gdt, "OtherActor")
    connect(gdt, "ReturnValue", lessd, "A")
    connect(knot_range, "OutputPin", lessd, "B")
    connect(lessd, "ReturnValue", ite_range, "Condition")

    # --- data: storage-component gate --------------------------------------
    connect(feach, "Array Element", gcbc, "self")
    connect(gcbc, "ReturnValue", isvalid, "Object")
    connect(isvalid, "ReturnValue", ite_storage, "Condition")

    # --- data: clear / add / return ----------------------------------------
    connect(clear_get, member_name, clear_call, "TargetArray")
    connect(add_get, member_name, add_call, "TargetArray")
    connect(feach, "Array Element", add_call, "NewItem")
    connect(return_get, member_name, knot_return, "InputPin")

    auto_layout(g.nodes, origin=(0, 0), dx=260, dy=220, per_column=6)

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

    open(out_path, "w", encoding="utf-8").write(g.render())
    print(f"{func_name}: nodes={len(g.nodes)} wrote={out_path} problems={len(problems)}")
    for pr in problems:
        print("  !", pr)
    print(f"  knots -> exec(entry.then)={knot_exec.name} anchor(entry.AnchorActor)={knot_anchor.name} "
          f"range(entry.Range)={knot_range.name} completed(->Return exec)={knot_completed.name} "
          f"returnvalue(->Return data)={knot_return.name}")


build("ManagedContainers", "then", "GatherNearbyStorageContainers",
      MOD + r"\.ccmod\graphs\menu_gathernearbystoragecontainers_body.t3d")
build("ManagedStations", "else", "GatherNearbyBenches",
      MOD + r"\.ccmod\graphs\menu_gathernearbybenches_body.t3d")
