r"""Fresh-author the Save-Rule form widget tree for W_AmadanMenu.

Hand-typed T3D text (NOT ccmod's Pin/Graph instantiate() engine -- UMG widgets don't have
exec/data pins the way Blueprint graph nodes do, they have Slot objects with Parent=/Content=
references; see the [[stocker-umg-spike]] memory for why direct string authoring is the proven
technique here, same as the 9-object W_StockerTestPanel spike).

Produces a SELF-CONTAINED subtree -- root is a SizeBox ("SaveRuleFormBox", fixed 640x240,
wrapping the VerticalBox "SaveRuleForm") -- with no Parent=/Content= wiring back to the existing
VerticalBox_65 -- per the umg-spike memory's proven paste model, the outer parent relationship is
created by UMG itself from whichever container is selected in the Designer hierarchy at paste
time, not from clipboard data. So: select VerticalBox_65 in the Designer before pasting. The
640x240 box is meant to sit left-justified inside the existing 640x480 Border_283.

Widgets created, one row each inside SaveRuleForm:
  BenchDropdown      (ComboBoxString)   -- populated at Construct time from ManagedStations
  TemplateIDInput    (EditableTextBox)  -- MVP stand-in for the full item type-ahead (deferred)
  KeepInput          (EditableTextBox)
  KeepAllCheckbox    (CheckBox)
  SaveButton         (Button, label "Save Rule") -- OnClicked wired in a separate pass, same
                     ComponentBoundEvent shape already proven live on Button_634 ("Close")

Names picked to avoid colliding with the existing tree (Border_283, VerticalBox_65,
TextBlock_110, MultiLineEditableTextBox_74, Button_634, TextBlock_179).
"""

TARGET_WIDGET_TREE = "/Game/Mods/Menu/W_AmadanMenu.W_AmadanMenu:WidgetTree"


def export_path(cls, *path_parts):
    dotted = ".".join(path_parts)
    return f"\"{cls}'{TARGET_WIDGET_TREE}.{dotted}'\""


def leaf(cls, name, body_lines=None):
    lines = [f'Begin Object Class={cls} Name="{name}" ExportPath={export_path(cls, name)}']
    for bl in body_lines or []:
        lines.append(f"   {bl}")
    lines.append("End Object")
    return "\n".join(lines)


def text_block(name, text):
    return leaf(
        "/Script/UMG.TextBlock",
        name,
        [f'Text=NSLOCTEXT("UMG", "TextBlockDefaultValue", "{text}")'],
    )


def container(cls, slot_cls, name, children, extra_props=None):
    """children: list of (widget_class, widget_name) in slot order."""
    n = len(children)
    slot_names = [f"{name}Slot_{i}" for i in range(n)]

    lines = [f"Begin Object Class={cls} Name=\"{name}\" ExportPath={export_path(cls, name)}"]
    # forward-declare stubs (matches the clean pattern VerticalBox_65 itself uses)
    for sn in slot_names:
        lines.append(f'   Begin Object Class={slot_cls} Name="{sn}" ExportPath={export_path(slot_cls, name, sn)}')
        lines.append("   End Object")
    # real slot fill-ins with Parent=/Content=
    for sn, (wcls, wname) in zip(slot_names, children):
        lines.append(f'   Begin Object Name="{sn}" ExportPath={export_path(slot_cls, name, sn)}')
        lines.append(f"      Parent={quote_ref(cls, name)}")
        lines.append(f"      Content={quote_ref(wcls, wname)}")
        lines.append("   End Object")
    for i, sn in enumerate(slot_names):
        lines.append(f'   Slots({i})={quote_ref(slot_cls, sn)}')
    for prop in extra_props or []:
        lines.append(f"   {prop}")
    lines.append("   bExpandedInDesigner=True")
    lines.append("End Object")
    return "\n".join(lines)


def quote_ref(cls, name):
    return f"\"{cls}'{name}'\""


# Emission order matches the real captured menu_w_amadanmenu_widgettree.t3d exactly: each
# container is emitted BEFORE its own children (depth-first pre-order, container-then-leaves) --
# that's how UE itself serializes on Ctrl+C, so mirroring it removes any doubt about whether
# forward-references in Content="..." need their target already defined earlier in the text.

