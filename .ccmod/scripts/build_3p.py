"""Author stocker_3p.t3d -- GetActorByUniqueID round-trip check.

Operates on the FULL live graph (pulled via `ccmod pull`), not a fresh
standalone body -- per the process lesson from 3O (see memory
stocker-full-graph-edits): splice new logic onto the true tail in code, then
push back a full corrected graph for a select-all-delete-then-paste, rather
than asking for a hand-wire into a large existing graph.

THE QUESTION: given the UniqueID printed in 3O, does GetActorByUniqueID hand
back the SAME actor? 3O only proved the id itself is stable across a
relaunch; this proves the reverse lookup actually resolves.

THE MECHANISM (discovered this session): GetActorByUniqueID is not a plain
static function -- it's a Blueprint INTERFACE call,
BaseGameModeInterface::Get_Actor_By_UniqueID_Interface. Its self pin needs
something implementing that interface. Real idiom, captured from
SOF_EnableBarkeeper (a tiny asset, 4 calls total):
    GameplayStatics::GetGameMode() -> GameModeBase
      -> Cast to BaseGameModeInterface -> AsBaseGameModeInterface (interface)
         -> self pin of Get_Actor_By_UniqueID_Interface

    Event (once): GetGameMode() [pure] -> Cast(gm) -> BaseGameModeInterface
      then -> ForEach ManagedContainers:
        GetActorUniqueID(c) -> uid
          Get_Actor_By_UniqueID_Interface(gmInterface, uid) -> resultActor
            NotEqual_ObjectObject(resultActor, c) -> mismatch?
              True  -> Print "MISMATCH" + display name
              False -> Print "OK roundtrip" + display name
      Completed -> Print "STOCKER_3P done"
      CastFailed -> Print "STOCKER_3P cast failed" (diagnostic, dead end)

Splices onto whatever node is currently "STOCKER_3O done" (3O's true tail,
identified by literal InString text -- safe here since that text is NOT
data-wired, unlike the traps this session hit twice already).
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

PRE = "/Game/Systems/Building/Placeables/"
BASE_CONTAINER = PRE + "BP_PlaceableItemContainer.BP_PlaceableItemContainer_C"

ws = Workspace.resolve()
conn = db.connect(ws.cache_db)
row = conn.execute("SELECT t3d FROM graphs WHERE name=?", ("stocker_3p_base",)).fetchone()
assert row, "run `ccmod pull --save stocker_3p_base` first"
g = parse(row[0])
print("pulled nodes:", len(g.nodes))


def tmpl_file(path):
    t = parse(open(path, encoding="utf-8-sig").read())
    for n in t.nodes:
        for p in n.pins:
            p.links = []
    return t


PRINT_T   = None
for n in g.nodes:
    isp = n.pin_by_name("InString")
    if isp and isp._get("DefaultValue") == '"STOCKER_3N begin (storage-only candidates; benches excluded)"':
        t = Graph(nodes=[n])
        import copy as _copy
        nn = _copy.deepcopy(n)
        for p in nn.pins:
            p.links = []
        PRINT_T = Graph(nodes=[nn])
        break
assert PRINT_T, "could not find a PrintString template via literal 3N banner text"

FEACH_T  = None
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
assert FEACH_T, "could not find a typed ForEachLoop template"

GDN_T    = tmpl_file(LIB + r"\call\get_display_name.t3d")
UID_T    = tmpl_file(LIB + r"\actor\get_actor_unique_id.t3d")
LOOKUP_T = tmpl_file(LIB + r"\actor\get_actor_by_unique_id.t3d")
GM_T     = tmpl_file(LIB + r"\actor\get_game_mode.t3d")
CAST_T   = tmpl_file(LIB + r"\actor\cast_to_basegamemode_interface.t3d")
NEQ_T    = tmpl_file(LIB + r"\math\not_equal_object.t3d")
BRANCH_T = None
for n in g.nodes:
    if n.class_path.endswith("K2Node_IfThenElse"):
        import copy as _copy
        nn = _copy.deepcopy(n)
        for p in nn.pins:
            p.links = []
        BRANCH_T = Graph(nodes=[nn])
        break
assert BRANCH_T, "could not find an IfThenElse template"

MCGET_T = tmpl_file(WLIB + r"\stocker\get_managed_containers.t3d")


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


def bgc(path):
    return f'''"/Script/Engine.BlueprintGeneratedClass'{path}'"'''


def type_foreach(node, subobj_raw):
    setf(node, "Array", "PinType.PinCategory", '"object"')
    setf(node, "Array", "PinType.PinSubCategoryObject", subobj_raw)
    setf(node, "Array", "PinType.ContainerType", "Array")
    setf(node, "Array Element", "PinType.PinCategory", '"object"')
    setf(node, "Array Element", "PinType.PinSubCategoryObject", subobj_raw)
    setf(node, "Array Element", "PinType.ContainerType", "None")


# --- find 3O's true tail (literal text, not data-wired -- safe to match) ---
spike_done = None
for n in g.nodes:
    isp = n.pin_by_name("InString")
    if isp and isp._get("DefaultValue") == '"STOCKER_3O done"':
        spike_done = n
        break
assert spike_done, "could not find STOCKER_3O done node"
assert not pin(spike_done, "then").links, "STOCKER_3O done.then is not dangling -- already spliced?"

# --- build the round-trip check ---
pLbl = add(PRINT_T)
setd(pLbl, "InString", "STOCKER_3P begin (round-trip check)")

gm = add(GM_T)
cast = add(CAST_T)
connect(gm, "ReturnValue", cast, "Object")

pCastFail = add(PRINT_T)
setd(pCastFail, "InString", "STOCKER_3P cast to BaseGameModeInterface FAILED")

mcGet = add(MCGET_T)
fe = add(FEACH_T)
type_foreach(fe, bgc(BASE_CONTAINER))
connect(mcGet, "ManagedContainers", fe, "Array")

callUid = add(UID_T)
connect(fe, "Array Element", callUid, "self")

lookup = add(LOOKUP_T)
connect(cast, "AsBase Game Mode Interface", lookup, "self")
connect(callUid, "UniqueID", lookup, "UniqueID")

neq = add(NEQ_T)
connect(lookup, "Actor", neq, "A")
connect(fe, "Array Element", neq, "B")

branch = add(BRANCH_T)
connect(neq, "ReturnValue", branch, "Condition")

gdnOk = add(GDN_T)
connect(fe, "Array Element", gdnOk, "Object")
pOk = add(PRINT_T)
setd(pOk, "InString", "STOCKER_3P OK roundtrip=")
connect(gdnOk, "ReturnValue", pOk, "InString")

gdnMismatch = add(GDN_T)
connect(fe, "Array Element", gdnMismatch, "Object")
pMismatch = add(PRINT_T)
setd(pMismatch, "InString", "STOCKER_3P MISMATCH=")
connect(gdnMismatch, "ReturnValue", pMismatch, "InString")

pDone = add(PRINT_T)
setd(pDone, "InString", "STOCKER_3P done")

# --- exec -------------------------------------------------------------------
connect_exec(spike_done, pLbl)
connect_exec(pLbl, cast, "then", "execute")
connect_exec(cast, pCastFail, "CastFailed", "execute")
connect_exec(cast, fe, "then", "execute")
connect_exec(fe, callUid, "LoopBody", "execute")
connect_exec(callUid, lookup, "then", "execute")
connect_exec(lookup, branch, "then", "execute")
connect_exec(branch, pMismatch, "then", "execute")   # True (NotEqual) = mismatch
connect_exec(branch, pOk, "else", "execute")          # False (Equal) = match
connect_exec(fe, pDone, "Completed", "execute")

# --- layout (rough, off to the side) ----------------------------------------
pLbl.set_position(2000, 400)
gm.set_position(2000, 550); cast.set_position(2260, 550)
pCastFail.set_position(2500, 750)
mcGet.set_position(2000, 700); fe.set_position(2500, 400)
callUid.set_position(2760, 400); lookup.set_position(3020, 400)
neq.set_position(3280, 550); branch.set_position(3540, 400)
gdnOk.set_position(3800, 350); pOk.set_position(4060, 350)
gdnMismatch.set_position(3800, 500); pMismatch.set_position(4060, 500)
pDone.set_position(2500, 300)

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
         if p._get("PinType.PinCategory") == '"wildcard"']
assert not wilds, f"unresolved wildcards: {wilds}"
assert "BaseGameModeInterface" in g.render(), "interface ref missing"

out = MOD + r"\.ccmod\graphs\stocker_3p.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"nodes: {len(g.nodes)}   wrote: {out}")
print(f"non-reciprocal / dangling problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
