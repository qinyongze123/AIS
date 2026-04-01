import os
import datetime
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QComboBox, QTextEdit, 
                             QFileDialog, QMessageBox)
from PySide6.QtCore import Qt
from remake.ui.ui_creation import Ui_ProjectCreationDialog
import json

class ProjectCreationDialog(QDialog):
    """
    Independent project creation/registration window.
    Closes and returns QDialog.Accepted upon successful registration.
    """
    def __init__(self, config_data, parent=None):
        super().__init__(parent)
        self.config_data = config_data
        self.ui = Ui_ProjectCreationDialog()
        self.ui.setupUi(self)
        self.setWindowTitle("Project Registration")
        self.setMinimumWidth(500)
        self.load_defaults()
        self.setup_signals()

    def setup_signals(self):
        self.ui.btn_browse.clicked.connect(self.on_browse)
        self.ui.btn_start.clicked.connect(self.on_register)
        self.ui.btn_delete_op.clicked.connect(self.on_delete_operator)
        self.ui.edit_proj_path.textChanged.connect(self.on_path_changed)

    def load_defaults(self):
        root_path = self.config_data.get("LAST_PROJECT_PATH", os.path.join(os.getcwd(), "projects"))
        proj_name = self.config_data.get("LAST_PROJECT_NAME", "DefaultProject")
        self.ui.edit_proj_path.setText(root_path)
        
        # Populate Project names after setting root path
        self.on_path_changed(root_path)
        self.ui.combo_proj_name.setCurrentText(proj_name)
        
        self.ui.edit_session_name.setText(datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
        
        self.refresh_operator_list()
        self.ui.combo_operator.setCurrentText(self.config_data.get("LAST_OPERATOR", "Admin"))

    def on_path_changed(self, path):
        """When project path changes, list subdirectories in the combo box."""
        self.ui.combo_proj_name.clear()
        if os.path.isdir(path):
            try:
                subdirs = [d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))]
                self.ui.combo_proj_name.addItems(subdirs)
            except Exception:
                pass

    def refresh_operator_list(self):
        self.ui.combo_operator.clear()
        operators = self.config_data.get("OPERATORS", ["Admin"])
        self.ui.combo_operator.addItems(operators)

    def on_delete_operator(self):
        current_op = self.ui.combo_operator.currentText()
        if not current_op:
            return
            
        ops = self.config_data.get("OPERATORS", [])
        if current_op in ops:
            reply = QMessageBox.question(self, 'Confirmation', 
                                       f"Are you sure you want to delete operator '{current_op}'?",
                                       QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

            if reply == QMessageBox.Yes:
                ops.remove(current_op)
                self.config_data["OPERATORS"] = ops
                self._save_config()
                self.refresh_operator_list()

    def _save_config(self):
        """Saves current configuration back to config.json."""
        try:
            config_path = os.path.join(os.path.dirname(__file__), "config.json")
            with open(config_path, "w") as f:
                json.dump(self.config_data, f, indent=4)
        except Exception as e:
            print(f"Failed to save config: {e}")

    def on_browse(self):
        path = QFileDialog.getExistingDirectory(self, "Select Project Root", self.ui.edit_proj_path.text())
        if path:
            self.ui.edit_proj_path.setText(path)

    def on_register(self):
        root_path = self.ui.edit_proj_path.text()
        proj_name = self.ui.combo_proj_name.currentText()
        sess_name = self.ui.edit_session_name.text()
        operator_name = self.ui.combo_operator.currentText()
        
        if not proj_name or not sess_name or not operator_name:
            QMessageBox.critical(self, "Error", "Project, Session and Operator names are required.")
            return

        # Record new operator if it's not in the list
        ops = self.config_data.get("OPERATORS", [])
        if operator_name not in ops:
            ops.append(operator_name)
            self.config_data["OPERATORS"] = ops

        full_path = os.path.join(root_path, proj_name, sess_name)
        try:
            os.makedirs(os.path.join(full_path, "logs"), exist_ok=True)
            os.makedirs(os.path.join(full_path, "images"), exist_ok=True)
            os.makedirs(os.path.join(full_path, "videos"), exist_ok=True)
            
            # Store updated configuration to be used by the main window
            self.result_data = {
                "project_path": full_path,
                "operator": operator_name,
                "config_update": {
                    "LAST_PROJECT_PATH": root_path,
                    "LAST_PROJECT_NAME": proj_name,
                    "LAST_OPERATOR": operator_name,
                    "OPERATORS": ops
                }
            }
            # Save final config update
            for k, v in self.result_data["config_update"].items():
                self.config_data[k] = v
            self._save_config()
            
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create project: {e}")

