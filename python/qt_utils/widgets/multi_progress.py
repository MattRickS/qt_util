import itertools
import traceback

from PySide2 import QtCore, QtGui, QtWidgets


class WorkerSignals(QtCore.QObject):
    completed = QtCore.Signal(object)
    failed = QtCore.Signal(str)
    progressUpdate = QtCore.Signal(str, int)


class Worker(QtCore.QRunnable):
    def __init__(self, func, args, kwargs):
        super(Worker, self).__init__()
        self.signals = WorkerSignals()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            result = self.func(*self.args, **self.kwargs)
        except Exception:
            error = traceback.format_exc()
            self.signals.failed.emit(error)
        else:
            self.signals.completed.emit(result)


class WorkerItem(object):
    ThreadPool = QtCore.QThreadPool()

    def __init__(self, func, *args, **kwargs):
        # type: (callable) -> None
        self.has_error = False
        self.is_running = False
        self.max_progress = 100
        self.message = "Idle"
        self.progress = 0
        self.result = None

        self.worker = Worker(func, args, kwargs)
        self.worker.setAutoDelete(False)
        self.worker.signals.completed.connect(self.complete)
        self.worker.signals.failed.connect(self.fail)
        self.worker.signals.progressUpdate.connect(self.update)

    def __repr__(self):
        return (
            "{s.__class__.__name__}({s.name!r}, *{s.worker.args}, "
            "**{s.worker.kwargs})"
        ).format(s=self)

    @property
    def name(self):
        # type: () -> str
        return self.worker.func.__name__

    def complete(self, result):
        # type: (object) -> None
        self.has_error = False
        self.is_running = False
        self.message = "Complete!"
        self.progress = self.max_progress
        self.result = result

    def fail(self, error):
        # type: (str) -> None
        self.has_error = True
        self.is_running = False
        self.message = error
        self.progress = self.max_progress

    def percentage(self):
        # type: () -> float
        return self.progress / float(self.max_progress)

    def start(self):
        self.ThreadPool.start(self.worker)
        self.is_running = True

    def update(self, message, progress):
        # type: (str, int) -> None
        self.message = message
        self.progress = max(0, min(progress, self.max_progress))


class WorkerItemColumn(object):
    NAMES = ["name", "progress", "message", "result"]

    Name = 0
    Progress = 1
    Message = 2
    Result = 3


class ProgressColour(object):
    Completed = "#00FF00"
    Failed = "#FF0000"
    Running = "#0000FF"


class WorkerItemModel(QtCore.QAbstractItemModel):
    def __init__(self, worker_items=None, parent=None):
        # type: (list[WorkerItem], QtWidgets.QWidget) -> None
        super(WorkerItemModel, self).__init__(parent)
        self._worker_items = worker_items or []
        self._connect_items(self._worker_items)

    def _connect_items(self, worker_items):
        for worker_item in worker_items:
            refresh_func = lambda *args, witem=worker_item: self.refresh_row(witem)
            worker_item.worker.signals.failed.connect(refresh_func)
            worker_item.worker.signals.completed.connect(refresh_func)
            worker_item.worker.signals.progressUpdate.connect(refresh_func)

    def _disconnect_items(self, worker_items):
        for worker_item in worker_items:
            # TODO: How to disconnect then the methods are lambda...?
            worker_item.worker.signals.failed.disconnect(self.refresh_row)
            worker_item.worker.signals.completed.disconnect(self.refresh_row)
            worker_item.worker.signals.progressUpdate.disconnect(self.refresh_row)

    def add_items(self, worker_items, index=None, parent=QtCore.QModelIndex()):
        # type: (list[WorkerItem], int, QtCore.QModelIndex) -> None
        start = self.rowCount() if index is None else index
        num = len(worker_items)
        self.beginInsertRows(parent, start, start + num)
        self.insertRows(start, num, parent)
        self._worker_items = (
            self._worker_items[:start] + worker_items + self._worker_items[start:]
        )
        self._connect_items(worker_items)
        self.endInsertRows()

    def index_from_item(self, worker_item):
        # type: (WorkerItem) -> QtCore.QModelIndex
        for row, item in enumerate(self._worker_items):
            if item == worker_item:
                return self.index(row, 0)
        return QtCore.QModelIndex()

    def refresh_row(self, worker_item):
        # type: (WorkerItem) -> None
        index = self.index_from_item(worker_item)
        if not index.isValid():
            raise ValueError("Item is not part of the model: {}".format(worker_item))

        start = index.sibling(index.row(), 0)
        end = index.sibling(index.row(), self.columnCount(index.parent()))
        self.dataChanged.emit(start, end)

    def remove_items(self, worker_items, parent=QtCore.QModelIndex()):
        # type: (list[WorkerItem], QtCore.QModelIndex) -> None
        # Guarantees order, avoids errors for invalid entities (but won't give warning)
        indexes = [idx for idx, e in enumerate(self._worker_items) if e in worker_items]
        # Remove in reversed order to prevent modifying indices during loop
        for _, grp in itertools.groupby(
            reversed(indexes), key=lambda x, y=itertools.count(): next(y) + x
        ):
            indices = list(grp)
            # Indices are reversed
            end, start = indices[0], indices[-1]
            self.beginRemoveRows(parent, start, end)
            self.removeRows(start, end - start, parent)
            items = self._worker_items[start : end + 1]
            self._disconnect_items(items)
            self._worker_items[start : end + 1] = []
            self.endRemoveRows()

    def set_items(self, worker_items):
        # type: (list[WorkerItem]) -> None
        self.beginResetModel()
        self._disconnect_items(self._worker_items)
        self._worker_items = worker_items or []
        self._connect_items(self._worker_items)
        self.endResetModel()

    def columnCount(self, parent=QtCore.QModelIndex()):
        # type: (QtCore.QModelIndex) -> int
        return len(WorkerItemColumn.NAMES)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        # type: (QtCore.QModelIndex, int) -> object
        if not index.isValid():
            return
        worker_item = self._worker_items[index.row()]
        if role == QtCore.Qt.DisplayRole:
            if index.column() == WorkerItemColumn.Name:
                return worker_item.name
            elif index.column() == WorkerItemColumn.Progress:
                return worker_item.progress
            elif index.column() == WorkerItemColumn.Message:
                return worker_item.message
            elif index.column() == WorkerItemColumn.Result:
                return str(worker_item.result)

        if role == QtCore.Qt.ToolTipRole:
            return worker_item.message

        if (
            role == QtCore.Qt.TextAlignmentRole
            and index.column() == WorkerItemColumn.Progress
        ):
            return QtCore.Qt.AlignLeft

        if (
            role == QtCore.Qt.BackgroundRole
            and index.column() == WorkerItemColumn.Progress
        ):
            if worker_item.has_error:
                return QtGui.QColor(ProgressColour.Failed)
            elif worker_item.is_running:
                return QtGui.QColor(ProgressColour.Running)
            else:
                return QtGui.QColor(ProgressColour.Running)

    def flags(self, index):
        # type: (QtCore.QModelIndex) -> QtCore.Qt.ItemFlags
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        # type: (int, QtCore.Qt.Orientation, int) -> str
        if role == QtCore.Qt.DisplayRole and orientation == QtCore.Qt.Horizontal:
            return WorkerItemColumn.NAMES[section]

    def index(self, row, column, parent=QtCore.QModelIndex()):
        # type: (int, int, QtCore.QModelIndex) -> QtCore.QModelIndex
        return self.createIndex(row, column, self._worker_items[row])

    def parent(self, child):
        # type: (QtCore.QModelIndex) -> QtCore.QModelIndex
        return QtCore.QModelIndex()

    def rowCount(self, parent=QtCore.QModelIndex()):
        # type: (QtCore.QModelIndex) -> int
        return len(self._worker_items)

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        # type: (QtCore.QModelIndex, object, int) -> bool
        if not index.isValid() or role not in (
            QtCore.Qt.EditRole,
            QtCore.Qt.DisplayRole,
        ):
            return False

        item = self._worker_items[index.row()]
        if index.column() == WorkerItemColumn.Progress:
            item.progress = value
            self.dataChanged.emit(index, index)
            return True

        return False


