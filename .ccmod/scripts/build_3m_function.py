"""Author BPFL_Stocker2::ApplyKeepRule v2 — reconcile the bench to the rule, BOTH ways.

v1 only tidied excess away. v2 also restocks a deficit by pulling from nearby
storage. Same rule, same signature -- the function's job is now honestly "make the
bench hold exactly Keep of this item", which is what a house rule always meant.

    ApplyKeepRule(Station: Actor, TemplateID: int, Keep: int,
                  Candidates: Array<BP_PlaceableItemContainer>)
        -> Moved: int, Outcome: E_Stocker_Outcome

Six termini, one literal Return node each:

    Entry
      srcInv = GetInventoryByType(Station, PlaceableInventory)
      IsValid(srcInv)?      no -> RETURN (0, InvalidInput)
      have   = GetNumberOfItemsByTemplate(srcInv, TemplateID)
      excess = have - Keep

      excess > 0?                                          <- TIDY (v1, unchanged)
        ForEach c: c holds >0  and  c != Station
            moved = srcInv.MoveItemsByTemplateId(TID, excess, true, cInv, true)
            -> RETURN (moved, Moved)
        Completed            -> RETURN (0, NoDestination)  <- orphan

      Keep > have?                                         <- RESTOCK (new)
        deficit = Keep - have
        ForEach c: c holds >0  and  c != Station
            moved = cInv.MoveItemsByTemplateId(TID, deficit, true, srcInv, true)
            -> RETURN (moved, Restocked)                   <- note: self/target SWAPPED
        Completed            -> RETURN (0, NoSource)       <- nothing nearby has any

      otherwise              -> RETURN (0, NoExcess)       <- exactly at Keep

The restock move is the tidy move with `self` and `targetInventory` swapped: the
CHEST becomes the source and the bench the target. Same proven node, same
bMoveAllAvailable=true ("move UP TO quantity", settled in 3I).

NO NEW MATH: deficit = Subtract_IntInt(Keep, have), and the test is
Greater_IntInt(Keep, have) -- the same node as the excess test with its operands
swapped.

Both search loops are structurally incapable of moving anything on their failure
path: the move node exists only inside the found branch. NoDestination and NoSource
are shapes, not flags.

Enum values are NewEnumeratorN -- Blueprint enums name entries that way and the
labels you type are display-only. Order verified from the asset's byte layout.
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

l3 = parse(open(MOD + r"\.ccmod\graphs\stocker_3l.t3d", encoding="utf-8").read())
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
BRANCH_T = tmpl_from(l3, "K2Node_IfThenElse_0")
FEACH_T  = tmpl_from(l3, "K2Node_MacroInstance_0")
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
    setf(node, "Array", "PinType.PinCategory", '"object"')
    setf(node, "Array", "PinType.PinSubCategoryObject", bgc(path))
    setf(node, "Array", "PinType.ContainerType", "Array")
    setf(node, "Array Element", "PinType.PinCategory", '"object"')
    setf(node, "Array Element", "PinType.PinSubCategoryObject", bgc(path))
    setf(node, "Array Element", "PinType.ContainerType", "None")


# Blueprint enums really name their entries NewEnumeratorN; the labels are display
# only. Order confirmed against the asset's byte layout.
OUTCOME = {
    "NoExcess":      "NewEnumerator0",
    "Moved":         "NewEnumerator1",
    "NoDestination": "NewEnumerator2",
    "InvalidInput":  "NewEnumerator3",
    "Restocked":     "NewEnumerator4",
    "NoSource":      "NewEnumerator5",
}


def terminus(outcome, moved_default="0"):
    r = add(RESULT_T)
    setd(r, "Outcome", OUTCOME[outcome])
    if moved_default is not None:
        setd(r, "Moved", moved_default)
    return r


def search_loop(candidates_knot, station_knot, template_knot):
    """A candidate search: 'first container holding >0 of the item, not the Station'.

    Both directions need exactly this, so build it twice. Returns the ForEach (for
    its Completed pin), the branch that gates the body, and the matched container's
    inventory (to wire as either move source or move target).
    """
    fe = add(FEACH_T)
    type_foreach(fe, BASE_CONTAINER)
    connect(candidates_knot, "OutputPin", fe, "Array")
    cInv = add(GIBT_T)
    setd(cInv, "inventoryType", "PlaceableInventory")
    connect(fe, "Array Element", cInv, "owner")
    cCount = add(GNIBT_T)
    connect(cInv, "ReturnValue", cCount, "self")
    connect(template_knot, "OutputPin", cCount, "templateID")
    holds = add(GTI_T)
    setd(holds, "B", "0")
    connect(cCount, "ReturnValue", holds, "A")
    brHolds = add(BRANCH_T)
    connect(holds, "ReturnValue", brHolds, "Condition")
    notSelf = add(NEQ_T)
    connect(fe, "Array Element", notSelf, "A")
    connect(station_knot, "OutputPin", notSelf, "B")
    brNotSelf = add(BRANCH_T)
    connect(notSelf, "ReturnValue", brNotSelf, "Condition")
    connect_exec(fe, brHolds, "LoopBody", "execute")
    connect_exec(brHolds, brNotSelf, "then", "execute")
    return fe, brNotSelf, cInv


# --- stand-ins for the un-pasteable entry node ------------------------------
# UE rejects a pasted FunctionEntry and silently drops every link that referenced
# it, and it can't be deleted either. So the body omits it; these knots are what
# the user hand-wires the entry's pins into -- one drag per pin, not per consumer.
kStation = add(KNOT_T)
for pn in ("InputPin", "OutputPin"):
    setf(kStation, pn, "PinType.PinSubCategoryObject",
         '''"/Script/CoreUObject.Class'/Script/Engine.Actor'"''')
kTemplate = add(KNOT_T)
for pn in ("InputPin", "OutputPin"):
    setf(kTemplate, pn, "PinType.PinCategory", '"int"')
    setf(kTemplate, pn, "PinType.PinSubCategoryObject", "None")
kKeep = add(KNOT_T)
for pn in ("InputPin", "OutputPin"):
    setf(kKeep, pn, "PinType.PinCategory", '"int"')
    setf(kKeep, pn, "PinType.PinSubCategoryObject", "None")
kCand = add(KNOT_T)
for pn in ("InputPin", "OutputPin"):
    setf(kCand, pn, "PinType.PinCategory", '"object"')
    setf(kCand, pn, "PinType.PinSubCategoryObject", bgc(BASE_CONTAINER))
    setf(kCand, pn, "PinType.ContainerType", "Array")

# --- resolve + validate the bench's inventory -------------------------------
srcInv = add(GIBT_T)
setd(srcInv, "inventoryType", "PlaceableInventory")
connect(kStation, "OutputPin", srcInv, "owner")
isv = add(IV_T)
connect(srcInv, "ReturnValue", isv, "Object")
brValid = add(BRANCH_T)
connect(isv, "ReturnValue", brValid, "Condition")
retInvalid = terminus("InvalidInput")

# --- have / excess ----------------------------------------------------------
have = add(GNIBT_T)
connect(srcInv, "ReturnValue", have, "self")
connect(kTemplate, "OutputPin", have, "templateID")
excess = add(SUB_T)                       # have - Keep
connect(have, "ReturnValue", excess, "A")
connect(kKeep, "OutputPin", excess, "B")
hasExcess = add(GTI_T)                    # excess > 0
setd(hasExcess, "B", "0")
connect(excess, "ReturnValue", hasExcess, "A")
brExcess = add(BRANCH_T)
connect(hasExcess, "ReturnValue", brExcess, "Condition")

# --- TIDY: move excess out --------------------------------------------------
feTidy, brTidyMatch, tidyDstInv = search_loop(kCand, kStation, kTemplate)
mvOut = add(MOVE_T)
setd(mvOut, "bMoveAllAvailable", "true")
setd(mvOut, "ignoreSizeLimit", "true")
connect(srcInv, "ReturnValue", mvOut, "self")            # FROM the bench
connect(kTemplate, "OutputPin", mvOut, "templateID")
connect(excess, "ReturnValue", mvOut, "quantity")
connect(tidyDstInv, "ReturnValue", mvOut, "targetInventory")   # TO the chest
retMoved = terminus("Moved", moved_default=None)
connect(mvOut, "ReturnValue", retMoved, "Moved")
retNoDest = terminus("NoDestination")

# --- RESTOCK: pull a deficit in ---------------------------------------------
needMore = add(GTI_T)                     # Keep > have
connect(kKeep, "OutputPin", needMore, "A")
connect(have, "ReturnValue", needMore, "B")
brRestock = add(BRANCH_T)
connect(needMore, "ReturnValue", brRestock, "Condition")
deficit = add(SUB_T)                      # Keep - have
connect(kKeep, "OutputPin", deficit, "A")
connect(have, "ReturnValue", deficit, "B")
feRe, brReMatch, reSrcInv = search_loop(kCand, kStation, kTemplate)
mvIn = add(MOVE_T)
setd(mvIn, "bMoveAllAvailable", "true")
setd(mvIn, "ignoreSizeLimit", "true")
connect(reSrcInv, "ReturnValue", mvIn, "self")           # FROM the chest  <- swapped
connect(kTemplate, "OutputPin", mvIn, "templateID")
connect(deficit, "ReturnValue", mvIn, "quantity")
connect(srcInv, "ReturnValue", mvIn, "targetInventory")  # TO the bench    <- swapped
retRestocked = terminus("Restocked", moved_default=None)
connect(mvIn, "ReturnValue", retRestocked, "Moved")
retNoSource = terminus("NoSource")

# --- balanced ---------------------------------------------------------------
retNoExcess = terminus("NoExcess")

# --- exec: every path ends at a literal Return ------------------------------
# NB: brValid.execute is left OPEN -- the user wires entry.then into it.
connect_exec(brValid, retInvalid, "else", "execute")
connect_exec(brValid, brExcess, "then", "execute")
# excess > 0 -> tidy
connect_exec(brExcess, feTidy, "then", "Exec")
connect_exec(brTidyMatch, mvOut, "then", "execute")
connect_exec(mvOut, retMoved)
connect_exec(feTidy, retNoDest, "Completed", "execute")
# else -> is it a deficit?
connect_exec(brExcess, brRestock, "else", "execute")
connect_exec(brRestock, feRe, "then", "Exec")
connect_exec(brReMatch, mvIn, "then", "execute")
connect_exec(mvIn, retRestocked)
connect_exec(feRe, retNoSource, "Completed", "execute")
# neither -> balanced
connect_exec(brRestock, retNoExcess, "else", "execute")

# --- layout -----------------------------------------------------------------
kStation.set_position(200, 40); kTemplate.set_position(200, 90)
kKeep.set_position(200, 140); kCand.set_position(200, 190)
srcInv.set_position(360, 240); isv.set_position(560, 240)
brValid.set_position(400, 0); retInvalid.set_position(400, 200)
have.set_position(660, 340); excess.set_position(860, 340); hasExcess.set_position(1040, 340)
brExcess.set_position(720, 0)
feTidy.set_position(1000, -140)
mvOut.set_position(1700, -140); retMoved.set_position(1980, -140)
retNoDest.set_position(1000, 60)
brRestock.set_position(1000, 460)
needMore.set_position(760, 560); deficit.set_position(760, 640)
feRe.set_position(1260, 460)
mvIn.set_position(1960, 460); retRestocked.set_position(2240, 460)
retNoSource.set_position(1260, 660)
retNoExcess.set_position(1000, 760)

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

assert not [n for n in g.nodes if "FunctionEntry" in n.class_path], "entry must NOT be pasted"
results = [n for n in g.nodes if "FunctionResult" in n.class_path]
assert len(results) == 6, f"expected 6 termini, got {len(results)}"
got = sorted(str(pin(r, "Outcome")._get("DefaultValue")).strip('"') for r in results)
assert got == sorted(OUTCOME.values()), got
wilds = [(n.name, p.name) for n in g.nodes for p in n.pins
         if p._get("PinType.PinCategory") == '"wildcard"']
assert not wilds, f"unresolved wildcards: {wilds}"
moves = [n for n in g.nodes if "MoveItemsByTemplateId" in " ".join(t for k, t in n.body if k == "raw")]
assert len(moves) == 2, f"expected 2 moves (out and in), got {len(moves)}"

out = MOD + r"\.ccmod\graphs\bpfl_applykeeprule_v2.t3d"
open(out, "w", encoding="utf-8").write(g.render())
rev = {v: k for k, v in OUTCOME.items()}
print(f"nodes: {len(g.nodes)}   wrote: {out}")
print(f"termini: {sorted(rev[v] for v in got)}")
print(f"non-reciprocal / dangling problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
