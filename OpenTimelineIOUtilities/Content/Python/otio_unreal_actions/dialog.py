# SPDX-License-Identifier: Apache-2.0
# Copyright Contributors to the OpenTimelineIO project

import logging
import os
import traceback

import unreal
import opentimelineio as otio
from opentimelineview import timeline_widget
from PySide2 import QtCore, QtGui, QtWidgets

from otio_unreal import (
    export_otio,
    import_otio,
    get_item_frame_ranges,
    get_level_seq_references,
)

from .filesystem_path_edit import (
    FileSystemPathEdit,
    FileSystemPathDialogType,
    FileSystemPathType,
)
from .icons import get_icon_path


logger = logging.getLogger(__name__)


class TimelineSyncMode(object):
    """
    Enum of supported timeline sync modes.
    """

    IMPORT = "import"
    EXPORT = "export"


class BaseTreeItem(QtWidgets.QTreeWidgetItem):
    """
    Tree item with custom sort implementation and builtin global icon
    caching.
    """

    TYPE = QtWidgets.QTreeWidgetItem.UserType
    ICON_KEY = None

    _icon_cache = {}

    def __init__(self, parent, values):
        super(BaseTreeItem, self).__init__(parent, values, type=self.TYPE)

        if self.ICON_KEY is not None:
            icon = self._get_icon(self.ICON_KEY)
            if icon is not None:
                self.setIcon(0, icon)

    def __lt__(self, other):
        # Re-implement default column sorting
        tree = self.treeWidget()
        if tree is not None:
            sort_col = tree.sortColumn()
            return self.text(sort_col) < other.text(sort_col)

        return False

    def _get_icon(self, icon_key):
        """
        Load and cache an icon. Subsequent requests for the icon are
        pulled from the cache, so that each icon is loaded at most
        once.

        Args:
            icon_key (str): Icon key

        Returns:
            QtGui.QIcon: Loaded icon or None
        """
        icon = self._icon_cache.get(icon_key)
        if icon is None:
            icon_path = get_icon_path(icon_key)
            if icon_path is not None:
                icon = QtGui.QIcon(icon_path)
                self._icon_cache[icon_key] = icon
        return icon


class FolderItem(BaseTreeItem):
    """
    Tree item representing an Unreal Editor content browser folder.
    """

    TYPE = BaseTreeItem.TYPE + 1
    ICON_KEY = "folder-open"

    def __init__(self, parent, name):
        """
        Args:
            name (str): Folder name
        """
        super(FolderItem, self).__init__(parent, [name, "", "", ""])

    def update_icon(self):
        """
        Call on item expand or collapse to update the folder icon (open
        or closed folder)
        """
        if self.isExpanded():
            icon_key = "folder-open"
        else:
            icon_key = "folder-closed"

        icon = self._get_icon(icon_key)
        if icon is not None:
            self.setIcon(0, icon)

    def __lt__(self, other):
        # Always sort folders after level sequences
        if other.type() == LevelSeqItem.TYPE:
            return False

        return super(FolderItem, self).__lt__(other)


class LevelSeqItem(BaseTreeItem):
    """
    Tree item representing an Unreal Engine level sequence.
    """

    TYPE = BaseTreeItem.TYPE + 2
    ICON_KEY = "level-sequence-actor"

    def __init__(self, parent, package_name, asset_path, otio_item, mode):
        """
        Args:
            package_name (str): Level sequence package name
            asset_path (str): Level sequence asset path
            otio_item (otio.schema.Item): Item associated with the
                level sequence.
            mode (str): Timeline sync mode
        """
        # Get anticipated frame ranges from timeline
        range_in_parent, source_range = get_item_frame_ranges(otio_item)
        values = [
            package_name,
            "",
            "{:d}-{:d}".format(range_in_parent[0], range_in_parent[1]),
            "{:d}-{:d}".format(source_range[0], source_range[1]),
        ]

        super(LevelSeqItem, self).__init__(parent, values)

        # Choose icon based on sync mode and asset status
        if mode == TimelineSyncMode.IMPORT:
            self.asset_data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
            if self.asset_data.is_valid():
                icon_key = "edit"
            else:
                icon_key = "plus"
        else:
            icon_key = "export"

        icon = self._get_icon(icon_key)
        if icon is not None:
            self.setIcon(1, icon)

        self.otio_item = otio_item

    def __lt__(self, other):
        # Always sort folders after level sequences
        if other.type() == FolderItem.TYPE:
            return True

        return super(LevelSeqItem, self).__lt__(other)


