r"""Fresh-author a second button, "SaveAndCloseButton", for W_AmadanMenu.

Same hand-typed-T3D technique as build_amadanmenu_saverule_widgets.py (UMG widgets, not graph
nodes -- see that script's docstring / [[stocker-umg-spike]] for why). Self-contained single-button
subtree (Button + its TextBlock label), no Parent=/Content= wiring back to SaveRuleForm -- select
SaveRuleForm in the Designer hierarchy before pasting, same paste-attaches-to-selection model as
every other widget-tree fragment this project.

This is deliberately a NEW button alongside SaveButton, not a replacement -- user wants both:
plain Save (stays open, for adding several rules in one sitting) and Save-and-Close (closes after,
the common one-and-done case). ESC does not close this popup (confirmed live, CloseOnESC's actual
value was never resolved from the DataTable and turned out not to matter -- it doesn't close),
so an explicit close affordance is genuinely required, not just nice-to-have.
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
    n = len(children)
    slot_names = [f"{name}Slot_{i}" for i in range(n)]
    lines = [f"Begin Object Class={cls} Name=\"{name}\" ExportPath={export_path(cls, name)}"]
    for sn in slot_names:
        lines.append(f'   Begin Object Class={slot_cls} Name="{sn}" ExportPath={export_path(slot_cls, name, sn)}')
        lines.append("   End Object")
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


save_and_close_button = container(
    "/Script/UMG.Button", "/Script/UMG.ButtonSlot", "SaveAndCloseButton",
    [("/Script/UMG.TextBlock", "TextBlock_185")],
)

blocks = [
    save_and_close_button,
    text_block("TextBlock_185", "Save and Close"),
]

out = "\n".join(blocks) + "\n"

import pathlib
MOD = str(pathlib.Path(__file__).resolve().parents[2])
path = MOD + r"\.ccmod\graphs\amadanmenu_saveandclose_widget.t3d"
open(path, "w", encoding="utf-8").write(out)
print(f"wrote: {path}")
print(f"{out.count('Begin Object')} objects")
