"""Add an IsValid check on ActivateModule's return so the log tells us WHICH
world we're in:

  ActivateModule("ContainerInfo").ReturnValue (WindowRoot)
     -> IsValid -> Branch
          true  -> Print "RESULT VALID"  (call works + module found; nothing
                   rendered = missing SetContent / client-side render)
          false -> Print "RESULT NULL"   (the call itself fails from our
                   interact context -> server-side / needs client RPC)

Everything upstream (InteractableActivate -> Print begin -> GetGUIModuleController
-> ActivateModule) is the proven-firing session-11 modtest graph, untouched. Only
the tail changes: ActivateModule.then now feeds the Branch instead of the plain
"done" print; the old done-print is reused as the VALID branch.

Nodes minted from real captures (no hand-fabricated signatures):
  * IsValid    -> library/call/is_valid.t3d (KismetSystemLibrary::IsValid)
  * IfThenElse -> the real node from chalkcircle_getuimodulename.t3d, links
                  stripped so nothing external rides in (ccmod capture-link bug)
  * 2nd Print  -> a clean copy of the graph's own PrintString
"""
import sys, copy

CCMOD = r"<CCMOD_HOME>"
sys.path.insert(0, CCMOD)
from ccmod.t3d import parse
from ccmod.t3d.generator import instantiate, connect, connect_exec

MOD = r"<MOD_ROOT>"
G = MOD + r"\.ccmod\graphs\amadan_interact_modtest.t3d"
CC = MOD + r"\.ccmod\graphs\chalkcircle_getuimodulename.t3d"
ISV = CCMOD + r"\library\call\is_valid.t3d"
OUT = MOD + r"\.ccmod\graphs\amadan_interact_modtest_diag.t3d"


def clean_template(node):
    """A single-node Graph copy with every pin link stripped."""
    n = copy.deepcopy(node)
    for p in n.pins:
        p.links = []
    return parse(n.render())


g = parse(open(G, encoding="utf-8").read())
act = g.by_name("K2Node_CallFunction_5")      # ActivateModule("ContainerInfo")
done = g.by_name("K2Node_CallFunction_22")    # existing "done" print -> reuse as VALID
assert act and done

# --- 1) detach ActivateModule.then -> done.execute (clear BOTH ends) -----------
then_pin = act.pin_by_name("then", output=True)
done_exec = done.pin_by_name("execute", output=False)
assert (done.name, done_exec.pin_id) in then_pin.links, "expected act.then -> done.execute"
then_pin.links = [l for l in then_pin.links if l[0] != done.name]
done_exec.links = [l for l in done_exec.links if l[0] != act.name]

# --- 2) mint the three new nodes ------------------------------------------------
isv = instantiate(parse(open(ISV, encoding="utf-8").read()), g)[0]

cc = parse(open(CC, encoding="utf-8").read())
branch = instantiate(clean_template(cc.by_name("K2Node_IfThenElse_0")), g)[0]

null_print = instantiate(clean_template(done), g)[0]

# place them so the user can read the branch (positions are cosmetic)
isv.set_position(2120, 260)
branch.set_position(2120, 40)
null_print.set_position(2460, 260)

# --- 3) wire the diagnostic -----------------------------------------------------
connect_exec(act, branch)                                   # act.then -> branch.execute
connect(act, "ReturnValue", isv, "Object")                 # WindowRoot -> IsValid.Object
connect(isv, "ReturnValue", branch, "Condition")           # bool -> Branch.Condition
connect_exec(branch, done, "then", "execute")              # true  -> VALID print
connect_exec(branch, null_print, "else", "execute")        # false -> NULL print

# --- 4) relabel the two result prints ------------------------------------------
done.pin_by_name("InString")._set(
    "DefaultValue", '"STOCKER_MODTEST_RESULT VALID (ActivateModule returned a WindowRoot)"')
null_print.pin_by_name("InString")._set(
    "DefaultValue", '"STOCKER_MODTEST_RESULT NULL (ActivateModule returned nothing)"')

# --- 5) full reciprocal-link + dangling-ref validation -------------------------
names = {n.name for n in g.nodes}
problems = []
for n in g.nodes:
    for p in n.pins:
        for (lnn, lp) in p.links:
            if lnn not in names:
                problems.append(f"{n.name}.{p.name} -> MISSING node {lnn}"); continue
            other = g.by_name(lnn).pin_by_id(lp)
            if other is None:
                problems.append(f"{n.name}.{p.name} -> {lnn} missing pin {lp}"); continue
            if (n.name, p.pin_id) not in other.links:
                problems.append(f"non-reciprocal: {n.name}.{p.name} -> {lnn}")

# sanity: exactly the exec topology we intended
assert len(then_pin.links) == 1 and then_pin.links[0][0] == branch.name, then_pin.links
bt = branch.pin_by_name("then", output=True).links
be = branch.pin_by_name("else", output=True).links
assert len(bt) == 1 and bt[0][0] == done.name, bt
assert len(be) == 1 and be[0][0] == null_print.name, be

open(OUT, "w", encoding="utf-8").write(g.render())
print(f"nodes: {len(g.nodes)}  (added IsValid={isv.name}, Branch={branch.name}, NullPrint={null_print.name})")
print(f"act.then -> {then_pin.links}")
print(f"branch.true -> {bt}   branch.false -> {be}")
print(f"wrote: {OUT}")
print(f"link problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
