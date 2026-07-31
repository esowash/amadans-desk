"""BFS the real BeginPlay exec spine of Stocker_ModController, following ONLY exec-category
pins, starting from the ReceiveBeginPlay event. Prints the ordered chain: node name, class,
FunctionReference/VariableReference where relevant, and any literal print-string label, so we can
tell which of the several overlapping tidy-pass (3M/3N/3R/3T/3U) implementations is actually live
vs a dead leftover never reached from the real event.
"""
import sys

import os, pathlib
CCMOD = os.environ.get("CCMOD_HOME") or str(pathlib.Path(__file__).resolve().parents[3] / "claude-conan-modder")
sys.path.insert(0, CCMOD)
from ccmod.t3d import parse

import pathlib
MOD = str(pathlib.Path(__file__).resolve().parents[2])
SRC_GRAPH = MOD + r"\.ccmod\graphs\stocker_modcontroller_probe_a_live.t3d"

g = parse(open(SRC_GRAPH, encoding="utf-8-sig").read())
by_name = {n.name: n for n in g.nodes}


def src_of(pin):
    """Describe whatever feeds a (non-exec) input pin, one hop back."""
    if not pin or not pin.links:
        return f"UNCONNECTED(default={pin._get('DefaultValue') if pin else '?'})"
    nn, pid = pin.links[0]
    other = by_name.get(nn)
    if not other:
        return f"{nn}(missing)"
    raw = " ".join(t for k, t in other.body if k == "raw")
    for k, v in other.body:
        if k == "raw" and v.strip().startswith("VariableReference"):
            return f"{nn}:{v.strip()}"
        if k == "raw" and v.strip().startswith("FunctionReference"):
            return f"{nn}:{v.strip()}"
    return nn


def describe(n):
    raw = " ".join(t for k, t in n.body if k == "raw")
    bits = [n.name, n.class_path.rsplit(".", 1)[-1]]
    if "FunctionReference" in raw:
        for k, v in n.body:
            if k == "raw" and v.strip().startswith("FunctionReference"):
                bits.append(v.strip())
    if "VariableReference" in raw:
        for k, v in n.body:
            if k == "raw" and v.strip().startswith("VariableReference"):
                bits.append(v.strip())
    isp = n.pin_by_name("InString")
    if isp and isp._get("DefaultValue"):
        bits.append("PRINT:" + isp._get("DefaultValue"))
    if n.class_path.endswith("K2Node_IfThenElse"):
        bits.append("COND<-" + src_of(n.pin_by_name("Condition")))
    if n.class_path.endswith("K2Node_MacroInstance"):
        bits.append("ARRAY<-" + src_of(n.pin_by_name("Array")))
    if n.class_path.endswith("K2Node_CallFunction") and "ApplyKeepRule" in raw:
        for pn in ("Station", "TemplateID", "Keep", "KeepAll", "Candidates"):
            bits.append(f"{pn}<-" + src_of(n.pin_by_name(pn)))
    return " | ".join(bits)


# find the entry event (ReceiveBeginPlay / Event BeginPlay)
roots = [n for n in g.nodes if n.class_path.endswith("K2Node_Event")]
for r in roots:
    print("ROOT CANDIDATE:", describe(r))
print("---")

visited = set()
order = []


def walk(node, depth):
    if node.name in visited:
        return
    visited.add(node.name)
    order.append((depth, describe(node)))
    for p in node.pins:
        if not p.is_exec or not p.is_output:
            continue
        for (nn, pid) in p.links:
            nxt = by_name.get(nn)
            if nxt:
                walk(nxt, depth + 1)


for r in roots:
    walk(r, 0)

for depth, desc in order:
    print(f"[{depth:>2}] " + "  " * depth + desc)

print("---")
print(f"visited {len(visited)} / {len(g.nodes)} nodes via exec-only BFS from event root(s)")
unreached = [n for n in g.nodes if n.name not in visited]
print(f"unreached: {len(unreached)}")
for n in unreached:
    if n.pin_by_name("InString"):
        print("  UNREACHED PRINT NODE:", describe(n))
