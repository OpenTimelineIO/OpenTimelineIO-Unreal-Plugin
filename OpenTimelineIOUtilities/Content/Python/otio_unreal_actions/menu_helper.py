# SPDX-License-Identifier: Apache-2.0
# Copyright Contributors to the OpenTimelineIO project

import unreal


@unreal.uclass()
class PythonMenuEntry(unreal.ToolMenuEntryScript):
    """ToolMenuEntryScript implementation which executes a Python
    callback with supplied arguments.
    """

    def __init__(self, callback, args=None, kwargs=None):
        """
        Args:
            callback (callable): Python callable to execute.
            args (tuple, optional): Tuple of callback positional
                arguments.
            kwargs (dict, optional): Dictionary of callback keyword
                arguments.
        """
        super(PythonMenuEntry, self).__init__()

        self._callback = callback
        self._args = args or ()
        self._kwargs = kwargs or {}

    @unreal.ufunction(override=True)
    def execute(self, context):
        self._callback(*self._args, **self._kwargs)

    @unreal.ufunction(override=True)
    def can_execute(self, context):
        return True


class UnrealMenuHelper(object):
    """Static helper class which manages custom Unreal Editor menus and
    script entries.
    """

    # Keep track of all the menu entries that have been registered to UE.
    # Without keeping these around, the Unreal GC will remove the menu objects
    # and break the in-engine menu.
    _menu_entries = []

    @classmethod
    def add_menu_entry(
        cls,
        menu,
        section_name,
        callback,
        entry_name,
        entry_label=None,
        entry_tooltip="",
    ):
        """Add Python script entry to a UE menu.

        Args:
            menu (unreal.ToolMenu): Menu to add the entry to.
            section_name (str): Section to add the entry to.
            callback (callable): Python callable to execute when the
                entry is executed.
            entry_name (str): Menu entry name.
            entry_label (str, optional): Menu entry label.
            entry_tooltip (str, optional): Menu entry tooltip.
        """
        tool_menus = unreal.ToolMenus.get()

        # Create a register script entry
        menu_entry = PythonMenuEntry(callback)
        menu_entry.init_entry(
            unreal.Name("otio_unreal_actions"),
            unreal.Name(
                "{parent_menu}.{menu}.{entry}".format(
                    parent_menu=menu.menu_parent, menu=menu.menu_name, entry=entry_name
                )
            ),
            unreal.Name(section_name),
            unreal.Name(entry_name),
            label=unreal.Text(entry_label or entry_name),
            tool_tip=unreal.Text(entry_tooltip),
        )

        # Store entry reference prior to adding it to the menu
        cls._menu_entries.append(menu_entry)

        menu.add_menu_entry_object(menu_entry)

        # Tell engine to refresh all menus
        tool_menus.refresh_all_widgets()
