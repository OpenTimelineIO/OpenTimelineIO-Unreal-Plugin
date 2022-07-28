# SPDX-License-Identifier: Apache-2.0
# Copyright Contributors to the OpenTimelineIO project

import unreal

from .dialog import TimelineSyncMode, show_dialog
from .menu_helper import UnrealMenuHelper
from .qt_helper import UnrealQtHelper


SECTION_NAME = "OpenTimelineIO"


# Start QApplication in Unreal Editor
UnrealQtHelper.ensure_qapp_available()

# Add tool actions to Unreal Editor menus
tool_menus = unreal.ToolMenus.get()

for menu_name in (
    "LevelEditor.LevelEditorToolBar.Cinematics",
    "ContentBrowser.AssetContextMenu.{cls}".format(cls=unreal.LevelSequence.__name__),
):
    menu = tool_menus.extend_menu(unreal.Name(menu_name))
    menu.add_section(unreal.Name(SECTION_NAME), unreal.Text(SECTION_NAME))

    UnrealMenuHelper.add_menu_entry(
        menu,
        SECTION_NAME,
        lambda: show_dialog(
            TimelineSyncMode.EXPORT, parent=UnrealQtHelper.get_parent_widget()
        ),
        "export_otio_dialog",
        entry_label="Export Sequence to OTIO...",
    )
    UnrealMenuHelper.add_menu_entry(
        menu,
        SECTION_NAME,
        lambda: show_dialog(
            TimelineSyncMode.IMPORT, parent=UnrealQtHelper.get_parent_widget()
        ),
        "import_otio_dialog",
        entry_label="Update Sequence from OTIO...",
    )
