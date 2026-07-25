"""Author RestockManagedStations() on Menu_ModController -- the verified pass-2 restock port
(session 15 full BFS trace, see stocker-menu-pivot memory). Void function, no params, no return --
only ONE hand-wire needed (Entry.then -> the start of this body).

Structure (fully traced, not guessed):
  ForEachLoop(KeepRulesV2) as Rule
    Break Rule -> Container/TemplateID/Keep/KeepAll
    GetGameMode -> Cast(BaseGameModeInterface) -> GetActorByUniqueID(Container) -> Station
    ApplyKeepRule(Station, Rule.TemplateID, Rule.Keep, Rule.KeepAll, Candidates=ManagedContainers)

Unlike tidy, restock is fully generic per-rule -- no station-scoping, no RuleTemplateID, uses each
rule's own Keep/KeepAll directly (not hardcoded).
"""
import copy
import sys

CCMOD = r"<CCMOD_HOME>"
sys.path.insert(0, CCMOD)
from ccmod.t3d import parse, connect, connect_exec, auto_layout
from ccmod.t3d.generator import instantiate
from ccmod.t3d.model import Graph

MOD = r"<MOD_ROOT>"
LIB = CCMOD + r"\library"
WLIB = MOD + r"\.ccmod\library"
SRC_GRAPH = MOD + r"\.ccmod\graphs\stocker_modcontroller_probe_a_live.t3d"

PLACEABLE_BGC = '''"/Script/Engine.BlueprintGeneratedClass'/Game/Systems/Building/Placeables/BP_PlaceableItemContainer.BP_PlaceableItemContainer_C'"'''
KEEPRULE_STRUCT = '''"/Script/CoreUObject.UserDefinedStruct'/Game/Mods/Menu/S_KeepRule.S_KeepRule'"'''
MENU_MC_BGC = '''"/Script/Engine.BlueprintGeneratedClass'/Game/Mods/Menu/Menu_ModController.Menu_ModController_C'"'''
MENU_BPFL_BGC = '''"/Script/Engine.BlueprintGeneratedClass'/Game/Mods/Menu/BPFL_Stocker2.BPFL_Stocker2_C'"'''
MENU_BPFL_DEFAULT = '"/Game/Mods/Menu/BPFL_Stocker2.Default__BPFL_Stocker2_C"'


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


def find_by_raw(src_graph, needle, want_class=None):
    for n in src_graph.nodes:
        if want_class and not n.class_path.endswith(want_class):
            continue
        raw = " ".join(t for k, t in n.body if k == "raw")
        if needle in raw:
            nn = copy.deepcopy(n)
            for p in nn.pins:
                p.links = []
            return Graph(nodes=[nn])
    raise KeyError(needle)


def find_all_by_raw(src_graph, needle, want_class=None):
    out = []
    for n in src_graph.nodes:
        if want_class and not n.class_path.endswith(want_class):
            continue
        raw = " ".join(t for k, t in n.body if k == "raw")
        if needle in raw:
            nn = copy.deepcopy(n)
            for p in nn.pins:
                p.links = []
            out.append(Graph(nodes=[nn]))
    return out


src = parse(open(SRC_GRAPH, encoding="utf-8-sig").read())

KNOT_T = tmpl_file(LIB + r"\flow\knot.t3d")
FEACH_T = tmpl_file(LIB + r"\flow\foreach.t3d")
GETGAMEMODE_T = tmpl_file(LIB + r"\actor\get_game_mode.t3d")
CAST_T = tmpl_file(LIB + r"\actor\cast_to_basegamemode_interface.t3d")
GETACTOR_T = tmpl_file(LIB + r"\actor\get_actor_by_unique_id.t3d")
GET_CONTAINERS_T = tmpl_file(WLIB + r"\stocker\get_managed_containers.t3d")
GET_KEEPRULESV2_T = tmpl_file(WLIB + r"\stocker\get_keeprules_v2.t3d")

BREAKSTRUCT_T = find_by_raw(src, "S_KeepRule.S_KeepRule", want_class="K2Node_BreakStruct")
# two ApplyKeepRule calls exist -- take the SECOND one found (the restock call, Keep/KeepAll wired
# from the broken rule, not the tidy call whose Keep/KeepAll are hardcoded 0/false)
APPLYKEEPRULE_T = find_all_by_raw(src, 'MemberName="ApplyKeepRule"', want_class="K2Node_CallFunction")[1]

SEQ_T = find_by_raw(src, "", want_class="K2Node_ExecutionSequence")
PRINT_T = find_by_raw(src, 'MemberName="PrintString"', want_class="K2Node_CallFunction")
LEN_T = find_by_raw(src, "Array_Length", want_class="K2Node_CallArrayFunction")
CONV_T = find_by_raw(src, "Conv_IntToString", want_class="K2Node_CallFunction")


def make_print(text):
    n = add(PRINT_T)
    setf(n, "InString", "DefaultValue", f'"{text}"')
    return n


