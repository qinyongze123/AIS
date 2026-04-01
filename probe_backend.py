
from PySide6.QtCore import QObject, Signal, Slot, QTimer
from .globals import session_globals

class ProbeBackend(QObject):
    """
    QObject-based Zaber hardware backend for the Probe (Device 2).
    Designed to be moved to a QThread.
    """
    connected = Signal(bool)
    disconnected = Signal(bool)
    position_updated = Signal(dict)
    move_done = Signal(bool)

    tip_message = Signal(str)
    debug_message = Signal(str)

    def __init__(self):
        super().__init__()
        self.port = session_globals.get_setting("DEFAULT_PORT")
        self.refresh_rate_ms = session_globals.get_setting("REFRESH_RATE_MS", 100)
        self.connection = None
        self.device = None
        self.axes = {}
        self.poll_timer = None
        self._current_pos = {"X": 0, "Y": 0, "Z": 0, "Rz": 0}
        self._active_command = None

    @Slot()
    def connect_zaber(self):
        # 模仿 InjectorBackend 但针对 Device Index 2
        if self.poll_timer is None:
            self.poll_timer = QTimer(self)
            self.poll_timer.timeout.connect(self.poll_positions)
        
        # 暂时作为占位实现，逻辑与 Injector 镜像
        self.connected.emit(True)
        self.poll_timer.start(self.refresh_rate_ms)

    @Slot()
    def poll_positions(self):
        # Update local cache (in real implementation, get from Zaber)
        # self._current_pos = ... 
        
        # 发送汇总状态包给 Control
        status_packet = {
            "pos": self._current_pos,
            "is_busy": False,
            "active_command": self._active_command
        }
        self.position_updated.emit(status_packet)

