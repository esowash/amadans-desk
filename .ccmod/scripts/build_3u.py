"""Author stocker_3u.t3d -- fix the "ruled anywhere = protected everywhere" bug.

Operates on the FULL live graph (pull-edit-repaste), per stocker-full-graph-edits.

THE BUG (found this session, 3T's playtest): RuleTemplateID was a GLOBAL cache
-- every TemplateID across ALL of KeepRulesV2, regardless of which station a
rule names. So an item ruled for Station A becomes invisible to tidy at every
OTHER station too, even where no rule governs it -- and restock only ever
touches the specific station a rule names, so that item at Station B is
skipped by tidy AND ignored by restock. Not corrupted, just administratively
forgotten. Confirmed in play: Metal's Silk (ruled only via a Wood-station
rule) was touched by nothing.

THE FIX (design discussion, user's framing): tidy's implicit-deny fallback
("if nothing rules it, sweep it away") was always correct -- the MATCH was
too coarse. Firewall analogy: a rule needs to match on the full tuple
(station, item), not just item. Rebuild RuleTemplateID PER STATION instead of
once globally: for each station, only include a rule's TemplateID if that
rule's Container ACTUALLY RESOLVES to the station currently being tidied.

Mechanism: move the GameMode+Interface cast (previously built only for the
restock pass, firing after pass 1) to fire right after seeding instead,
BEFORE pass 1 -- its output (the resolved interface) is a data value, safe to
read by multiple consumers regardless of when it was computed, as long as
it's computed before anyone reads it. Then, inside the outer per-station
loop, before tidying that station's items: Clear RuleTemplateID, ForEach
KeepRulesV2, Break each rule, resolve its Container via the SAME
GetActorByUniqueID round-trip proven in 3P, compare to the CURRENT station
via NotEqual_ObjectObject, and only Array_Add the TemplateID if they match.

New order: seed KeepRulesV2 -> GameMode+Cast (moved earlier) -> pass 1: for
each station { rebuild RuleTemplateID scoped to THIS station -> tidy this
station's items } -> restock (identity-resolved, unchanged) -> 3O -> 3P.

The old GLOBAL cache-rebuild (Array_Clear + ForEach KeepRulesV2 + Array_Add,
~4 nodes) becomes unreachable once its trigger points are rerouted below, and
gets removed by the same mark-and-sweep GC used in 3R -- safer than manually
enumerating nodes.

BEHAVIOUR CHANGE, deliberate: Metal's Silk (previously untouched forever)
will now be correctly recognised as unruled AT METAL and tidied away to
storage on the next run.
"""
import sys
import copy as _copy

import os, pathlib
CCMOD = os.environ.get("CCMOD_HOME") or str(pathlib.Path(__file__).resolve().parents[3] / "claude-conan-modder")
sys.path.insert(0, CCMOD)
from ccmod import db
from ccmod.t3d import parse, connect, connect_exec
from ccmod.t3d.generator import instantiate
from ccmod.t3d.model import Graph
from ccmod.workspace import Workspace

import pathlib
MOD = str(pathlib.Path(__file__).resolve().parents[2])
LIB = CCMOD + r"\library"
WLIB = MOD + r"\.ccmod\library"

ws = Workspace.resolve()
conn = db.connect(ws.cache_db)
row = conn.execute("SELECT t3d FROM graphs WHERE name=?", ("stocker_3u_base",)).fetchone()
assert row, "run `ccmod pull --save stocker_3u_base` first"
g = parse(row[0])
print("pulled nodes:", len(g.nodes))


def pin(n, name):
    p = n.pin_by_name(name)
    assert p, f"{n.name} has no pin {name}"
    return p


def tmpl_file(path):
    t = parse(open(path, encoding="utf-8-sig").read())
    for n in t.nodes:
        for p in n.pins:
            p.links = []
    return t


def add(t):
    return instantiate(t, g)[0]


def setf(n, pn, k, raw):
    pin(n, pn)._set(k, raw)


