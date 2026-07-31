"""Author RunSweep() on Menu_ModController -- the thin orchestrator that will eventually be called
by the repeating sweep Timer. Just calls TidyManagedStations() then RestockManagedStations() in that
order (matching the original BeginPlay's tidy-then-restock sequencing). Void, no params.

Both callees are same-class self calls (no target/self pin needed, no MemberParent -- they're defined
directly on Menu_ModController itself), so this is authored from scratch rather than extracted from
the Stocker source, which never had these functions.
"""
import sys

import os, pathlib
CCMOD = os.environ.get("CCMOD_HOME") or str(pathlib.Path(__file__).resolve().parents[3] / "claude-conan-modder")
sys.path.insert(0, CCMOD)
from ccmod.t3d import parse, connect, connect_exec, auto_layout
from ccmod.t3d.generator import instantiate
from ccmod.t3d.model import Graph

import pathlib
MOD = str(pathlib.Path(__file__).resolve().parents[2])
LIB = CCMOD + r"\library"


def tmpl_file(path):
    t = parse(open(path, encoding="utf-8-sig").read())
    for n in t.nodes:
        for p in n.pins:
            p.links = []
    return t


def setf(n, pn, k, raw, output=None):
    n.pin_by_name(pn, output=output)._set(k, raw)


KNOT_T = tmpl_file(LIB + r"\flow\knot.t3d")

CALL_RAW = '''Begin Object Class=/Script/BlueprintGraph.K2Node_CallFunction Name="K2Node_CallFunction_0"
   FunctionReference=(MemberName="{name}")
   NodeGuid=00000000000000000000000000000000
   CustomProperties Pin (PinId=00000000000000000000000000000001,PinName="execute",PinType.PinCategory="exec",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False,)
   CustomProperties Pin (PinId=00000000000000000000000000000002,PinName="then",Direction="EGPD_Output",PinType.PinCategory="exec",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False,)
End Object'''


def call_template(name):
    return parse(CALL_RAW.format(name=name))


def type_knot(n, category):
    for pn in ("InputPin", "OutputPin"):
        setf(n, pn, "PinType.PinCategory", f'"{category}"')
        setf(n, pn, "PinType.PinSubCategoryObject", "None")
        setf(n, pn, "PinType.ContainerType", "None")


g = Graph()


def add(t):
    return instantiate(t, g)[0]


knot_entry = add(KNOT_T)
type_knot(knot_entry, "exec")

call_tidy = add(call_template("TidyManagedStations"))
call_restock = add(call_template("RestockManagedStations"))

connect(knot_entry, "OutputPin", call_tidy, "execute")
connect_exec(call_tidy, call_restock)

auto_layout(g.nodes, origin=(0, 0), dx=260, dy=0, per_column=0)

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

out = MOD + r"\.ccmod\graphs\menu_runsweep_body.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"RunSweep: nodes={len(g.nodes)} wrote={out} problems={len(problems)}")
for pr in problems:
    print("  !", pr)
print(f"  knot -> exec(entry.then) = {knot_entry.name}")
