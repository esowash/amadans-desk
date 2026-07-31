r"""Add a persistence load-guard to Menu_ModController's BeginPlay.

Full pull+edit+repaste onto the live graph (modcontroller_beginplay_s19_persist.t3d),
which turned out to be tiny and clean: ReceiveBeginPlay -> K2_SetTimer (the RunSweep
timer). K2Node_Event CAN be pasted (unlike K2Node_FunctionEntry), so this whole thing
should paste with no hand-wire needed at all.

Design: fork right after ReceiveBeginPlay via a new ExecutionSequence -- one branch keeps
the existing SetTimer call untouched, the other branch polls IsDataDoneLoading (pure,
off the same self-context PersistenceComponent get proven this session) via a Branch
that loops back through itself on a 1s Delay until true, then prints a confirmation with
the restored rule count. This is a standard, safe polling idiom (Delay yields control
back to the engine every cycle -- not a tight synchronous loop, nothing like the
self-recursion hang from earlier tonight).

Real captured precedent, all already on disk from this session's work:
- PersistenceComponent get + IsDataDoneLoading call: persistence_check2_s19.t3d
- KeepRulesV2 get: addkeeprule_live_s19_persist.t3d
- IfThenElse (Branch): addkeeprule_live_s19_persist.t3d
- Delay (Duration=1.0, cloned and overridden): menu_modcontroller_eventgraph_live_s16.t3d
- ExecutionSequence / Array_Length / Conv_IntToString / PrintString:
  stocker_modcontroller_probe_a_live.t3d (this project's oldest, most-reused template source)
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
GRAPHS = MOD + r"\.ccmod\graphs"

g = parse(open(GRAPHS + r"\modcontroller_beginplay_s19_persist.t3d", encoding="utf-8-sig").read())
persist_src = parse(open(GRAPHS + r"\persistence_check2_s19.t3d", encoding="utf-8-sig").read())
addrule_src = parse(open(GRAPHS + r"\addkeeprule_live_s19_persist.t3d", encoding="utf-8-sig").read())
timer_src = parse(open(GRAPHS + r"\menu_modcontroller_eventgraph_live_s16.t3d", encoding="utf-8-sig").read())
probe_src = parse(open(GRAPHS + r"\stocker_modcontroller_probe_a_live.t3d", encoding="utf-8-sig").read())


def pin(n, name, output=None):
    p = n.pin_by_name(name, output=output)
    assert p, f"{n.name} has no pin {name}"
    return p


def setf(n, pn, k, raw, output=None):
    pin(n, pn, output=output)._set(k, raw)


def add(t):
    return instantiate(t, g)[0]


def clone_from(src_graph, name):
    n = copy.deepcopy(src_graph.by_name(name))
    for p in n.pins:
        p.links = []
    return Graph(nodes=[n])


event = g.by_name("K2Node_Event_0")            # ReceiveBeginPlay
setTimer = g.by_name("K2Node_CallFunction_10298")  # existing K2_SetTimer

# disconnect the existing direct link so we can splice a Sequence in between
event_then = pin(event, "then", output=True)
setTimer_exec = pin(setTimer, "execute", output=False)
event_then.links = []
setTimer_exec.links = []

seq = add(clone_from(probe_src, "K2Node_ExecutionSequence_0"))
connect_exec(event, seq, "then", "execute")
connect_exec(seq, setTimer, "then_0", "execute")

# --- IsDataDoneLoading poll chain ---------------------------------------------------------
persistGet = add(clone_from(persist_src, "K2Node_VariableGet_1"))   # self-context PersistenceComponent get
isDoneCall = add(clone_from(persist_src, "K2Node_CallFunction_2"))  # IsDataDoneLoading (pure)
connect(persistGet, "PersistenceComponent", isDoneCall, "self")

branch = add(clone_from(addrule_src, "K2Node_IfThenElse_0"))
connect(isDoneCall, "ReturnValue", branch, "Condition")
connect_exec(seq, branch, "then_1", "execute")

delay = add(clone_from(timer_src, "K2Node_CallFunction_68"))
setf(delay, "Duration", "DefaultValue", "1.000000")
connect_exec(branch, delay, "else", "execute")
connect_exec(delay, branch, "then", "execute")  # loop back: re-poll after the wait

# --- success print: label + rule count ----------------------------------------------------
PRINT_T = clone_from(probe_src, "K2Node_CallFunction_21")
LEN_T = clone_from(probe_src, "K2Node_CallArrayFunction_0")
CONV_T = clone_from(probe_src, "K2Node_CallFunction_32")

keepRulesGet = add(clone_from(addrule_src, "K2Node_VariableGet_50"))  # self-context KeepRulesV2 get

lenCall = add(LEN_T)
setf(lenCall, "TargetArray", "PinType.PinCategory", '"struct"')
setf(lenCall, "TargetArray", "PinType.PinSubCategoryObject",
     '''"/Script/CoreUObject.UserDefinedStruct'/Game/Mods/Menu/S_KeepRule.S_KeepRule'"''')
setf(lenCall, "TargetArray", "PinType.ContainerType", "Array")
connect(keepRulesGet, "KeepRulesV2", lenCall, "TargetArray")

convCall = add(CONV_T)
connect(lenCall, "ReturnValue", convCall, "InInt")

printLabel = add(PRINT_T)
setf(printLabel, "InString", "DefaultValue", '"MENU_PERSISTENCE: data loaded, rules restored:"')
printCount = add(PRINT_T)
connect(convCall, "ReturnValue", printCount, "InString")

connect_exec(branch, printLabel, "then", "execute")
connect_exec(printLabel, printCount, "then", "execute")

# --- validate --------------------------------------------------------------------------------
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

out = GRAPHS + r"\modcontroller_beginplay_persist_loadguard.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"nodes: {len(g.nodes)}   wrote: {out}")
print(f"problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
print("wildcards:", wilds)
