# -*- coding: utf-8 -*-

from PySide6.QtCore import (QCoreApplication, QMetaObject, QSize, Qt)
from PySide6.QtWidgets import (QGridLayout, QHBoxLayout, QLabel, 
    QComboBox, QPushButton, QVBoxLayout, QWidget, QSpacerItem, QSizePolicy, QGroupBox)

class Ui_ConnectionDialog(object):
    def setupUi(self, ConnectionDialog):
        if not ConnectionDialog.objectName():
            ConnectionDialog.setObjectName(u"ConnectionDialog")
        ConnectionDialog.resize(600, 480)
        ConnectionDialog.setStyleSheet(u"QWidget { font-family: \"Segoe UI\", \"Arial\"; font-size: 13px; color: #333; }\n"
"QPushButton { padding: 6px 12px; border-radius: 4px; border: 1px solid #ccc; background: #fdfdfd; }\n"
"QPushButton:hover { background: #f0f7ff; border-color: #2196F3; }\n"
"QComboBox { padding: 4px; border: 1px solid #ccc; border-radius: 4px; background: white; }")

        self.layout = QVBoxLayout(ConnectionDialog)
        self.layout.setContentsMargins(25, 25, 25, 25)
        self.layout.setSpacing(15)
        
        self.header = QLabel("Hardware Connection")
        self.header.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px; margin-left: -5px;")
        self.layout.addWidget(self.header)

        # Status Panel - Flat Grid
        self.grid_status = QGridLayout()
        self.grid_status.setVerticalSpacing(12)
        self.grid_status.setHorizontalSpacing(10)
        
        # Helper to style status labels
        def get_status_label():
            lbl = QLabel("Offline")
            lbl.setStyleSheet("color: #e53935; font-weight: bold;")
            return lbl

        # Injector
        self.l_stat_inj = QLabel("Injector Unit:")
        self.combo_port_inj = QComboBox()
        self.combo_port_inj.setMinimumWidth(150)
        self.val_stat_inj = get_status_label()
        self.btn_retry_inj = QPushButton("Connect")
        self.grid_status.addWidget(self.l_stat_inj, 0, 0)
        self.grid_status.addWidget(self.combo_port_inj, 0, 1)
        self.grid_status.addWidget(self.val_stat_inj, 0, 2)
        self.grid_status.addWidget(self.btn_retry_inj, 0, 3)

        # Probe
        self.l_port_probe = QLabel("Probe Unit:")
        self.combo_port_probe = QComboBox()
        self.val_stat_probe = get_status_label()
        self.btn_retry_probe = QPushButton("Connect")
        self.grid_status.addWidget(self.l_port_probe, 1, 0)
        self.grid_status.addWidget(self.combo_port_probe, 1, 1)
        self.grid_status.addWidget(self.val_stat_probe, 1, 2)
        self.grid_status.addWidget(self.btn_retry_probe, 1, 3)

        # RGBD
        self.l_cam_rgbd = QLabel("RGBD Camera:")
        self.combo_cam_rgbd = QComboBox()
        self.val_stat_rgbd = get_status_label()
        self.btn_retry_rgbd = QPushButton("Connect")
        self.grid_status.addWidget(self.l_cam_rgbd, 2, 0)
        self.grid_status.addWidget(self.combo_cam_rgbd, 2, 1)
        self.grid_status.addWidget(self.val_stat_rgbd, 2, 2)
        self.grid_status.addWidget(self.btn_retry_rgbd, 2, 3)

        # Ultrasound
        self.l_stat_us = QLabel("Ultrasound:")
        self.combo_cam_us = QComboBox()
        self.val_stat_us = get_status_label()
        self.btn_retry_us = QPushButton("Connect")
        self.grid_status.addWidget(self.l_stat_us, 3, 0)
        self.grid_status.addWidget(self.combo_cam_us, 3, 1)
        self.grid_status.addWidget(self.val_stat_us, 3, 2)
        self.grid_status.addWidget(self.btn_retry_us, 3, 3)

        self.layout.addLayout(self.grid_status)
        
        self.layout.addStretch()

        # Bottom Controls
        self.btn_layout = QHBoxLayout()
        self.btn_next = QPushButton("Enter Console")
        self.btn_next.setMinimumHeight(48)
        self.btn_next.setMinimumWidth(160)
        self.btn_next.setStyleSheet("background-color: #2e7d32; color: white; font-weight: bold; font-size: 14px;")
        self.btn_layout.addStretch()
        self.btn_layout.addWidget(self.btn_next)
        self.layout.addLayout(self.btn_layout)

    def retranslateUi(self, ConnectionDialog):
        pass
