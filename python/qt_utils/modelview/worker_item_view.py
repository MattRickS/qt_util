import itertools
import traceback

from PySide2 import QtCore, QtGui, QtWidgets


class WorkerSignals(QtCore.QObject):
    """
    QRunnable does not inherit from QObject so cannot define signals.
    This class acts as a simple container for the required signals.
    """

    completed = QtCore.Signal(object)
    failed = QtCore.Signal(str)
    progressUpdated = QtCore.Signal(str, int)


class Worker(QtCore.QRunnable):
    """ Simple threadable function wrapper """

    def __init__(self, func, *args, **kwargs):
        """
        Args:
            func (callable): Any callable object
            *args: Positional arguments to pass to the callable
            **kwargs: Keyword arguments to pass to the callable
        """
        super(Worker, self).__init__()
        self.signals = WorkerSignals()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def __repr__(self):
        return "{s.__class__.__name__}({s.func!r}, *{s.args!r}, **{s.kwargs!r})".format(
            s=self
        )

    def __str__(self):
        return self.func.__name__

    def run(self):
        try:
            result = self.func(*self.args, **self.kwargs)
        except Exception:
            error = traceback.format_exc()
            self.signals.failed.emit(error)
        else:
            self.signals.completed.emit(result)


class WorkerItemState(object):
    """ Running state of a WorkerItem """

    Idle = 0
    Running = 1
    Complete = 2
    Failed = 3


class WorkerItemColumn(object):
    """ Column names and indexes for WorkerItems in the WorkerItemModel """

    NAMES = ["name", "progress", "message"]

    Name = 0
    Progress = 1
    Message = 2


class WorkerProgressColour(object):
    """ Colours to use for the WorkerItem progress column """

    Completed = "#56BF21"
    Failed = "#BF3821"
    Running = "#0000FF"


class WorkerItem(QtCore.QObject):
    """
    Wrapper for displaying a Worker in the WorkerItemModel. If using a custom
    Worker, set_worker should be implemented to connect/disconnect the complete,
    fail, and update methods.
    """

    workerCompleted = QtCore.Signal(object)
    workerFailed = QtCore.Signal(str)
    workerUpdated = QtCore.Signal(str, int)

    ThreadPool = QtCore.QThreadPool()

    def __init__(self, worker):
        """
        Args:
            worker (Worker): Worker runnable the item represents
        """
        super(WorkerItem, self).__init__()
        self._worker = None

        self.min_progress = 0
        self.max_progress = 100
        self._progress = self.min_progress

        self._message = "-"
        self._result = None
        self._state = WorkerItemState.Idle

        self.set_worker(worker)

    def __repr__(self):
        return "{s.__class__.__name__}({s._worker!r})".format(s=self)

    def __str__(self):
        return "{s.__class__.__name__}({s._worker})".format(s=self)

    @property
    def message(self):
        """
        Returns:
            str: Current progress description
        """
        return self._message

    @property
    def name(self):
        """
        Returns:
            str: Name to display for the Worker
        """
        return self.worker.func.__name__

    @property
    def progress(self):
        """
        Returns:
            int: Current progress value
        """
        return self._progress

    @property
    def result(self):
        """
        Returns:
            object|None: Return value from the Worker once complete or None if
                incomplete/failed
        """
        return self._result

    @property
    def state(self):
        """
        Returns:
            int: WorkerItemState of the Worker, eg, WorkerItemState.Running
        """
        return self._state

    @property
    def worker(self):
        """
        Returns:
            Worker: Worker runnable the item represents
        """
        return self._worker

    def complete(self, result):
        """
        Marks the item as completed and stores the result. Message is updated to
        display the result

        Args:
            result (object): Result of the Worker
        """
        self._state = WorkerItemState.Complete
        self._message = "Result: {}".format(result)
        self._progress = self.max_progress
        self._result = result
        self.workerCompleted.emit(result)

    def fail(self, error):
        """
        Marks the item as failed and updates the current message

        Args:
            error (str): Error message
        """
        self._state = WorkerItemState.Failed
        self._message = error
        self.workerFailed.emit(error)

    def percentage(self):
        """
        Returns:
            float: Percentage of progress between 0 and 1
        """
        return (self._progress - self.min_progress) / float(
            self.max_progress - self.min_progress
        )

    def set_worker(self, worker):
        """
        Replaces the Worker, resets the state to Idle

        Args:
            worker (Worker): Worker to set on the item.
        """
        if self._worker is not None:
            self._worker.signals.completed.disconnect(self.complete)
            self._worker.signals.failed.disconnect(self.fail)
            self._worker.signals.progressUpdated.disconnect(self.update)

        self._worker = worker
        self._worker.setAutoDelete(False)
        self._worker.signals.completed.connect(self.complete)
        self._worker.signals.failed.connect(self.fail)
        self._worker.signals.progressUpdated.connect(self.update)

        self._state = WorkerItemState.Idle
        self._message = "-"
        self._result = None

    def start(self):
        """ Starts the Worker in a thread """
        self.ThreadPool.start(self._worker)
        self._state = WorkerItemState.Running

    def update(self, message, progress):
        """
        Args:
            message (str): Process update message
            progress (int): Progress value to set. Will be clamped between min
                and max
        """
        self._message = message
        self._progress = max(self.min_progress, min(progress, self.max_progress))
        self.workerUpdated.emit(message, self._progress)


