r"""ItemDropdown (ComboBoxString) -- replaces the raw TemplateIDInput number-entry field.

Self-contained single-widget fragment, same technique as build_amadanmenu_saveandclose_widget.py.
Delete the OLD row first (HorizontalBox_61: TextBlock_182 "Item ID:" + TemplateIDInput), then
select SaveRuleForm and paste this in its place.
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
    return leaf("/Script/UMG.TextBlock", name, [f'Text=NSLOCTEXT("UMG", "TextBlockDefaultValue", "{text}")'])


def container(cls, slot_cls, name, children):
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
    lines.append("   bExpandedInDesigner=True")
    lines.append("End Object")
    return "\n".join(lines)


row = container(
    "/Script/UMG.HorizontalBox", "/Script/UMG.HorizontalBoxSlot", "HorizontalBox_70",
    [("/Script/UMG.TextBlock", "TextBlock_190"), ("/Script/UMG.ComboBoxString", "ItemDropdown")],
)

blocks = [
    row,
    text_block("TextBlock_190", "Item:"),
    leaf("/Script/UMG.ComboBoxString", "ItemDropdown"),
]

out = "\n".join(blocks) + "\n"
import pathlib
MOD = str(pathlib.Path(__file__).resolve().parents[2])
path = MOD + r"\.ccmod\graphs\amadanmenu_itemdropdown_widget.t3d"
open(path, "w", encoding="utf-8").write(out)
print(f"wrote: {path}")
print(f"{out.count('Begin Object')} objects")
