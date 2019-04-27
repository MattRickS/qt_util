from PySide2 import QtCore


class ThreadedFunction(QtCore.QObject, QtCore.QRunnable):
    functionFinished = QtCore.Signal(object)

    def __init__(self, func, *args, **kwargs):
        super(ThreadedFunction, self).__init__()
        QtCore.QRunnable.__init__(self)
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        result = self.func(*self.args, **self.kwargs)
        self.functionFinished.emit(result)