class WorkerItemModel(QtCore.QAbstractItemModel):
    def __init__(self, worker_items=None, parent=None):
        """
        Keyword Args:
            worker_items (list[WorkerItems]):
            parent (QtCore.QObject):
        """
        super(WorkerItemModel, self).__init__(parent)
        self._connections = {}

        self._worker_items = worker_items or []
        self._connect_items(self._worker_items)

    def _connect_items(self, worker_items):
        for worker_item in worker_items:
            # Track the temporary function so that it can be disconnected when
            # removing items.
            refresh_func = lambda *args, witem=worker_item: self.refresh_item(witem)
            self._connections[worker_item] = refresh_func
            worker_item.workerCompleted.connect(refresh_func)
            worker_item.workerFailed.connect(refresh_func)
            worker_item.workerUpdated.connect(refresh_func)

    def _disconnect_items(self, worker_items):
        for worker_item in worker_items:
            func = self._connections.pop(worker_item)
            worker_item.workerCompleted.disconnect(func)
            worker_item.workerFailed.disconnect(func)
            worker_item.workerUpdated.disconnect(func)

    def add_items(self, worker_items, start_index=None):
        """
        Args:
            worker_items (list[WorkerItem]): List of worker items to add
            start_index (:obj:`int`, optional): Index to add the items at. Acts
                as an insert operation if given, or an append operation if not
        """
        start = self.rowCount() if start_index is None else start_index
        num = len(worker_items)
        parent = QtCore.QModelIndex()

        # Trigger the correct signals
        self.beginInsertRows(parent, start, start + num)
        self._worker_items = (
            self._worker_items[:start] + worker_items + self._worker_items[start:]
        )
        self._connect_items(worker_items)
        self.endInsertRows()

    def index_from_item(self, worker_item, column=0):
        """
        Args:
            worker_item (WorkerItem): Item to retrieve the index for
            column (:obj:`int`, optional): Column to get the index for, defaults
                to the first column

        Returns:
            QtCore.QModelIndex: index for the item
        """
        for row, item in enumerate(self._worker_items):
            if item == worker_item:
                return self.index(row, column)
        return QtCore.QModelIndex()

    def refresh_item(self, worker_item):
        """
        Args:
            worker_item (WorkerItem): Emits dataChanged for the row's indexes
                belonging to the given item
        """
        index = self.index_from_item(worker_item)
        if not index.isValid():
            raise ValueError("Item is not part of the model: {}".format(worker_item))

        start = index.sibling(index.row(), 0)
        end = index.sibling(index.row(), self.columnCount(index.parent()))
        self.dataChanged.emit(start, end)

    def remove_items(self, worker_items):
        """
        Args:
            worker_items (list[WorkerItem]): List of worker items to remove
        """
        parent = QtCore.QModelIndex()
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
        """
        Args:
            worker_items (list[WorkerItem]): List of worker items to populate
                the model with. Will clear all existing items. Set with an empty
                list to clear the model.
        """
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
                if worker_item.state == WorkerItemState.Idle:
                    return "Idle"
                if worker_item.state == WorkerItemState.Failed:
                    return "Failed"
                elif worker_item.state == WorkerItemState.Running:
                    return "{:3d}%".format(int(worker_item.percentage() * 100))
                elif worker_item.state == WorkerItemState.Complete:
                    return "Complete"
            elif index.column() == WorkerItemColumn.Message:
                return worker_item.message

        if role == QtCore.Qt.ToolTipRole:
            return worker_item.message

        if (
            role == QtCore.Qt.TextAlignmentRole
            and index.column() == WorkerItemColumn.Progress
        ):
            return QtCore.Qt.AlignCenter

        if (
            role == QtCore.Qt.BackgroundRole
            and index.column() == WorkerItemColumn.Progress
        ):
            if worker_item.state == WorkerItemState.Failed:
                return QtGui.QColor(WorkerProgressColour.Failed)
            elif worker_item.state == WorkerItemState.Running:
                return QtGui.QColor(WorkerProgressColour.Running)
            elif worker_item.state == WorkerItemState.Complete:
                return QtGui.QColor(WorkerProgressColour.Completed)

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


