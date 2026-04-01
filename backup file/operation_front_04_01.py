import sys
import cv2
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QApplication, QFileDialog, QDialog, QPushButton, QCheckBox, QSlider, QLabel
from PySide6.QtCore import QTimer, Qt, Slot, Signal
from PySide6.QtGui import QImage, QPixmap
from remake.ui.ui import Ui_ControlForm
from remake.connection_front import ConnectionDialog
from remake.visualization import Visualizer3D
from remake.logger import logger
import json
import os
import datetime


class VisualControl(QWidget):
    """
    Left panel UI inside the Visualization Group Box.
    Provides controls for camera reset, axis visibility, sphere size and position text.
    """
    reset_view_clicked = Signal()
    front_view_clicked = Signal()
    top_view_clicked = Signal()
    toggle_axes_clicked = Signal(bool)
    sphere_scale_changed = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            """
            QWidget {
                font-family: "Segoe UI", "Arial";
                font-size: 13px;
                background: white;
            }
            QPushButton {
                padding: 4px 8px;
                border-radius: 4px;
                border: 1px solid #ccc;
                background: #fdfdfd;
            }
            QPushButton:hover { background: #f0f7ff; border-color: #2196F3; }
            """
        )

        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(10)
        self.layout.setContentsMargins(5, 5, 5, 5)

        self.btn_reset_view = QPushButton("Reset Camera (30°)")
        self.btn_reset_view.clicked.connect(self.reset_view_clicked.emit)
        self.layout.addWidget(self.btn_reset_view)

        self.btn_front_view = QPushButton("Front View")
        self.btn_front_view.clicked.connect(self.front_view_clicked.emit)
        self.layout.addWidget(self.btn_front_view)

        self.btn_top_view = QPushButton("Top View")
        self.btn_top_view.clicked.connect(self.top_view_clicked.emit)
        self.layout.addWidget(self.btn_top_view)

        self.check_axes = QCheckBox("Show Axes")
        self.check_axes.setChecked(True)
        self.check_axes.toggled.connect(self.toggle_axes_clicked.emit)
        self.layout.addWidget(self.check_axes)

        self.layout.addWidget(QLabel("Sphere Radius (cm):"))
        self.slider_sphere = QSlider(Qt.Horizontal)
        self.slider_sphere.setMinimum(1)
        self.slider_sphere.setMaximum(50)
        self.slider_sphere.setValue(5)
        self.slider_sphere.valueChanged.connect(self.on_slider_changed)
        self.layout.addWidget(self.slider_sphere)

        self.label_val = QLabel("0.5 cm")
        self.layout.addWidget(self.label_val)

        self.layout.addStretch()

        self.pos_title = QLabel("Robot Position")
        self.pos_title.setStyleSheet("font-size: 13px; font-weight: 600; color: #555;")
        self.label_pos_injector = QLabel("Inj: (0.0, 0.0, 0.0)")
        self.label_pos_injector.setStyleSheet("font-size: 13px; color: #333;")
        self.label_pos_probe = QLabel("Prb: (0.0, 0.0, 0.0)")
        self.label_pos_probe.setStyleSheet("font-size: 13px; color: #333;")

        self.pos_layout = QVBoxLayout()
        self.pos_layout.setSpacing(4)
        self.pos_layout.setContentsMargins(0, 0, 0, 0)
        self.pos_layout.addWidget(self.pos_title)
        self.pos_layout.addWidget(self.label_pos_injector)
        self.pos_layout.addWidget(self.label_pos_probe)
        self.layout.addLayout(self.pos_layout)

    def on_slider_changed(self, value):
        radius = value / 10.0
        self.label_val.setText(f"{radius:.1f} cm")
        self.sphere_scale_changed.emit(radius)

