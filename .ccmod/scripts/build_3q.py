"""Author stocker_3q.t3d -- seed KeepRulesV2 and drive restock through the new
identity-based S_KeepRule schema, proving it resolves to the same station as
the old hardcoded-Wood-station path.

Operates on the FULL live graph (pull-edit-repaste), per stocker-full-graph-edits.

WHAT THIS PROVES: with Identity fully verified (3O persistence, 3P round-trip),
the S_KeepRule{Container: UniqueID, TemplateID: int, Keep: int} schema agreed in
session 6 can actually be built. This is the FIRST proof, kept narrow: pass 1
(tidy) stays on the OLD KeepRules Map untouched; only a NEW, parallel pass
drives ApplyKeepRule from KeepRulesV2 instead. Full unification (retiring the
Map, switching tidy too) is a follow-on step once this is proven.

Container can't be a design-time literal (UniqueID objects only exist at
runtime), so the array has to be POPULATED by graph logic, not the Details
panel -- this build seeds it itself, standing in for what the eventual UI will
do: resolve the Wood station's real UniqueID once via GetActorUniqueID, build
two S_KeepRule structs from it (the SAME two rules 3N already runs: Wood
10011 keep=200, Silk 12515 keep=300), Array_Add both into KeepRulesV2.

Then a ForEach over KeepRulesV2: Break each rule -> Container/TemplateID/Keep,
resolve Container back to an actor via the 3P round-trip idiom (GetGameMode ->
Cast to BaseGameModeInterface -> Get_Actor_By_UniqueID_Interface), call
ApplyKeepRule(Station=resolved, TemplateID, Keep, Candidates=ManagedContainers).
If this reaches the SAME Wood station via resolved identity as the old
hardcoded wire does, the outcome should match whatever 3N's own pass-2 already
produced against the current world (steady state, since pass 2 has already run
against this world several times this session -- NoExcess/NoSource are the
expected, fine outcomes here, not a regression; the point is the STATION
resolved correctly, not a fresh move).

Also prunes 4 orphaned nodes left over from placing capture-scratch nodes this
session (Get KeepRulesV2 / Make S_KeepRule / Break S_KeepRule) and last
session (ItemInventory.BlackWhiteList, from the orphan-plan research) -- true
orphans, zero links on every pin, confirmed before removal.
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
row = conn.execute("SELECT t3d FROM graphs WHERE name=?", ("stocker_3q_base",)).fetchone()
assert row, "run `ccmod pull --save stocker_3q_base` first"
g = parse(row[0])
print("pulled nodes:", len(g.nodes))

# --- prune confirmed orphans (zero links on every pin) ----------------------
ORPHAN_NAMES = {
    "K2Node_VariableGet_31",  # ItemInventory.BlackWhiteList, session 6 leftover
    "K2Node_VariableGet_50",  # Get KeepRulesV2 capture scratch
    "K2Node_MakeStruct_0",    # Make S_KeepRule capture scratch
    "K2Node_BreakStruct_0",   # Break S_KeepRule capture scratch
}
for name in ORPHAN_NAMES:
    n = g.by_name(name)
    assert n is not None, f"expected orphan {name} not found"
    assert not any(p.links for p in n.pins), f"{name} is not actually orphaned -- aborting"
g.nodes = [n for n in g.nodes if n.name not in ORPHAN_NAMES]
print(f"pruned {len(ORPHAN_NAMES)} orphans -> {len(g.nodes)} nodes")


def tmpl_file(path):
    t = parse(open(path, encoding="utf-8-sig").read())
    for n in t.nodes:
        for p in n.pins:
            p.links = []
    return t


def pin(n, name):
    p = n.pin_by_name(name)
    assert p, f"{n.name} has no pin {name}"
    return p


def setf(n, pn, k, raw):
    pin(n, pn)._set(k, raw)


def setd(n, pn, v):
    setf(n, pn, "DefaultValue", f'"{v}"')


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


def find_by_text(text):
    """Find a PrintString by literal text -- only valid when InString has NO
    LinkedTo (never trust displayed text on a data-wired pin, see
    stocker-test-loop-gotchas #12)."""
    for n in g.nodes:
        isp = n.pin_by_name("InString")
        if isp and isp._get("DefaultValue") == f'"{text}"' and not isp.links:
            return n
    raise KeyError(text)


def literal_print_template():
    n = find_by_text("STOCKER_3N begin (storage-only candidates; benches excluded)")
    nn = _copy.deepcopy(n)
    for p in nn.pins:
        p.links = []
    return Graph(nodes=[nn])


PRINT_T = literal_print_template()

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

UID_T    = tmpl_file(LIB + r"\actor\get_actor_unique_id.t3d")
LOOKUP_T = tmpl_file(LIB + r"\actor\get_actor_by_unique_id.t3d")
GM_T     = tmpl_file(LIB + r"\actor\get_game_mode.t3d")
CAST_T   = tmpl_file(LIB + r"\actor\cast_to_basegamemode_interface.t3d")
GDN_T    = tmpl_file(LIB + r"\call\get_display_name.t3d")
ADD_T    = tmpl_file(LIB + r"\array\array_add.t3d")

GET_RULES_T   = tmpl_file(WLIB + r"\stocker\get_keeprules_v2.t3d")
MAKE_RULE_T   = tmpl_file(WLIB + r"\stocker\make_keeprule.t3d")
BREAK_RULE_T  = tmpl_file(WLIB + r"\stocker\break_keeprule.t3d")
MCGET_T       = tmpl_file(WLIB + r"\stocker\get_managed_containers.t3d")
CALL_T        = tmpl_file(WLIB + r"\stocker\call_applykeeprule.t3d")
E2S_T         = tmpl_file(WLIB + r"\stocker\enum_to_string.t3d")

CONV_T = None
for n in g.nodes:
    raw = " ".join(t for k, t in n.body if k == "raw")
    if 'MemberName="Conv_IntToString"' in raw:
        nn = _copy.deepcopy(n)
        for p in nn.pins:
            p.links = []
        CONV_T = Graph(nodes=[nn])
        break
assert CONV_T


def add(t):
    return instantiate(t, g)[0]


# --- reuse the existing woodItem reference (feeds pass2's hardcoded call) ---
wood_item = g.by_name("K2Node_GetArrayItem_1")
assert wood_item is not None

tail = find_by_text("STOCKER_3P done")
assert not pin(tail, "then").links, "STOCKER_3P done.then not dangling -- already spliced?"

CONTAINER_PIN = "Container_4_62E0F0614C1CC5F95CAE6B97F57E9504"
TEMPLATEID_PIN = "TemplateID_6_7331DAFA4369B9E2C105A59FAAA510CD"
KEEP_PIN = "Keep_8_5132904E4CC17522C07075A43E93B26E"

# --- seed: resolve Wood station's UniqueID once, build 2 rules -------------
pLbl = add(PRINT_T)
setd(pLbl, "InString", "STOCKER_3Q begin (rules-v2 seed+restock)")

callWoodUid = add(UID_T)
connect(wood_item, "Output", callWoodUid, "self")

make1 = add(MAKE_RULE_T)
connect(callWoodUid, "UniqueID", make1, CONTAINER_PIN)
setf(make1, TEMPLATEID_PIN, "DefaultValue", '"10011"')
setf(make1, KEEP_PIN, "DefaultValue", '"200"')

rulesGet1 = add(GET_RULES_T)
add1 = add(ADD_T)
connect(rulesGet1, "KeepRulesV2", add1, "TargetArray")
connect(make1, "S_KeepRule", add1, "NewItem")

make2 = add(MAKE_RULE_T)
connect(callWoodUid, "UniqueID", make2, CONTAINER_PIN)
setf(make2, TEMPLATEID_PIN, "DefaultValue", '"12515"')
setf(make2, KEEP_PIN, "DefaultValue", '"300"')

rulesGet2 = add(GET_RULES_T)
add2 = add(ADD_T)
connect(rulesGet2, "KeepRulesV2", add2, "TargetArray")
connect(make2, "S_KeepRule", add2, "NewItem")

pSeeded = add(PRINT_T)
setd(pSeeded, "InString", "STOCKER_3Q seeded 2 rules")

# --- resolve+apply: ForEach KeepRulesV2, per rule resolve Container, restock -
gm2 = add(GM_T)
cast2 = add(CAST_T)
connect(gm2, "ReturnValue", cast2, "Object")

pCastFail2 = add(PRINT_T)
setd(pCastFail2, "InString", "STOCKER_3Q cast to BaseGameModeInterface FAILED")

rulesGet3 = add(GET_RULES_T)
feRules = add(FEACH_T)
type_foreach_struct(feRules)
connect(rulesGet3, "KeepRulesV2", feRules, "Array")

brk = add(BREAK_RULE_T)
connect(feRules, "Array Element", brk, "S_KeepRule")

lookup2 = add(LOOKUP_T)
connect(cast2, "AsBase Game Mode Interface", lookup2, "self")
connect(brk, CONTAINER_PIN, lookup2, "UniqueID")

mcGet3 = add(MCGET_T)
call3 = add(CALL_T)
connect(lookup2, "Actor", call3, "Station")
connect(brk, TEMPLATEID_PIN, call3, "TemplateID")
connect(brk, KEEP_PIN, call3, "Keep")
connect(mcGet3, "ManagedContainers", call3, "Candidates")

gdn3 = add(GDN_T)
connect(lookup2, "Actor", gdn3, "Object")
pStation = add(PRINT_T)
connect(gdn3, "ReturnValue", pStation, "InString")

convTid3 = add(CONV_T)
connect(brk, TEMPLATEID_PIN, convTid3, "InInt")
pTid3 = add(PRINT_T)
connect(convTid3, "ReturnValue", pTid3, "InString")

e2s3 = add(E2S_T)
connect(call3, "Outcome", e2s3, "Enumerator")
pOut3 = add(PRINT_T)
connect(e2s3, "ReturnValue", pOut3, "InString")

convMv3 = add(CONV_T)
connect(call3, "Moved", convMv3, "InInt")
pMv3 = add(PRINT_T)
connect(convMv3, "ReturnValue", pMv3, "InString")

pDoneQ = add(PRINT_T)
setd(pDoneQ, "InString", "STOCKER_3Q done")

# --- exec ---------------------------------------------------------------
connect_exec(tail, pLbl)
connect_exec(pLbl, callWoodUid, "then", "execute")
connect_exec(callWoodUid, add1, "then", "execute")
connect_exec(add1, add2, "then", "execute")
connect_exec(add2, pSeeded, "then", "execute")
connect_exec(pSeeded, cast2, "then", "execute")
connect_exec(cast2, pCastFail2, "CastFailed", "execute")
connect_exec(cast2, feRules, "then", "execute")
connect_exec(feRules, lookup2, "LoopBody", "execute")
connect_exec(lookup2, call3, "then", "execute")
connect_exec(call3, pStation, "then", "execute")
connect_exec(pStation, pTid3)
connect_exec(pTid3, pOut3)
connect_exec(pOut3, pMv3)
connect_exec(feRules, pDoneQ, "Completed", "execute")

# --- layout (off to the side again) --------------------------------------
pLbl.set_position(2000, 1100)
callWoodUid.set_position(2260, 1100)
make1.set_position(2520, 1000); rulesGet1.set_position(2520, 900); add1.set_position(2780, 1100)
make2.set_position(3040, 1000); rulesGet2.set_position(3040, 900); add2.set_position(3300, 1100)
pSeeded.set_position(3560, 1100)
gm2.set_position(3560, 1250); cast2.set_position(3820, 1250)
pCastFail2.set_position(4080, 1400)
rulesGet3.set_position(3820, 1400); feRules.set_position(4080, 1100)
brk.set_position(4340, 950)
lookup2.set_position(4600, 1100)
mcGet3.set_position(4600, 950); call3.set_position(4860, 1100)
gdn3.set_position(5120, 950); pStation.set_position(5380, 1100)
convTid3.set_position(5640, 950); pTid3.set_position(5900, 1100)
e2s3.set_position(6160, 950); pOut3.set_position(6420, 1100)
convMv3.set_position(6680, 950); pMv3.set_position(6940, 1100)
pDoneQ.set_position(4080, 900)

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
assert "S_KeepRule" in g.render(), "S_KeepRule struct ref missing"

out = MOD + r"\.ccmod\graphs\stocker_3q.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"nodes: {len(g.nodes)}   wrote: {out}")
print(f"non-reciprocal / dangling problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
