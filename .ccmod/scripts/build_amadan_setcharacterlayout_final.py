"""Splice the SetCharacterLayout call (hand-added by the user, resolved as a plain K2Node_CallFunction
since Amadan statically implements HasCharacterLayoutInterface - not the crash-prone K2Node_Message
variant) into Amadan's BeginPlay, after the existing ReceiveBeginPlay->CallParentFunction chain.
Fills the 5 MakeStruct constructor nodes (MeshLayout/TextureLayout/TintLayout/BoolParams/EnumParams,
real node shapes discovered live by the user dragging off the split Layout_* pins) with his real
extracted appearance values from docs/AMADAN-BUG.md. Adds a K2Node_Self (cloned from a real capture
elsewhere in this repo) to feed the Target/self interface pin, which the DevKit left unconnected.
IsServer is a real literal-editable bool on this CallFunction variant (unlike a Message node) - set
directly to true, no IsServer() call needed.

IntParams/ScalarParams/ArmourDyeParams sub-pins deliberately left unconnected (undocumented/candidate-
only data) - unconnected struct sub-pins on a CallFunction node just use their zeroed default, no
compile error, matching every other unconnected-pin case in this project.
"""
import sys, copy, pathlib

CCMOD = str(pathlib.Path(__file__).resolve().parents[3] / "claude-conan-modder")
sys.path.insert(0, CCMOD)
from ccmod.t3d import parse, connect, connect_exec
from ccmod.t3d.generator import instantiate
from ccmod.t3d.model import Graph

MOD = str(pathlib.Path(__file__).resolve().parents[2])

SRC_PATH = MOD + r"\.ccmod\graphs\amadan_beginplay_full_with_setlayout_s21.t3d"
src = parse(open(SRC_PATH, encoding="utf-8-sig").read())

SELF_SRC_PATH = MOD + r"\.ccmod\graphs\amadanmenu_refreshruleslist_body.t3d"
self_src = parse(open(SELF_SRC_PATH, encoding="utf-8-sig").read())

g = Graph(nodes=[copy.deepcopy(n) for n in src.nodes])
by_name = {n.name: n for n in g.nodes}

event = by_name["K2Node_Event_3"]
call_parent = by_name["K2Node_CallParentFunction_0"]
set_layout = by_name["K2Node_CallFunction_0"]
mesh = by_name["K2Node_MakeStruct_1"]
texture = by_name["K2Node_MakeStruct_2"]
tint = by_name["K2Node_MakeStruct_3"]
boolp = by_name["K2Node_MakeStruct_4"]
enump = by_name["K2Node_MakeStruct_5"]


def setpin(node, pname, value):
    p = node.pin_by_name(pname)
    assert p, f"{node.name} has no pin {pname}"
    p._set("DefaultValue", f'"{value}"')


# --- MeshLayout ---
setpin(mesh, "Helmet", "-2")
setpin(mesh, "Hair", "7")
setpin(mesh, "FacialHair", "8")
setpin(mesh, "Head", "4")
setpin(mesh, "Forearms", "0")
setpin(mesh, "Hands", "0")
setpin(mesh, "UpperBody", "0")
setpin(mesh, "LowerBody", "0")
setpin(mesh, "Legs", "0")
setpin(mesh, "Feet", "0")

# --- TextureLayout ---
setpin(texture, "EyebrowTexture", "0")
setpin(texture, "EyeTexture", "1")
setpin(texture, "LipTexture", "0")
setpin(texture, "WarpaintFaceTexture", "0")
setpin(texture, "WarpaintBodyTexture", "0")
setpin(texture, "WarpaintHandsTexture", "0")
# HairlineTexture / FacialHairlineTexture: undocumented, left at default.

# --- TintLayout ---
setpin(tint, "Skin", "4")
setpin(tint, "Hair", "9")
setpin(tint, "SecondaryHair", "9")
setpin(tint, "FacialHair", "10")
setpin(tint, "BodyHair", "0")
setpin(tint, "InnerIrisEyeLeft", "4")
setpin(tint, "InnerIrisEyeRight", "4")
setpin(tint, "MiddleIrisEyeLeft", "4")
setpin(tint, "MiddleIrisEyeRight", "4")
setpin(tint, "OuterIrisEyeLeft", "2")
setpin(tint, "OuterIrisEyeRight", "2")
setpin(tint, "Eyebrows", "0")
setpin(tint, "EyeMakeup", "0")
setpin(tint, "LipMakeup", "0")
setpin(tint, "Warpaint", "0")

# --- BoolParams ---
setpin(boolp, "IsFemale", "false")

# --- EnumParams ---
setpin(enump, "Race", "Stygian")
# God/CrimeOne/Two/Three: undocumented/irrelevant, left at default.

# --- IsServer: real literal-editable bool on this CallFunction variant ---
setpin(set_layout, "IsServer", "true")

# --- Self node, cloned from a real capture, feeds the Target/self interface pin ---
SELF_T = None
for n in self_src.nodes:
    if n.name == "K2Node_Self_0":
        nn = copy.deepcopy(n)
        for p in nn.pins:
            p.links = []
        SELF_T = Graph(nodes=[nn])
        break
assert SELF_T, "K2Node_Self template not found"
self_node = instantiate(SELF_T, g)[0]

# --- exec splice: CallParentFunction.then -> SetCharacterLayout.execute ---
call_parent.pin_by_name("then", output=True).links = []
set_layout.pin_by_name("execute").links = []
connect_exec(call_parent, set_layout, "then", "execute")

# --- self/Target ---
connect(self_node, "self", set_layout, "self")

out_path = MOD + r"\.ccmod\graphs\amadan_beginplay_setcharacterlayout_final_s21.t3d"
open(out_path, "w", encoding="utf-8").write(g.render())
print("wrote", out_path, "-", len(g.nodes), "nodes")