class WorkerItemProgressDelegate(QtWidgets.QStyledItemDelegate):
    """ Delegate for drawing the progress bar for a WorkerItem """

    def paint(self, painter, option, index):
        # type: (QtGui.QPainter, QtWidgets.QStyleOptionViewItem, QtCore.QModelIndex) -> None
        if not index.isValid():
            return

        worker_item = index.internalPointer()
        if worker_item.state == WorkerItemState.Running:
            progress_opt = QtWidgets.QStyleOptionProgressBar()
            progress_opt.rect = option.rect
            progress_opt.text = index.data(QtCore.Qt.DisplayRole)
            progress_opt.textVisible = True
            progress_opt.textAlignment = option.displayAlignment
            progress_opt.minimum = 0
            progress_opt.maximum = worker_item.max_progress
            progress_opt.progress = worker_item.progress

            bg_colour = index.data(QtCore.Qt.BackgroundRole)
            progress_opt.palette.setColor(QtGui.QPalette.Base, bg_colour)
            progress_opt.palette.setColor(QtGui.QPalette.Foreground, bg_colour)
            progress_opt.palette.setColor(QtGui.QPalette.Highlight, bg_colour)

            QtWidgets.QApplication.style().drawControl(
                QtWidgets.QStyle.CE_ProgressBar, progress_opt, painter
            )
        else:
            super(WorkerItemProgressDelegate, self).paint(painter, option, index)


class WorkerItemView(QtWidgets.QTableView):
    selectedItemsChanged = QtCore.Signal(object)

    def __init__(self, parent=None):
        # type: (QtWidgets.QWidget) -> None
        super(WorkerItemView, self).__init__(parent)
        self.horizontalHeader().setStretchLastSection(True)
        self.setModel(WorkerItemModel())
        self.setItemDelegateForColumn(
            WorkerItemColumn.Progress, WorkerItemProgressDelegate(self)
        )

        # Note: Due to a bug in PySide2, trying to access a method on the
        # selectionModel without keeping a reference to the selectionModel will
        # cause a segfault
        selection_model = self.selectionModel()
        selection_model.selectionChanged.connect(
            self.on_selection_model_selection_changed
        )

    def add_items(self, items):
        """
        Args:
            items (list[WorkerItem]): List of worker items to add
        """
        self.model().add_items(items)

    def count(self):
        """
        Returns:
            int: Number of items in the model/view
        """
        return self.model().rowCount()

    def item(self, row):
        """
        Args:
            row (int): Row to get the item for

        Returns:
            WorkerItem: Item in the row
        """
        index = self.model().index(row, 0)
        if not index.isValid():
            raise ValueError("Invalid row: {}".format(row))
        return index.internalPointer()

    def remove_items(self, items):
        """
        Args:
            items (list[WorkerItem]): List of worker items to remove
        """
        self.model().remove_items(items)

    def selected_items(self):
        """
        Returns:
            list[WorkerItem]: List of selected WorkerItems
        """
        return list({
            index.internalPointer()
            for index in self.selectedIndexes()
            if index.isValid()
        })

    def set_items(self, items):
        """
        Args:
            items (list[WorkerItem]): List of worker items to populate the
                model/view with. Will clear all existing items. Set with an
                empty list to clear the model/view.
        """
        self.model().set_items(items)

    def on_selection_model_selection_changed(self):
        self.selectedItemsChanged.emit(self.selected_items())


if __name__ == "__main__":
    import random
    import sys
    import time

    app = QtWidgets.QApplication(sys.argv)

    def debug(*args):
        print(args)

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
    for i in range(4):
        worker = Worker(func)
        worker.kwargs["callback"] = worker.signals.progressUpdated.emit
        item = WorkerItem(worker)
        items.append(item)

    view = WorkerItemView()
    view.selectedItemsChanged.connect(debug)
    view.set_items(items)
    view.show()

    view.remove_items(items[:1])

    def start_all():
        for row in range(view.count()):
            item = view.item(row)
            item.start()

    btn = QtWidgets.QPushButton("Start")
    btn.clicked.connect(start_all)
    btn.show()

    app.exec_()
    sys.exit()
