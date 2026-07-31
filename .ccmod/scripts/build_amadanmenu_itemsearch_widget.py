r"""Item search box + 8 result rows -- replaces ItemDropdown (ComboBoxString) with a real
type-ahead: EditableTextBox for the search text, 8 pre-built result-row Buttons (hidden by
default via Visibility=Collapsed), each containing a TextBlock that gets its Text set live by
the OnTextChanged filter handler (separate fragment). Fixed-N-rows, not dynamic per-keystroke
widget creation -- see the earlier scope discussion: dynamic Construct-Widget + per-instance
delegate binding is UMG's riskiest, most fragile pattern and was deliberately avoided.

Self-contained subtree, same technique as every other widget fragment this session. Delete the
OLD ItemDropdown row (HorizontalBox_70: TextBlock_190 "Item:" + ItemDropdown) first, then select
SaveRuleForm and paste this in its place.
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


def text_block(name, text, extra=None):
    body = [f'Text=NSLOCTEXT("UMG", "TextBlockDefaultValue", "{text}")']
    body.extend(extra or [])
    return leaf("/Script/UMG.TextBlock", name, body)


def container(cls, slot_cls, name, children, extra_props=None):
    n = len(children)
    slot_names = [f"{name}Slot_{i}" for i in range(n)]
    lines = [f"Begin Object Class={cls} Name=\"{name}\" ExportPath={export_path(cls, name)}"]
    for sn in slot_names:
        lines.append(f'   Begin Object Class={slot_cls} Name="{sn}" ExportPath={export_path(slot_cls, name, sn)}')
        lines.append("   End Object")
    for sn, (wcls, wname) in zip(slot_names, children):
        lines.append(f'   Begin Object Name="{sn}" ExportPath={export_path(slot_cls, name, sn)}')
        lines.append(f"      Parent=\"{cls}'{name}'\"")
        lines.append(f"      Content=\"{wcls}'{wname}'\"")
        lines.append("   End Object")
    for i, sn in enumerate(slot_names):
        lines.append(f"   Slots({i})=\"{slot_cls}'{sn}'\"")
    for prop in extra_props or []:
        lines.append(f"   {prop}")
    lines.append("   bExpandedInDesigner=True")
    lines.append("End Object")
    return "\n".join(lines)


N_RESULTS = 8
blocks = []
result_button_names = []

for i in range(N_RESULTS):
    btn_name = f"ItemResult_{i}"
    lbl_name = f"ItemResultText_{i}"
    result_button_names.append(btn_name)
    blocks.append(container(
        "/Script/UMG.Button", "/Script/UMG.ButtonSlot", btn_name,
        [("/Script/UMG.TextBlock", lbl_name)],
    ))
    blocks.append(text_block(lbl_name, "", extra=[]))

results_box = container(
    "/Script/UMG.VerticalBox", "/Script/UMG.VerticalBoxSlot", "ItemResultsBox",
    [("/Script/UMG.Button", n) for n in result_button_names],
)

row = container(
    "/Script/UMG.HorizontalBox", "/Script/UMG.HorizontalBoxSlot", "HorizontalBox_80",
    [("/Script/UMG.TextBlock", "TextBlock_195"), ("/Script/UMG.EditableTextBox", "ItemSearchInput")],
)

form_wrapper = container(
    "/Script/UMG.VerticalBox", "/Script/UMG.VerticalBoxSlot", "ItemSearchForm",
    [("/Script/UMG.HorizontalBox", "HorizontalBox_80"), ("/Script/UMG.VerticalBox", "ItemResultsBox")],
)

blocks = [
    form_wrapper,
    row, text_block("TextBlock_195", "Item:"), leaf("/Script/UMG.EditableTextBox", "ItemSearchInput"),
    results_box,
] + blocks

# Each result button starts hidden -- collapsed until a real match populates it. Add Visibility
# directly onto the already-emitted button blocks by re-emitting them with the extra property.
blocks_final = []
for b in blocks:
    if any(f'Name="ItemResult_{i}"' in b.split("\n")[0] for i in range(N_RESULTS)):
        lines = b.split("\n")
        lines.insert(-2, "   Visibility=Collapsed")
        b = "\n".join(lines)
    blocks_final.append(b)

out = "\n".join(blocks_final) + "\n"

import pathlib
MOD = str(pathlib.Path(__file__).resolve().parents[2])
path = MOD + r"\.ccmod\graphs\amadanmenu_itemsearch_widget.t3d"
open(path, "w", encoding="utf-8").write(out)
print(f"wrote: {path}")
print(f"{out.count('Begin Object')} objects")