def type_foreach_struct(node):
    struct_ref = ('"/Script/CoreUObject.UserDefinedStruct\'/Game/Mods/Stocker/'
                  'S_KeepRule.S_KeepRule\'"')
    setf(node, "Array", "PinType.PinCategory", '"struct"')
    setf(node, "Array", "PinType.PinSubCategoryObject", struct_ref)
    setf(node, "Array", "PinType.ContainerType", "Array")
    setf(node, "Array Element", "PinType.PinCategory", '"struct"')
    setf(node, "Array Element", "PinType.PinSubCategoryObject", struct_ref)
    setf(node, "Array Element", "PinType.ContainerType", "None")


CONTAINER_PIN = "Container_4_62E0F0614C1CC5F95CAE6B97F57E9504"
TEMPLATEID_PIN = "TemplateID_6_7331DAFA4369B9E2C105A59FAAA510CD"

# --- identify fixed structural anchors --------------------------------------
seed_end = None
for n in g.nodes:
    isp = n.pin_by_name("InString")
    if isp and isp._get("DefaultValue") == '"STOCKER_3Q seeded 2 rules"' and not isp.links:
        seed_end = n
assert seed_end

feCache = g.by_name("K2Node_MacroInstance_7")     # OLD global cache ForEach
clearNode = g.by_name("K2Node_CallArrayFunction_13")  # OLD global Array_Clear
feStations = g.by_name("K2Node_MacroInstance_9")  # outer per-station ForEach
fe1 = g.by_name("K2Node_MacroInstance_2")         # inner per-item ForEach
cast2 = g.by_name("K2Node_DynamicCast_6")         # Cast to BaseGameModeInterface
feRules = g.by_name("K2Node_MacroInstance_6")     # resolve+apply's ForEach

assert pin(seed_end, "then").links[0][0] == clearNode.name
assert pin(clearNode, "execute").links[0][0] == seed_end.name
assert pin(feCache, "Completed").links[0][0] == feStations.name
assert pin(feStations, "Exec").links[0][0] == feCache.name
assert pin(feStations, "LoopBody").links[0][0] == fe1.name
assert pin(feStations, "Completed").links[0][0] == cast2.name
assert pin(cast2, "then").links[0][0] == feRules.name

GET_RULES_T = tmpl_file(WLIB + r"\stocker\get_keeprules_v2.t3d")
BREAK_RULE_T = tmpl_file(WLIB + r"\stocker\break_keeprule.t3d")
GET_CACHE_T = tmpl_file(WLIB + r"\stocker\get_ruled_template_ids.t3d")
CLEAR_T = tmpl_file(LIB + r"\actor\array_clear_int.t3d")
ADD_T = tmpl_file(LIB + r"\array\array_add.t3d")
LOOKUP_T = tmpl_file(LIB + r"\actor\get_actor_by_unique_id.t3d")
NEQ_T = tmpl_file(LIB + r"\math\not_equal_object.t3d")

FEACH_T = None
for n in g.nodes:
    if n.class_path.endswith("K2Node_MacroInstance"):
        arr = n.pin_by_name("Array")
        if arr and arr.category == "object":
            nn = _copy.deepcopy(n)
            for p in nn.pins:
                p.links = []
            FEACH_T = Graph(nodes=[nn])
            break
assert FEACH_T

BRANCH_T = None
for n in g.nodes:
    if n.class_path.endswith("K2Node_IfThenElse"):
        nn = _copy.deepcopy(n)
        for p in nn.pins:
            p.links = []
        BRANCH_T = Graph(nodes=[nn])
        break
assert BRANCH_T

# --- rewire 1: cast2 fires right after seeding, not after pass 1 -----------
pin(seed_end, "then").links = []
pin(clearNode, "execute").links = []
pin(cast2, "execute").links = []
connect_exec(seed_end, cast2)

pin(cast2, "then").links = []
pin(feStations, "Exec").links = []
pin(feCache, "Completed").links = []
connect_exec(cast2, feStations)

pin(feStations, "Completed").links = []
pin(feRules, "Exec").links = []
connect_exec(feStations, feRules, "Completed", "Exec")

# --- build: per-station RuleTemplateID rebuild, inside feStations.LoopBody -
cacheGetClear = add(GET_CACHE_T)
clearNode2 = add(CLEAR_T)
connect(cacheGetClear, "RuleTemplateID", clearNode2, "TargetArray")

