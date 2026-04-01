import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QHBoxLayout, QWidget
from visual_module import O3DRenderer
from front_module import ControlPanel

class IntegratedWindow(QMainWindow):
    """
    主体窗口整合前端模块 (front_module) 和 渲染模块 (visual_module)。
    它是两个模块之间的“粘合剂”和“控制器”。
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Open3D Embedded - Integrated Test (Modularized)")
        self.resize(1200, 800)

        # 1. 主窗口容器
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)

        # 2. 实例化分离的模块
        self.controls = ControlPanel(self)  # 前端 UI 类
        self.renderer = O3DRenderer(self)   # 3D 渲染可视化类

        # 3. 将模块添加到布局
        # 左侧放控制面板 (固定宽度)
        self.controls.setFixedWidth(250)
        self.main_layout.addWidget(self.controls)
        # 右侧放 3D 窗口 (占据盈余空间)
        self.main_layout.addWidget(self.renderer)

        # 4. 连接信号和槽来实现模块间通信 (Logic Linking)
        # 将 UI 前端的信号，连到可视化端的对应接口上
        self.controls.position_changed.connect(self.renderer.update_point_position)
        self.controls.file_selected.connect(self.renderer.load_3d_file)
        self.controls.reset_view_requested.connect(self.renderer.reset_view)

    def closeEvent(self, event):
        # 显式关闭渲染模块内部关联窗口
        self.renderer.closeEvent(event)
        super().closeEvent(event)

def main():
    app = QApplication(sys.argv)
    window = IntegratedWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
