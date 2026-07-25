r"""Fix: RefreshRulesList's row text always showed the numeric Keep value, even for
KeepAll=true rules (where the number is stale/meaningless -- user reported this after
session 18's live playtest). Full pull+edit+repaste of the whole RefreshRulesList body,
based on amadanmenu_refreshruleslist_fixed.t3d (the last real pulled-and-corrected state,
post the GetAllActorsOfClass exec-pin fix) -- per this project's own "prefer full
pull+edit+repaste unless the splice point has a distinctive GUI label" rule, since this
touches several nodes buried inside the per-rule loop body.

Lucky break: K2Node_BreakStruct_rr in the live graph ALREADY exposes a KeepAll output
pin (PinId=12EE8DDE455B03CFFCA01F92D02C8838, PersistentGuid=A6025F204FE4948B8C46EE8626A13B30)
-- unconnected, but present. UE auto-expanded the BreakStruct's shown properties to the
struct's full 4 fields at some point after our original build script (which only declared
3), so no BreakStruct surgery is needed at all, just a new wire off the existing pin.

Design: fork right after Concat_2 (the "<Bench> - <Item>" prefix, shared either way).
The existing Concat_3/Concat_4/ConvI2S/ConvS2T/SetText(K2Node_CallFunction_7) chain
(": " + Keep number) is left completely untouched and only reached on the KeepAll=false
branch. A new parallel chain (" (All)" literal, no number) is built for KeepAll=true.
Both converge into the existing AddChild (K2Node_CallFunction_4) exec pin -- a plain
fan-in, two independent exec sources landing on one input pin, which is normal/legal
K2 wiring (distinct from the project's known output-fanout gotcha, which only applies to
ONE output pin driving multiple destinations and needs a Sequence node instead).

IfThenElse node cloned from a real, already-compiling precedent (menu_tidymanagedstations_body.t3d's
K2Node_IfThenElse_0) rather than hand-typed -- same discipline as every other node shape
in this project. Concat_StrStr/Conv_StringToText/SetText clones come from THIS SAME live
graph (Concat_3, ConvS2T, CallFunction_7), so their FunctionReference/self-pin shape is
guaranteed correct, zero guessing.
"""
import sys

CCMOD = r"<CCMOD_HOME>"
sys.path.insert(0, CCMOD)
from ccmod.t3d import parse, connect, connect_exec
from ccmod.t3d.generator import instantiate
from ccmod.t3d.model import Graph

MOD = r"<MOD_ROOT>"
BASE_SRC = MOD + r"\.ccmod\graphs\amadanmenu_refreshruleslist_fixed.t3d"
TIDY_SRC = MOD + r"\.ccmod\graphs\menu_tidymanagedstations_body.t3d"

g = parse(open(BASE_SRC, encoding="utf-8-sig").read())
tidy_src = parse(open(TIDY_SRC, encoding="utf-8-sig").read())


def pin(n, name, output=None):
    p = n.pin_by_name(name, output=output)
    assert p, f"{n.name} has no pin {name}"
    return p


def setf(n, pn, k, raw, output=None):
    pin(n, pn, output=output)._set(k, raw)


def tmpl_from_live(name):
    import copy
    n = copy.deepcopy(g.by_name(name))
    for p in n.pins:
        p.links = []
    return Graph(nodes=[n])


def add(t):
    return instantiate(t, g)[0]


# --- existing nodes we splice around ------------------------------------------------
breakRule = g.by_name("K2Node_BreakStruct_rr")
concat2 = g.by_name("K2Node_CallFunction_Concat_2")
setOwning = g.by_name("K2Node_VariableSet_1")       # sets NewRow.OwningMenu
setTextKeep = g.by_name("K2Node_CallFunction_7")    # existing SetText, false-path (numeric)
addChild = g.by_name("K2Node_CallFunction_4")
ruleTextGet = g.by_name("K2Node_VariableGet_2")     # NewRow.RuleText getter (pure, fans out)

# --- branch on Rule.KeepAll -----------------------------------------------------------
import copy
ifte_src = copy.deepcopy(tidy_src.by_name("K2Node_IfThenElse_0"))
for p in ifte_src.pins:
    p.links = []
branch = add(Graph(nodes=[ifte_src]))

# disconnect the old direct exec wire (setOwning.then -> setTextKeep.execute)
setOwning_then = pin(setOwning, "then", output=True)
setTextKeep_exec = pin(setTextKeep, "execute", output=False)
setOwning_then.links = []
setTextKeep_exec.links = []

connect_exec(setOwning, branch, "then", "execute")
connect(breakRule, "KeepAll_10_A6025F204FE4948B8C46EE8626A13B30", branch, "Condition")
connect_exec(branch, setTextKeep, "else", "execute")  # false: unchanged numeric chain

# --- new "(All)" chain, forked off Concat_2's shared "<Bench> - <Item>" prefix --------
concatAll = add(tmpl_from_live("K2Node_CallFunction_Concat_3"))
connect(concat2, "ReturnValue", concatAll, "A")
setf(concatAll, "B", "DefaultValue", '" (All)"')

convAll = add(tmpl_from_live("K2Node_CallFunction_ConvS2T"))
connect(concatAll, "ReturnValue", convAll, "InString")

setTextAll = add(tmpl_from_live("K2Node_CallFunction_7"))
connect(ruleTextGet, "RuleText", setTextAll, "self")
connect(convAll, "ReturnValue", setTextAll, "InText")
connect_exec(branch, setTextAll, "then", "execute")  # true: KeepAll

# --- converge both paths into the existing AddChild exec input (fan-in, legal) --------
connect_exec(setTextAll, addChild, "then", "execute")

# --- validate --------------------------------------------------------------------------
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

out = MOD + r"\.ccmod\graphs\amadanmenu_refreshruleslist_keepall_fix.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"nodes: {len(g.nodes)}   wrote: {out}")
print(f"problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
print()
print("This is a FULL function-body replacement, same as the earlier GAC-exec-pin fix:")
print("select the whole RefreshRulesList body in the DevKit, delete, paste this file's")
print("contents, then re-do the ONE entry hand-wire (Entry.then -> the ClearChildren knot),")
print("same as every previous RefreshRulesList build.")
