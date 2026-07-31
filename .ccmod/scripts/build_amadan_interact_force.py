"""Final runtime-path test: ActivateModule("StockerHouseRules", activate=true,
force=TRUE) with the IsValid diagnostic. Long shot -- `force` most likely means
"re-activate an already-registered module," not "re-scan the table for unknown
names" -- but it's the one ActivateModule param never tried, and it closes the
door on any runtime fix before we commit to the base-override.

Two pin-default changes vs amadan_interact_modtest_diag.t3d:
  * ActivateModule.moduleName  "ContainerInfo" -> "StockerHouseRules"  (our merged, un-cached module)
  * ActivateModule.force       "false"         -> "true"
Structure (IsValid -> Branch -> VALID/NULL prints) is identical. Labels updated.
"""
import sys

import os, pathlib
CCMOD = os.environ.get("CCMOD_HOME") or str(pathlib.Path(__file__).resolve().parents[3] / "claude-conan-modder")
sys.path.insert(0, CCMOD)
from ccmod.t3d import parse

import pathlib
MOD = str(pathlib.Path(__file__).resolve().parents[2])
SRC = MOD + r"\.ccmod\graphs\amadan_interact_modtest_diag.t3d"
OUT = MOD + r"\.ccmod\graphs\amadan_interact_force.t3d"

g = parse(open(SRC, encoding="utf-8").read())
act = g.by_name("K2Node_CallFunction_5")
assert "ActivateModule" in next(t for k, t in act.body if k == "raw" and "FunctionReference" in t)

mod_pin = act.pin_by_name("moduleName")
force_pin = act.pin_by_name("force")
assert mod_pin._get("DefaultValue") == '"ContainerInfo"', mod_pin._get("DefaultValue")
assert force_pin._get("DefaultValue") == '"false"', force_pin._get("DefaultValue")
mod_pin._set("DefaultValue", '"StockerHouseRules"')
force_pin._set("DefaultValue", '"true"')

# relabel begin print so the log is self-describing
g.by_name("K2Node_CallFunction_21").pin_by_name("InString")._set(
    "DefaultValue", '"STOCKER_MODTEST begin (ActivateModule StockerHouseRules force=true)"')

# link integrity
names = {n.name for n in g.nodes}
problems = []
for n in g.nodes:
    for p in n.pins:
        for (lnn, lp) in p.links:
            if lnn not in names:
                problems.append(f"{n.name}.{p.name} -> missing {lnn}"); continue
            other = g.by_name(lnn).pin_by_id(lp)
            if other is None or (n.name, p.pin_id) not in other.links:
                problems.append(f"bad link {n.name}.{p.name} -> {lnn}")

open(OUT, "w", encoding="utf-8").write(g.render())
print("moduleName:", mod_pin._get("DefaultValue"), " force:", force_pin._get("DefaultValue"))
print("nodes:", len(g.nodes), " wrote:", OUT, " link problems:", len(problems))
for pr in problems: print("  !", pr)
