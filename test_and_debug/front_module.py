from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QDoubleSpinBox, QFileDialog)
from PySide6.QtCore import Signal

class ControlPanel(QWidget):
    """
    专门的前端控制面板。
    仅负责 UI 交互，不包含任何 Open3D 渲染逻辑。
    通过信号向上层汇报用户操作。
    """
    # 定义自定义信号
    position_changed = Signal(float, float, float)
    file_selected = Signal(str)
    reset_view_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        
        # 视图控制部分
        layout.addWidget(QLabel("View Control:"))
        self.btn_reset_view = QPushButton("Reset Camera (Up=Y)")
        self.btn_reset_view.clicked.connect(self.reset_view_requested.emit)
        layout.addWidget(self.btn_reset_view)

        layout.addSpacing(20)
        
        # 文件加载部分
        layout.addWidget(QLabel("File Import:"))
        self.btn_load_file = QPushButton("Load 3D File (.obj, .stl, .ply)")
        self.btn_load_file.clicked.connect(self.on_load_file_clicked)
        layout.addWidget(self.btn_load_file)
        
        layout.addSpacing(20)
        layout.addWidget(QLabel("Coordinate Control:"))
        
        # X 轴控制
        x_layout = QHBoxLayout()
        x_layout.addWidget(QLabel("X:"))
        self.spin_x = QDoubleSpinBox()
        self.spin_x.setRange(-5.0, 5.0)
        self.spin_x.setSingleStep(0.1)
        x_layout.addWidget(self.spin_x)
        layout.addLayout(x_layout)
        # ... (Spin Y/Z 保持不变)


        # Y 轴控制 (保持和原来 test_visualization 一致的 Left/Right 可替代)
        y_layout = QHBoxLayout()
        y_layout.addWidget(QLabel("Y:"))
        self.spin_y = QDoubleSpinBox()
        self.spin_y.setRange(-5.0, 5.0)
        self.spin_y.setSingleStep(0.1)
        y_layout.addWidget(self.spin_y)
        layout.addLayout(y_layout)

        # Z 轴控制
        z_layout = QHBoxLayout()
        z_layout.addWidget(QLabel("Z:"))
        self.spin_z = QDoubleSpinBox()
        self.spin_z.setRange(-5.0, 5.0)
        self.spin_z.setSingleStep(0.1)
        z_layout.addWidget(self.spin_z)
        layout.addLayout(z_layout)

        # 提交按钮
        self.btn_apply = QPushButton("Apply Position")
        self.btn_apply.clicked.connect(self.on_apply_clicked)
        layout.addWidget(self.btn_apply)

        # 辅助提示
        layout.addStretch()
        layout.addWidget(QLabel("Interaction: Mouse drag on 3D view to rotate."))

    def on_apply_clicked(self):
        # 发送坐标值到上层 (Main)
        self.position_changed.emit(
            self.spin_x.value(),
            self.spin_y.value(),
            self.spin_z.value()
        )

    def on_load_file_clicked(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open 3D File", "", "3D Files (*.obj *.stl *.ply *.off *.gltf)"
        )
        if file_path:
            self.file_selected.emit(file_path)
