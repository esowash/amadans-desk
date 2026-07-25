"""Author the body of BPFL_Stocker::ApplyKeepRule — the reusable mover.

This is 3I's logic refactored into a callable function, so rules can be data
instead of hardcoded graph. Goes in the FUNCTION graph of BPFL_Stocker, not the
ModController's EventGraph (a separate script builds the caller).

    ApplyKeepRule(Station: Actor, TemplateID: int, Keep: int,
                  Candidates: Array<BP_PlaceableItemContainer>)
        -> Moved: int, Outcome: E_Stocker_Outcome

Four termini, one literal Return node each (user spec: "identify a clear terminus
in the event the mover can't find a destination, and clearly decide not to move"):

    Entry
      srcInv = GetInventoryByType(Station, PlaceableInventory)
      IsValid(srcInv)?   no -> RETURN (0, InvalidInput)
      excess = GetNumberOfItemsByTemplate(srcInv, TemplateID) - Keep
      excess > 0?        no -> RETURN (0, NoExcess)
      ForEach c in Candidates:
          cInv = GetInventoryByType(c, PlaceableInventory)
          GetNumberOfItemsByTemplate(cInv, TemplateID) > 0?
            and c != Station?
              moved = srcInv.MoveItemsByTemplateId(TemplateID, excess, true, cInv, true)
              -> RETURN (moved, Moved)        <- early return: FIRST match wins
      Completed          -> RETURN (0, NoDestination)   <- ORPHAN

Two properties worth stating, because they are structural rather than incidental:

1. The orphan path CANNOT move anything. The move node exists only inside the
   found-destination branch, so NoDestination isn't a decision to skip the move --
   there is no move on that path. "Clearly decide not to move" is enforced by the
   graph's shape, not by a flag.
2. Early-return from inside the loop fixes 3I's over-move bug for free (3I read
   srcIron once before the loop, so every qualifying destination would have moved
   the same stale excess). First match wins, then the function exits.

Partial moves (destination full / size limit) need no fifth state: the caller
compares Moved against what it expected.

Enum is E_Stocker_Outcome (the user's asset name -- underscores). Enum pins are
PinCategory="byte" with PinSubCategoryObject = the enum asset; the value is set as
the enumerator NAME in DefaultValue, exactly like GetInventoryByType's
inventoryType="PlaceableInventory".

LESSON APPLIED (cost 3I a compile): the ForEach brick was captured unconnected, so
its Array/Array Element pins are wildcard and UE resolves them at paste time from
whichever link it processes first. Array Element here feeds an Actor pin
(GetInventoryByType.owner) AND an Object pin (NotEqual_ObjectObject.A) -- exactly
the mix that collapsed to Object and broke 3I. type_foreach() pins it down.

NO ENTRY NODE IN THE OUTPUT -- and this is deliberate. A function graph must have
exactly one entry node: it cannot be deleted (it IS the signature) and UE's paste
REJECTS an incoming one ("one node couldn't be pasted"), silently dropping every
link that referenced it. So the entry stays in the graph and the body is pasted
around it, leaving 5 pins to hand-wire.

To keep that hand-wiring to a minimum, Station and TemplateID fan out through KNOT
(reroute) nodes rather than connecting directly to their 2 and 3 consumers. That
makes the manual step exactly ONE drag per entry pin -- 5 wires, not 8 -- and every
target sits at a fixed, predictable position. The knots are pure plumbing; they add
no logic.
"""
import copy
import sys

CCMOD = r"<CCMOD_HOME>"
sys.path.insert(0, CCMOD)
from ccmod.t3d import parse, connect, connect_exec
from ccmod.t3d.generator import instantiate
from ccmod.t3d.model import Graph

MOD = r"<MOD_ROOT>"
LIB = CCMOD + r"\library"
WLIB = MOD + r"\.ccmod\library"

BASE_CONTAINER = ("/Game/Systems/Building/Placeables/"
                  "BP_PlaceableItemContainer.BP_PlaceableItemContainer_C")

i3 = parse(open(MOD + r"\.ccmod\graphs\stocker_3i.t3d", encoding="utf-8").read())
skel = parse(open(WLIB + r"\stocker\applykeeprule_skeleton.t3d", encoding="utf-8-sig").read())


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


