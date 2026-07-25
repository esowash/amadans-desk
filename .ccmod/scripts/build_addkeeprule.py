"""AddKeepRule: the function body for Stocker_ModController::AddKeepRule.

New function (entry node hand-built by the user, per the standing rule that
K2Node_FunctionEntry can't be pasted). This script generates everything AFTER
the entry -- self-contained, no reference to the live FunctionEntry_0 node --
so the user does exactly 5 hand-wires from the entry's exposed pins into this
fragment (Station->cast.Object, then->cast.execute, TemplateID->rule's
TemplateID pin, Keep->rule's Keep pin, KeepAll->rule's KeepAll pin). None of
the entry's pins fan out to more than one destination, so no knots needed.

Shape: Cast(Station->BP_Master_Placeables) -> GetActorUniqueID -> Make
S_KeepRule(Container=uid, TemplateID/Keep/KeepAll from entry) -> Array_Add
into (Get) KeepRulesV2. CastFailed and success both get a confirmatory print.
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

ws = Workspace.resolve()
conn = db.connect(ws.cache_db)


def load_graph(name):
    row = db.get_graph(conn, name)
    assert row, f"no saved graph '{name}' -- run `ccmod pull --save {name}` first"
    return parse(row["t3d"])


def load_template(key):
    row = db.get_template(conn, key)
    assert row, f"no template '{key}'"
    graph = parse(row["t3d"])
    assert len(graph.nodes) == 1, f"expected single-node template for '{key}', got {len(graph.nodes)}"
    return tmpl_from(graph, graph.nodes[0].name)


def tmpl_from(graph, name):
    n = copy.deepcopy(graph.by_name(name))
    for p in n.pins:
        p.links = []
    return Graph(nodes=[n])


g = Graph(nodes=[])


def add(t):
    return instantiate(t, g)[0]


def pin(n, name):
    p = n.pin_by_name(name)
    assert p, f"{n.name} has no pin {name}"
    return p


def setf(n, pn, k, raw):
    pin(n, pn)._set(k, raw)


def setd(n, pn, v):
    setf(n, pn, "DefaultValue", f'"{v}"')


# --- templates -------------------------------------------------------------
castGraph = load_graph("stocker/cast_master_placeables")
CAST_T = tmpl_from(castGraph, "K2Node_DynamicCast_0")

UID_T = load_template("actor/get_actor_unique_id")

# Make S_KeepRule (4-field, post-KeepAll shape) -- the keepall_seed.t3d file
# has real, playtest-proven MakeStruct nodes with the KeepAll pin.
seedText = open(MOD + r"\.ccmod\graphs\keepall_seed.t3d", encoding="utf-8").read()
seedGraph = parse(seedText)
makeNodeName = next(n.name for n in seedGraph.nodes if n.class_path == "/Script/BlueprintGraph.K2Node_MakeStruct")
MAKE_RULE_T = tmpl_from(seedGraph, makeNodeName)

GET_RULES_T = load_template("stocker/get_keeprules_v2")
ADD_T = load_template("array/array_add")

exampleText = open(CCMOD + r"\library\examples\beginplay_print.t3d", encoding="utf-8").read()
exampleGraph = parse(exampleText)
PRINT_T = tmpl_from(exampleGraph, "K2Node_CallFunction_0")

CONTAINER_PIN = "Container_4_62E0F0614C1CC5F95CAE6B97F57E9504"
TEMPLATEID_PIN = "TemplateID_6_7331DAFA4369B9E2C105A59FAAA510CD"
KEEP_PIN = "Keep_8_5132904E4CC17522C07075A43E93B26E"
KEEPALL_PIN = "KeepAll_10_A6025F204FE4948B8C46EE8626A13B30"

# --- build -------------------------------------------------------------------
cast = add(CAST_T)
# execute + Object left UNLINKED -- user hand-wires from the real entry node.

uid = add(UID_T)
connect(cast, "AsBP Master Placeables", uid, "self")
connect_exec(cast, uid, "then", "execute")

rule = add(MAKE_RULE_T)
connect(uid, "UniqueID", rule, CONTAINER_PIN)
# TemplateID / Keep / KeepAll pins left UNLINKED -- hand-wired from entry.

STRUCT_REF = "/Script/CoreUObject.UserDefinedStruct'/Game/Mods/Stocker/S_KeepRule.S_KeepRule'"

getvar = add(GET_RULES_T)
addcall = add(ADD_T)
setf(addcall, "TargetArray", "PinType.PinCategory", '"struct"')
setf(addcall, "TargetArray", "PinType.PinSubCategoryObject", f'"{STRUCT_REF}"')
setf(addcall, "TargetArray", "PinType.ContainerType", "Array")
setf(addcall, "NewItem", "PinType.PinCategory", '"struct"')
setf(addcall, "NewItem", "PinType.PinSubCategoryObject", f'"{STRUCT_REF}"')
connect(getvar, "KeepRulesV2", addcall, "TargetArray")
connect(rule, "S_KeepRule", addcall, "NewItem")
connect_exec(uid, addcall, "then", "execute")

printOk = add(PRINT_T)
setd(printOk, "InString", "STOCKER_ADDRULE: rule added")
connect_exec(addcall, printOk, "then", "execute")

printFail = add(PRINT_T)
setd(printFail, "InString", "STOCKER_ADDRULE: cast to placeable failed")
connect_exec(cast, printFail, "CastFailed", "execute")

# --- layout ------------------------------------------------------------------
cast.set_position(400, 0)
uid.set_position(750, 0)
rule.set_position(1100, 100)
getvar.set_position(1100, -150)
addcall.set_position(1450, 0)
printOk.set_position(1800, 0)
printFail.set_position(750, 300)

# --- validate: every LINK inside this fragment must be reciprocal and none of
# the pins we deliberately left dangling should show up as "problems" (they
# simply have no links at all, which is fine -- they're the hand-wire points).
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

wilds = [(n.name, p.name) for n in g.nodes for p in n.pins
         if p._get("PinType.PinCategory") == '"wildcard"']
assert not wilds, f"unresolved wildcards: {wilds}"

dangling = [(n.name, p.name) for n in g.nodes for p in n.pins if not p.links]
print("intentionally dangling (hand-wire points):")
for nn, pn in dangling:
    print(f"  {nn}.{pn}")

out = MOD + r"\.ccmod\graphs\addkeeprule_body.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"\nnodes: {len(g.nodes)}   wrote: {out}")
print(f"problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
