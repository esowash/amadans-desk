"""Author stocker_3o.t3d -- Identity spike: print each managed container's
persistent UniqueID.

THE QUESTION: does GetActorUniqueID survive a relaunch? This build only answers
half of it (the print). The other half is manual: run this, read the log, quit
the game, relaunch, run it again, diff the two id lists by eye. If the same
container prints the same id both times, GetActorByUniqueID becomes safe to
design the rules schema around.

THE MECHANISM (discovered this session, not assumed):
  BP_BAC_Storage's own EventGraph calls a PURE GetUniqueID off a
  PersistenceComponent -- but a cleaner idiom exists one level up:
  BP_Master_Placeables::GetActorUniqueID(self) -> UniqueID, an IMPURE member
  function (has exec pins) callable directly on the placeable actor, no
  component lookup needed. BP_PlaceableItemContainer's ParentClass is
  confirmed (grepped from the source uasset) to be BP_Master_Placeables_C
  directly, so ManagedContainers' element type wires straight into it --
  no cast.
  Conv_UniqueIDToString is a separate STATIC function on
  UE4Dreamworld.DreamworldBlueprints (self hidden/CDO) that turns the
  UniqueID struct into a printable string.

DELIBERATELY NOT a fresh gather: this is a pure ADDITION appended after 3N's
existing chain, not a new Event BeginPlay (pasting a second one would make UE
substitute a CustomEvent -- a known trap, see stocker-test-loop-gotchas). It
reuses the ManagedContainers member array 3N already populates earlier in the
same BeginPlay run ("storage in range" -- exactly the scope we want). Nothing
here writes to ManagedContainers or calls ApplyKeepRule; it only reads and
prints, so it can't disturb 3N's proven move behaviour.

Paste target: after 3N's very last node (the pass-2 "Moved" print). Hand-wire
ONE exec link from that node's output into this body's entry (pName2Lbl below)
-- a paste can't make that link, per the standard division of labour.

    ForEach (Get ManagedContainers):
      GetActorUniqueID(c) -> UniqueID
        Conv_UniqueIDToString(UniqueID) -> idStr
        GetDisplayName(c) -> name
        Print "STOCKER_3O name=<name>"
        Print "STOCKER_3O uid=<idStr>"
    Completed -> Print "STOCKER_3O done"
"""
import copy
import sys

import os, pathlib
CCMOD = os.environ.get("CCMOD_HOME") or str(pathlib.Path(__file__).resolve().parents[3] / "claude-conan-modder")
sys.path.insert(0, CCMOD)
from ccmod.t3d import parse, connect, connect_exec
from ccmod.t3d.generator import instantiate
from ccmod.t3d.model import Graph

import pathlib
MOD = str(pathlib.Path(__file__).resolve().parents[2])
LIB = CCMOD + r"\library"
WLIB = MOD + r"\.ccmod\library"

PRE = "/Game/Systems/Building/Placeables/"
BASE_CONTAINER = PRE + "BP_PlaceableItemContainer.BP_PlaceableItemContainer_C"

n3 = parse(open(MOD + r"\.ccmod\graphs\stocker_3n.t3d", encoding="utf-8").read())


def tmpl_from(graph, name):
    n = copy.deepcopy(graph.by_name(name))
    for p in n.pins:
        p.links = []
    return Graph(nodes=[n])


def tmpl_file(path):
    g = parse(open(path, encoding="utf-8-sig").read())
    for n in g.nodes:
        for p in n.pins:
            p.links = []
    return g


def find_tmpl(graph, member):
    import re
    for n in graph.nodes:
        raw = " ".join(t for k, t in n.body if k == "raw")
        if re.search(r'MemberName="%s"' % member, raw):
            return tmpl_from(graph, n.name)
    raise KeyError(member)


PRINT_T   = find_tmpl(n3, "PrintString")
FEACH_T   = tmpl_from(n3, "K2Node_MacroInstance_0")
GDN_T     = tmpl_file(LIB + r"\call\get_display_name.t3d")
UID_T     = tmpl_file(LIB + r"\actor\get_actor_unique_id.t3d")
UIDSTR_T  = tmpl_file(LIB + r"\actor\conv_uniqueid_to_string.t3d")
MCGET_T   = tmpl_file(WLIB + r"\stocker\get_managed_containers.t3d")

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


def bgc(path):
    return f'''"/Script/Engine.BlueprintGeneratedClass'{path}'"'''


def type_foreach(node, subobj_raw):
    setf(node, "Array", "PinType.PinCategory", '"object"')
    setf(node, "Array", "PinType.PinSubCategoryObject", subobj_raw)
    setf(node, "Array", "PinType.ContainerType", "Array")
    setf(node, "Array Element", "PinType.PinCategory", '"object"')
    setf(node, "Array Element", "PinType.PinSubCategoryObject", subobj_raw)
    setf(node, "Array Element", "PinType.ContainerType", "None")


# --- entry: reuse ManagedContainers, already populated earlier in 3N -------
pLbl = add(PRINT_T)
setd(pLbl, "InString", "STOCKER_3O begin (identity spike)")
mcGet = add(MCGET_T)
fe = add(FEACH_T)
type_foreach(fe, bgc(BASE_CONTAINER))
connect(mcGet, "ManagedContainers", fe, "Array")

# --- identity: GetActorUniqueID -> Conv_UniqueIDToString, + display name ---
callUid = add(UID_T)
connect(fe, "Array Element", callUid, "self")
convStr = add(UIDSTR_T)
connect(callUid, "UniqueID", convStr, "uid")
gdn = add(GDN_T)
connect(fe, "Array Element", gdn, "Object")
pName = add(PRINT_T)
setd(pName, "InString", "STOCKER_3O name=")
connect(gdn, "ReturnValue", pName, "InString")
pUid = add(PRINT_T)
setd(pUid, "InString", "STOCKER_3O uid=")
connect(convStr, "ReturnValue", pUid, "InString")

pDone = add(PRINT_T)
setd(pDone, "InString", "STOCKER_3O done")

# --- exec -------------------------------------------------------------------
# pLbl's "execute" pin is left UNLINKED on purpose -- the user hand-wires it
# to the tail of 3N's existing chain (a paste can't make that link).
connect_exec(pLbl, fe, "then", "Exec")
connect_exec(fe, callUid, "LoopBody", "execute")
connect_exec(callUid, pName, "then", "execute")
connect_exec(pName, pUid)
connect_exec(fe, pDone, "Completed", "execute")

# --- layout -----------------------------------------------------------------
pLbl.set_position(0, -600)
mcGet.set_position(0, -440)
fe.set_position(280, -600)
callUid.set_position(560, -600)
convStr.set_position(840, -460)
gdn.set_position(840, -700)
pName.set_position(1120, -600)
pUid.set_position(1360, -600)
pDone.set_position(280, -900)

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
assert "UE4Dreamworld.UniqueID" in g.render(), "UniqueID struct ref missing"
assert not pin(pLbl, "execute").links, "pLbl.execute should stay unwired for hand-splice"

out = MOD + r"\.ccmod\graphs\stocker_3o.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"nodes: {len(g.nodes)}   wrote: {out}")
print(f"non-reciprocal / dangling problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