row1 = container(
    "/Script/UMG.HorizontalBox", "/Script/UMG.HorizontalBoxSlot", "HorizontalBox_60",
    [("/Script/UMG.TextBlock", "TextBlock_181"), ("/Script/UMG.ComboBoxString", "BenchDropdown")],
)
row2 = container(
    "/Script/UMG.HorizontalBox", "/Script/UMG.HorizontalBoxSlot", "HorizontalBox_61",
    [("/Script/UMG.TextBlock", "TextBlock_182"), ("/Script/UMG.EditableTextBox", "TemplateIDInput")],
)
row3 = container(
    "/Script/UMG.HorizontalBox", "/Script/UMG.HorizontalBoxSlot", "HorizontalBox_62",
    [("/Script/UMG.TextBlock", "TextBlock_183"), ("/Script/UMG.EditableTextBox", "KeepInput")],
)
row4 = container(
    "/Script/UMG.HorizontalBox", "/Script/UMG.HorizontalBoxSlot", "HorizontalBox_63",
    [("/Script/UMG.TextBlock", "TextBlock_184"), ("/Script/UMG.CheckBox", "KeepAllCheckbox")],
)
save_button = container(
    "/Script/UMG.Button", "/Script/UMG.ButtonSlot", "SaveButton",
    [("/Script/UMG.TextBlock", "TextBlock_180")],
)
form = container(
    "/Script/UMG.VerticalBox", "/Script/UMG.VerticalBoxSlot", "SaveRuleForm",
    [
        ("/Script/UMG.HorizontalBox", "HorizontalBox_60"),
        ("/Script/UMG.HorizontalBox", "HorizontalBox_61"),
        ("/Script/UMG.HorizontalBox", "HorizontalBox_62"),
        ("/Script/UMG.HorizontalBox", "HorizontalBox_63"),
        ("/Script/UMG.Button", "SaveButton"),
    ],
)

# Fixed-size wrapper: 640x240, left-justified inside the existing 640x480 Border_283 (see
# menu_w_amadanmenu_widgettree.t3d -- Border_283's own Background.ImageSize is already 640x480,
# this box is meant to sit inside it, not replace it). SizeBox forces its own Desired Size
# regardless of the VerticalAlignment/HorizontalAlignment the connecting slot ends up with, so
# the 640x240 dimension is locked in by this wrapper either way. The connecting slot itself
# (VerticalBox_65's future VerticalBoxSlot_N for this box) is created fresh by UE at paste time,
# same self-contained-subtree model as before -- if it doesn't default to left-justified, set
# its HorizontalAlignment to "Left" once in the Details panel after pasting (cosmetic, no
# functional/compile risk, not worth re-touching the live existing VerticalBox_65 object blind).
size_box = container(
    "/Script/UMG.SizeBox", "/Script/UMG.SizeBoxSlot", "SaveRuleFormBox",
    [("/Script/UMG.VerticalBox", "SaveRuleForm")],
    extra_props=[
        "WidthOverride=640.000000",
        "bOverride_WidthOverride=True",
        "HeightOverride=240.000000",
        "bOverride_HeightOverride=True",
    ],
)

blocks = [
    size_box,
    form,
    row1, text_block("TextBlock_181", "Bench:"), leaf("/Script/UMG.ComboBoxString", "BenchDropdown"),
    row2, text_block("TextBlock_182", "Item ID:"), leaf("/Script/UMG.EditableTextBox", "TemplateIDInput"),
    row3, text_block("TextBlock_183", "Keep:"), leaf("/Script/UMG.EditableTextBox", "KeepInput"),
    row4, text_block("TextBlock_184", "Keep All:"), leaf("/Script/UMG.CheckBox", "KeepAllCheckbox"),
    save_button, text_block("TextBlock_180", "Save Rule"),
]

out = "\n".join(blocks) + "\n"

import pathlib
MOD = str(pathlib.Path(__file__).resolve().parents[2])
path = MOD + r"\.ccmod\graphs\amadanmenu_saverule_widgettree.t3d"
open(path, "w", encoding="utf-8").write(out)
print(f"wrote: {path}")
print(f"{out.count('Begin Object')} objects")
