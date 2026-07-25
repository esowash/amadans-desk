# How this mod's Blueprint graphs were built

**Problem.** Wiring Blueprint graphs by hand — dragging pins, right-click-searching
nodes — doesn't scale well for anything beyond a handful of nodes, and it's easy to
introduce silent, compiles-clean-but-wrong bugs (a wire landing on the wrong pin, a
loop's per-iteration signal wired to a function's `Return` instead of its `Completed`
pin, etc.).

**Blueprint nodes round-trip through the clipboard as plain text** — Unreal's own
`T3D` export format. Select nodes in a graph, `Ctrl+C`, and the clipboard holds a
readable text block per node:

```
Begin Object Class=/Script/BlueprintGraph.K2Node_CallFunction Name="K2Node_CallFunction_0"
   FunctionReference=(MemberParent="...",MemberName="...")
   NodePosX=... NodePosY=... NodeGuid=<GUID>
   CustomProperties Pin (PinId=<GUID>,PinName="...",Direction="EGPD_Input|Output",
       PinType.PinCategory="exec|object|...",...,LinkedTo=(<OtherNodeName> <OtherPinId>,),...)
End Object
```

- **Nodes** are identified by `Name="..."`; **pins** by `PinId=<GUID>`.
- **Connections** are `LinkedTo=(<TargetNodeName> <TargetPinId>,)`, present on **both**
  ends of a wire — UE requires the link recorded reciprocally at each end.
- Paste the text back in and the whole node network instantiates, fully wired.

## The workflow used throughout `.ccmod/`

1. **Capture real node shapes from ground truth**, never hand-type a guess. Drop a node
   via the DevKit's own right-click search (or find a real base-game Blueprint that
   already calls the function you need), select it, `Ctrl+C`, and read the exact T3D —
   this captures the correct `PinType.*` metadata, default values, and hidden pins that
   would be tedious and error-prone to hand-write.
2. **Assemble graphs programmatically** (`.ccmod/scripts/*.py`): clone captured node
   templates, remint unique `Name`/`NodeGuid`/`PinId` values, wire nodes together by
   writing matching `LinkedTo` pairs, and validate every link is reciprocal before
   trusting the result.
3. **Paste the assembled graph into the DevKit**, compile, and — critically — **pull
   the pasted result back and re-diff it** before considering anything "done." A clean
   compile does not guarantee correct wiring; several real bugs in this project were
   only caught by re-pulling and comparing against the intended graph.

## Real gotchas worth knowing before touching `.ccmod/graphs`

- **`K2Node_FunctionEntry` (a Function's entry node) cannot be pasted.** Function bodies
  in this repo are captured *without* their entry node; pasting one into an existing
  Function means redoing one hand-wire (`FunctionEntry.then` → the first real node,
  usually routed through a "knot" reroute node left at the splice point for this
  purpose). `K2Node_Event` and `K2Node_CustomEvent`, by contrast, paste fully intact —
  no hand-wire needed.
- **Latent/async nodes (`K2Node_AsyncAction`, `Delay`, etc.) cannot exist inside a plain
  Blueprint Function — only Event Graphs.** If a graph needs a latent call, it needs to
  live in a Custom Event, not a Function.
- **`K2Node_Message` (interface calls) do not support literal default values on
  unconnected input pins** — every parameter must be wired from a real value node, even
  simple ones like a bool. Also: in this specific DevKit build, pasting a `K2Node_Message`
  via the clipboard mechanism has reproducibly crashed the editor
  (`EXCEPTION_ACCESS_VIOLATION` inside `BlueprintGraph.dll`) — hand-add these via the
  GUI's own node search instead of clipboard paste.
- **Same-class self-calls** (a function calling another function on the same Blueprint)
  don't reliably survive being synthesized from scratch via clipboard paste — clone a
  real, already-working self-call node from elsewhere in the same graph instead, and
  just retarget its `MemberName` (omit `MemberGuid` entirely; Unreal resolves by name
  when it's absent, then fixes up the GUID on the next save).
- Cloning the *same* node template twice into one target graph needs care: a naive
  rename-on-collision can leave the `ExportPath` string's own trailing object-path
  reference stale even after the node's `Name=` is correctly updated, producing two
  distinct nodes with colliding `ExportPath`s that Unreal may silently mis-import.

## Verifying results (not covered here in depth)

Build → deploy the cooked `.pak` → launch → check `LogBlueprintUserMessages` in the
game's log for any debug `PrintString` checkpoints, and cross-reference the save
database (`Game_0.db`, SQLite) for ground truth on what actually happened in the world
(item counts, character records, etc.) rather than trusting log text alone.