def make_count_print(label, array_node, array_pin_name, array_category, array_subobj):
    alen = add(LEN_T)
    setf(alen, "TargetArray", "PinType.PinCategory", f'"{array_category}"')
    setf(alen, "TargetArray", "PinType.PinSubCategoryObject", array_subobj)
    setf(alen, "TargetArray", "PinType.ContainerType", "Array")
    connect(array_node, array_pin_name, alen, "TargetArray")
    conv = add(CONV_T)
    connect(alen, "ReturnValue", conv, "InInt")
    pLbl = make_print(label)
    pCount = add(PRINT_T)
    connect(conv, "ReturnValue", pCount, "InString")
    connect_exec(pLbl, pCount)
    return pLbl


def type_knot(n, category, subcat_obj="None", container="None"):
    for pn in ("InputPin", "OutputPin"):
        setf(n, pn, "PinType.PinCategory", f'"{category}"')
        setf(n, pn, "PinType.PinSubCategoryObject", subcat_obj)
        setf(n, pn, "PinType.ContainerType", container)


g = Graph()


def add(t):
    return instantiate(t, g)[0]


# ---- entry hand-wire (only one: Entry.then -> here) --------------------
knot_entry = add(KNOT_T)
type_knot(knot_entry, "exec")

# ---- loop: KeepRulesV2 as Rule -------------------------------------------
keeprules_get = add(GET_KEEPRULESV2_T)
setf(keeprules_get, "self", "PinType.PinSubCategoryObject", MENU_MC_BGC, output=False)
feach_rules = add(FEACH_T)
setf(feach_rules, "Array", "PinType.PinCategory", '"struct"')
setf(feach_rules, "Array", "PinType.PinSubCategoryObject", KEEPRULE_STRUCT)
setf(feach_rules, "Array", "PinType.ContainerType", "Array")
setf(feach_rules, "Array Element", "PinType.PinCategory", '"struct"', output=True)
setf(feach_rules, "Array Element", "PinType.PinSubCategoryObject", KEEPRULE_STRUCT, output=True)
setf(feach_rules, "Array Element", "PinType.ContainerType", "None", output=True)

break_rule = add(BREAKSTRUCT_T)
break_rule._replace_prop("StructType", KEEPRULE_STRUCT)
setf(break_rule, "S_KeepRule", "PinType.PinSubCategoryObject", KEEPRULE_STRUCT)

gamemode_get = add(GETGAMEMODE_T)
cast_gm = add(CAST_T)
getactor = add(GETACTOR_T)
containers_get = add(GET_CONTAINERS_T)
setf(containers_get, "self", "PinType.PinSubCategoryObject", MENU_MC_BGC, output=False)
apply_call = add(APPLYKEEPRULE_T)
setf(apply_call, "self", "PinType.PinSubCategoryObject", MENU_BPFL_BGC)
setf(apply_call, "self", "DefaultObject", MENU_BPFL_DEFAULT)
apply_call._replace_prop(
    "FunctionReference",
    f'(MemberParent={MENU_BPFL_BGC},MemberName="ApplyKeepRule",MemberGuid=A01F81A84B78ED10894F5EA336D8583C)',
)

# =====================  WIRING  ==========================================
seq_entry = add(SEQ_T)
connect(knot_entry, "OutputPin", seq_entry, "execute")
connect_exec(seq_entry, feach_rules, "then_0", "Exec")
print_rules = make_count_print("MENU_RESTOCK: rules to process:", keeprules_get, "KeepRulesV2", "struct", KEEPRULE_STRUCT)
connect_exec(seq_entry, print_rules, "then_1", "execute")
connect(keeprules_get, "KeepRulesV2", feach_rules, "Array")

print_castfail = make_print("MENU_RESTOCK: GetGameMode cast to BaseGameModeInterface FAILED")
connect_exec(cast_gm, print_castfail, "CastFailed", "execute")

connect(feach_rules, "Array Element", break_rule, "S_KeepRule")
connect_exec(feach_rules, cast_gm, "LoopBody", "execute")
connect(gamemode_get, "ReturnValue", cast_gm, "Object")
connect_exec(cast_gm, getactor, "then", "execute")
connect(cast_gm, "AsBase Game Mode Interface", getactor, "self")
connect(break_rule, "Container_4_62E0F0614C1CC5F95CAE6B97F57E9504", getactor, "UniqueID")

connect_exec(getactor, apply_call, "then", "execute")
connect(getactor, "Actor", apply_call, "Station")
connect(break_rule, "TemplateID_6_7331DAFA4369B9E2C105A59FAAA510CD", apply_call, "TemplateID")
connect(break_rule, "Keep_8_5132904E4CC17522C07075A43E93B26E", apply_call, "Keep")
connect(break_rule, "KeepAll_10_A6025F204FE4948B8C46EE8626A13B30", apply_call, "KeepAll")
connect(containers_get, "ManagedContainers", apply_call, "Candidates")

auto_layout(g.nodes, origin=(0, 0), dx=260, dy=200, per_column=6)

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

out = MOD + r"\.ccmod\graphs\menu_restockmanagedstations_body.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"RestockManagedStations: nodes={len(g.nodes)} wrote={out} problems={len(problems)}")
for pr in problems:
    print("  !", pr)
print(f"  knot -> exec(entry.then) = {knot_entry.name}")
