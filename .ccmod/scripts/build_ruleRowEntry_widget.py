r"""W_RuleRowEntry's root widget tree: a HorizontalBox with a TextBlock (RuleText, populated per
instance by RefreshRulesList) and a small delete Button (DeleteButton, containing DeleteButtonText
= "X"). This is the whole tree for a brand-new, currently-empty Widget Blueprint -- same
raw-text-authoring technique as every other widget-tree fragment this session (UMG trees are
plain Begin/End Object + Slots blocks, no Blueprint graph pins involved).
"""

TARGET_WIDGET_TREE = "/Game/Mods/Menu/W_RuleRowEntry.W_RuleRowEntry:WidgetTree"


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


delete_btn = container(
    "/Script/UMG.Button", "/Script/UMG.ButtonSlot", "DeleteButton",
    [("/Script/UMG.TextBlock", "DeleteButtonText")],
)
delete_text = text_block("DeleteButtonText", "X")
rule_text = text_block("RuleText", "")

root = container(
    "/Script/UMG.HorizontalBox", "/Script/UMG.HorizontalBoxSlot", "RuleRowRoot",
    [("/Script/UMG.TextBlock", "RuleText"), ("/Script/UMG.Button", "DeleteButton")],
)

blocks = [root, rule_text, delete_btn, delete_text]
out = "\n".join(blocks) + "\n"

import pathlib
MOD = str(pathlib.Path(__file__).resolve().parents[2])
path = MOD + r"\.ccmod\graphs\ruleRowEntry_widget.t3d"
open(path, "w", encoding="utf-8").write(out)
print(f"wrote: {path}")
print(f"{out.count('Begin Object')} objects")