class TimelineDialog(QtWidgets.QWidget):
    """
    Base dialog which facilitates syncing between an Unreal level
    sequence hierarchy and an OTIO timeline, with a preview of the
    impact of that operation before running it.
    """

    _ICON_WIDTH = 16

    def __init__(self, mode, parent=None):
        """
        Args:
            mode (str): Timeline sync mode
        """
        super(TimelineDialog, self).__init__(parent)

        self.setWindowFlags(self.windowFlags() | QtCore.Qt.Dialog)
        self.setWindowTitle("OTIO " + mode.title())

        self._mode = mode
        self._parent = parent
        self._prev_timeline_path = None

        # Widgets
        self.timeline_file_edit = FileSystemPathEdit(
            FileSystemPathType.FILE,
            validate_path=False,
            path_desc="Timeline file",
            dialog_type=FileSystemPathDialogType.SAVE
            if self._mode == TimelineSyncMode.EXPORT
            else FileSystemPathDialogType.LOAD,
        )
        if self._mode == TimelineSyncMode.EXPORT:
            self.timeline_file_edit.setToolTip("Choose a OTIO file to export to.")
        else:  # IMPORT
            self.timeline_file_edit.setToolTip("Choose a OTIO file to update from.")
            self.timeline_file_edit.textChanged.connect(
                self._on_timeline_source_changed
            )

        self.root_level_seq_label = QtWidgets.QLineEdit()
        self.root_level_seq_label.setEnabled(False)

        self.timeline_tree = QtWidgets.QTreeWidget()
        self.timeline_tree.setToolTip(
            "Hierarchy of level sequences and their frame ranges which will\n"
            "be created or updated by this tool."
        )
        self.timeline_tree.setHeaderLabels(
            ["Level Sequence", "Status", "Range in Parent", "Source Range"]
        )
        self.timeline_tree.setSelectionMode(QtWidgets.QTreeWidget.SingleSelection)
        self.timeline_tree.setSelectionBehavior(QtWidgets.QTreeWidget.SelectRows)
        self.timeline_tree.setUniformRowHeights(True)
        self.timeline_tree.setIconSize(QtCore.QSize(self._ICON_WIDTH, self._ICON_WIDTH))
        self.timeline_tree.itemExpanded.connect(self._on_timeline_tree_item_expanded)
        self.timeline_tree.itemCollapsed.connect(self._on_timeline_tree_item_expanded)
        self.timeline_tree.itemSelectionChanged.connect(
            self._on_timeline_tree_selection_changed
        )

        # otioview component
        self.timeline_view = timeline_widget.Timeline()
        self.timeline_view.selection_changed.connect(
            self._on_timeline_view_selection_changed
        )

        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.close)

        # Layout
        option_layout = QtWidgets.QFormLayout()
        option_layout.setLabelAlignment(QtCore.Qt.AlignRight)
        option_layout.addRow("Timeline File", self.timeline_file_edit)
        if self._mode == TimelineSyncMode.EXPORT:
            option_layout.addRow("Root Level Sequence", self.root_level_seq_label)

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.button_box)

        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        self.splitter.addWidget(self.timeline_tree)
        self.splitter.addWidget(self.timeline_view)

        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(option_layout)
        layout.addWidget(self.splitter)
        layout.addLayout(button_layout)

        self.setLayout(layout)

        # Initialize
        self.resize(500, 600)

    def showEvent(self, event):
        super(TimelineDialog, self).showEvent(event)

        level_seq = self.get_current_level_seq()
        if level_seq is not None:
            # Set default timeline path
            saved_dir = os.path.realpath(unreal.Paths.project_saved_dir())
            otio_path = os.path.join(saved_dir, str(level_seq.get_name()) + ".otio")
            self.timeline_file_edit.setText(otio_path)

        # Load after showing dialog for auto-sizing
        if self._mode == TimelineSyncMode.EXPORT:
            self._on_timeline_source_changed()

    def accept(self):
        """
        Validate and execute import or export function.
        """
        # Do we have a timeline file?
        timeline_path = self.timeline_file_edit.text()
        if not timeline_path:
            self._show_error_message("Please specify a timeline file.")
            return

        # If importing timeline, does the file exist?
        if self._mode == TimelineSyncMode.IMPORT and not os.path.exists(timeline_path):
            self._show_error_message(
                "'{}' is not a valid timeline file.".format(timeline_path)
            )
            return

        # Is there an open level sequence to export or import?
        level_seq = self.get_current_level_seq()
        if level_seq is None:
            self._show_error_message("No level sequence is loaded to " + self._mode)
            self.close()
            return

        # Run export/import
        try:
            if self._mode == TimelineSyncMode.EXPORT:
                export_otio(timeline_path, level_seq)
            else:  # IMPORT
                _, timeline = import_otio(
                    timeline_path,
                    level_seq=level_seq,
                    undo_action_text="OTIO Import",
                )
        except Exception as exc:
            traceback.print_exc()
            err = "OTIO {} failed with error: {}".format(self._mode, str(exc))
            logger.error(err)
            self._show_error_message(err)
        else:
            self.close()
            if self._mode == TimelineSyncMode.IMPORT:
                # Open root level sequence on success
                unreal.AssetEditorSubsystem().open_editor_for_assets([level_seq])
            self._show_success_message(
                "OTIO {} completed successfully.".format(self._mode)
            )

    @staticmethod
    def get_current_level_seq():
        """
        Returns:
            unreal.LevelSequence|None: Current level sequence, if
                loaded.
        """
        level_seq_lib = unreal.LevelSequenceEditorBlueprintLibrary
        return level_seq_lib.get_current_level_sequence()

    def _show_message(self, title, msg, icon, parent=None):
        """
        Show a QMessageBox wrapped by a Slate window.

        Args:
            title (str): Window title
            msg (str): Message text
            icon (QtGui.QIcon): Window alert icon
            parent (QtWidgets.QWidget, optional) Parent window
        """
        msg_box = QtWidgets.QMessageBox(
            icon, title, msg, QtWidgets.QMessageBox.Ok, parent or self
        )
        unreal.parent_external_window_to_slate(msg_box.winId())
        msg_box.show()

    def _show_error_message(self, msg):
        """
        Show an error message dialog.
        """
        self._show_message("Error", msg, QtWidgets.QMessageBox.Critical)

    def _show_success_message(self, msg):
        """
        Show a success message dialog.
        """
        self._show_message(
            "Success",
            msg,
            QtWidgets.QMessageBox.Information,
            # Parent message to this widget's parent, since this widget will
            # close on success.
            parent=self._parent,
        )

    def _on_timeline_source_changed(self, *args, **kwargs):
        """
        Slot connected to any widget signal which indicates a change to
        the OTIO timeline being synced.
        """
        timeline_path = self.timeline_file_edit.text()

        level_seq = self.get_current_level_seq()
        if level_seq is None:
            return

        if self._mode == TimelineSyncMode.EXPORT:
            self.root_level_seq_label.setText(
                level_seq.get_path_name().rsplit(".", 1)[0]
            )

            # Load processed timeline without exporting
            timeline = export_otio(timeline_path, level_seq, dry_run=True)

        else:  # IMPORT
            # Does timeline exist?
            if not os.path.exists(timeline_path):
                return

            # Timeline already loaded?
            if timeline_path == self._prev_timeline_path:
                return None

            # Load processed timeline without syncing
            _, timeline = import_otio(timeline_path, level_seq=level_seq, dry_run=True)

        # Update timeline tree
        self.timeline_tree.clear()

        processed_path_items = {}

        def _add_asset_path(
            parent_item, processed_path, remaining_path_, asset_path_, otio_item_
        ):
            """
            Recursive and incremental folder hierarchy tree item
            creation.

            Args:
                parent_item (QtWidgets.QTreeWidgetItem): Parent tree
                    item.
                processed_path (str): Path tokens processed so far
                remaining_path_ (str): Path tokens remaining to be
                    processed.
                asset_path_ (str): Level sequence asset path
                    (equivalent to processed_path + remaining_path_).
                otio_item_ (otio.schema.Item): Associated OTIO item
            """
            if "/" in remaining_path_:
                part, remaining_path_ = remaining_path_.split("/", 1)
                processed_path = "/".join([processed_path, part])

                # Cache folder items, which may be needed by multiple level
                # sequences.
                if processed_path in processed_path_items:
                    item_ = processed_path_items[processed_path]
                else:
                    item_ = FolderItem(parent_item, part)
                    processed_path_items[processed_path] = item_

                # Increment to next directory level
                _add_asset_path(
                    item_, processed_path, remaining_path_, asset_path_, otio_item_
                )

            elif remaining_path_:
                # Add level sequence leaf item
                LevelSeqItem(
                    parent_item, remaining_path_, asset_path_, otio_item_, self._mode
                )

        # Build folder structure starting from a common prefix. Only show asset package
        # names, with the asset name stripped, since that's what users generally see in
        # Editor.
        level_seq_refs = sorted(
            get_level_seq_references(timeline, level_seq=level_seq), key=lambda d: d[0]
        )
        asset_paths = list(filter(None, [t[0] for t in level_seq_refs]))

        if asset_paths:
            # Get common prefix of all asset paths, which will be used as a top-level
            # tree item to reduce folder items to only those needed to organize level
            # sequences.
            common_prefix = os.path.commonprefix(asset_paths)
            root_item = FolderItem(self.timeline_tree, common_prefix.rstrip("/"))

            for asset_path, otio_item in level_seq_refs:
                # Strip common prefix
                remaining_path = asset_path[len(common_prefix) :]
                # Strip asset name
                remaining_path = remaining_path.rsplit(".", 1)[0]

                # Build folder/level sequence hierarchy from path tokens
                # following common prefix.
                _add_asset_path(
                    root_item, common_prefix, remaining_path, asset_path, otio_item
                )

        # Update timeline view
        self.timeline_view.set_timeline(timeline)

        if self._mode == TimelineSyncMode.IMPORT:
            # Store loaded timeline to prevent reloading it from repeat signals.
            self._prev_timeline_path = timeline_path

        # Resize widgets for best fit
        col_count = self.timeline_tree.columnCount()
        fm = self.timeline_tree.fontMetrics()
        max_col_width = [0] * col_count
        max_depth = 0
        indentation = self.timeline_tree.indentation()
        header_item = self.timeline_tree.headerItem()

        self.timeline_tree.expandAll()
        self.timeline_tree.sortByColumn(0, QtCore.Qt.AscendingOrder)

        for i in range(col_count):
            self.timeline_tree.resizeColumnToContents(i)
            max_col_width[i] = fm.horizontalAdvance(header_item.text(i))

        it = QtWidgets.QTreeWidgetItemIterator(self.timeline_tree)
        while it.value():
            item = it.value()

            # Get item depth
            item_depth = 0
            item_parent = item.parent()
            while item_parent is not None:
                item_parent = item_parent.parent()
                item_depth += 1
            if item_depth > max_depth:
                max_depth = item_depth

            # Get item width per column
            for i in range(col_count):
                text_width = fm.horizontalAdvance(item.text(i))
                if text_width > max_col_width[i]:
                    max_col_width[i] = text_width
            it += 1

        row_width = (
            (indentation * max_depth) + self._ICON_WIDTH + sum(max_col_width) + 100
        )
        if self.width() < row_width:
            self.resize(row_width, self.height())

        sizes = self.splitter.sizes()
        total_size = sum(sizes)
        timeline_size = int(total_size * 0.35)
        self.splitter.setSizes([total_size - timeline_size, timeline_size])

    @QtCore.Slot(QtWidgets.QTreeWidgetItem)
    def _on_timeline_tree_item_expanded(self, item):
        """
        Update folder tree item icon.
        """
        if isinstance(item, FolderItem):
            item.update_icon()

    @QtCore.Slot()
    def _on_timeline_tree_selection_changed(self):
        """
        Sync timeline view (otioview) item selection to level sequence
        tree selection.
        """
        # Prevent infinite recursion
        self.timeline_view.blockSignals(True)

        selected = self.timeline_tree.selectedItems()
        if not selected:
            return

        item = selected[0]
        if isinstance(item, LevelSeqItem):
            otio_item = item.otio_item
            if isinstance(otio_item, otio.schema.Timeline):
                self.timeline_view.add_stack(otio_item.tracks)
            else:
                # Find nearest parent Stack of item, which will indicate which
                # stack (tab) needs to be viewed in the timeline view to see
                # item.
                parent_otio_item = otio_item.parent()
                while parent_otio_item and not isinstance(
                    parent_otio_item, otio.schema.Stack
                ):
                    parent_otio_item = parent_otio_item.parent()

                if not parent_otio_item and self.timeline_view.timeline:
                    self.timeline_view.add_stack(self.timeline_view.timeline.tracks)
                elif isinstance(parent_otio_item, otio.schema.Stack):
                    self.timeline_view.add_stack(parent_otio_item)

                # Search QGraphicsScene for item. Make it the exclusive selection and
                # scroll so that it's visible in timeline view.
                comp_view = self.timeline_view.currentWidget()
                if comp_view:
                    comp_scene = comp_view.scene()
                    for comp_item in comp_scene.items():
                        if hasattr(comp_item, "item") and comp_item.item == otio_item:
                            comp_scene.clearSelection()
                            comp_item.setSelected(True)
                            comp_view.ensureVisible(comp_item)
                            break

        self.timeline_view.blockSignals(False)

    def _on_timeline_view_selection_changed(self, otio_item):
        """
        Sync level sequence tree selection to timeline view (otioview)
        item selection.
        """
        # Prevent infinite recursion
        self.timeline_tree.blockSignals(True)

        # Search tree for level sequence item associated with selected OTIO item. Make
        # it the exclusive selection and scroll so that it's visible in tree view.
        it = QtWidgets.QTreeWidgetItemIterator(self.timeline_tree)
        while it.value():
            item = it.value()
            if isinstance(item, LevelSeqItem):
                if item.otio_item == otio_item:
                    self.timeline_tree.selectionModel().clear()
                    item.setSelected(True)
                    self.timeline_tree.scrollToItem(item)
                    break
            it += 1

        self.timeline_tree.blockSignals(False)


def show_dialog(mode, parent=None):
    """Show cinematic timeline sync dialog"""
    # Only open dialog if a level sequence is loaded
    level_seq = TimelineDialog.get_current_level_seq()
    if level_seq is None:
        unreal.EditorDialog.show_message(
            unreal.Text("Error"),
            unreal.Text("Please load a level sequence for OTIO {}.".format(mode)),
            unreal.AppMsgType.OK,
            unreal.AppReturnType.OK,
        )
        return

    dialog = TimelineDialog(mode, parent=parent)
    unreal.parent_external_window_to_slate(dialog.winId())
    dialog.show()

    return dialog
