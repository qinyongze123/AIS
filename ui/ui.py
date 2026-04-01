# -*- coding: utf-8 -*-

from PySide6.QtCore import (QCoreApplication, QMetaObject, QSize, Qt)
from PySide6.QtGui import (QImage, QPixmap)
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDoubleSpinBox,
    QGridLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QSizePolicy, QSpacerItem,
    QTabWidget, QTextEdit, QVBoxLayout, QWidget, QFileDialog)

class Ui_ControlForm(object):
    def setupUi(self, ControlForm):
        if not ControlForm.objectName():
            ControlForm.setObjectName(u"ControlForm")
        ControlForm.setWindowModality(Qt.WindowModality.NonModal)
        ControlForm.resize(1920, 1200)
        ControlForm.setStyleSheet(u"QWidget { font-family: \"Segoe UI\", \"Arial\"; font-size: 13px; color: #333; }\n"
"QGroupBox { font-weight: bold; border: 1px solid #dcdcdc; border-radius: 6px; margin-top: 12px; padding-top: 10px; }\n"
"QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #555; }\n"
"QPushButton { padding: 6px 12px; border-radius: 4px; border: 1px solid #ccc; background: #fdfdfd; }\n"
"QPushButton:hover { background: #f0f7ff; border-color: #2196F3; }\n"
"QPushButton:pressed { background: #e0efff; }\n"
"QComboBox, QLineEdit, QDoubleSpinBox { padding: 4px; border: 1px solid #ccc; border-radius: 4px; background: white; }\n"
"QComboBox:focus, QLineEdit:focus { border-color: #2196F3; }")
        
        self.mainLayout = QHBoxLayout(ControlForm)
        self.mainLayout.setSpacing(15)
        self.mainLayout.setContentsMargins(15, 15, 15, 15)
        
        self.leftPanel = QVBoxLayout()
        self.leftPanel.setSpacing(15)
        
        # --- Mode Control Group ---
        self.group_mode = QGroupBox("Device Mode & Operation")
        self.modeVBox = QVBoxLayout(self.group_mode)
        
        self.modeTopRow = QHBoxLayout()
        self.modeTopRow.setSpacing(8)

        self.modeHBox = QHBoxLayout()
        self.modeHBox.setSpacing(6)
        self.btn_mode_safe = QPushButton("SAFE POSITION")
        self.btn_mode_safe.setCheckable(True)
        self.btn_mode_safe.setChecked(True)
        self.btn_mode_safe.setMinimumHeight(40)
        self.btn_mode_safe.setStyleSheet("QPushButton:checked { background-color: #ef9a9a; font-weight: bold; }")
        self.btn_mode_work = QPushButton("WORK POSITION")
        self.btn_mode_work.setCheckable(True)
        self.btn_mode_work.setMinimumHeight(40)
        self.btn_mode_work.setStyleSheet("QPushButton:checked { background-color: #a5d6a7; font-weight: bold; }")
        self.modeHBox.addWidget(self.btn_mode_safe)
        self.modeHBox.addWidget(self.btn_mode_work)

        self.btn_reconnect = QPushButton("RECONNECT")
        self.btn_reconnect.setMinimumHeight(30)
        self.btn_reconnect.setMaximumWidth(120)
        self.btn_reconnect.setStyleSheet("background-color: #fb8c00; color: white; font-weight: bold;")
        self.btn_stop_main = QPushButton("STOP")
        self.btn_stop_main.setMinimumHeight(30)
        self.btn_stop_main.setMaximumWidth(90)
        self.btn_stop_main.setStyleSheet("background-color: #d32f2f; color: white; font-weight: bold;")

        self.modeTopRow.addLayout(self.modeHBox, 3)
        self.modeTopRow.addStretch(1)
        self.modeTopRow.addWidget(self.btn_reconnect)
        self.modeTopRow.addWidget(self.btn_stop_main)
        self.modeVBox.addLayout(self.modeTopRow)

        # --- Added for SAFE mode hint ---
        self.label_safe_hint = QLabel("Please switch to WORK POSITION to operate robot")
        self.label_safe_hint.setAlignment(Qt.AlignCenter)
        self.label_safe_hint.setStyleSheet("font-size: 16px; color: #757575; font-weight: bold; padding: 20px; border: 1px dashed #ccc; border-radius: 8px; background: #fafafa;")
        self.label_safe_hint.setVisible(True)
        self.modeVBox.addWidget(self.label_safe_hint)

        # Main Operation Widget
        self.widget_operation = QWidget()
        self.opVBox = QVBoxLayout(self.widget_operation)
        self.label_op_hint = QLabel("Select Embryo in 3D View to start")
        self.label_op_hint.setStyleSheet("padding: 10px; background: #e3f2fd; color: #1565c0; font-weight: bold;")
        self.btn_get_close = QPushButton("1. Get Close to Embryo")
        self.btn_select_inject_pos = QPushButton("2. Select Injection Position")
        self.btn_do_injection = QPushButton("3. Execute Injection")
        self.btn_do_injection.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        self.opVBox.addWidget(self.label_op_hint)
        self.opVBox.addWidget(self.btn_get_close)
        self.opVBox.addWidget(self.btn_select_inject_pos)
        self.opVBox.addWidget(self.btn_do_injection)
        self.widget_operation.setVisible(False)
        self.modeVBox.addWidget(self.widget_operation)

        self.leftPanel.addWidget(self.group_mode)

        # Terminal
        self.group_terminal = QGroupBox("System Terminal")
        self.terminalVBox = QVBoxLayout(self.group_terminal)
        self.termFilterHBox = QHBoxLayout()
        self.check_log_tip = QCheckBox("Tip")
        self.check_log_info = QCheckBox("Info")
        self.check_log_error = QCheckBox("Error")
        self.check_log_debug = QCheckBox("Debug")
        self.check_show_details = QCheckBox("Details")
        self.btn_clear_log = QPushButton("Clear")
        for cb in [self.check_log_tip, self.check_log_info, self.check_log_error, self.check_log_debug]:
            self.termFilterHBox.addWidget(cb)
            cb.setChecked(True) if "Debug" not in cb.text() else None
        self.termFilterHBox.addStretch()
        self.termFilterHBox.addWidget(self.check_show_details)
        self.termFilterHBox.addWidget(self.btn_clear_log)
        self.check_show_details.setChecked(False)
        self.text_terminal = QTextEdit()
        self.text_terminal.setReadOnly(True)
        self.text_terminal.setStyleSheet("font-family: Consolas; background: white;")
        self.terminalVBox.addLayout(self.termFilterHBox)
        self.terminalVBox.addWidget(self.text_terminal)
        self.leftPanel.addWidget(self.group_terminal)
        
        self.leftPanel.setStretch(0, 3)
        self.leftPanel.setStretch(1, 2)
        self.mainLayout.addLayout(self.leftPanel)

        # Right Panel
        self.rightPanel = QVBoxLayout()
        self.group_us = QGroupBox("Ultrasound Visualization")
        self.label_us_video = QLabel()
        self.label_us_video.setStyleSheet("background: black;")
        self.label_us_video.setAlignment(Qt.AlignCenter)
        self.usVBox = QVBoxLayout(self.group_us)
        self.usVBox.addWidget(self.label_us_video)
        self.rightPanel.addWidget(self.group_us)

        self.group_o3d = QGroupBox("3D Scene Visualization")
        self.widget_open3d = QWidget()
        self.widget_open3d.setStyleSheet("background: white;")
        self.o3dVBox = QVBoxLayout(self.group_o3d)
        self.o3dVBox.addWidget(self.widget_open3d)
        self.rightPanel.addWidget(self.group_o3d)
        
        self.mainLayout.addLayout(self.rightPanel)
        self.mainLayout.setStretch(0, 1)
        self.mainLayout.setStretch(1, 1)
        
        self.rightPanel.setStretch(0, 1)
        self.rightPanel.setStretch(1, 1)

    def retranslateUi(self, ControlForm):
        pass

