# SPDX-License-Identifier: Apache-2.0
# Copyright Contributors to the OpenTimelineIO project

import os

from PySide2 import QtCore, QtGui, QtWidgets

from .icons import get_icon_path


class FileSystemPathDialogType(object):
    """
    Enum of filesystem path dialog types, which are used to determine
    the ``QtWidgets.QFileDialog`` constructor and related behaviors.
    """

    LOAD = "load"
    SAVE = "save"

    ALL = (LOAD, SAVE)


class FileSystemPathType(object):
    """
    Enum of filesystem path types, which drive ``FileSystemPathEdit``
    behavior.
    """

    FILE = "file"
    DIRECTORY = "directory"

    ALL = (FILE, DIRECTORY)


class FileSystemPathEdit(QtWidgets.QLineEdit):
    """
    Line edit for filesystem paths with builtin path existence
    validation and a browse button.
    """

    def __init__(
        self,
        path_type,
        validate_path=False,
        path_filter=None,
        path_desc=None,
        dialog_type=None,
        parent=None,
    ):
        """
        :param str path_type: Type of path
        :param bool validate_path: Optionally validate whether path
            should exist. If True, an invalid path will trigger an
            error state on the widget.
        :param str path_filter: ``QDialog``-supported file type filter
        :param str path_desc: Optional path description, which shows up
            in placeholder text and child ``FileDialog`` instances.
        :param enum.Enum dialog_type: An optional enum specifying which
            type of dialog to construct. Default:
            ``FileSystemPathDialogType.LOAD``
        :param QtCore.QObject parent: Optional parent object
        """
        super(FileSystemPathEdit, self).__init__(parent)
        self.setMouseTracking(True)

        all_path_types = FileSystemPathType.ALL
        if path_type not in all_path_types:
            raise ValueError(
                "Invalid path type '{path_type}'. Supported path types are: "
                "{supported}".format(
                    path_type=path_type, supported=", ".join(map(str, all_path_types))
                )
            )

        self._dialog_type = dialog_type or FileSystemPathDialogType.LOAD
        self._path_type = path_type
        self._path_filter = path_filter or ""
        self._validate_path = validate_path
        self._error_msg = None

        # Set through property to trigger side-effects
        self._path_desc = None
        self.path_desc = path_desc or self._path_type

        # Path type icon
        if self._path_type == FileSystemPathType.FILE:
            if self._dialog_type == FileSystemPathDialogType.SAVE:
                browse_icon_key = "save"
            else:
                browse_icon_key = "file"
        else:
            browse_icon_key = "folder-closed"

        # Browse button
        self._browse_action = QtWidgets.QAction()

        browse_icon_path = get_icon_path(browse_icon_key)
        if browse_icon_path is not None:
            browse_icon = QtGui.QIcon(browse_icon_path)
            self._browse_action.setIcon(browse_icon)

        self.addAction(self._browse_action, QtWidgets.QLineEdit.TrailingPosition)

        # Signals/slots
        self._browse_action.triggered.connect(self._on_browse_action_triggered)
        self.textChanged.connect(self._on_text_changed)

    @property
    def path_type(self):
        return self._path_type

    @property
    def error_msg(self):
        return self._error_msg or ""

    @property
    def validate_path(self):
        return self._validate_path

    @validate_path.setter
    def validate_path(self, validate_path):
        self._validate_path = validate_path
        self._on_text_changed(self.text())

    @property
    def path_filter(self):
        return self._path_filter

    @path_filter.setter
    def path_filter(self, path_filter):
        self._path_filter = path_filter

    @property
    def path_desc(self):
        return self._path_desc

    @path_desc.setter
    def path_desc(self, path_desc):
        self._path_desc = path_desc
        if self._path_desc is not None:
            self.setPlaceholderText(self._path_desc)

    def has_error(self):
        """
        If path existence checking is enabled, check if current path
        has triggered an error.

        :return: Whether path has an error
        :rtype: bool
        """
        return self._error_msg is not None

    @QtCore.Slot()
    def _on_text_changed(self, path):
        """
        Validate path during edit.
        """
        self._error_msg = None

        if not path or not self._validate_path:
            # No validation needed
            pass
        elif not os.path.exists(path):
            self._error_msg = "Path '{path}' does not exist".format(path=path)
        elif (
            self._path_type == FileSystemPathType.FILE and not os.path.isfile(path)
        ) or (
            self._path_type == FileSystemPathType.DIRECTORY and not os.path.isdir(path)
        ):
            self._error_msg = "Path '{path}' is not a valid {type}".format(
                path=path, type=self._path_type
            )

        if self._error_msg is not None:
            self.setStyleSheet(
                "QLineEdit {{ color: {hex}; }}".format(
                    hex=QtGui.QColor(QtCore.Qt.red).lighter(125).name()
                )
            )
            self.setToolTip(self._error_msg)
        else:
            self.setStyleSheet("")
            self.setToolTip(self._path_desc)

    @QtCore.Slot()
    def _on_browse_action_triggered(self):
        """
        Browse button clicked.
        """
        current_path = self.text()
        caption = "Choose {path_desc}".format(path_desc=self._path_desc)

        if self._path_type == FileSystemPathType.FILE:
            if self._dialog_type == FileSystemPathDialogType.SAVE:
                new_path, sel_filter = QtWidgets.QFileDialog.getSaveFileName(
                    self, caption, os.path.dirname(current_path), self._path_filter
                )
            else:
                if self._validate_path:
                    default_path = current_path
                else:
                    default_path = os.path.dirname(current_path)

                new_path, sel_filter = QtWidgets.QFileDialog.getOpenFileName(
                    self, caption, default_path, self._path_filter
                )

        else:  # DIRECTORY
            new_path = QtWidgets.QFileDialog.getExistingDirectory(
                self, caption, current_path
            )

        if new_path and new_path != current_path:
            self.setText(new_path)
