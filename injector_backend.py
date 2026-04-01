import math
import time
from PySide6.QtCore import QObject, Signal, Slot, QTimer
from zaber_motion import Library, Units, Measurement
from zaber_motion.ascii import Connection, AxisGroup
from zaber_motion.exceptions import ConnectionFailedException
from .globals import session_globals

class InjectorBackend(QObject):
    """
    QObject-based Zaber hardware backend for the Injector (Device 1).
    Designed to be moved to a QThread (moveToThread).
    """

    connected = Signal(bool) 
    disconnected = Signal(bool) 
    
    # Operation status signals: (is_success)
    home_done = Signal(bool)
    angle_done = Signal(bool)
    move_done = Signal(bool)
    position_updated = Signal(dict) 

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
        self._current_pos = {'X': 0, 'Y': 0, 'Z': 0, 'Rz': 0}
        
        # Internal state tracking for non-blocking operations
        self._active_command = None # Identifies current task: "HOME", "ANGLE", "MOVE"
        self._last_busy_state = False # Tracks hardware busy transition (True -> False)
        
    @Slot()
    def connect_zaber(self):
        """Attempts to open serial port and detect the injector device (Index 1)."""
        if self.poll_timer is None:
            self.poll_timer = QTimer(self) 
            self.poll_timer.timeout.connect(self.poll_positions)

        try:
            Library.enable_device_db_store()
            self.connection = Connection.open_serial_port(self.port)
            detected_devices = self.connection.detect_devices()
            
            if not detected_devices:
                self.debug_message.emit(f"ERROR: [InjectorBackend.connect_zaber] No devices found on {self.port}")
                self.tip_message.emit("No Zaber devices found. Check cable connections.")
                self.connected.emit(False)
                return

            # Hardcode: index 1 is injector
            if len(detected_devices) > 1:
                self.device = detected_devices[1]
                axis_map = {'X': 1, 'Y': 2, 'Z': 3, 'Rz': 4}
                self.axes = {
                    name: self.device.get_axis(num) for name, num in axis_map.items()
                }
                
                self.tip_message.emit("Injector Connected.")
                self.connected.emit(True)
                
                # Start polling using rate from config
                self.poll_timer.start(self.refresh_rate_ms)
            else:
                self.debug_message.emit(f"ERROR: [InjectorBackend.connect_zaber] Device 1 (Injector) not found on {self.port}")
                self.tip_message.emit("Injector device not found.")
                self.connected.emit(False)
            
        except ConnectionFailedException as e:
            self.debug_message.emit(f"ERROR: [InjectorBackend.connect_zaber] Connection failed: {e}")
            self.connected.emit(False)
        except Exception as e:
            self.debug_message.emit(f"ERROR: [InjectorBackend.connect_zaber] {e}")
            self.connected.emit(False)

    @Slot()
    def disconnect_zaber(self):
        """Closes hardware connection."""
        if self.poll_timer:
            self.poll_timer.stop()
        if self.connection and self.connection.is_open:
            self.connection.close()
        self.device = None
        self.axes = {}
        self.disconnected.emit(True)

    @Slot()
    def stop(self):
        """Emergency stop for all axes on this device."""
        if self.device:
            try:
                self.device.all_axes.stop()
                self._active_command = None
                self.tip_message.emit("Injector STOPPED.")
            except Exception as e:
                self.debug_message.emit(f"ERROR: [InjectorBackend.stop] {e}")

    @Slot()
    def sethome(self):
        """Homes linear axes for the injector - Non-blocking."""
        if not self.axes:
            self.debug_message.emit("ERROR: [InjectorBackend.sethome] No axes found.")
            self.home_done.emit(False)
            return
            
        if self._active_command:
            self.tip_message.emit("Injector BUSY with another command.")
            return

        try:
            self.tip_message.emit("Homing Injector...")
            self._active_command = "HOME"
            
            linear_axes = [self.axes[n] for n in ['X', 'Y', 'Z']]
            linear_group = AxisGroup(linear_axes)
            # Home without waiting (wait_until_idle=False is implicit for many Zaber start commands)
            linear_group.home(wait_until_idle=False)
            
            # Control returns immediately to event loop
        except Exception as e:
            self._active_command = None
            msg = f"ERROR: [InjectorBackend.sethome] {e}"
            self.debug_message.emit(msg)
            self.tip_message.emit("Homing failed.")
            self.home_done.emit(False)

    @Slot(bool)
    def setangle(self, to_safe: bool):
        """Sets the Rz axis - Non-blocking."""
        if 'Rz' not in self.axes:
            self.debug_message.emit("ERROR: [InjectorBackend.setangle] Rz axis not found.")
            self.angle_done.emit(False)
            return

        if self._active_command:
            self.tip_message.emit("Injector BUSY.")
            return

        try:
            axis = self.axes['Rz']
            self._active_command = "ANGLE"
            if to_safe:
                self.tip_message.emit("Setting SAFE angle...")
                axis.home(wait_until_idle=False)
            else:
                self.tip_message.emit("Setting INJECT angle...")
                axis.move_absolute(90.0, unit=Units.ANGLE_DEGREES, wait_until_idle=False)
            
        except Exception as e:
            self._active_command = None
            msg = f"ERROR: [InjectorBackend.setangle] {e}"
            self.debug_message.emit(msg)
            self.tip_message.emit("Angle set failed.")
            self.angle_done.emit(False)
    
    @Slot(float, float, float)
    def move_relative(self, x: float, y: float, z: float):
        """Linear relative movement - Non-blocking."""
        if not self.axes:
            self.debug_message.emit("ERROR: [InjectorBackend.move_relative] No axes found.")
            self.move_done.emit(False)
            return
        
        if self._active_command:
            self.tip_message.emit("Injector BUSY.")
            return

        velocity = session_globals.get_setting("DEFAULT_VELOCITY", 5.0)
        
        if self._check_range(x, y, z):
            try:
                self._active_command = "MOVE"
                stream = self.device.streams.get_stream(1)
                stream.setup_live(1, 2, 3)
                stream.set_max_speed(velocity, Units.VELOCITY_MILLIMETRES_PER_SECOND)
                
                stream.line_relative(
                    Measurement(x, Units.LENGTH_MILLIMETRES),
                    Measurement(y, Units.LENGTH_MILLIMETRES),
                    Measurement(z, Units.LENGTH_MILLIMETRES),
                )
                # Note: No while loop here!
            except Exception as e:
                self._active_command = None
                msg = f"ERROR: [InjectorBackend.move_relative] {e}"
                self.debug_message.emit(msg)
                self.tip_message.emit("Movement failed.")
                self.move_done.emit(False)
        else:
            self.tip_message.emit("Move Out of Range.")
            self.debug_message.emit(f"ERROR: [InjectorBackend.move_relative] Relative move ({x}, {y}, {z}) exceeds limits.")
            self.move_done.emit(False)

    @Slot(float)
    def move_forward(self, step: float):
        """Moves forward along needle angle."""
        angle_deg = session_globals.get_setting("INJECT_ANGLE", 30.0)
        angle_rad = math.radians(angle_deg)
        dx = step * math.cos(angle_rad)
        dz = step * math.sin(angle_rad)
        self.move_relative(dx, 0, dz)

    @Slot()
    def poll_positions(self):
        """Callback for periodic status monitoring / Non-blocking completion checking."""
        if not self.axes: return
            
        try:
            # 1. Update positions (always runs, never blocked)
            positions = {}
            for name, axis in self.axes.items():
                unit = Units.ANGLE_DEGREES if name == 'Rz' else Units.LENGTH_MILLIMETRES
                positions[name] = axis.get_position(unit)
            
            self._current_pos = positions
            
            # 2. Check for task completion
            is_busy = self.device.all_axes.is_busy()
            
            # 发送汇总状态包
            status_packet = {
                "pos": positions,
                "is_busy": is_busy,
                "active_command": self._active_command
            }
            self.position_updated.emit(status_packet)

            # 3. Transition from Busy -> Not Busy while a command is active
            if self._active_command and not is_busy:
                # Task just finished
                finished_task = self._active_command
                self._active_command = None # Reset flag
                
                if finished_task == "HOME":
                    self.tip_message.emit("Home complete.")
                    self.home_done.emit(True)
                elif finished_task == "ANGLE":
                    self.tip_message.emit("Angle set.")
                    self.angle_done.emit(True)
                elif finished_task == "MOVE":
                    # Post-move stream cleanup if necessary
                    try:
                        stream = self.device.streams.get_stream(1)
                        stream.disable()
                    except: pass
                    self.move_done.emit(True)
            
            self._last_busy_state = is_busy

        except Exception as e:
            # Silence polling errors but log critical ones to debug
            pass

    def _check_range(self, dx: float, dy: float, dz: float) -> bool:
        """Internal bounds checking using internal position cache."""
        new_x = self._current_pos.get('X', 0) + dx
        new_y = self._current_pos.get('Y', 0) + dy
        new_z = self._current_pos.get('Z', 0) + dz
        
        limit_x = session_globals.get_setting("LIMIT_X", 100.0)
        limit_y = session_globals.get_setting("LIMIT_Y", 50.0)
        limit_z = session_globals.get_setting("LIMIT_Z", 150.0)
        
        return (0 <= new_x <= limit_x) and (0 <= new_y <= limit_y) and (0 <= new_z <= limit_z)
