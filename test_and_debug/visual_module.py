import open3d as o3d
import win32gui
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import QTimer
from PySide6.QtGui import QWindow
import uuid

class O3DRenderer(QWidget):
    """
    专门负责 Open3D 渲染的模块。
    通过 win32gui 将 Open3D 窗口嵌入到 PySide6 Widget 中。
    """
    def __init__(self, parent=None, width=800, height=600):
        super().__init__(parent)
        self.setMinimumSize(width, height)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # 1. 初始化 Open3D Visualizer
        self.vis = o3d.visualization.Visualizer()
        # 使用随机 ID 确保窗口名唯一，防止 FindWindow 找错
        self.win_name = f"O3D_Embed_{uuid.uuid4().hex[:8]}"
        self.vis.create_window(window_name=self.win_name, width=width, height=height, visible=True)
        
        # 2. 嵌入窗口
        hwnd = win32gui.FindWindow(None, self.win_name)
        if hwnd:
            self.o3d_window = QWindow.fromWinId(hwnd)
            self.window_container = QWidget.createWindowContainer(self.o3d_window, self)
            self.layout.addWidget(self.window_container)
        else:
            print(f"Error: Could not find Open3D window with name {self.win_name}")

        # 3. 初始场景设置
        self.sphere = None
        self.setup_initial_scene()

        # 4. 渲染定时器 (保持鼠标交互响应)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.render_tick)
        self.timer.start(16)

    def setup_initial_scene(self):
        # 1. 添加地平面 (Grid/Plane)
        grid = o3d.geometry.TriangleMesh.create_box(width=10.0, height=0.01, depth=10.0)
        grid.paint_uniform_color([0.7, 0.7, 0.7])
        grid.translate([-5.0, -0.01, -5.0]) # 放在中心下方一点
        self.vis.add_geometry(grid)

        # 2. 添加坐标轴参考
        axes = o3d.geometry.TriangleMesh.create_coordinate_frame(size=0.5, origin=[0, 0, 0])
        self.vis.add_geometry(axes)

        # 3. 静态物体参考
        for i in range(3):
            box = o3d.geometry.TriangleMesh.create_box(width=0.2, height=0.2, depth=0.2)
            box.paint_uniform_color([0.5, 0.5, 0.8])
            box.translate([i * 0.5 - 0.5, 0, 0])
            self.vis.add_geometry(box)

        # 4. 预留的外部可操作球体
        self.sphere = o3d.geometry.TriangleMesh.create_sphere(radius=0.1)
        self.sphere.paint_uniform_color([1.0, 0, 0])
        self.sphere.compute_vertex_normals()
        self.sphere.translate([0, 0.5, 0])
        self.vis.add_geometry(self.sphere)

    def reset_view(self):
        """
        回正视角：将相机锁定在正面
        """
        ctr = self.vis.get_view_control()
        # 设置固定的 Up 向量，防止视角歪斜
        ctr.set_up([0, 1, 0]) # 强制 Y 轴向上
        ctr.set_front([0, 0, -1]) # 从 Z 轴看向中心
        ctr.set_lookat([0, 0, 0])
        ctr.set_zoom(0.8)
        self.vis.update_renderer()

    def limit_up_vector(self):
        """
        限制视角转动：强制 Up 向量始终垂直向上 (Y=1)，防止左右歪斜。
        这类似于卫星地图或建筑软件的视角限制（只有水平旋转和俯仰，没有自身的 Roll）。
        """
        ctr = self.vis.get_view_control()
        cp = ctr.convert_to_pinhole_camera_parameters()
        # 强制 Up 轴始终垂直
        # 注意：Open3D 内部可能在 poll_events 中重置。 
        # 最有效的办法是强制锁定 Up 向量
        ctr.set_up([0, 1, 0])

    def load_3d_file(self, file_path):
        """
        加载现有的 3D 文件（如 .ply, .stl, .obj, .off 等）。
        """
        try:
            # Open3D 自动根据扩展名识别格式
            mesh = o3d.io.read_triangle_mesh(file_path)
            if not mesh.has_vertices():
                # 尝试作为点云读取（针对某些只有点云的 ply）
                mesh = o3d.io.read_point_cloud(file_path)
            
            if mesh.is_empty():
                print(f"Error: File is empty or not supported: {file_path}")
                return False

            mesh.compute_vertex_normals() # 为模型添加法向量以正常显示光照
            self.vis.add_geometry(mesh)
            self.vis.reset_view_point(True) # 自动调整相机以看全物体
            print(f"Successfully loaded: {file_path}")
            return True
        except Exception as e:
            print(f"Failed to load 3D file: {e}")
            return False

    def update_point_position(self, x, y, z):
        """
        预留的外部调用接口。
        允许外部函数提供坐标来移动可视化点。
        """
        if self.sphere:
            # 计算位移 (translate 是相对位移，所以先获取当前中心)
            curr_center = self.sphere.get_center()
            self.sphere.translate([x - curr_center[0], y - curr_center[1], z - curr_center[2]])
            self.vis.update_geometry(self.sphere)
            # update_renderer 将在下一次 render_tick 中自动调用

    def render_tick(self):
        # poll_events 允许鼠标通过 Open3D 自身的交互逻辑旋转/缩放视角
        self.vis.poll_events()
        # 实时锁死 Up 向量，防止视角倾斜
        self.vis.get_view_control().set_up([0, 1, 0])
        self.vis.update_renderer()

    def closeEvent(self, event):
        self.vis.destroy_window()
        event.accept()
