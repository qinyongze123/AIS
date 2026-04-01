import os
import datetime
import inspect
from collections import deque
from PySide6.QtCore import QObject, Signal

class SystemLogger(QObject):
    """Core logging system: handles file persistence, memory buffering, and UI signaling."""
    new_log_signal = Signal(str, str, str, str)

    def __init__(self, log_dir="log", max_memory_logs=2000):
        super().__init__()
        self.log_dir = log_dir
        self.max_memory_logs = max_memory_logs
        self.buffer = deque(maxlen=self.max_memory_logs)
        self.is_project_registered = False
        self.total_logs_count = 0
        self._pending_buffer = []  # Logs produced before persistence criteria met
        
        # Determine initial log path
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_path = os.path.join(self.log_dir, f"session_{timestamp}.log")
        
        # Try to load settings from config.json if available
        self._load_config_settings()

    def _load_config_settings(self):
        """Loads MAX_LOGS from config.json if it exists."""
        try:
            config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
            if os.path.exists(config_path):
                import json
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                if "MAX_LOGS" in config:
                    self.max_memory_logs = int(config["MAX_LOGS"])
                    old_logs = list(self.buffer)
                    self.buffer = deque(old_logs, maxlen=self.max_memory_logs)
        except Exception as e:
            print(f"Logger: Failed to load config.json: {e}")

    def set_project_registered(self, registered=True):
        """Enable file persistence once a project is registered."""
        self.is_project_registered = registered
        if registered:
            self._ensure_path_exists()
            self._flush_pending_logs()

    def _ensure_path_exists(self):
        """Ensures the directory for the current log_path exists."""
        try:
            parent_dir = os.path.dirname(self.log_path)
            if parent_dir and not os.path.exists(parent_dir):
                os.makedirs(parent_dir, exist_ok=True)
        except Exception:
            pass

    def _flush_pending_logs(self):
        """Writes logs collected before registration or 10-log limit to disk."""
        if not self._pending_buffer or not self.is_project_registered or self.total_logs_count < 10:
            return
        
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                for line in self._pending_buffer:
                    f.write(line)
            self._pending_buffer.clear()
        except Exception:
            pass

    def update_log_file(self, new_dir):
        """Moves current log file to a new session folder."""
        try:
            old_path = self.log_path
            new_path = os.path.join(new_dir, os.path.basename(old_path))
            self.log_path = new_path
            if self.is_project_registered:
                self._ensure_path_exists()
        except Exception as e:
            self.error(f"Failed to update log file: {e}")

    def clear_buffer(self):
        """Clears the in-memory log buffer for UI refresh."""
        self.buffer.clear()
        self.new_log_signal.emit("INFO", datetime.datetime.now().strftime("%H:%M:%S"), "Logger", "Logs cleared by user.")

    def _log(self, level, message):
        """Internal logic: updates buffer, conditionally writes to file, and emits signal."""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.total_logs_count += 1
        
        source = "Unknown"
        try:
            frames = inspect.stack()
            for frame_info in frames:
                if os.path.abspath(frame_info.filename) != os.path.abspath(__file__):
                    frame = frame_info.frame
                    file_name = os.path.basename(frame_info.filename)
                    class_name = "Global"
                    if "self" in frame.f_locals:
                        class_name = frame.f_locals["self"].__class__.__name__
                    func_name = frame.f_code.co_name
                    source = f"{file_name} -> {class_name}.{func_name}"
                    break
        except Exception:
            pass
        
        log_entry = {
            "level": level.upper(),
            "time": timestamp,
            "src": source,
            "msg": str(message)
        }
        self.buffer.append(log_entry)
        
        formatted_line = f"{timestamp} | {level.upper()} | {source} | {message}\n"
        
        # Check registration and log count requirements for persistence
        if not self.is_project_registered:
            self._pending_buffer.append(formatted_line)
        else:
            if self.total_logs_count < 10:
                self._pending_buffer.append(formatted_line)
            else:
                # Flush pending if this is exactly the 10th or later
                if self._pending_buffer:
                    self._flush_pending_logs()
                
                try:
                    with open(self.log_path, "a", encoding="utf-8") as f:
                        f.write(formatted_line)
                except Exception:
                    self._pending_buffer.append(formatted_line)

        self.new_log_signal.emit(level.upper(), timestamp, source, str(message))


    def debug(self, msg): self._log("DEBUG", msg)
    def info(self, msg):  self._log("INFO", msg)
    def tip(self, msg):   self._log("TIP", msg)
    def error(self, msg): self._log("ERROR", msg)

    def get_buffered_logs(self, allowed_levels=None):
        """Returns filtered logs from the memory buffer."""
        if allowed_levels is None:
            return list(self.buffer)
        
        allowed_levels = [lvl.upper() for lvl in allowed_levels]
        return [entry for entry in self.buffer if entry["level"] in allowed_levels]

# Global instance for project-wide access
# Initialized here, but max_memory_logs can be updated later from config if needed.
logger = SystemLogger()
