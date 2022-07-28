# SPDX-License-Identifier: Apache-2.0
# Copyright Contributors to the OpenTimelineIO project

import sys

import unreal
from PySide2 import QtCore, QtGui, QtWidgets


SLATE_PARENT_OBJECT_NAME = "qapp_slate_parent"
PACKAGE_TAG = "qapp_created_by_otio_unreal_actions"


class UnrealPalette(QtGui.QPalette):
    """QPalette configured to closely match the UE5 Slate color
    palette.
    """

    def __init__(self, palette=None):
        """
        Args:
            palette (QtGui.QPalette): Existing palette to inherit
                from.
        """
        super(UnrealPalette, self).__init__(palette=palette)

        self.setColor(QtGui.QPalette.Window, QtGui.QColor(47, 47, 47))
        self.setColor(QtGui.QPalette.WindowText, QtGui.QColor(192, 192, 192))
        self.setColor(QtGui.QPalette.Base, QtGui.QColor(26, 26, 26))
        self.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(25, 25, 25))
        self.setColor(QtGui.QPalette.Foreground, QtGui.QColor(192, 192, 192))
        self.setColor(QtGui.QPalette.ToolTipBase, QtGui.QColor(255, 255, 255))
        self.setColor(QtGui.QPalette.ToolTipText, QtGui.QColor(255, 255, 255))
        self.setColor(QtGui.QPalette.Text, QtGui.QColor(192, 192, 192))
        self.setColor(QtGui.QPalette.Button, QtGui.QColor(47, 47, 47))
        self.setColor(QtGui.QPalette.ButtonText, QtGui.QColor(192, 192, 192))
        self.setColor(QtGui.QPalette.BrightText, QtGui.QColor(255, 255, 255))
        self.setColor(QtGui.QPalette.Link, QtGui.QColor(186, 186, 186))
        self.setColor(QtGui.QPalette.Highlight, QtGui.QColor(64, 87, 111))
        self.setColor(QtGui.QPalette.HighlightedText, QtGui.QColor(255, 255, 255))

        self.setColor(
            QtGui.QPalette.Disabled,
            QtGui.QPalette.Text,
            QtGui.QColor(110, 110, 110),
        )
        self.setColor(
            QtGui.QPalette.Disabled,
            QtGui.QPalette.ButtonText,
            QtGui.QColor(140, 140, 140),
        )


class UnrealQtHelper(object):
    """Static helper class which manages a QApplication instance in
    the Unreal Editor.
    """

    _qapp = None

    @classmethod
    def ensure_qapp_available(cls):
        """Creates a QApplication if one doesn't exist and sets up
        required interactions with Unreal Engine.

        Returns:
            Qtwidgets.QApplication: Qt application instance.
        """
        # Have we already setup an app?
        if cls._qapp is not None:
            return cls._qapp

        # Does an app instance exist? If not, create one.
        qapp = QtWidgets.QApplication.instance()
        if not qapp:
            qapp = QtWidgets.QApplication(sys.argv)
            # Use a property to indicate our ownership of the app
            qapp.setProperty(PACKAGE_TAG, True)

        # Early out of the app was not created by this plugin
        if not qapp.property(PACKAGE_TAG):
            return qapp

        # Add the process events function if needed to tick the QApplication
        if sys.platform != "win32":
            # Win32 apparently no longer needs a process events on tick to update
            # https://github.com/ue4plugins/tk-unreal/blob/master/engine.py#L117-L123
            unreal.register_slate_post_tick_callback(
                lambda delta_time: qapp.processEvents
            )

        # Setup app styling
        qapp.setStyle("Fusion")
        qapp.setPalette(UnrealPalette(qapp.palette()))

        # Register callback to exit the QApplication on shutdown
        unreal.register_python_shutdown_callback(cls.quit_qapp)

        # Store a reference to the app for future requests
        cls._qapp = qapp
        return cls._qapp

    @classmethod
    def get_parent_widget(cls):
        """
        Returns:
            Qtwidgets.QWidget: Qt application parent widget.
        """
        qapp = cls.ensure_qapp_available()

        parent_widget = qapp.property(SLATE_PARENT_OBJECT_NAME)
        if parent_widget is None:
            # Create an invisible parent widget for all UIs parented to the app's main
            # window. This is so that widgets don't have to individually attach to the
            # app window as top-level.
            parent_widget = QtWidgets.QWidget()
            parent_widget.setObjectName(SLATE_PARENT_OBJECT_NAME)
            parent_widget.setWindowFlags(
                QtCore.Qt.Widget | QtCore.Qt.FramelessWindowHint
            )
            parent_widget.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
            parent_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
            parent_widget.setVisible(True)

            # Store widget on the application in a property so it is only set up once
            qapp.setProperty(SLATE_PARENT_OBJECT_NAME, parent_widget)

            # Store it as a python attribute to block GC
            setattr(qapp, SLATE_PARENT_OBJECT_NAME, parent_widget)

            # Parent the widget to slate
            unreal.parent_external_window_to_slate(
                parent_widget.winId(), unreal.SlateParentWindowSearchMethod.MAIN_WINDOW
            )

        return parent_widget

    @classmethod
    def show_widget(cls, widget):
        """Show widget in the Unreal Engine UI.

        Args:
            widget (QtWidgets.QWidget): Widget to show.
        """
        # Make non-window widgets into a window
        if not widget.isWindow():
            widget.setWindowFlag(QtCore.Qt.Window, True)

        # Ensure window is parented to the Slate parent widget
        widget.setParent(cls.get_parent_widget())
        widget.show()
        widget.raise_()

    @classmethod
    def quit_qapp(cls):
        """Quit QApplication prior to UE exiting."""
        qapp = QtWidgets.QApplication.instance()

        # If a QApplication instance is present and we created it, shut it down
        if qapp and qapp.property(PACKAGE_TAG):
            qapp.quit()
            qapp.deleteLater()
