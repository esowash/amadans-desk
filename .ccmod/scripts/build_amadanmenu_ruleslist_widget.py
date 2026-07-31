r"""Saved-rules list: RulesListBox (VerticalBox) with 8 fixed rows (RuleRow_0..7), each a
HorizontalBox of a TextBlock (RuleRowText_N, shows "<bench> - <item>: <keep>") and a small
delete Button (RuleRowDelete_N, containing RuleRowDeleteText_N = "X"). Fixed-N-rows, same
discipline as ItemResultsBox -- no dynamic per-rule widget creation.

Self-contained subtree, same raw-text-authoring technique as
build_amadanmenu_itemsearch_widget.py (UMG widget trees are plain Begin/End Object + Slots
blocks, no Blueprint graph pins involved, so this doesn't need the ccmod t3d node/pin model at
all). Rows start Collapsed by default, same as ItemResult_N -- shown/hidden by a refresh
function driven by the real KeepRulesV2 count, built separately once RemoveKeepRule exists.

Placement: paste as a new top-level child of the same parent that holds SaveRuleForm /
ItemSearchForm (exact position is layout/padding, deferred to the already-planned cosmetic
polish pass) -- confirm the real parent via a widget-tree pull before pasting, don't guess
blind at the exact splice point.
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


N_ROWS = 8
blocks = []
row_names = []

for i in range(N_ROWS):
    row_name = f"RuleRow_{i}"
    text_name = f"RuleRowText_{i}"
    del_btn_name = f"RuleRowDelete_{i}"
    del_text_name = f"RuleRowDeleteText_{i}"
    row_names.append(row_name)

    blocks.append(container(
        "/Script/UMG.Button", "/Script/UMG.ButtonSlot", del_btn_name,
        [("/Script/UMG.TextBlock", del_text_name)],
    ))
    blocks.append(text_block(del_text_name, "X"))
    blocks.append(text_block(text_name, ""))
    blocks.append(container(
        "/Script/UMG.HorizontalBox", "/Script/UMG.HorizontalBoxSlot", row_name,
        [("/Script/UMG.TextBlock", text_name), ("/Script/UMG.Button", del_btn_name)],
    ))

rules_list_box = container(
    "/Script/UMG.VerticalBox", "/Script/UMG.VerticalBoxSlot", "RulesListBox",
    [("/Script/UMG.HorizontalBox", n) for n in row_names],
)

blocks = [rules_list_box] + blocks

# Every row starts hidden -- collapsed until the refresh logic finds a real rule for that index.
blocks_final = []
for b in blocks:
    first_line = b.split("\n")[0]
    if any(f'Name="RuleRow_{i}"' in first_line for i in range(N_ROWS)):
        lines = b.split("\n")
        lines.insert(-2, "   Visibility=Collapsed")
        b = "\n".join(lines)
    blocks_final.append(b)

out = "\n".join(blocks_final) + "\n"

import pathlib
MOD = str(pathlib.Path(__file__).resolve().parents[2])
path = MOD + r"\.ccmod\graphs\amadanmenu_ruleslist_widget.t3d"
open(path, "w", encoding="utf-8").write(out)
print(f"wrote: {path}")
print(f"{out.count('Begin Object')} objects")
