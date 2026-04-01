from PySide6.QtWidgets import QDialog
from PySide6.QtCore import QTimer, Signal
from remake.ui.ui_connection import Ui_ConnectionDialog

class ConnectionDialog(QDialog):
    """
    Independent device connection window.
    Closes and returns QDialog.Accepted once all required devices are connected or skipped.
    """
    transition_to_operation_requested = Signal()

    def __init__(self, control, config_data=None, parent=None):
        super().__init__(parent)
        self.control = control
        self.config_data = config_data or {}
        self.ui = Ui_ConnectionDialog()
        self.ui.setupUi(self)
        self.setWindowTitle("Hardware Connection Check")
        
        # Mapping between status keys and UI labels/buttons
        self.status_map = {
            "injector": (self.ui.val_stat_inj, self.ui.btn_retry_inj),
            "probe": (self.ui.val_stat_probe, self.ui.btn_retry_probe),
            "rgbd": (self.ui.val_stat_rgbd, self.ui.btn_retry_rgbd),
            "us": (self.ui.val_stat_us, self.ui.btn_retry_us)
        }

        # Connect retry buttons
        self.ui.btn_retry_inj.clicked.connect(lambda: self.control.reconnect("injector"))
        self.ui.btn_retry_probe.clicked.connect(lambda: self.control.reconnect("probe"))
        self.ui.btn_retry_rgbd.clicked.connect(lambda: self.control.reconnect("rgbd"))
        self.ui.btn_retry_us.clicked.connect(lambda: self.control.reconnect("us"))
        
        # Connect Next button
        self.ui.btn_next.clicked.connect(self._on_next_clicked)

        # Timer to refresh status
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_status)
        self.timer.start(200)

    def update_status(self):
        status = self.control.get_status()
        
        # Count connected devices
        online_count = 0
        for key, (label, btn) in self.status_map.items():
            connected = status.get(key, {}).get("connected", False)
            if connected:
                label.setText("Online")
                label.setStyleSheet("color: #2e7d32; font-weight: bold;")
                online_count += 1
            else:
                label.setText("Offline")
                label.setStyleSheet("color: #e53935; font-weight: bold;")

        # Update button text once all devices are online
        if online_count == len(self.status_map):
            self.ui.btn_next.setText("All Devices Online - Go Next")
            self.ui.btn_next.setStyleSheet("background-color: #2e7d32; color: white; font-weight: bold;")

    def closeEvent(self, event):
        # Stop status refresh timer
        self.timer.stop()
        super().closeEvent(event)

    def _on_next_clicked(self):
        # Emit first so caller can display transition overlay before this dialog closes.
        self.transition_to_operation_requested.emit()
        QTimer.singleShot(0, self.accept)
