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
        
        self.tab_main_control = QTabWidget(ControlForm)
        self.tab_main_control.setStyleSheet(u"QTabBar::tab { height: 36px; width: 140px; font-weight: bold; background: #eee; border: 1px solid #ddd; border-bottom: none; border-top-left-radius: 4px; border-top-right-radius: 4px; margin-right: 2px; }\n"
"QTabBar::tab:selected { background: #fff; border-bottom: 3px solid #2196F3; color: #2196F3; }\n"
"QTabWidget::pane { border: 1px solid #ddd; top: -1px; background: white; border-radius: 4px; }")

        # --- Tab 1: Create ---
        self.tab_create = QWidget()
        self.createMainVBox = QVBoxLayout(self.tab_create)
        self.grid_project = QGridLayout()
        
        self.l_proj_path = QLabel("Project Path:")
        self.edit_proj_path = QLineEdit()
        self.btn_browse_proj = QPushButton("Browse")
        self.grid_project.addWidget(self.l_proj_path, 0, 0)
        self.grid_project.addWidget(self.edit_proj_path, 0, 1)
        self.grid_project.addWidget(self.btn_browse_proj, 0, 2)
        
        self.l_proj_name = QLabel("Project Name:")
        self.edit_proj_name = QLineEdit()
        self.grid_project.addWidget(self.l_proj_name, 1, 0)
        self.grid_project.addWidget(self.edit_proj_name, 1, 1, 1, 2)
        
        self.l_session_name = QLabel("Record Name:")
        self.edit_session_name = QLineEdit()
        self.grid_project.addWidget(self.l_session_name, 2, 0)
        self.grid_project.addWidget(self.edit_session_name, 2, 1, 1, 2)
        
        self.l_operator = QLabel("Operator:")
        self.combo_operator = QComboBox()
        self.combo_operator.setEditable(True)
        self.btn_del_operator = QPushButton("Delete")
        self.grid_project.addWidget(self.l_operator, 3, 0)
        self.grid_project.addWidget(self.combo_operator, 3, 1)
        self.grid_project.addWidget(self.btn_del_operator, 3, 2)
        
        self.l_note = QLabel("Note:")
        self.edit_note = QTextEdit()
        self.edit_note.setMaximumHeight(80)
        self.grid_project.addWidget(self.l_note, 4, 0)
        self.grid_project.addWidget(self.edit_note, 4, 1, 1, 2)

        self.regBtnHBox = QHBoxLayout()
        self.regBtnSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.regBtnHBox.addItem(self.regBtnSpacer)
        self.btn_create_session = QPushButton("Register Session")
        self.btn_create_session.setMinimumWidth(120)
        self.btn_create_session.setStyleSheet("background-color: #81c784; color: white; font-weight: bold; border: none; height: 32px;")
        self.regBtnHBox.addWidget(self.btn_create_session)
        self.grid_project.addLayout(self.regBtnHBox, 5, 0, 1, 3)

        self.createMainVBox.addLayout(self.grid_project)
        self.createMainVBox.addStretch()
        self.tab_main_control.addTab(self.tab_create, "CREATE")

        # --- Tab 2: Connection ---
        self.tab_connection = QWidget()
        self.connMainVBox = QVBoxLayout(self.tab_connection)
        self.grid_status = QGridLayout()
        
        # Injector
        self.l_stat_inj = QLabel("Injector Port:")
        self.combo_port_inj = QComboBox()
        self.val_stat_inj = QLabel("Offline")
        self.val_stat_inj.setStyleSheet("color: #e53935; font-weight: bold;")
        self.pushButton = QPushButton("Retry")
        self.grid_status.addWidget(self.l_stat_inj, 0, 0)
        self.grid_status.addWidget(self.combo_port_inj, 0, 1)
        self.grid_status.addWidget(self.val_stat_inj, 0, 2)
        self.grid_status.addWidget(self.pushButton, 0, 3)

        # Probe
        self.l_port_probe = QLabel("Probe Port:")
        self.combo_port_probe = QComboBox()
        self.val_stat_probe = QLabel("Offline")
        self.val_stat_probe.setStyleSheet("color: #e53935; font-weight: bold;")
        self.pushButton_2 = QPushButton("Retry")
        self.grid_status.addWidget(self.l_port_probe, 1, 0)
        self.grid_status.addWidget(self.combo_port_probe, 1, 1)
        self.grid_status.addWidget(self.val_stat_probe, 1, 2)
        self.grid_status.addWidget(self.pushButton_2, 1, 3)

        # RGBD
        self.l_cam_rgbd = QLabel("RGBD Camera:")
        self.combo_cam_rgbd = QComboBox()
        self.val_stat_rgbd = QLabel("Offline")
        self.val_stat_rgbd.setStyleSheet("color: #e53935; font-weight: bold;")
        self.pushButton_3 = QPushButton("Retry")
        self.grid_status.addWidget(self.l_cam_rgbd, 2, 0)
        self.grid_status.addWidget(self.combo_cam_rgbd, 2, 1)
        self.grid_status.addWidget(self.val_stat_rgbd, 2, 2)
        self.grid_status.addWidget(self.pushButton_3, 2, 3)

        # Ultrasound
        self.l_stat_us = QLabel("Ultrasound:")
        self.combo_cam_us = QComboBox()
        self.val_stat_us = QLabel("Offline")
        self.val_stat_us.setStyleSheet("color: #e53935; font-weight: bold;")
        self.pushButton_4 = QPushButton("Retry")
        self.grid_status.addWidget(self.l_stat_us, 3, 0)
        self.grid_status.addWidget(self.combo_cam_us, 3, 1)
        self.grid_status.addWidget(self.val_stat_us, 3, 2)
        self.grid_status.addWidget(self.pushButton_4, 3, 3)

        self.connMainVBox.addLayout(self.grid_status)
        self.connMainVBox.addStretch()
        self.tab_main_control.addTab(self.tab_connection, "CONNECTION")

        # --- Tab 3: Operation ---
        self.tab_control = QWidget()
        self.controlMainVBox = QVBoxLayout(self.tab_control)
        self.modeHBox = QHBoxLayout()
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
        self.controlMainVBox.addLayout(self.modeHBox)

        # Removed redundant tab_work_mode QTabWidget
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
        
        self.controlMainVBox.addWidget(self.widget_operation)
        
        self.posHBox = QHBoxLayout()
        self.label_pos_injector = QLabel("Inj: (0, 0, 0)")
        self.label_pos_probe = QLabel("Prb: (0, 0, 0)")
        self.btn_stop_main = QPushButton("STOP")
        self.btn_stop_main.setStyleSheet("background-color: #d32f2f; color: white; font-weight: bold;")
        self.posHBox.addWidget(self.label_pos_injector)
        self.posHBox.addWidget(self.label_pos_probe)
        self.posHBox.addStretch()
        self.posHBox.addWidget(self.btn_stop_main)
        self.controlMainVBox.addLayout(self.posHBox)
        
        self.tab_main_control.addTab(self.tab_control, "OPERATION")

        self.leftPanel.addWidget(self.tab_main_control)

        # Terminal
        self.group_terminal = QGroupBox("System Terminal")
        self.terminalVBox = QVBoxLayout(self.group_terminal)
        self.termFilterHBox = QHBoxLayout()
        self.check_log_tip = QCheckBox("Tip")
        self.check_log_info = QCheckBox("Info")
        self.check_log_error = QCheckBox("Error")
        self.check_log_debug = QCheckBox("Debug")
        self.check_show_details = QCheckBox("Details")
        for cb in [self.check_log_tip, self.check_log_info, self.check_log_error, self.check_log_debug]:
            self.termFilterHBox.addWidget(cb)
            cb.setChecked(True) if "Debug" not in cb.text() else None
        self.termFilterHBox.addStretch()
        self.termFilterHBox.addWidget(self.check_show_details)
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
        self.widget_open3d.setStyleSheet("background: #1a1a1b;")
        self.o3dVBox = QVBoxLayout(self.group_o3d)
        self.o3dVBox.addWidget(self.widget_open3d)
        self.rightPanel.addWidget(self.group_o3d)
        
        self.mainLayout.addLayout(self.rightPanel)
        self.mainLayout.setStretch(0, 4)
        self.mainLayout.setStretch(1, 5)

    def retranslateUi(self, ControlForm):
        pass

