from PySide6.QtCore import QObject, Signal, Slot, QMetaObject, Qt
from remake.logger import logger

class Control(QObject):
    """
    Mediator Layer: Bridges FrontEnd (UI) and Backend Services.
    Runs in the Main Thread. 
    STRONGLY DECOUPLED: Communicates with services ONLY via Signals and Slots.
    """
    # Signals to UI (Proxying status from services to FrontEnd)
    status_updated = Signal(dict)
    
    # Signals to Backend Services (Commands)
    request_connect = Signal(str) # device_name: "injector", "probe", "all"
    request_disconnect = Signal(str)
    request_step = Signal(str, dict) # step_name, params
    request_stop = Signal()

    def __init__(self):
        super().__init__()
        # Internal state cache for UI polling/updates
        # This acts as the "Single Source of Truth" for the FrontEnd
        self._last_status = {
            "injector": {
                "connected": False, 
                "pos": {"X":0,"Y":0,"Z":0,"Rz":0},
                "is_busy": False,
                "active_command": None
            },
            "probe": {
                "connected": False, 
                "pos": {"X":0,"Y":0,"Z":0,"Rz":0},
                "is_busy": False,
                "active_command": None
            },
            "rgbd": {"connected": False},
            "us": {"connected": False}
        }

    @Slot(dict)
    def update_injector_status(self, data):
        """
        Slot connected to InjectorBackend.position_updated.
        Expects: {'pos': dict, 'is_busy': bool, 'active_command': str}
        """
        self._last_status["injector"].update(data)
        self._last_status["injector"]["connected"] = True
        self.status_updated.emit(self._last_status)

    @Slot(dict)
    def update_probe_status(self, data):
        """
        Slot connected to ProbeBackend.position_updated.
        """
        self._last_status["probe"].update(data)
        self._last_status["probe"]["connected"] = True
        self.status_updated.emit(self._last_status)

    @Slot(bool)
    def set_injector_connection_state(self, is_connected):
        self._last_status["injector"]["connected"] = is_connected
        self.status_updated.emit(self._last_status)

    @Slot(bool)
    def set_probe_connection_state(self, is_connected):
        self._last_status["probe"]["connected"] = is_connected
        self.status_updated.emit(self._last_status)

    def reconnect(self, device_name: str):
        logger.info(f"Control: Proxying reconnect request for {device_name}")
        self.request_connect.emit(device_name)

    def execute_step(self, step_name: str):
        logger.info(f"Control: UI requested step: {step_name}")
        self.request_step.emit(step_name, {})

    def stop_all(self):
        logger.error("Control: BROADCASTING EMERGENCY STOP")
        self.request_stop.emit()

    def get_status(self) -> dict:
        """Fallback for synchronous UI polling if needed."""
        return self._last_status

    def set_mode(self, mode_name: str):
        """Sets the operating mode: 'safe' or 'work'."""
        logger.info(f"Control: Setting robot mode to {mode_name}")
        # Logic to notify backends if needed can be added here
        self.request_step.emit("set_mode", {"mode": mode_name})

    def shutdown(self):
        self.stop_all()
        self.request_disconnect.emit("all")

    def connect_all(self):
        self.request_connect.emit("all")
