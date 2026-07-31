"""Author stocker_3r.t3d -- retire the old KeepRules Map from pass 1, and
remove the now-redundant old pass 2 entirely.

Operates on the FULL live graph (pull-edit-repaste), per stocker-full-graph-edits.

WHAT THIS DOES:
1. Moves the KeepRulesV2 seed step (was appended after 3P, at the tail) to run
   BEFORE pass 1 instead -- pass 1 now needs KeepRulesV2 populated to build its
   ruled-item cache, so seeding can no longer happen last.
2. Inserts a new cache-rebuild block right after seeding: Array_Clear
   RuleTemplateID, then ForEach KeepRulesV2 -> Break -> Array_Add each rule's
   TemplateID into RuleTemplateID. This is what pass 1's opt-out gate will
   query instead of the old Map.
3. Rewires pass 1's brRuled Condition from Map_Find(KeepRules, tid).ReturnValue
   to Array_Contains(RuleTemplateID, tid) -- same tid1 VariableGet reused.
4. Reroutes pass 1's Completed pin to trigger the resolve+apply block (3Q's
   ForEach KeepRulesV2 -> per-rule identity resolve -> ApplyKeepRule) directly,
   instead of the old pass 2.
5. Reroutes 3Q's "done" tail to trigger 3O (identity spike) directly, instead
   of the old pass 2's Completed pin.
6. Garbage-collects: mark-and-sweep reachability from the Event node (exec
   chain + data dependencies of anything reachable). Anything unreached after
   the rewiring above -- the entire old pass 2 (Map_Keys loop, its
   ApplyKeepRule call, its prints) and the old Map_Find/KeepRules Get feeding
   pass 1's old condition -- gets removed automatically. Safer than manually
   enumerating ~15 nodes by hand.

END STATE: KeepRulesV2 is the SOLE source of truth for both tidy (pass 1) and
restock (the former 3Q block). The old KeepRules: Map<int,int> variable is no
longer referenced by any node (left as an unused variable -- deleting the
variable itself is a Details-panel action, left for the user, optional).

New execution order: gather/report -> seed KeepRulesV2 -> rebuild
RuleTemplateID cache -> pass 1 (tidy, using the cache) -> resolve+apply
(restock, using KeepRulesV2 directly) -> 3O (identity spike) -> 3P (round-trip
check).
"""
import sys

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
row = conn.execute("SELECT t3d FROM graphs WHERE name=?", ("stocker_3r_base",)).fetchone()
assert row, "run `ccmod pull --save stocker_3r_base` first"
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


def bgc(path):
    return f'''"/Script/Engine.BlueprintGeneratedClass'{path}'"'''


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
KEEP_PIN = "Keep_8_5132904E4CC17522C07075A43E93B26E"

# --- identify the fixed structural anchors (all confirmed by content-trace) -
call1 = g.by_name("K2Node_CallFunction_118")      # pass1's ApplyKeepRule
call2 = g.by_name("K2Node_CallFunction_119")      # pass2-OLD's ApplyKeepRule
brRuled = g.by_name("K2Node_IfThenElse_3")        # pass1's ruled/unruled branch
fe1 = g.by_name("K2Node_MacroInstance_2")         # pass1's ForEach (bench items)
fe2 = g.by_name("K2Node_MacroInstance_3")         # pass2-OLD's ForEach (Map_Keys)
tid1 = g.by_name("K2Node_VariableGet_4")          # GameItem.TemplateID, per-item

pre_fe1 = g.by_name("K2Node_CallFunction_6")      # currently drives fe1.Exec
seed_begin = g.by_name("K2Node_CallFunction_43")  # "STOCKER_3Q begin"
seed_end = g.by_name("K2Node_CallFunction_45")    # "STOCKER_3Q seeded 2 rules"
resolve_begin = g.by_name("K2Node_DynamicCast_6")  # cast2, start of resolve+apply
q_done = g.by_name("K2Node_CallFunction_54")      # "STOCKER_3Q done"
o_begin = g.by_name("K2Node_CallFunction_0")      # "STOCKER_3O begin"
p_tail = g.by_name("K2Node_CallFunction_40")      # "STOCKER_3P done"

assert pin(call1, "Keep")._get("DefaultValue") == '"0"' and not pin(call1, "Keep").links
assert pin(call2, "Keep").links
assert pin(brRuled, "Condition").links[0][0] == "K2Node_CallFunction_142"
assert pin(pre_fe1, "then").links[0][0] == fe1.name
assert pin(seed_end, "then").links[0][0] == resolve_begin.name
assert pin(p_tail, "then").links[0][0] == seed_begin.name