RESULT_T = tmpl_from(skel, "K2Node_FunctionResult_0")
KNOT_T   = tmpl_file(LIB + r"\flow\knot.t3d")
BRANCH_T = tmpl_from(i3, "K2Node_IfThenElse_0")
FEACH_T  = tmpl_from(i3, "K2Node_MacroInstance_0")
IV_T     = tmpl_file(LIB + r"\call\is_valid.t3d")
GIBT_T   = tmpl_file(LIB + r"\inventory\get_inventory_by_type.t3d")
GNIBT_T  = tmpl_file(LIB + r"\inventory\get_number_of_items_by_template.t3d")
MOVE_T   = tmpl_file(LIB + r"\inventory\move_items_by_template.t3d")
SUB_T    = tmpl_file(LIB + r"\math\subtract_int.t3d")
GTI_T    = tmpl_file(LIB + r"\math\greater_int.t3d")
NEQ_T    = tmpl_file(LIB + r"\math\not_equal_object.t3d")

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


def type_foreach(node, path):
    """Pin down the ForEach macro's wildcards. See module docstring."""
    setf(node, "Array", "PinType.PinCategory", '"object"')
    setf(node, "Array", "PinType.PinSubCategoryObject", bgc(path))
    setf(node, "Array", "PinType.ContainerType", "Array")
    setf(node, "Array Element", "PinType.PinCategory", '"object"')
    setf(node, "Array Element", "PinType.PinSubCategoryObject", bgc(path))
    setf(node, "Array Element", "PinType.ContainerType", "None")


# A Blueprint (user-defined) enum's entries are really named NewEnumeratorN --
# "NoExcess" etc. are only DISPLAY names. Setting DefaultValue to the label fails
# to compile: "not a valid enumerant of E_Stocker_Outcome". Native enums don't have
# this problem, which is why inventoryType="PlaceableInventory" has always worked
# (EInventoryType is C++, so its enumerator name is real).
#
# Index order confirmed from the asset's file layout: the display names appear in
# creation order, pairing with NewEnumerator0..3 respectively.
OUTCOME = {
    "NoExcess":      "NewEnumerator0",
    "Moved":         "NewEnumerator1",
    "NoDestination": "NewEnumerator2",
    "InvalidInput":  "NewEnumerator3",
}


def terminus(outcome, moved_default="0"):
    """A Return node for one outcome. Each terminus is a literal node."""
    r = add(RESULT_T)
    setd(r, "Outcome", OUTCOME[outcome])
    if moved_default is not None:
        setd(r, "Moved", moved_default)
    return r


# --- stand-ins for the un-pasteable entry node ------------------------------
# The user drags each entry pin to one of these. Everything downstream reads
# from the knot, so each entry pin needs exactly one manual wire.
kStation = add(KNOT_T)
setf(kStation, "InputPin", "PinType.PinSubCategoryObject",
     '''"/Script/CoreUObject.Class'/Script/Engine.Actor'"''')
setf(kStation, "OutputPin", "PinType.PinSubCategoryObject",
     '''"/Script/CoreUObject.Class'/Script/Engine.Actor'"''')
kTemplate = add(KNOT_T)
for pn in ("InputPin", "OutputPin"):
    setf(kTemplate, pn, "PinType.PinCategory", '"int"')
    setf(kTemplate, pn, "PinType.PinSubCategoryObject", "None")

# --- resolve + validate the source inventory --------------------------------
srcInv = add(GIBT_T)
setd(srcInv, "inventoryType", "PlaceableInventory")
isv = add(IV_T)
brValid = add(BRANCH_T)
retInvalid = terminus("InvalidInput")

# --- excess = count - keep --------------------------------------------------
srcCount = add(GNIBT_T)
excess = add(SUB_T)
hasExcess = add(GTI_T)
setd(hasExcess, "B", "0")
brExcess = add(BRANCH_T)
retNoExcess = terminus("NoExcess")

# --- destination search -----------------------------------------------------
feach = add(FEACH_T)
type_foreach(feach, BASE_CONTAINER)
cInv = add(GIBT_T)
setd(cInv, "inventoryType", "PlaceableInventory")
cCount = add(GNIBT_T)
holds = add(GTI_T)
setd(holds, "B", "0")
brHolds = add(BRANCH_T)
notSelf = add(NEQ_T)
brNotSelf = add(BRANCH_T)

