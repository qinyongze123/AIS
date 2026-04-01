import numpy as np
import open3d as o3d
import sys
import os
import win32gui
from PySide6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, 
                             QHBoxLayout, QWidget, QPushButton, QGridLayout)
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QWindow

# Locate project root and add to sys.path
from pathlib import Path
root = None
for p in Path(__file__).resolve().parents:
    if (p / "remake").is_dir():
        root = str(p)
        break
if root:
    sys.path.insert(0, root)

class Open3DWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Open3D Embedded in PySide6 (Win32)")
        self.resize(1024, 800)

        # Main Widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        # Controls Layout
        self.controls_layout = QHBoxLayout()
        self.btn_left = QPushButton("Move Left")
        self.btn_right = QPushButton("Move Right")
        self.controls_layout.addWidget(self.btn_left)
        self.controls_layout.addWidget(self.btn_right)
        self.main_layout.addLayout(self.controls_layout)

        # Open3D Visualizer Setup
        self.vis = o3d.visualization.Visualizer()
        # Use a unique window name to find it via win32gui
        win_name = "Open3D_Embedded_Window"
        self.vis.create_window(window_name=win_name, width=800, height=600, visible=True)
        
        # Find the window handle (HWND) using the window name
        hwnd = win32gui.FindWindow(None, win_name)
        if hwnd:
            # Create a QWindow from the Win32 handle
            self.o3d_window = QWindow.fromWinId(hwnd)
            # Create a widget container for the QWindow
            self.window_container = QWidget.createWindowContainer(self.o3d_window)
            self.main_layout.addWidget(self.window_container)
        else:
            print("Error: Could not find Open3D window handle.")

        self.setup_scene()
        
        # Buttons logic
        self.btn_left.clicked.connect(lambda: self.move_ball(-0.2))
        self.btn_right.clicked.connect(lambda: self.move_ball(0.2))
        
        # Timer for UI refreshing and Open3D events
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll_vis)
        self.timer.start(16)

    def setup_scene(self):
        # Add 5 static cubes
        for i in range(5):
            mesh_box = o3d.geometry.TriangleMesh.create_box(width=0.4, height=0.4, depth=0.4)
            mesh_box.paint_uniform_color([0.3, 0.7, 0.3]) 
            mesh_box.compute_vertex_normals()
            mesh_box.translate([i * 0.8 - 1.6, 0, 0])
            self.vis.add_geometry(mesh_box)

        # Add 1 red ball
        self.sphere = o3d.geometry.TriangleMesh.create_sphere(radius=0.2)
        self.sphere.paint_uniform_color([1.0, 0, 0])
        self.sphere.compute_vertex_normals()
        self.sphere.translate([0, 0.6, 0])
        self.vis.add_geometry(self.sphere)

    def move_ball(self, delta):
        self.sphere.translate([delta, 0, 0])
        self.vis.update_geometry(self.sphere)
        self.vis.update_renderer()

    def poll_vis(self):
        # Keep Open3D window responsive
        self.vis.poll_events()
        self.vis.update_renderer()

    def closeEvent(self, event):
        self.vis.destroy_window()
        event.accept()

def main():
    app = QApplication(sys.argv)
    window = Open3DWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
