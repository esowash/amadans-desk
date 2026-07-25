"""One-step test: does ActivateModule open an EXISTING module from our desk's
interact? Isolates the call mechanism from module-registration.

Session 10 called ActivateModule(moduleName="StockerHouseRules") and got a None
return -- which we blamed on the DT_UIModuleTable boot-cache timing wall. But
"StockerHouseRules" was never registered anywhere, so None just means
"module not found." It says nothing about whether the CALL works.

This changes exactly one thing: moduleName "StockerHouseRules" -> "ContainerInfo",
a module that IS in the boot-cached table (confirmed: BP_PlaceableItemContainer's
InteractableGetUIModuleName returns literally "ContainerInfo"). Our desk is itself
a container, so ContainerInfo is a natural, clean-rendering target.

Interpretation of the cook:
  * a panel opens WITH a working cursor  -> the direct ActivateModule path works
    from our interact; the ONLY remaining problem is registering OUR module. No
    re-basing the placeable needed.
  * nothing opens / None again          -> the call itself is the problem (context:
    real callers guard with IsLocallyControlled and the sign opens from a client
    RPC). Then we escalate (client-side event) or reconsider re-basing to a
    plain container.

The override deliberately does NOT call Parent, so the crafting-station native
InteractableActivate does not run and the Artisan crafting UI stays closed --
leaving ActivateModule("ContainerInfo") as the only thing that can open a panel,
so the result is unambiguous. Print banners bracket the call.
"""
import sys

CCMOD = r"<CCMOD_HOME>"
sys.path.insert(0, CCMOD)
from ccmod.t3d import parse

MOD = r"<MOD_ROOT>"
SRC = MOD + r"\.ccmod\graphs\amadan_interact_activatemodule.t3d"
OUT = MOD + r"\.ccmod\graphs\amadan_interact_modtest.t3d"

g = parse(open(SRC, encoding="utf-8").read())

# --- the one real change: retarget ActivateModule at a registered module -------
act = g.by_name("K2Node_CallFunction_5")
assert act is not None
fn = next(t for k, t in act.body if k == "raw" and "FunctionReference" in t)
assert "ActivateModule" in fn, fn
mod_pin = act.pin_by_name("moduleName")
assert mod_pin._get("DefaultValue") == '"StockerHouseRules"', mod_pin._get("DefaultValue")
mod_pin._set("DefaultValue", '"ContainerInfo"')

# --- relabel the two print banners so the log is self-describing ---------------
begin = g.by_name("K2Node_CallFunction_21")   # "begin" print
done = g.by_name("K2Node_CallFunction_22")    # "done" print
begin.pin_by_name("InString")._set("DefaultValue", '"STOCKER_MODTEST begin (ActivateModule ContainerInfo)"')
done.pin_by_name("InString")._set("DefaultValue", '"STOCKER_MODTEST done (ActivateModule returned)"')

# --- verify link integrity is untouched ----------------------------------------
names = {n.name for n in g.nodes}
problems = []
for n in g.nodes:
    for p in n.pins:
        for (lnn, lp) in p.links:
            if lnn not in names:
                problems.append(f"{n.name}.{p.name} -> missing {lnn}"); continue
            other = g.by_name(lnn).pin_by_id(lp)
            if other is None:
                problems.append(f"{n.name}.{p.name} -> {lnn} missing pin {lp}"); continue
            if (n.name, p.pin_id) not in other.links:
                problems.append(f"non-reciprocal: {n.name}.{p.name} -> {lnn}")

open(OUT, "w", encoding="utf-8").write(g.render())
print("moduleName now:", act.pin_by_name("moduleName")._get("DefaultValue"))
print("nodes:", len(g.nodes), " wrote:", OUT)
print("link problems:", len(problems))
for pr in problems:
    print("  !", pr)