class ProgressBarDelegate(QtWidgets.QStyledItemDelegate):
    def paint(self, painter, option, index):
        # type: (QtGui.QPainter, QtWidgets.QStyleOptionViewItem, QtCore.QModelIndex) -> None
        if not index.isValid():
            return

        worker_item = index.internalPointer()

        progress_opt = QtWidgets.QStyleOptionProgressBar()
        progress_opt.rect = option.rect
        progress_opt.text = option.text
        progress_opt.textVisible = True
        progress_opt.textAlignment = option.displayAlignment
        progress_opt.minimum = 0
        progress_opt.maximum = worker_item.max_progress
        progress_opt.progress = worker_item.progress

        # bg_colour = index.data(QtCore.Qt.BackgroundRole)
        # print(bg_colour)
        # progress_opt.palette.setColor(QtGui.QPalette.Base, bg_colour)
        # progress_opt.palette.setColor(QtGui.QPalette.Foreground, bg_colour)
        # progress_opt.palette.setColor(QtGui.QPalette.Highlight, bg_colour)

        QtWidgets.QApplication.style().drawControl(
            QtWidgets.QStyle.CE_ProgressBar, progress_opt, painter
        )


class MultiProcessView(QtWidgets.QTableView):
    def __init__(self, parent=None):
        # type: (QtWidgets.QWidget) -> None
        super(MultiProcessView, self).__init__(parent)
        # TODO: Stretch message instead of result
        self.horizontalHeader().setStretchLastSection(True)
        self.setModel(WorkerItemModel())
        self.setItemDelegateForColumn(
            WorkerItemColumn.Progress, ProgressBarDelegate(self)
        )

    def add_items(self, items):
        # type: (list[WorkerItem]) -> None
        self.model().add_items(items)

    def remove_items(self, items):
        # type: (list[WorkerItem]) -> None
        self.model().remove_items(items)

    def set_items(self, items):
        # type: (list[WorkerItem]) -> None
        self.model().set_items(items)


if __name__ == "__main__":
    import random
    import sys
    import time

    app = QtWidgets.QApplication(sys.argv)

    def func(callback=None):
        callback = callback or (lambda msg, value: None)
        count = random.randint(3, 6)
        for i in range(count):
            progress = int((i / float(count)) * 100)
            callback("Doing {}".format(i), progress)
            time.sleep(random.random() * 2)

            if random.random() < 0.1:
                raise ValueError("Something is wrong")

        return random.randint(0, 3)

    items = []
    for i in range(3):
        item = WorkerItem(func)
        item.worker.kwargs["callback"] = item.worker.signals.progressUpdate.emit
        items.append(item)

    view = MultiProcessView()
    view.set_items(items)
    view.show()

    for item in items:
        item.start()

    app.exec_()
    sys.exit()
