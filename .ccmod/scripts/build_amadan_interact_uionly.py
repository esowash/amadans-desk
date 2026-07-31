"""Desk interact chain: swap SetInputMode_GameAndUIEx -> SetInputMode_UIOnlyEx.

Rationale (2026-07-18, session 11): the mouse-cursor dead end from session 10
was reached while the desk graph used Game-And-UI input mode. Two forum root
causes (https://forums.unrealengine.com/t/cant-hide-mouse-cursor-again/410006)
reframe it:
  1. A focused UMG widget uses its OWN cursor settings, overriding the
     PlayerController -- so every prior attempt (all on PlayerController's
     bShowMouseCursor) fought the wrong object. (-> widget Cursor property,
     handled in the Details panel, not here.)
  2. Game-And-UI mode does a game-capture dance that is the flaky cursor path;
     UI-Only is the reliable one. UI-Only was tried ONCE in session 10 -- as the
     very first attempt, BEFORE the inherited crafting menu (focus thief) and the
     camera lock were fixed -- and never retried after those confounds cleared.
     So "UI-Only + focus set + camera locked + no parent crafting menu" has never
     actually run.

This edit is a strict-subset derivation from the real captured GameAndUIEx node
(same WidgetBlueprintLibrary): UIOnlyEx's params are GameAndUIEx's minus
bHideCursorDuringCapture (bFlushInput is kept -- confirmed superset relationship,
[[stocker-current-state]]). All exec/data links (Set bShowMouseCursor.then ->
this.execute, this.then -> SetIgnoreMoveInput.execute, CreateWidget ->
InWidgetToFocus, GetPlayerController -> PlayerController) are preserved untouched.

Everything else in the chain is byte-for-byte the session-10 live graph
(amadan_interact_gameandui.t3d): InteractableActivate -> Print(begin) ->
CreateWidget -> AddToViewport -> Set bShowMouseCursor(true) -> [this node] ->
SetIgnoreMoveInput -> SetIgnoreLookInput -> Print(done).
"""
import sys

import os, pathlib
CCMOD = os.environ.get("CCMOD_HOME") or str(pathlib.Path(__file__).resolve().parents[3] / "claude-conan-modder")
sys.path.insert(0, CCMOD)
from ccmod.t3d import parse

import pathlib
MOD = str(pathlib.Path(__file__).resolve().parents[2])
SRC = MOD + r"\.ccmod\graphs\amadan_interact_gameandui.t3d"
OUT = MOD + r"\.ccmod\graphs\amadan_interact_uionly.t3d"

g = parse(open(SRC, encoding="utf-8").read())
n = g.by_name("K2Node_CallFunction_2")
assert n is not None, "SetInputMode node K2Node_CallFunction_2 not found"

# --- confirm we're editing the node we think we are ---------------------------
fnline = next(t for k, t in n.body if k == "raw" and "FunctionReference" in t)
assert "SetInputMode_GameAndUIEx" in fnline, f"unexpected function: {fnline}"
before = [p.name for p in n.pins]
assert before == ["execute", "then", "self", "PlayerController",
                  "InWidgetToFocus", "InMouseLockMode",
                  "bHideCursorDuringCapture", "bFlushInput"], before

# --- capture the links we must preserve, to assert they survive ---------------
def links_of(pname):
    return list(n.pin_by_name(pname).links)

pre = {p: links_of(p) for p in
       ("execute", "then", "PlayerController", "InWidgetToFocus")}

# --- 1) rename the member: GameAndUIEx -> UIOnlyEx -----------------------------
n._replace_prop(
    "FunctionReference",
    '(MemberParent="/Script/CoreUObject.Class\'/Script/UMG.WidgetBlueprintLibrary\'"'
    ',MemberName="SetInputMode_UIOnlyEx")',
)

# --- 2) drop the one GameAndUI-only pin: bHideCursorDuringCapture --------------
drop = n.pin_by_name("bHideCursorDuringCapture")
assert drop is not None and not drop.links, "bHideCursorDuringCapture should be link-free"
n.body = [(k, v) for (k, v) in n.body
          if not (k == "pin" and v is drop)]

# --- verify ---------------------------------------------------------------------
after = [p.name for p in n.pins]
assert after == ["execute", "then", "self", "PlayerController",
                 "InWidgetToFocus", "InMouseLockMode", "bFlushInput"], after
newfn = next(t for k, t in n.body if k == "raw" and "FunctionReference" in t)
assert "SetInputMode_UIOnlyEx" in newfn and "GameAndUI" not in newfn, newfn
for p, expect in pre.items():
    got = links_of(p)
    assert got == expect, f"link on {p} changed: {expect} -> {got}"

# --- reciprocal-link integrity across the whole graph --------------------------
names = {x.name for x in g.nodes}
problems = []
for node in g.nodes:
    for p in node.pins:
        for (lnn, lp) in p.links:
            if lnn not in names:
                problems.append(f"{node.name}.{p.name} -> missing node {lnn}")
                continue
            other = g.by_name(lnn).pin_by_id(lp)
            if other is None:
                problems.append(f"{node.name}.{p.name} -> {lnn} missing pin {lp}")
                continue
            if (node.name, p.pin_id) not in other.links:
                problems.append(f"non-reciprocal: {node.name}.{p.name} -> {lnn}")

open(OUT, "w", encoding="utf-8").write(g.render())
print(f"nodes: {len(g.nodes)}   pins now: {after}")
print(f"function: {newfn.strip()}")
print(f"wrote: {OUT}")
print(f"reciprocal-link problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
