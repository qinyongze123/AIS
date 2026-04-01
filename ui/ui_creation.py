# -*- coding: utf-8 -*-

from PySide6.QtCore import (QCoreApplication, QMetaObject, QSize, Qt)
from PySide6.QtWidgets import (QGridLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QComboBox, QTextEdit, QVBoxLayout, QWidget, QSpacerItem, QSizePolicy, QGroupBox)

class Ui_ProjectCreationDialog(object):
    def setupUi(self, ProjectCreationDialog):
        if not ProjectCreationDialog.objectName():
            ProjectCreationDialog.setObjectName(u"ProjectCreationDialog")
        ProjectCreationDialog.resize(600, 500)
        ProjectCreationDialog.setStyleSheet(u"QWidget { font-family: \"Segoe UI\", \"Arial\"; font-size: 13px; color: #333; }\n"
"QGroupBox { font-weight: bold; border: 1px solid #dcdcdc; border-radius: 6px; margin-top: 12px; padding-top: 10px; }\n"
"QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #555; }\n"
"QPushButton { padding: 6px 12px; border-radius: 4px; border: 1px solid #ccc; background: #fdfdfd; }\n"
"QPushButton:hover { background: #f0f7ff; border-color: #2196F3; }\n"
"QComboBox, QLineEdit, QDoubleSpinBox { padding: 4px; border: 1px solid #ccc; border-radius: 4px; background: white; }")

        self.layout = QVBoxLayout(ProjectCreationDialog)
        self.layout.setContentsMargins(25, 25, 25, 25)
        self.layout.setSpacing(15)
        
        self.header = QLabel("Project Registration")
        self.header.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px; margin-left: -5px;")
        self.layout.addWidget(self.header)

        # Project Info Section - Flat
        self.grid_proj = QGridLayout()
        self.grid_proj.setVerticalSpacing(12)

        # Project Root Path
        self.l_proj_path = QLabel("Project Root:")
        self.edit_proj_path = QLineEdit()
        self.btn_browse = QPushButton("Browse")
        self.grid_proj.addWidget(self.l_proj_path, 0, 0)
        self.grid_proj.addWidget(self.edit_proj_path, 0, 1)
        self.grid_proj.addWidget(self.btn_browse, 0, 2)

        # Project Name
        self.l_proj_name = QLabel("Project Name:")
        self.combo_proj_name = QComboBox()
        self.combo_proj_name.setEditable(True)
        self.grid_proj.addWidget(self.l_proj_name, 1, 0)
        self.grid_proj.addWidget(self.combo_proj_name, 1, 1, 1, 2)

        # Session Name
        self.l_session_name = QLabel("Session Name:")
        self.edit_session_name = QLineEdit()
        self.grid_proj.addWidget(self.l_session_name, 2, 0)
        self.grid_proj.addWidget(self.edit_session_name, 2, 1, 1, 2)

        self.layout.addLayout(self.grid_proj)

        # Operator Section - Flat
        # 为了保证对齐，将 Operator 加入到 grid_proj 中，而不是创建新的 layout
        self.l_operator = QLabel("Operator:")
        self.combo_operator = QComboBox()
        self.combo_operator.setEditable(True)
        self.btn_delete_op = QPushButton("Delete Selected")
        self.btn_delete_op.setStyleSheet("background-color: #ffebee; color: #c62828;")
        
        self.grid_proj.addWidget(self.l_operator, 3, 0)
        self.grid_proj.addWidget(self.combo_operator, 3, 1)
        self.grid_proj.addWidget(self.btn_delete_op, 3, 2)

        # Notes Section - Flat
        self.l_notes = QLabel("Notes:")
        self.layout.addWidget(self.l_notes)
        self.edit_note = QTextEdit()
        self.edit_note.setMaximumHeight(80)
        self.layout.addWidget(self.edit_note)

        self.layout.addStretch()

        # Bottom Buttons
        self.btn_layout = QHBoxLayout()
        self.btn_start = QPushButton("Create")
        self.btn_start.setMinimumHeight(48)
        self.btn_start.setMinimumWidth(160)
        self.btn_start.setStyleSheet("background-color: #2e7d32; color: white; font-weight: bold; font-size: 14px;")
        self.btn_layout.addStretch()
        self.btn_layout.addWidget(self.btn_start)
        self.layout.addLayout(self.btn_layout)

    def retranslateUi(self, ProjectCreationDialog):
        pass