rulesGetCheck = add(GET_RULES_T)
feRulesCheck = add(FEACH_T)
type_foreach_struct(feRulesCheck)
connect(rulesGetCheck, "KeepRulesV2", feRulesCheck, "Array")

brkCheck = add(BREAK_RULE_T)
connect(feRulesCheck, "Array Element", brkCheck, "S_KeepRule")

lookupCheck = add(LOOKUP_T)
connect(cast2, "AsBase Game Mode Interface", lookupCheck, "self")
connect(brkCheck, CONTAINER_PIN, lookupCheck, "UniqueID")

neqCheck = add(NEQ_T)
connect(lookupCheck, "Actor", neqCheck, "A")
connect(feStations, "Array Element", neqCheck, "B")

branchCheck = add(BRANCH_T)
connect(neqCheck, "ReturnValue", branchCheck, "Condition")

cacheGetAdd = add(GET_CACHE_T)
addCache2 = add(ADD_T)
connect(cacheGetAdd, "RuleTemplateID", addCache2, "TargetArray")
connect(brkCheck, TEMPLATEID_PIN, addCache2, "NewItem")

# --- exec: feStations.LoopBody -> clear -> ForEach -> [match?] -> Add ------
# -> feRulesCheck.Completed -> fe1 (per-item tidy, now scoped correctly)
pin(fe1, "Exec").links = []
pin(feStations, "LoopBody").links = []
connect_exec(feStations, clearNode2, "LoopBody", "execute")
connect_exec(clearNode2, feRulesCheck, "then", "Exec")
connect_exec(feRulesCheck, lookupCheck, "LoopBody", "execute")
connect_exec(lookupCheck, branchCheck, "then", "execute")
connect_exec(branchCheck, addCache2, "else", "execute")   # NotEqual==false -> same station -> keep it ruled here
connect_exec(feRulesCheck, fe1, "Completed", "Exec")

# --- layout ------------------------------------------------------------------
cacheGetClear.set_position(-1700, -2700)
clearNode2.set_position(-1500, -2700)
rulesGetCheck.set_position(-1500, -2500)
feRulesCheck.set_position(-1300, -2700)
brkCheck.set_position(-1080, -2560)
lookupCheck.set_position(-880, -2700)
neqCheck.set_position(-680, -2560)
branchCheck.set_position(-480, -2700)
cacheGetAdd.set_position(-260, -2560)
addCache2.set_position(-260, -2700)

# --- garbage collect: mark-and-sweep reachability from the Event node ------
event = None
for n in g.nodes:
    if n.class_path.endswith("K2Node_Event"):
        event = n
        break
assert event

by_name = {n.name: n for n in g.nodes}
marked = set()


def mark(n):
    if n.name in marked:
        return
    marked.add(n.name)
    for p in n.pins:
        is_exec_out = p.is_exec and p.is_output
        is_data_in = (not p.is_exec) and (not p.is_output)
        if is_exec_out or is_data_in:
            for (tgt_name, _) in p.links:
                tgt = by_name.get(tgt_name)
                if tgt is not None:
                    mark(tgt)


mark(event)
removed = [n.name for n in g.nodes if n.name not in marked]
print(f"garbage-collecting {len(removed)} unreachable nodes:")
for name in removed:
    print("  -", name, by_name[name].class_path)
g.nodes = [n for n in g.nodes if n.name in marked]

removed_set = set(removed)
stale_dropped = 0
for n in g.nodes:
    for p in n.pins:
        kept = [(tn, tp) for (tn, tp) in p.links if tn not in removed_set]
        if len(kept) != len(p.links):
            stale_dropped += len(p.links) - len(kept)
            p.links = kept
print(f"dropped {stale_dropped} stale links pointing at removed nodes")

# --- validate ---------------------------------------------------------------
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
         if p._get("PinType.PinCategory") == '"wildcard"'
         and not n.class_path.endswith("K2Node_CallArrayFunction")]
assert not wilds, f"unresolved wildcards: {wilds}"

out = MOD + r"\.ccmod\graphs\stocker_3u.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"nodes: {len(g.nodes)}   wrote: {out}")
print(f"non-reciprocal / dangling problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
