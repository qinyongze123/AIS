import sys
import os

# Ensure the project root is in sys.path so 'remake' can be imported when run directly
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PySide6.QtWidgets import QApplication, QDialog, QWidget, QLabel, QVBoxLayout
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import QThread, Qt, QTimer, QEventLoop

# Remake core modules
from remake.creation_front import ProjectCreationDialog
from remake.connection_front import ConnectionDialog
from remake.operation_front import RobotFrontEnd
from remake.control import Control
from remake.probe_backend import ProbeBackend
from remake.injector_backend import InjectorBackend
from remake.globals import session_globals


class LoadingOverlay(QWidget):
    """Fullscreen transition overlay to hide native renderer startup artifacts."""

    def __init__(self, message, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setStyleSheet("background-color: #eef1f4;")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(14)
        root.setAlignment(Qt.AlignCenter)

        icon_label = QLabel()
        icon_label.setAlignment(Qt.AlignCenter)
        overlay_icon_path = os.path.join(current_dir, "icon", "mouse_holding_needle.png")
        if os.path.exists(overlay_icon_path):
            overlay_pixmap = QPixmap(overlay_icon_path)
            if not overlay_pixmap.isNull():
                icon_label.setPixmap(
                    overlay_pixmap.scaled(
                        240,
                        240,
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation,
                    )
                )
        root.addWidget(icon_label)

        label = QLabel(message)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet(
            "color: #4b5563;"
            "font-size: 22px;"
            "font-weight: 600;"
            "padding: 12px 20px;"
            "background: transparent;"
        )
        root.addWidget(label)

def main():
    """
    Main entry point for the remake project.
    Now includes standalone onboarding windows before opening the main operation UI.
    """
    app = QApplication(sys.argv)
    icon_path = os.path.join(current_dir, "icon", "mouse_holding_needle.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # 1. Configuration/Settings
    session_globals.load_from_disk()
    config_data = {} # Assuming session_globals or separate config is available.
    config_path = os.path.join(current_dir, "config.json")
    if os.path.exists(config_path):
        import json
        with open(config_path, "r") as f:
            config_data = json.load(f)

    # --- Onboarding Step 1: Project Creation Window ---
    login_dialog = ProjectCreationDialog(config_data)
    if login_dialog.exec() != QDialog.Accepted:
        sys.exit(0) # User cancelled at start
    
    # Apply context to session or config
    project_results = getattr(login_dialog, 'result_data', {})
    # Update config.json if needed
    if "config_update" in project_results:
        config_data.update(project_results["config_update"])
        with open(config_path, "w") as f:
            json.dump(config_data, f, indent=4)

    # 2. Service Layer (Backend Threads)
    # ... (Threads same as before)
    # Injector Backend Thread
    injector_thread = QThread()
    injector_thread.setObjectName("InjectorThread")
    injector_backend = InjectorBackend()
    injector_backend.moveToThread(injector_thread)
    injector_thread.start()

    # Probe Backend Thread
    probe_thread = QThread()
    probe_thread.setObjectName("ProbeThread")
    probe_backend = ProbeBackend()
    probe_backend.moveToThread(probe_thread)
    probe_thread.start()

    # 3. Mediator Layer (Control - Running in Main Thread)
    robot_control = Control()

    # 5. Interaction Layer (Front End)
    exit_code = 0
    while True:
        # --- Onboarding Step 2: Connection Window ---
        # Passing mediator 'robot_control' and 'config_data'
        conn_dialog = ConnectionDialog(robot_control, config_data)
        overlay = LoadingOverlay("Preparing Operation Console...")

        def show_transition_overlay():
            overlay.showFullScreen()
            overlay.raise_()
            overlay.activateWindow()
            app.processEvents()

        conn_dialog.transition_to_operation_requested.connect(show_transition_overlay)
        if conn_dialog.exec() != QDialog.Accepted:
            overlay.close()
            break # Exit if cancelled or closed

        # If transition signal did not run for any reason, ensure overlay is visible now.
        if not overlay.isVisible():
            show_transition_overlay()

        window = RobotFrontEnd(robot_control, config_data)
        window.set_startup_updates_frozen(True)

        wait_loop = QEventLoop()
        ready_state = {"ready": False}

        def on_visual_ready():
            ready_state["ready"] = True
            wait_loop.quit()

        def on_timeout():
            wait_loop.quit()

        window.visualization_ready.connect(on_visual_ready)
        QTimer.singleShot(1200, on_timeout)
        wait_loop.exec()

        if not ready_state["ready"]:
            window.set_visualization_pending_hint(True)
        else:
            window.set_visualization_pending_hint(False)
        
        # In this new mode, we no longer need the reconnection loop in main()
        # because the dialog is launched and accepted within RobotFrontEnd
        window.showMaximized()
        window.set_startup_updates_frozen(False)
        app.processEvents()
        settle_loop = QEventLoop()
        QTimer.singleShot(120, settle_loop.quit)
        settle_loop.exec()
        overlay.close()
        overlay.deleteLater()

        # Run this window instance
        exit_code = app.exec()
        
        # In this updated model, Reconnect is just a dialog popup, it doesn't close 
        # the main window and doesn't re-loop. We only loop if we want to.
        # But we already have the window open. Let's just break for now.
        break
        
    # 5. Clean Exit
    # Graceful shutdown of threads
    injector_thread.quit()
    injector_thread.wait()
    probe_thread.quit()
    probe_thread.wait()
    
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