# --- the move + its terminus ------------------------------------------------
move = add(MOVE_T)
setd(move, "bMoveAllAvailable", "true")
setd(move, "ignoreSizeLimit", "true")
retMoved = terminus("Moved", moved_default=None)   # Moved is data-fed
retNoDest = terminus("NoDestination")              # <- the ORPHAN terminus

# --- data wiring (entry pins are read via the knots) -------------------------
connect(kStation, "OutputPin", srcInv, "owner")
connect(srcInv, "ReturnValue", isv, "Object")
connect(isv, "ReturnValue", brValid, "Condition")

connect(srcInv, "ReturnValue", srcCount, "self")
connect(kTemplate, "OutputPin", srcCount, "templateID")
connect(srcCount, "ReturnValue", excess, "A")
connect(excess, "ReturnValue", hasExcess, "A")
connect(hasExcess, "ReturnValue", brExcess, "Condition")

connect(feach, "Array Element", cInv, "owner")
connect(cInv, "ReturnValue", cCount, "self")
connect(kTemplate, "OutputPin", cCount, "templateID")
connect(cCount, "ReturnValue", holds, "A")
connect(holds, "ReturnValue", brHolds, "Condition")
connect(feach, "Array Element", notSelf, "A")
connect(kStation, "OutputPin", notSelf, "B")
connect(notSelf, "ReturnValue", brNotSelf, "Condition")

connect(srcInv, "ReturnValue", move, "self")            # called ON the source
connect(kTemplate, "OutputPin", move, "templateID")
connect(excess, "ReturnValue", move, "quantity")
connect(cInv, "ReturnValue", move, "targetInventory")
connect(move, "ReturnValue", retMoved, "Moved")

# --- exec wiring: each path ends at a literal Return ------------------------
# NB: brValid.execute is left OPEN -- the user wires entry.then into it.
connect_exec(brValid, retInvalid, "else", "execute")     # invalid -> terminus
connect_exec(brValid, brExcess, "then", "execute")
connect_exec(brExcess, retNoExcess, "else", "execute")   # no excess -> terminus
connect_exec(brExcess, feach, "then", "Exec")
connect_exec(feach, brHolds, "LoopBody", "execute")
connect_exec(brHolds, brNotSelf, "then", "execute")
connect_exec(brNotSelf, move, "then", "execute")
connect_exec(move, retMoved)                             # moved -> terminus
connect_exec(feach, retNoDest, "Completed", "execute")   # ORPHAN -> terminus

# --- layout -----------------------------------------------------------------
# The four hand-wired targets sit in a column just right of where the entry node
# lives, so each drag is short and unambiguous.
kStation.set_position(200, 120)
kTemplate.set_position(200, 170)
srcInv.set_position(260, 180); isv.set_position(470, 180)
brValid.set_position(300, 0); retInvalid.set_position(300, 200)
srcCount.set_position(560, 300); excess.set_position(760, 300)
hasExcess.set_position(940, 300)
brExcess.set_position(620, 0); retNoExcess.set_position(620, 200)
feach.set_position(900, 0)
cInv.set_position(1180, 300); cCount.set_position(1380, 300)
holds.set_position(1580, 300); notSelf.set_position(1580, 440)
brHolds.set_position(1200, 0); brNotSelf.set_position(1420, 0)
move.set_position(1660, 0); retMoved.set_position(1940, 0)
retNoDest.set_position(900, 260)

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

assert not [n for n in g.nodes if "FunctionEntry" in n.class_path], "entry node must NOT be in the paste"
results = [n for n in g.nodes if "FunctionResult" in n.class_path]
assert len(results) == 4, f"expected 4 termini, got {len(results)}"
outcomes = sorted(str(pin(r, "Outcome")._get("DefaultValue")).strip('"') for r in results)
assert outcomes == sorted(OUTCOME.values()), outcomes
wilds = [(n.name, p.name) for n in g.nodes for p in n.pins
         if p._get("PinType.PinCategory") == '"wildcard"']
assert not wilds, f"unresolved wildcards: {wilds}"

out = MOD + r"\.ccmod\graphs\bpfl_applykeeprule.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"nodes: {len(g.nodes)}   wrote: {out}")
print(f"termini: {outcomes}")
print(f"non-reciprocal / dangling problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
