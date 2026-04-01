import sys
import cv2
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QApplication, QFileDialog
from PySide6.QtCore import QTimer, Qt, Slot
from PySide6.QtGui import QImage, QPixmap
from remake.ui.ui import Ui_ControlForm
from remake.logger import logger
import json
import os
import datetime

class RobotFrontEnd(QWidget):
    """
    Main Qt application UI front-end using Ui_ControlForm from ui.py.
    The primary UI handles showing data and only communicates with control.py.
    """
    def __init__(self, injector_control):
        super().__init__()
        self.control = injector_control
        self.ui = Ui_ControlForm()
        self.ui.setupUi(self)
        self.setWindowTitle("Embryo Injection Controller (Remake)")

        # Load config for log limits
        self._load_config()

        # Initialize logging connection
        self._init_logging()

        # Set fixed size and force window state
        # Using a fixed size can sometimes conflict with layout stretching on different DPIs.
        # We ensure the minimum size is set to the intended 1920x1200.
        self.setMinimumSize(1920, 1200)
        self.showMaximized()

        # State tracking
        self.is_running = True
        self.cap = None
        self.is_session_registered = False

        # 1. UI Initialization
        self._init_ui_states()
        self._setup_connections()

        # Set default tab to Create (index 0)
        if hasattr(self.ui, "tab_main_control"):
            self.ui.tab_main_control.setCurrentIndex(0)

        # Set scaledContents to true for the video label to allow the image to scale 
        # with the layout WITHOUT triggering a resize event loop.
        self.ui.label_us_video.setScaledContents(True)

        # 2. Main Update Timer
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._on_tick)
        self.update_timer.start(100)  # fast status polling

        # 3. Video Stream Initialization (Ultrasound)
        self._init_video_stream()

    def _init_ui_states(self):
        # Set default values from control status
        self.ui.btn_mode_safe.setChecked(True)
        self.ui.widget_operation.setVisible(False)
        self.ui.label_safe_hint.setVisible(True)
        
        self.ui.val_stat_inj.setText("Disconnected")
        self.ui.val_stat_probe.setText("Disconnected")
        
        # Default checkbox states: TIP and INFO by default
        self.ui.check_log_info.setChecked(True)
        self.ui.check_log_tip.setChecked(True)
        self.ui.check_log_error.setChecked(True)
        self.ui.check_log_debug.setChecked(False)
        self.ui.check_show_details.setChecked(False)

        # Flag to toggle between full details (Time/Source/Level) and compact (Message only)
        # show_full_logs is now handled by UI checkbox check_show_details
        
        # Load project context
        self._load_project_context()
        
        # Trigger initial display refresh
        self._refresh_terminal_display()

    def _load_config(self):
        """Loads configuration for UI limits and project context."""
        self.max_ui_logs = 500 # Default fallback
        self.config_data = {}
        try:
            config_path = os.path.join(os.path.dirname(__file__), "config.json")
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    self.config_data = json.load(f)
                    self.max_ui_logs = self.config_data.get("MAX_LOGS", 500)
            else:
                self.config_data = {"MAX_LOGS": 500, "OPERATORS": ["Admin"]}
        except Exception as e:
            print(f"Error loading config: {e}")

    def _save_config(self):
        """Saves current configuration back to disk."""
        try:
            config_path = os.path.join(os.path.dirname(__file__), "config.json")
            with open(config_path, "w") as f:
                json.dump(self.config_data, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save config: {e}")

    def _load_project_context(self):
        """Initializes the project management fields with saved or default values."""
        # 1. Project Path & Name
        last_path = self.config_data.get("LAST_PROJECT_PATH", os.path.join(os.getcwd(), "projects"))
        last_name = self.config_data.get("LAST_PROJECT_NAME", "DefaultProject")
        self.ui.edit_proj_path.setText(last_path)
        self.ui.edit_proj_name.setText(last_name)

        # 2. Session Name (Default: Date)
        default_session = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.ui.edit_session_name.setText(default_session)

        # 3. Operators
        operators = self.config_data.get("OPERATORS", ["Admin"])
        self.ui.combo_operator.clear()
        self.ui.combo_operator.addItems(operators)
        last_op = self.config_data.get("LAST_OPERATOR", "Admin")
        self.ui.combo_operator.setCurrentText(last_op)

    def _setup_connections(self):
        """Connect UI signals to mediator methods."""
        # Listen for global status updates from Control
        self.control.status_updated.connect(self._on_status_broadcast)

        # Project tab
        self.ui.btn_browse_proj.clicked.connect(self._on_browse_project)
        self.ui.btn_create_session.clicked.connect(self._on_register_session)
        self.ui.btn_del_operator.clicked.connect(self._on_delete_operator)
        
        # Mode buttons
        self.ui.btn_mode_safe.clicked.connect(self._on_mode_safe)
        self.ui.btn_mode_work.clicked.connect(self._on_mode_work)
        
        # Action buttons
        self.ui.btn_get_close.clicked.connect(self._on_action_get_close)
        self.ui.btn_select_inject_pos.clicked.connect(self._on_action_select_pos)
        self.ui.btn_do_injection.clicked.connect(self._on_action_inject)
        self.ui.btn_stop_main.clicked.connect(self._on_stop_main)
        
        # Connection retry buttons
        self.ui.pushButton.clicked.connect(lambda: self.control.reconnect("injector"))
        self.ui.pushButton_2.clicked.connect(lambda: self.control.reconnect("probe"))
        self.ui.pushButton_3.clicked.connect(lambda: self.control.reconnect("rgbd"))
        self.ui.pushButton_4.clicked.connect(lambda: self.control.reconnect("us"))

        # Terminal filter logic
        self.ui.check_log_tip.stateChanged.connect(self._refresh_terminal_display)
        self.ui.check_log_info.stateChanged.connect(self._refresh_terminal_display)
        self.ui.check_log_error.stateChanged.connect(self._refresh_terminal_display)
        self.ui.check_log_debug.stateChanged.connect(self._refresh_terminal_display)
        self.ui.check_show_details.stateChanged.connect(self._refresh_terminal_display)
        self.ui.btn_clear_log.clicked.connect(self._on_clear_logs)

    def _init_logging(self):
        """Hook into SystemLogger to display logs in UI."""
        logger.new_log_signal.connect(self._on_new_log)

    def _on_new_log(self, level, timestamp, source, message):
        """Slot to receive log records from logger.py via signal."""
        # Use full refresh to ensure data consistency with Logger's internal buffer
        self._refresh_terminal_display()

    @Slot()
    def _on_clear_logs(self):
        """Clears the logger buffer and refreshes the display."""
        logger.clear_buffer()
        self._refresh_terminal_display()

    @Slot()
    def _refresh_terminal_display(self):
        """Reconstructs the terminal text box from the logger's memory buffer."""
        allowed_levels = []
        if self.ui.check_log_tip.isChecked(): allowed_levels.append("TIP")
        if self.ui.check_log_info.isChecked(): allowed_levels.append("INFO")
        if self.ui.check_log_error.isChecked(): allowed_levels.append("ERROR")
        if self.ui.check_log_debug.isChecked(): allowed_levels.append("DEBUG")
        
        # Get logs from logger's deque buffer
        logs = logger.get_buffered_logs(allowed_levels)
        
        show_details = self.ui.check_show_details.isChecked()
        
        # Build the HTML content
        html_lines = []
        for log in logs:
            level = log["level"]
            timestamp = log["time"]
            source = log["src"]
            msg = log["msg"]
            
            # Color Mapping: Error is RED, TIP is DARK GREEN, others are BLACK
            if level == "ERROR":
                color = "#e53935"
            elif level == "TIP":
                color = "#2e7d32" # Dark Green
            else:
                color = "#333333"
            
            if show_details:
                display_text = f"[{timestamp}] [{level}] [{source}]: {msg}"
            else:
                display_text = f"[{level}] {msg}"
                
            html_lines.append(f"<div style=\"color:{color}; font-family: 'Consolas';\">{display_text}</div>")
            
        # Efficiently update the terminal text
        # Using setHtml for a full refresh can be slow if logs are huge, but logger.buffer is limited to 2000.
        # This approach ensures that toggling "Details" updates all existing logs instantly.
        self.ui.text_terminal.setHtml("".join(html_lines))
        
        # Auto-scroll to bottom
        self.ui.text_terminal.verticalScrollBar().setValue(
            self.ui.text_terminal.verticalScrollBar().maximum()
        )

    def _init_video_stream(self):
        """Initialize OpenCV or camera backend for ultrasound."""
        pass 

    def _on_tick(self):
        """Main refresh loop (10Hz). Updates status labels and positions."""
        status = self.control.get_status()
        self._update_status_label(self.ui.val_stat_inj, status["injector"]["connected"])
        self._update_status_label(self.ui.val_stat_probe, status["probe"]["connected"])
        self._update_status_label(self.ui.val_stat_rgbd, status["rgbd"]["connected"])
        self._update_status_label(self.ui.val_stat_us, status["us"]["connected"])

        inj_p = status["injector"]["pos"]
        prb_p = status["probe"]["pos"]
        # Use keys 'X', 'Y', 'Z' instead of indices 0, 1, 2
        self.ui.label_pos_injector.setText(f"Inj: ({inj_p.get('X',0):.1f}, {inj_p.get('Y',0):.1f}, {inj_p.get('Z',0):.1f})")
        self.ui.label_pos_probe.setText(f"Prb: ({prb_p.get('X',0):.1f}, {prb_p.get('Y',0):.1f}, {prb_p.get('Z',0):.1f})")

    def _update_status_label(self, label, connected):
        if connected:
            label.setText("Online")
            label.setStyleSheet("color: #43a047; font-weight: bold;")
        else:
            label.setText("Offline")
            label.setStyleSheet("color: #e53935; font-weight: bold;")

    @Slot()
    def _on_browse_project(self):
        path = QFileDialog.getExistingDirectory(self, "Select Project Directory", self.ui.edit_proj_path.text())
        if path:
            self.ui.edit_proj_path.setText(path)

    @Slot()
    def _on_delete_operator(self):
        """Removes the currently selected operator from the list and config."""
        current_op = self.ui.combo_operator.currentText()
        if not current_op:
            return
        
        ops = self.config_data.get("OPERATORS", [])
        if current_op in ops:
            ops.remove(current_op)
            self.config_data["OPERATORS"] = ops
            
            # Update UI
            self.ui.combo_operator.clear()
            self.ui.combo_operator.addItems(ops)
            
            if ops:
                self.ui.combo_operator.setCurrentIndex(0)
            else:
                self.ui.combo_operator.setCurrentText("")
                
            self._save_config()
            logger.info(f"Operator '{current_op}' removed.")

    @Slot()
    def _on_register_session(self):
        """Handles project folder creation and session initialization."""
        if self.is_session_registered:
            logger.tip("Session already registered. Cannot create again in the same run.")
            return

        root_path = self.ui.edit_proj_path.text()
        proj_name = self.ui.edit_proj_name.text()
        sess_name = self.ui.edit_session_name.text()
        operator = self.ui.combo_operator.currentText()
        notes = self.ui.edit_note.toPlainText()

        if not proj_name or not sess_name:
            logger.error("Project and Record names cannot be empty!")
            return

        full_path = os.path.join(root_path, proj_name, sess_name)
        try:
            os.makedirs(full_path, exist_ok=True)
            os.makedirs(os.path.join(full_path, "logs"), exist_ok=True)
            os.makedirs(os.path.join(full_path, "images"), exist_ok=True)
            os.makedirs(os.path.join(full_path, "videos"), exist_ok=True)

            info_file = os.path.join(full_path, "info.txt")
            with open(info_file, "w", encoding="utf-8") as f:
                f.write(f"Project: {proj_name}\nSession: {sess_name}\nOperator: {operator}\n")
                f.write(f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Notes:\n{notes}\n")

            log_folder = os.path.join(full_path, "logs")
            logger.update_log_file(log_folder)
            
            # Notify logger that project is now registered to enable persistence
            logger.set_project_registered(True)
            self.is_session_registered = True
            
            logger.info(f"Record path created and session initialized: {full_path}")
            logger.tip(f"Session '{sess_name}' registered successfully.")

            self.config_data["LAST_PROJECT_PATH"] = root_path
            self.config_data["LAST_PROJECT_NAME"] = proj_name
            self.config_data["LAST_OPERATOR"] = operator
            ops = self.config_data.get("OPERATORS", ["Admin"])
            if operator not in ops:
                ops.append(operator)
                self.config_data["OPERATORS"] = ops
            self._save_config()

        except Exception as e:
            logger.error(f"Failed to create session folder: {e}")

    @Slot()
    def _on_mode_safe(self):
        self.ui.btn_mode_work.setChecked(False)
        self.ui.btn_mode_safe.setChecked(True)
        # Hide operation buttons and show hint label
        self.ui.widget_operation.setVisible(False)
        self.ui.label_safe_hint.setVisible(True)
        self.control.set_mode("safe")

    @Slot()
    def _on_mode_work(self):
        self.ui.btn_mode_safe.setChecked(False)
        self.ui.btn_mode_work.setChecked(True)
        # Show operation buttons and hide hint label
        self.ui.widget_operation.setVisible(True)
        self.ui.label_safe_hint.setVisible(False)
        self.control.set_mode("work")

    @Slot()
    def _on_action_get_close(self):
        self.control.execute_step("get_close")

    @Slot()
    def _on_action_select_pos(self):
        self.control.execute_step("select_pos")

    @Slot()
    def _on_action_inject(self):
        self.control.execute_step("inject")

    @Slot()
    def _on_stop_main(self):
        self.control.stop_all()
        logger.error("EMERGENCY STOP PRESSED")

    @Slot(dict)
    def _on_status_broadcast(self, status):
        """Handle real-time status updates pushed from Control."""
        # This could supplement OR replace the 10Hz timer polling
        pass

    def closeEvent(self, event):
        self.is_running = False
        self._save_config()
        self.control.shutdown()
        event.accept()