class RobotFrontEnd(QWidget):
    """
    Main Qt application UI front-end using Ui_ControlForm from ui.py.
    The primary UI handles showing data and only communicates with control.py.
    """
    reconnect_requested = Signal()

    def __init__(self, injector_control, config_data=None):
        super().__init__()
        self.control = injector_control
        self.config_data = config_data or {}
        self.ui = Ui_ControlForm()
        self.ui.setupUi(self)
        self.setWindowTitle("Embryo Injection Controller (Operation)")

        # Initialize Visualization Components
        self._init_visualization()

        # Initialize logging connection
        self._init_logging()

        # Set fixed size and force window state
        # Using a fixed size can sometimes conflict with layout stretching on different DPIs.
        # We ensure the minimum size is set to the intended 1920x1200.
        self.setMinimumSize(1920, 1200)

        # State tracking
        self.is_running = True
        self.cap = None
        self.is_session_registered = False

        # 1. UI Initialization
        self._init_ui_states()
        self._setup_connections()

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
        
        # Default checkbox states: TIP and INFO by default
        self.ui.check_log_info.setChecked(True)
        self.ui.check_log_tip.setChecked(True)
        self.ui.check_log_error.setChecked(True)
        self.ui.check_log_debug.setChecked(False)
        self.ui.check_show_details.setChecked(False)

        # Flag to toggle between full details (Time/Source/Level) and compact (Message only)
        # show_full_logs is now handled by UI checkbox check_show_details
        
        # Trigger initial display refresh
        self._refresh_terminal_display()

    def _setup_connections(self):
        """Connect UI signals to mediator methods."""
        # Listen for global status updates from Control
        self.control.status_updated.connect(self._on_status_broadcast)

        # Mode buttons
        self.ui.btn_mode_safe.clicked.connect(self._on_mode_safe)
        self.ui.btn_mode_work.clicked.connect(self._on_mode_work)
        
        # Action buttons
        self.ui.btn_get_close.clicked.connect(self._on_action_get_close)
        self.ui.btn_select_inject_pos.clicked.connect(self._on_action_select_pos)
        self.ui.btn_do_injection.clicked.connect(self._on_action_inject)
        self.ui.btn_stop_main.clicked.connect(self._on_stop_main)
        self.ui.btn_reconnect.clicked.connect(self._on_reconnect)
        
        # Terminal filter logic
        self.ui.check_log_tip.stateChanged.connect(self._refresh_terminal_display)
        self.ui.check_log_info.stateChanged.connect(self._refresh_terminal_display)
        self.ui.check_log_error.stateChanged.connect(self._refresh_terminal_display)
        self.ui.check_log_debug.stateChanged.connect(self._refresh_terminal_display)
        self.ui.check_show_details.stateChanged.connect(self._refresh_terminal_display)
        self.ui.btn_clear_log.clicked.connect(self._on_clear_logs)

    def _init_visualization(self):
        """Setup the 3D visualization area with controls and renderer."""
        # 1. Provide a layout for the container widget if it doesn't have one
        if not self.ui.widget_open3d.layout():
            layout = QHBoxLayout(self.ui.widget_open3d)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(5)
            self.ui.widget_open3d.setLayout(layout)
        
        # 2. Create Left Control Panel
        self.viz_control = VisualControl(self.ui.widget_open3d)
        self.viz_control.setFixedWidth(180)
        self.ui.widget_open3d.layout().addWidget(self.viz_control)

        # 3. Create Right Renderer
        self.viz_renderer = Visualizer3D(self.ui.widget_open3d)
        self.ui.widget_open3d.layout().addWidget(self.viz_renderer)

        # 4. Connect Signals for internal sync
        self.viz_control.reset_view_clicked.connect(self.viz_renderer.reset_view)
        self.viz_control.front_view_clicked.connect(self.viz_renderer.set_front_view)
        self.viz_control.top_view_clicked.connect(self.viz_renderer.set_top_view)
        self.viz_control.toggle_axes_clicked.connect(self.viz_renderer.toggle_axes)
        self.viz_control.sphere_scale_changed.connect(self.viz_renderer.update_sphere_size)

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
        if not self.is_running:
            return

        status = self.control.get_status()

        inj_p = status["injector"]["pos"]
        prb_p = status["probe"]["pos"]
        
        # Access through viz_control where they are now located
        pos_str_inj = f"Inj: ({inj_p.get('X',0):.1f}, {inj_p.get('Y',0):.1f}, {inj_p.get('Z',0):.1f})"
        pos_str_prb = f"Prb: ({prb_p.get('X',0):.1f}, {prb_p.get('Y',0):.1f}, {prb_p.get('Z',0):.1f})"
        
        self.viz_control.label_pos_injector.setText(pos_str_inj)
        self.viz_control.label_pos_probe.setText(pos_str_prb)

    def _update_status_label(self, label, connected):
        if connected:
            label.setText("Online")
            label.setStyleSheet("color: #43a047; font-weight: bold;")
        else:
            label.setText("Offline")
            label.setStyleSheet("color: #e53935; font-weight: bold;")

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

    @Slot()
    def _on_reconnect(self):
        """Opens the connection window as a modal overlay above the operation console."""
        # Create the connection dialog with this widget as the parent
        conn_dialog = ConnectionDialog(self.control, self.config_data, parent=self)
        
        # Set window flags to ensure it stays on top and behaves like a popup
        conn_dialog.setWindowModality(Qt.WindowModal) # Blocks interaction with parent while open
        
        # Optional: Center it on the screen/parent if it's not already
        # conn_dialog.exec() is blocking, which is fine as it's a modal dialog
        if conn_dialog.exec() == QDialog.Accepted:
            logger.info("Connection dialog accepted, continuing operation.")
        else:
            logger.info("Connection dialog closed without changes.")

    @Slot(dict)
    def _on_status_broadcast(self, status):
        """Handle real-time status updates pushed from Control."""
        # This could supplement OR replace the 10Hz timer polling
        pass

    def closeEvent(self, event):
        if not self.is_running:
            event.accept()
            return

        self.is_running = False

        if hasattr(self, "update_timer") and self.update_timer.isActive():
            self.update_timer.stop()

        try:
            self.control.status_updated.disconnect(self._on_status_broadcast)
        except (RuntimeError, TypeError):
            pass

        try:
            logger.new_log_signal.disconnect(self._on_new_log)
        except (RuntimeError, TypeError):
            pass

        if hasattr(self, "viz_renderer") and self.viz_renderer is not None:
            self.viz_renderer.close()

        self.control.shutdown()
        event.accept()
