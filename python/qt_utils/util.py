import contextlib
import functools

from PySide2 import QtCore, QtGui, QtWidgets


def copy_to_clipboard(string):
    """
    Copies text into the operating system clipboard

    Args:
        string (str):
    """
    clipboard = QtWidgets.QApplication.clipboard()
    clipboard.setText(string)


def ensure_qapp(func):
    """ Decorator for ensuring a QApplication instance is initialised """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        app = None if QtWidgets.QApplication.instance() else QtWidgets.QApplication([])

        result = func(*args, **kwargs)

        if app is not None:
            app.exec_()

        return result

    return wrapper


def set_display_columns(view, columns):
    """
    Modifies the columns of a view so that the header only displays the given
    columns in that order

    Args:
        view (QtWidgets.QAbstractItemView): Qt View to modify the headers for
        columns (list[str]): List of column header names to display in order
    """
    model = view.model()
    header = view.header() if isinstance(view, QtWidgets.QTreeView) else view.horizontalHeader()

    # Pull the headers from the model
    logical_columns = [model.headerData(col, QtCore.Qt.Horizontal, QtCore.Qt.DisplayRole)
                       for col in range(model.columnCount())]
    for idx, col in enumerate(columns):
        # Let it raise a ValueError if sent an invalid column
        logical_index = logical_columns.index(col)
        visual_index = header.visualIndex(logical_index)
        # move operates on the visual index
        header.moveSection(visual_index, idx)
        # show / hide operates on the logical index
        header.showSection(logical_index)

    # Iterate over the logical indexes and hide the unneeded columns
    for idx, col in enumerate(logical_columns):
        if col not in columns:
            header.hideSection(idx)


@contextlib.contextmanager
def wait_cursor():
    """ Context manager for setting and restoring the wait cursor """
    QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
    yield
    QtWidgets.QApplication.restoreOverrideCursor()