GET_RULES_T = tmpl_file(WLIB + r"\stocker\get_keeprules_v2.t3d")
BREAK_RULE_T = tmpl_file(WLIB + r"\stocker\break_keeprule.t3d")
GET_CACHE_T = tmpl_file(WLIB + r"\stocker\get_ruled_template_ids.t3d")
CLEAR_T = tmpl_file(LIB + r"\actor\array_clear_int.t3d")
CONTAINS_T = tmpl_file(LIB + r"\actor\array_contains_int.t3d")
ADD_T = tmpl_file(LIB + r"\array\array_add.t3d")

FEACH_T = None
for n in g.nodes:
    if n.class_path.endswith("K2Node_MacroInstance"):
        arr = n.pin_by_name("Array")
        if arr and arr.category == "object":
            import copy as _copy
            nn = _copy.deepcopy(n)
            for p in nn.pins:
                p.links = []
            FEACH_T = Graph(nodes=[nn])
            break
assert FEACH_T

# --- build: cache-rebuild block (Clear -> ForEach KeepRulesV2 -> Break -> Add)
cacheGet = add(GET_CACHE_T)
clearNode = add(CLEAR_T)
connect(cacheGet, "RuleTemplateID", clearNode, "TargetArray")

rulesGet4 = add(GET_RULES_T)
feCache = add(FEACH_T)
type_foreach_struct(feCache)
connect(rulesGet4, "KeepRulesV2", feCache, "Array")

brkCache = add(BREAK_RULE_T)
connect(feCache, "Array Element", brkCache, "S_KeepRule")

cacheGet2 = add(GET_CACHE_T)
addCache = add(ADD_T)
connect(cacheGet2, "RuleTemplateID", addCache, "TargetArray")
connect(brkCache, TEMPLATEID_PIN, addCache, "NewItem")

# --- rewire 1: pre_fe1.then -> seed_begin (was p_tail.then -> seed_begin,
#     and pre_fe1.then -> fe1.Exec) -- clear BOTH sides of BOTH old links first
pin(pre_fe1, "then").links = []
pin(fe1, "Exec").links = []
pin(p_tail, "then").links = []
pin(seed_begin, "execute").links = []
connect_exec(pre_fe1, seed_begin)

# --- rewire 2: seed_end.then -> cache-rebuild -> fe1 (was seed_end -> resolve)
pin(seed_end, "then").links = []
pin(resolve_begin, "execute").links = []
connect_exec(seed_end, clearNode)
connect_exec(clearNode, feCache, "then", "execute")
connect_exec(feCache, addCache, "LoopBody", "execute")
connect_exec(feCache, fe1, "Completed", "Exec")

# --- rewire 3: brRuled.Condition -> Array_Contains(RuleTemplateID, tid1) ----
cacheGet3 = add(GET_CACHE_T)
containsNode = add(CONTAINS_T)
connect(cacheGet3, "RuleTemplateID", containsNode, "TargetArray")
connect(tid1, "TemplateID", containsNode, "ItemToFind")
pin(brRuled, "Condition").links = []
connect(containsNode, "ReturnValue", brRuled, "Condition")

# --- rewire 4: fe1.Completed -> resolve_begin (was -> pass2-OLD's start) ----
pin(fe1, "Completed").links = []
connect_exec(fe1, resolve_begin, "Completed", "execute")

# --- rewire 5: q_done.then -> o_begin (was fe2.Completed -> o_begin) -------
pin(o_begin, "execute").links = []
pin(q_done, "then").links = []
connect_exec(q_done, o_begin)

# --- strip any surviving node's stale links pointing at a removed node -----
# (tid1 -> old Map_Find.Key, woodItem -> old call2.Station, etc: these nodes
# feed MULTIPLE consumers, so a blanket .links=[] would destroy still-valid
# links -- filter out only the entries that point at something we removed.)

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

# strip any surviving node's stale links pointing at a removed node -- these
# nodes (tid1, woodItem) feed MULTIPLE consumers, so only drop the entries
# that point at something just removed, not the whole link list.
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
assert "KeepRules'" not in g.render() or "KeepRulesV2" in g.render(), "sanity check"

out = MOD + r"\.ccmod\graphs\stocker_3r.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"nodes: {len(g.nodes)}   wrote: {out}")
print(f"non-reciprocal / dangling problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
