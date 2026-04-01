# Ensure project root (parent of 'remake') is on sys.path so "import remake..." works
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from remake.injector_backend import InjectorBackend

from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QLineEdit, QTextEdit)
from PySide6.QtCore import Qt, Slot, QThread, QMetaObject, Q_ARG

class RobotTestGUI(QWidget):
    def __init__(self, backend: InjectorBackend):
        super().__init__()
        self.backend = backend
        self.is_busy = False
        self.init_ui()
        
        # Connect signals
        self.backend.home_done.connect(self.on_op_done)
        self.backend.angle_done.connect(self.on_op_done)
        self.backend.move_done.connect(self.on_op_done)
        self.backend.tip_message.connect(self.log_message)
        self.backend.debug_message.connect(self.log_debug)
        self.backend.position_updated.connect(self.update_pos)

    def init_ui(self):
        self.setWindowTitle("Zaber Controller Test Tool")
        self.setMinimumSize(400, 500)
        
        layout = QVBoxLayout()

        # Connection Group
        conn_layout = QHBoxLayout()
        self.btn_connect = QPushButton("Connect (COM3)")
        # Use invokeMethod to ensure connect_zaber runs on the backend thread
        self.btn_connect.clicked.connect(lambda: QMetaObject.invokeMethod(self.backend, "connect_zaber", Qt.QueuedConnection))
        self.btn_disconnect = QPushButton("Disconnect")
        self.btn_disconnect.clicked.connect(lambda: QMetaObject.invokeMethod(self.backend, "disconnect_zaber", Qt.QueuedConnection))
        conn_layout.addWidget(self.btn_connect)
        conn_layout.addWidget(self.btn_disconnect)
        layout.addLayout(conn_layout)

        # Homing/Angle Group
        home_layout = QHBoxLayout()
        self.btn_home = QPushButton("Home XYZ")
        self.btn_safe = QPushButton("Set Safe Ang")
        self.btn_inject = QPushButton("Set Inject Ang")
        # Re-map button clicks to use the new run_command logic
        self.btn_home.clicked.connect(lambda: self.run_command("sethome"))
        self.btn_safe.clicked.connect(lambda: self.run_command("setangle", True))
        self.btn_inject.clicked.connect(lambda: self.run_command("setangle", False))
        home_layout.addWidget(self.btn_home)
        home_layout.addWidget(self.btn_safe)
        home_layout.addWidget(self.btn_inject)
        layout.addLayout(home_layout)

        # Movement Group
        move_layout = QHBoxLayout()
        self.axis_input = QLineEdit("X")
        self.axis_input.setPlaceholderText("X/Y/Z")
        self.dist_input = QLineEdit("10")
        self.dist_input.setPlaceholderText("Dist (mm)")
        self.btn_move = QPushButton("Move Rel")
        self.btn_move.clicked.connect(self.handle_move)
        move_layout.addWidget(self.axis_input)
        move_layout.addWidget(self.dist_input)
        move_layout.addWidget(self.btn_move)
        layout.addLayout(move_layout)

        # Injector Move Group
        inj_layout = QHBoxLayout()
        self.step_input = QLineEdit("5")
        self.btn_forward = QPushButton("Inject Forward")
        # Change to pass the function name and argument separately
        self.btn_forward.clicked.connect(lambda: self.run_command("move_forward", float(self.step_input.text())))
        inj_layout.addWidget(QLabel("Step:"))
        inj_layout.addWidget(self.step_input)
        inj_layout.addWidget(self.btn_forward)
        layout.addLayout(inj_layout)

        # Position/Status Group
        self.status_label = QLabel("Status: Idle")
        self.pos_label = QLabel("Pos: X: 0.00, Y: 0.00, Z: 0.00, Rz: 0.00")
        layout.addWidget(self.status_label)
        layout.addWidget(self.pos_label)

        # Log Window
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        layout.addWidget(QLabel("Operation Log:"))
        layout.addWidget(self.log_area)

        self.setLayout(layout)

    def log_message(self, message):
        self.log_area.append(f"[TIP] {message}")

    def log_debug(self, message):
        self.log_area.append(f"[DEBUG] {message}")

    def update_pos(self, pos):
        self.pos_label.setText(f"Pos: X:{pos.get('X',0):.2f}, Y:{pos.get('Y',0):.2f}, Z:{pos.get('Z',0):.2f}, Rz:{pos.get('Rz',0):.2f}")

    def run_command(self, func_name, *args):
        if self.is_busy:
            self.log_area.append("[ERROR] System BUSY")
            return
        self.is_busy = True
        self.set_ui_enabled(False)
        self.status_label.setText("Status: BUSY")
        
        # Prepare Q_ARG list for invokeMethod
        q_args = [Q_ARG(type(arg), arg) for arg in args]
        
        # Invoke the function by name on the backend's thread
        QMetaObject.invokeMethod(self.backend, func_name, Qt.QueuedConnection, *q_args)

    def handle_move(self):
        axis = self.axis_input.text().upper()
        try:
            val = float(self.dist_input.text())
        except ValueError: return
        
        dx, dy, dz = 0.0, 0.0, 0.0
        if axis == 'X': dx = val
        elif axis == 'Y': dy = val
        elif axis == 'Z': dz = val
        
        self.run_command("move_relative", dx, dy, dz)

    def on_op_done(self, success):
        self.is_busy = False
        self.set_ui_enabled(True)
        self.status_label.setText(f"Status: Done (Success: {success})")
        self.log_area.append(f"[SIGNAL] Done | Success: {success}")

    def set_ui_enabled(self, enabled):
        self.btn_home.setEnabled(enabled)
        self.btn_safe.setEnabled(enabled)
        self.btn_inject.setEnabled(enabled)
        self.btn_move.setEnabled(enabled)
        self.btn_forward.setEnabled(enabled)

def main():
    app = QApplication(sys.argv)
    
    # 1. Create the backend and a QThread
    backend = InjectorBackend(port="COM3")
    worker_thread = QThread()
    
    # 2. Move backend to the thread
    backend.moveToThread(worker_thread)
    
    # 3. Ensure the thread stops when the app closes
    worker_thread.start()
    
    gui = RobotTestGUI(backend)
    gui.show()
    
    exit_code = app.exec()
    worker_thread.quit()
    worker_thread.wait()
    sys.exit(exit_code)

if __name__ == "__main__":
    main()

