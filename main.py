import sys


import numpy as np
import pyvista as pv
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QListWidget, QPushButton, QSlider, 
                             QLabel, QGroupBox, QFileDialog, QScrollArea)
from PyQt5.QtCore import Qt, QTimer
from pyvistaqt import QtInteractor

from Libraries.GeometryContainer import ActorContainer, VectorContainer
from Libraries.ReplayPlayer import ReplayPlayer
from Libraries.Transform import MatrixTransform

import os
if sys.platform == "linux":
    os.environ["QT_QPA_PLATFORM"] = "xcb"
elif sys.platform == "win32":
    os.environ["QT_QPA_PLATFORM"] = "windows"

print("Matrix-SMT-Visual-Debugger")
print("Current QT platform:", os.environ.get("QT_QPA_PLATFORM"))
print("Available QT plugins:", QApplication.libraryPaths())

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Matrix-SMT Visual Debugger")
        self.setGeometry(100, 100, 1280, 720)

        self.geometry: dict = {}
        self.vectors: list = []
        self.current_vector: int = 0

        self.player = ReplayPlayer()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        left_panel = QVBoxLayout()
        left_panel.setContentsMargins(5, 5, 5, 5)

        self.object_list = QListWidget()
        self.object_list.itemClicked.connect(self.on_object_selected)
        self.object_list.itemDoubleClicked.connect(self.on_object_double_clicked)
        left_panel.addWidget(QLabel("Objects:"))
        left_panel.addWidget(self.object_list)

        self.properties_display = QLabel("Select an object to view properties")
        self.properties_display.setWordWrap(True)
        self.properties_display.setAlignment(Qt.AlignTop)
        scroll = QScrollArea()
        scroll.setWidget(self.properties_display)
        scroll.setWidgetResizable(True)
        left_panel.addWidget(QLabel("Object properties:"))
        left_panel.addWidget(scroll)

        # Add left panel to main layout
        left_container = QWidget()
        left_container.setLayout(left_panel)
        left_container.setFixedWidth(300)
        main_layout.addWidget(left_container)

        # Right panel (renderer and controls)
        right_panel = QVBoxLayout()

        # PyVista Qt interactor
        self.plotter = QtInteractor(self)
        right_panel.addWidget(self.plotter.interactor)

        self.plotter.enable_terrain_style()
        self.plotter.enable_anti_aliasing()
        
        # Configure axes
        self.plotter.add_axes(
            xlabel="X (Left)",
            ylabel="Y (Up)",
            zlabel="Z (Forward)",
            line_width=5,
            labels_off=False
        )
        
        # Set initial camera position
        self.plotter.camera_position = [
            (-10, 10, 10),
            (0, 0, 0),
            (0, 1, 0)
        ]

        # Animation controls
        controls_group = QGroupBox("Animation Controls")
        controls_layout = QVBoxLayout()

        # Top row buttons
        button_row = QHBoxLayout()
        self.open_button = QPushButton("Open record")
        self.open_button.clicked.connect(self.open_animation_file)
        button_row.addWidget(self.open_button)

        self.play_button = QPushButton("Play")
        self.play_button.clicked.connect(self.toggle_play)
        button_row.addWidget(self.play_button)

        self.reverse_button = QPushButton("Reverse")
        self.reverse_button.clicked.connect(self.toggle_direction)
        button_row.addWidget(self.reverse_button)

        self.step_back_button = QPushButton("< Step")
        self.step_back_button.clicked.connect(lambda: self.step_animation(-1))
        button_row.addWidget(self.step_back_button)

        self.step_forward_button = QPushButton("Step >")
        self.step_forward_button.clicked.connect(lambda: self.step_animation(1))
        button_row.addWidget(self.step_forward_button)

        controls_layout.addLayout(button_row)

        # Speed slider
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("Speed:"))
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setMinimum(1)
        self.speed_slider.setMaximum(50)
        self.speed_slider.setValue(5)
        self.speed_slider.valueChanged.connect(self.update_speed)
        speed_layout.addWidget(self.speed_slider)
        self.speed_label = QLabel("1.0x")
        speed_layout.addWidget(self.speed_label)
        controls_layout.addLayout(speed_layout)

        # Progress slider
        progress_layout = QHBoxLayout()
        progress_layout.addWidget(QLabel("Progress:"))
        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setMinimum(0)
        self.progress_slider.setMaximum(100)
        self.progress_slider.valueChanged.connect(self.seek_animation)
        progress_layout.addWidget(self.progress_slider)

        self.frame_label = QLabel("Frame: 0/0 | Time: 0.00s")
        self.frame_label.setAlignment(Qt.AlignLeft)
        self.frame_label.setFixedWidth(200)
        progress_layout.addWidget(self.frame_label)
        controls_layout.addLayout(progress_layout)

        controls_group.setLayout(controls_layout)
        right_panel.addWidget(controls_group)

        # Add right panel to main layout
        main_layout.addLayout(right_panel)

        # Animation timer
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.update_animation)
        self.animation_timer.setInterval(16)

        # Add some test objects
        self.add_test_objects()

    def add_test_objects(self):
        """Add some test objects to the scene."""
        cube = pv.Cube(center=(0, 0, 0), x_length=1, y_length=2,z_length=1)
        self.plotter.add_mesh(cube, color="red", name="Cube")
        
        sphere = pv.Sphere(center=(2, 0, 0))
        self.plotter.add_mesh(sphere, color="blue", name="Sphere")

        cylinder = pv.Cylinder(center=(0, 2, 0), direction=(1, 1, 1), height=1.5)
        self.plotter.add_mesh(cylinder, color="green", name="Cylinder")

        self.update_object_list()

    def update_object_list(self):
        """Update the list of objects in the scene."""
        self.object_list.clear()

        for obj in self.geometry.values():
            if isinstance(obj.actor, pv.Actor):
                self.object_list.addItem(obj.actor.name)

    def on_object_selected(self, item):
        """Displays properties of the selected object."""
        obj_name = item.text()
        actor = self.plotter.actors[obj_name]

        container = None
        for obj in self.geometry.values():
            if(obj_name == f"{obj.name}: id[{obj.id}]"):
                container = obj
                break

        
        properties = {
            "Name": obj_name,
            "ID": str(container.id),
            "Position": "",
            "x": str(container.position[0]),
            "y": str(container.position[1]),
            "z": str(container.position[2]),
            "Rotation": "",
            "rx": str(container.rotation[0]),
            "ry": str(container.rotation[1]),
            "rz": str(container.rotation[2]),
            "rw": str(container.rotation[3]),
            "Visibility": str(actor.visibility),
            "Meta-data": container.metadata
        }
        
        text = "\n".join(f"{k}: {v}" for k, v in properties.items())
        self.properties_display.setText(text)

    def on_object_double_clicked(self, item):
        self.on_object_selected(item)

        obj_name = item.text()

        container = None
        for obj in self.geometry.values():
            if(obj_name == f"{obj.name}: id[{obj.id}]"):
                container = obj
                break
                
        if(container != None):
            self.plotter.camera_position = [
                (container.position[0], container.position[1] + 15, container.position[2] - 15),
                (container.position[0], container.position[1], container.position[2]),
                (0, 1, 0)
            ]


    def open_animation_file(self):
        """Open a JSON animation file."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Open replay File", "", "BSON Files (*.bson)")
        if filepath:
            self.player.load_replay(filepath)
            self.progress_slider.setMaximum(len(self.player.frames) - 1)
            self.instatiate_geometry()
            self.update_display()

    def toggle_play(self):
        """Toggle animation playback."""
        self.player.is_playing = not self.player.is_playing
        self.play_button.setText("Pause" if self.player.is_playing else "Play")
        if self.player.is_playing:
            self.animation_timer.start()
        else:
            self.animation_timer.stop()
            

    def toggle_direction(self):
        """Toggle animation direction."""
        self.player.direction *= -1
        self.reverse_button.setDown(self.player.direction == -1)

    def step_animation(self, step):
        """Step through animation manually."""
        self.player.direction = np.sign(step)
        self.player.step()
        self.update_display()

    def update_animation(self):
        """Update animation frame automatically."""
        if self.player.is_playing:
            self.player.step()
            self.update_display()

    def update_display(self):
        """Update the scene based on current animation frame."""
        self.hide_debug_geometry()

        frame_data = self.player.get_current_frame_data()
        if not frame_data:
            return

        # Update progress slider
        self.progress_slider.setValue(self.player.current_frame)

        current_time = round(frame_data.get("t", 0), 5)
        self.frame_label.setText(f"Frame: {self.player.current_frame}/{self.player.number_of_frames} | Time: {current_time}s")

        # Apply transformations to objects
        states = frame_data.get("states", [])
        for state in states:
            actor = self.geometry[state["id"]].actor
            self.geometry[state["id"]].position = state['p']
            self.geometry[state["id"]].rotation = state['r']

            if(state["i"] == "i"):
                actor.visibility = True
            else:
                actor.visibility = False

            if(self.player.current_frame == len(self.player.frames) - 1):
                actor.visibility = False

            self.geometry[state["id"]].metadata = state["m"]

            position = state['p']
            rotation = state['r']


            transform = MatrixTransform.set_transform(position, rotation)
            actor.SetUserTransform(transform)

        commands = frame_data.get("cmd", [])
        for command in commands:
            if(command["t"] == "v"):
                vector = self.vectors[self.current_vector]
                direction = [command.get("vx", 0), 
                            command.get("vy", 1), 
                            command.get("vz", 0)]
                
                position = [command.get("ox", 0), command.get("oy", 0), command.get("oz", 0)]
                transform = MatrixTransform.set_transform_from_vector(position, direction) 
                vector.actor.SetUserTransform(transform)

                vector.actor.visibility = True

                if(self.current_vector < len(self.vectors) - 1):
                    self.current_vector += 1

        self.plotter.render()

    def update_speed(self, value):
        """Update animation speed."""
        self.player.speed = value / 5.0  # Convert 1-10 to 0.2-2.0
        self.speed_label.setText(f"{self.player.speed:.1f}x")
        self.animation_timer.setInterval(int(100 / self.player.speed))

    def seek_animation(self, value):
        """Seek to a specific animation frame."""
        self.player.current_frame = value
        self.update_display()

    def instatiate_geometry(self):
        for actor in self.plotter.actors.values():
            self.plotter.remove_actor(actor)

        self.geometry.clear()
        origin = ActorContainer()
        origin.id = -1
        origin.name = "origin"
        origin.position = [0, 0, 0]
        origin.rotation = [0, 0, 0, 1]

        floor = pv.Plane(
            center=(0, 0, 0),
            direction=(0, 1, 0),
            i_size=20,
            j_size=20
        )
        plane_actor = self.plotter.add_mesh(
            floor, 
            color='lightgray', 
            show_edges=True,
            edge_color='gray',
            opacity=0.5,
            name=f"{origin.name}: id[{origin.id}]"
        )

        origin.actor = plane_actor

        self.geometry[origin.id] = origin
        
        for geom in self.player.objects:
            container = ActorContainer()
            container.id = geom["id"]
            container.name = geom["name"]
            
            if geom["type"] == "box":
                mesh = pv.Cube(x_length=geom["half_dimentions"][0] * 2, y_length=geom["half_dimentions"][1] * 2, z_length=geom["half_dimentions"][2] * 2)
            elif geom["type"] == "sphere":
                mesh = pv.Sphere(radius=geom["radius"])
            elif geom["type"] == "capsule":
                cylinder = pv.Cylinder(
                    center=(0, 0, 0), 
                    direction=(1, 0, 0), 
                    radius=geom["radius"], 
                    height=geom["half_height"] * 2
                )
                sphere1 = pv.Sphere(
                    radius=geom["radius"], 
                    center=(geom["half_height"], 0, 0)
                )
                sphere2 = pv.Sphere(
                    radius=geom["radius"], 
                    center=(-geom["half_height"], 0, 0)
                )
                mesh = cylinder + sphere1 + sphere2
            elif geom["type"] == "convex":
                vertices = geom["vertices"]
                points = pv.PolyData(vertices)
                mesh = points.delaunay_3d().extract_surface()

            actor = self.plotter.add_mesh(
            mesh,
            color=geom["color"],
            smooth_shading=False,
            reset_camera=False,
            name=f"{container.name}: id[{container.id}]")
            container.actor = actor

            actor.visibility = False
            
            self.geometry[container.id] = container
        
        self.update_object_list()

        for i in range(0, 50):
            vector = VectorContainer()

            arrow = pv.Arrow(
                    start = (0, 0, 0), 
                    direction = (0, 1, 0), 
                    tip_length = 0.05,
                    tip_radius = 0.07,
                    tip_resolution = 2,
                    shaft_radius = 0.01,
                    shaft_resolution = 1,
                )
            vector.arrow = arrow

            actor = self.plotter.add_mesh(arrow, color='red', opacity=1.0)
            actor.visibility = False
            vector.actor = actor

            self.vectors.append(vector)

    def hide_debug_geometry(self):
        for vector in self.vectors:
            vector.actor.visibility = False
        self.current_vector = 0

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())