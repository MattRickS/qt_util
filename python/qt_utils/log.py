import logging

from PySide2 import QtCore, QtGui, QtWidgets


# Signals must be on a QObject and it's not possible to use multiple inheritance
# with QObject and logging.Handler. Define a separate object to use for signals
class Signaller(QtCore.QObject):
    logReceived = QtCore.Signal(object)  # LogRecord


class LogHandler(logging.Handler):
    def __init__(self, level=logging.NOTSET):
        super(LogHandler, self).__init__(level)
        self.signaller = Signaller()

    def emit(self, record):
        self.signaller.logReceived.emit(record)


class LogDisplay(QtWidgets.QTextEdit):
    COLOURS = {
        logging.DEBUG: 'grey',
        logging.INFO: 'black',
        logging.WARNING: 'yellow',
        logging.ERROR: 'red',
        logging.CRITICAL: 'darkred',
    }

    def __init__(self, logger=None, level=logging.INFO):
        # type: (logging.Logger, int|str) -> None
        super(LogDisplay, self).__init__()
        self.setReadOnly(True)
        self.setWordWrapMode(QtGui.QTextOption.NoWrap)

        self._auto_refresh = True
        self._handler = LogHandler(level)
        self._logger = None

        self._handler.signaller.logReceived.connect(self.on_log_emitted)

        if logger is not None:
            self.set_logger(logger)

    @property
    def handler(self):
        """
        Returns:
            LogHandler: Log handler being used
        """
        return self._handler

    @property
    def logger(self):
        """
        Returns:
            logging.Logger: Logger currently being displayed
        """
        return self._logger

    def set_auto_refresh(self, refresh):
        """
        Args:
            refresh (bool): Whether or not to process events with each log
        """
        self._auto_refresh = bool(refresh)

    def set_formatter(self, formatter):
        """
        Args:
            formatter (logging.Formatter): Log formatter to use for logs
        """
        self._handler.setFormatter(formatter)

    def set_level(self, level):
        """
        Args:
            level (str|int): Log level to display. Note, this only applies to
                the handler. The logger level must also support the level for
                the logs to appear in the editor
        """
        self._handler.setLevel(level)

    def set_logger(self, logger):
        """
        Args:
            logger (logging.Logger): Logger to display in the editor
        """
        if self._logger is not None and self._handler in self._logger.handlers:
            self._logger.handlers.remove(self._handler)
        self._logger = logger
        if self._logger is not None:
            self._logger.addHandler(self._handler)

    def on_log_emitted(self, record):
        """
        Args:
            record (logging.LogRecord): Log record currently being processed
        """
        level = min(level for level in self.COLOURS if level >= record.levelno)
        msg = self._handler.format(record).replace('\n', '<br/>').replace(' ', '&nbsp;')
        self.append('<font color="%s">%s</font>' % (self.COLOURS[level], msg))
        if self._auto_refresh:
            QtWidgets.QApplication.processEvents()
