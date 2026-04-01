import open3d as o3d
import win32gui
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import QTimer, Signal, QEvent
from PySide6.QtGui import QWindow
import time
import uuid
import numpy as np

class Visualizer3D(QWidget):
    """
    Visualization module for 3D monitoring and UI updates.
    Handles rendering robot pathing, current state, and safety zones.
    Incorporates Open3D rendering embedded in PySide6.
    """
    first_frame_ready = Signal()

    def __init__(self, parent=None, width=600, height=400, camera_config=None):
        super().__init__(parent)
        self._is_destroyed = False
        self._vis_ready = False
        self._first_frame_emitted = False
        self.camera_config = camera_config or {}
        self._current_up = [0.0, 0.0, 1.0]
        self._lookat = self.camera_config.get("LOOKAT", [0.0, 0.0, 0.0])
        self._reset_elevation_deg = float(self.camera_config.get("RESET_ELEVATION_DEG", 30.0))
        self._reset_distance_cm = float(self.camera_config.get("RESET_DISTANCE_CM", 45.0))
        self._front_distance_cm = float(self.camera_config.get("FRONT_DISTANCE_CM", self._reset_distance_cm))
        self._top_distance_cm = float(self.camera_config.get("TOP_DISTANCE_CM", self._reset_distance_cm))
        self._wheel_zoom_speed = float(self.camera_config.get("WHEEL_ZOOM_SPEED", 0.12))
        self._wheel_zoom_speed = max(0.01, min(0.40, self._wheel_zoom_speed))
        self._wheel_min_distance_cm = float(self.camera_config.get("WHEEL_MIN_DISTANCE_CM", 5.0))
        self._wheel_max_distance_cm = float(self.camera_config.get("WHEEL_MAX_DISTANCE_CM", 500.0))
        self._keep_world_z_vertical = True
        initial_w = width
        initial_h = height
        if parent is not None:
            initial_w = max(width, parent.width())
            initial_h = max(height, parent.height())

        self.setMinimumSize(width, height)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.o3d_window = None
        self.window_container = None
        
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
        hwnd = self._find_window_handle(timeout_ms=300)
        if hwnd:
            self.o3d_window = QWindow.fromWinId(hwnd)
            self.window_container = QWidget.createWindowContainer(self.o3d_window, self)
            self.window_container.installEventFilter(self)
            self.layout.addWidget(self.window_container)
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

    def _find_window_handle(self, timeout_ms=300):
        """Poll briefly because GLFW window handle may appear asynchronously."""
        deadline = time.time() + (timeout_ms / 1000.0)
        hwnd = 0
        while time.time() < deadline:
            hwnd = win32gui.FindWindow(None, self.win_name)
            if hwnd:
                return hwnd
            time.sleep(0.01)

        return 0

    @staticmethod
    def _normalize(v):
        n = np.linalg.norm(v)
        if n <= 1e-9:
            return None
        return v / n

    def _current_camera_pose(self):
        ctr = self.vis.get_view_control()
        params = ctr.convert_to_pinhole_camera_parameters()
        ext = params.extrinsic
        r = np.asarray(ext[:3, :3], dtype=float)
        t = np.asarray(ext[:3, 3], dtype=float)

        camera_pos = -r.T @ t
        z_world = self._normalize(r.T[:, 2])
        up_world = self._normalize(r.T[:, 1])
        if z_world is None or up_world is None:
            return None, None, None

        # Open3D front convention in this module: lookat -> camera.
        front = -z_world
        return camera_pos, front, up_world

    def _apply_camera_pose(self, front, lookat=None, zoom=1.0, up=(0.0, 0.0, 1.0), distance_cm=None):
        """Apply camera pose while constraining world up to +Z."""
        if not self._vis_ready or self._is_destroyed:
            return

        if lookat is not None:
            self._lookat = list(lookat)

        if distance_cm is None:
            distance_cm = self._reset_distance_cm

        front_vec = self._normalize(np.asarray(front, dtype=float))
        up_world = self._normalize(np.asarray(up, dtype=float))
        if front_vec is None or up_world is None:
            return

        lookat_vec = np.asarray(self._lookat, dtype=float)
        camera_pos = lookat_vec + front_vec * float(distance_cm)

        # Camera forward axis (world) points from camera to lookat.
        z_world = self._normalize(lookat_vec - camera_pos)
        if z_world is None:
            return

        x_world = self._normalize(np.cross(z_world, up_world))
        if x_world is None:
            return

        y_world = self._normalize(np.cross(z_world, x_world))
        if y_world is None:
            return

        r = np.stack([x_world, y_world, z_world], axis=0)
        t = -r @ camera_pos

        ctr = self.vis.get_view_control()
        params = ctr.convert_to_pinhole_camera_parameters()
        extrinsic = np.eye(4, dtype=float)
        extrinsic[:3, :3] = r
        extrinsic[:3, 3] = t
        params.extrinsic = extrinsic
        ctr.convert_from_pinhole_camera_parameters(params, allow_arbitrary=True)

        self._current_up = [float(up[0]), float(up[1]), float(up[2])]
        ctr.set_up(self._current_up)
        self.vis.update_renderer()

    def eventFilter(self, watched, event):
        if watched is self.window_container and event.type() == QEvent.Wheel:
            if not self._vis_ready or self._is_destroyed:
                return True

            steps = event.angleDelta().y() / 120.0
            if abs(steps) < 1e-6:
                return True

            camera_pos, front, up_world = self._current_camera_pose()
            if camera_pos is None:
                return True

            lookat_vec = np.asarray(self._lookat, dtype=float)
            current_distance = float(np.linalg.norm(camera_pos - lookat_vec))
            if current_distance <= 1e-6:
                return True

            # wheel up(+) zooms in (distance decreases), wheel down(-) zooms out.
            distance_scale = (1.0 - self._wheel_zoom_speed) ** steps
            target_distance = current_distance * distance_scale
            target_distance = max(self._wheel_min_distance_cm, min(self._wheel_max_distance_cm, target_distance))

            self._apply_camera_pose(front, up=up_world, distance_cm=target_distance)
            return True

        return super().eventFilter(watched, event)

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
        Camera in -Y/+Z quadrant looking at origin.
        """
        angle_rad = np.deg2rad(self._reset_elevation_deg)
        # Open3D front points from lookat to camera, so signs are opposite of view direction.
        front = [0.0, -float(np.cos(angle_rad)), float(np.sin(angle_rad))]
        self._keep_world_z_vertical = True
        self._apply_camera_pose(front, up=(0.0, 0.0, 1.0), distance_cm=self._reset_distance_cm)

    def set_front_view(self):
        """Front view from negative Y axis looking to origin."""
        self._keep_world_z_vertical = True
        self._apply_camera_pose([0.0, -1.0, 0.0], up=(0.0, 0.0, 1.0), distance_cm=self._front_distance_cm)

    def set_top_view(self):
        """Top-down view from positive Z axis; right side points to +X."""
        self._keep_world_z_vertical = False
        self._apply_camera_pose([0.0, 0.0, 1.0], up=(0.0, 1.0, 0.0), distance_cm=self._top_distance_cm)

    def limit_up_vector(self):
        """Prevent roll by keeping the current view's up vector fixed."""
        if not self._vis_ready or self._is_destroyed:
            return

        ctr = self.vis.get_view_control()
        ctr.set_up(self._current_up)

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
            if self._keep_world_z_vertical:
                self.limit_up_vector()
            self.vis.update_renderer()

            if not self._first_frame_emitted:
                self._first_frame_emitted = True
                self.first_frame_ready.emit()
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

