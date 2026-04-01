import open3d as o3d
import win32gui
import win32con
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import QTimer
from PySide6.QtGui import QWindow
import uuid
import numpy as np

class Visualizer3D(QWidget):
    """
    Visualization module for 3D monitoring and UI updates.
    Handles rendering robot pathing, current state, and safety zones.
    Incorporates Open3D rendering embedded in PySide6.
    """
    def __init__(self, parent=None, width=600, height=400):
        super().__init__(parent)
        self._is_destroyed = False
        self._vis_ready = False
        initial_w = width
        initial_h = height
        if parent is not None:
            initial_w = max(width, parent.width())
            initial_h = max(height, parent.height())

        self.setMinimumSize(width, height)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # 1. Initialize Open3D Visualizer
        self.vis = o3d.visualization.Visualizer()
        self.win_name = f"O3D_Monitor_{uuid.uuid4().hex[:8]}"
        # Note: Coordinate system: X-right, Y-forward (into screen), Z-up
        self._vis_ready = self.vis.create_window(
            window_name=self.win_name,
            width=initial_w,
            height=initial_h,
            visible=True,
        )

        if not self._vis_ready:
            return
        
        # 2. Embed Window
        hwnd = win32gui.FindWindow(None, self.win_name)
        if hwnd:
            # Keep the native GLFW window out of task switching/focus while embedding.
            ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            ex_style |= win32con.WS_EX_TOOLWINDOW
            ex_style &= ~win32con.WS_EX_APPWINDOW
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style)

            # Hide native window first to avoid top-level flash before embedding.
            win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
            win32gui.SetWindowPos(
                hwnd,
                0,
                0,
                0,
                0,
                0,
                win32con.SWP_NOMOVE
                | win32con.SWP_NOSIZE
                | win32con.SWP_NOZORDER
                | win32con.SWP_NOACTIVATE
                | win32con.SWP_NOOWNERZORDER
                | win32con.SWP_FRAMECHANGED,
            )

            self.o3d_window = QWindow.fromWinId(hwnd)
            self.window_container = QWidget.createWindowContainer(self.o3d_window, self)
            self.layout.addWidget(self.window_container)
            # Show the foreign window only after it has been embedded into Qt.
            self.o3d_window.show()
        else:
            self._vis_ready = False
            return
        
        # 3. Scene Objects
        self.floor = None
        self.axes = None
        self.left_sphere = None
        self.right_sphere = None
        self.sphere_radius = 0.5 # Default 5mm (0.5cm)
        
        self.setup_scene()

        # 4. Render Timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.render_tick)
        self.timer.start(16)

    def _apply_camera_pose(self, front, lookat=(0.0, 0.0, 0.0), zoom=0.5):
        """Apply camera pose while constraining world up to +Z."""
        if not self._vis_ready or self._is_destroyed:
            return

        ctr = self.vis.get_view_control()
        ctr.set_up([0.0, 0.0, 1.0])
        ctr.set_front(front)
        ctr.set_lookat(list(lookat))
        ctr.set_zoom(zoom)
        self.vis.update_renderer()

    def setup_scene(self):
        if not self._vis_ready or self._is_destroyed:
            return

        # Floor: 15cm (X) x 30cm (Y) x 3cm (Z)
        # Center at x=0, y=0, z=-1.5 (Top surface at z=0)
        self.floor = o3d.geometry.TriangleMesh.create_box(width=15.0, height=30.0, depth=3.0)
        self.floor.paint_uniform_color([0.8, 0.8, 0.8])
        # Translate to center it
        self.floor.translate([-7.5, -15.0, -3.0])
        self.vis.add_geometry(self.floor)

        # Axes
        self.axes = o3d.geometry.TriangleMesh.create_coordinate_frame(size=2.0, origin=[0, 0, 0])
        self.vis.add_geometry(self.axes)

        # Left Sphere (Red) at x=-1, y=0, z=0
        self.left_sphere = o3d.geometry.TriangleMesh.create_sphere(radius=self.sphere_radius)
        self.left_sphere.paint_uniform_color([1.0, 0.0, 0.0])
        self.left_sphere.compute_vertex_normals()
        self.left_sphere.translate([-1.0, 0.0, 0.0])
        self.vis.add_geometry(self.left_sphere)

        # Right Sphere (Blue) at x=1, y=0, z=0
        self.right_sphere = o3d.geometry.TriangleMesh.create_sphere(radius=self.sphere_radius)
        self.right_sphere.paint_uniform_color([0.0, 0.0, 1.0])
        self.right_sphere.compute_vertex_normals()
        self.right_sphere.translate([1.0, 0.0, 0.0])
        self.vis.add_geometry(self.right_sphere)

        self.reset_view()

    def reset_view(self):
        """
        Default view: face +Y and -Z with 30 deg from +Y.
        """
        angle_rad = np.deg2rad(30)
        self._apply_camera_pose([0.0, float(np.cos(angle_rad)), -float(np.sin(angle_rad))], zoom=0.5)

    def set_front_view(self):
        """Front view along +Y axis."""
        self._apply_camera_pose([0.0, 1.0, 0.0], zoom=0.6)

    def set_top_view(self):
        """Top-down view along -Z axis."""
        self._apply_camera_pose([0.0, 0.0, -1.0], zoom=0.6)

    def limit_up_vector(self):
        """Prevent roll by forcing +Z as the camera up vector."""
        if not self._vis_ready or self._is_destroyed:
            return

        ctr = self.vis.get_view_control()
        ctr.set_up([0.0, 0.0, 1.0])

    def toggle_axes(self, visible):
        if not self._vis_ready or self._is_destroyed:
            return

        if visible:
            self.vis.add_geometry(self.axes, reset_bounding_box=False)
        else:
            self.vis.remove_geometry(self.axes, reset_bounding_box=False)

    def update_sphere_size(self, radius_cm):
        """Update both spheres' size by replacing geometry."""
        if not self._vis_ready or self._is_destroyed:
            return

        self.sphere_radius = radius_cm
        
        # Re-create Left Sphere
        old_center_l = self.left_sphere.get_center()
        self.vis.remove_geometry(self.left_sphere, reset_bounding_box=False)
        self.left_sphere = o3d.geometry.TriangleMesh.create_sphere(radius=self.sphere_radius)
        self.left_sphere.paint_uniform_color([1.0, 0.0, 0.0])
        self.left_sphere.compute_vertex_normals()
        self.left_sphere.translate(old_center_l)
        self.vis.add_geometry(self.left_sphere, reset_bounding_box=False)

        # Re-create Right Sphere
        old_center_r = self.right_sphere.get_center()
        self.vis.remove_geometry(self.right_sphere, reset_bounding_box=False)
        self.right_sphere = o3d.geometry.TriangleMesh.create_sphere(radius=self.sphere_radius)
        self.right_sphere.paint_uniform_color([0.0, 0.0, 1.0])
        self.right_sphere.compute_vertex_normals()
        self.right_sphere.translate(old_center_r)
        self.vis.add_geometry(self.right_sphere, reset_bounding_box=False)

    def update_object_pose(self, obj_id, x, y, z):
        """
        Interace for backend to update positions.
        obj_id: 'left', 'right', or custom names.
        """
        if not self._vis_ready or self._is_destroyed:
            return

        target = None
        if obj_id == "left": target = self.left_sphere
        elif obj_id == "right": target = self.right_sphere
        
        if target:
            curr_center = target.get_center()
            target.translate([x - curr_center[0], y - curr_center[1], z - curr_center[2]])
            self.vis.update_geometry(target)

    def render_tick(self):
        if self._is_destroyed or not self._vis_ready:
            return

        try:
            self.vis.poll_events()
            self.limit_up_vector()
            self.vis.update_renderer()
        except Exception:
            self._is_destroyed = True
            self._vis_ready = False
            if self.timer.isActive():
                self.timer.stop()

    def closeEvent(self, event):
        if self._is_destroyed:
            event.accept()
            return

        self._is_destroyed = True
        self._vis_ready = False

        if hasattr(self, "timer") and self.timer.isActive():
            self.timer.stop()

        if hasattr(self, "window_container") and self.window_container is not None:
            self.window_container.hide()

        if hasattr(self, "vis") and self.vis is not None:
            try:
                self.vis.destroy_window()
            except Exception:
                pass

        event.accept()

