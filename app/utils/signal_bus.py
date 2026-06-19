from PySide6.QtCore import QObject, Signal


class _SignalBus(QObject):
    dataChanged = Signal()

    def notifyChanged(self):
        self.dataChanged.emit()


_signal_bus_instance = None


def SignalBus():
    global _signal_bus_instance
    if _signal_bus_instance is None:
        _signal_bus_instance = _SignalBus()
    return _signal_bus_instance
