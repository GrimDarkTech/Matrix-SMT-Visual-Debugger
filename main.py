import json
import numpy as np
from scipy.spatial.transform import Rotation as R
from typing import Dict, List, Any
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QSlider, QLabel, QFileDialog, QFrame
)
from PyQt5.QtCore import Qt, QTimer
import pyvista as pv
from pyvistaqt import BackgroundPlotter
import vtk

class PhysXVisualizer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PhysX Visualizer")
        self.resize(1200, 900)
        
        # Data storage
        self.parsed_objects: List[Dict[str, Any]] = []
        self.parsed_frames: List[Dict[int, Dict[str, np.ndarray]]] = []
        self.current_frame: int = 0
        self.actors: Dict[int, pv.Actor] = {}
        self.original_meshes: Dict[int, pv.DataSet] = {}
        
        # Playback control
        self.is_playing: bool = False
        self.play_direction: int = 1
        self.playback_speed: float = 1.0
        
        # Create UI
        self.create_ui()
        
        # Setup visualization
        self.create_visualization()
        
        # Animation timer
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.update_animation)
        self.animation_timer.setInterval(16)  # ~60fps

    def create_ui(self):
        """Create the main UI layout."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)

        # Create container for the plotter
        self.plotter_container = QWidget()
        main_layout.addWidget(self.plotter_container, stretch=1)
        
        # Control panel
        control_frame = QFrame()
        control_frame.setFrameShape(QFrame.StyledPanel)
        main_layout.addWidget(control_frame)
        
        control_layout = QVBoxLayout(control_frame)
        
        # Top row - file controls
        top_row = QHBoxLayout()
        self.open_button = QPushButton("Open JSON")
        self.open_button.clicked.connect(self.open_file)
        top_row.addWidget(self.open_button)
        control_layout.addLayout(top_row)
        
        # Middle row - playback controls
        middle_row = QHBoxLayout()
        
        self.play_button = QPushButton("Play")
        self.play_button.clicked.connect(self.toggle_play)
        middle_row.addWidget(self.play_button)
        
        self.reverse_button = QPushButton("Reverse")
        self.reverse_button.clicked.connect(self.reverse_playback)
        middle_row.addWidget(self.reverse_button)
        
        self.step_back_button = QPushButton("< Step")
        self.step_back_button.clicked.connect(lambda: self.step_frame(-1))
        middle_row.addWidget(self.step_back_button)
        
        self.step_forward_button = QPushButton("Step >")
        self.step_forward_button.clicked.connect(lambda: self.step_frame(1))
        middle_row.addWidget(self.step_forward_button)
        
        self.speed_label = QLabel("Speed:")
        middle_row.addWidget(self.speed_label)
        
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(1, 50)
        self.speed_slider.setValue(10)
        self.speed_slider.valueChanged.connect(self.set_playback_speed)
        middle_row.addWidget(self.speed_slider, stretch=1)
        
        control_layout.addLayout(middle_row)
        
        # Bottom row - frame navigation
        bottom_row = QHBoxLayout()
        
        self.frame_slider = QSlider(Qt.Horizontal)
        self.frame_slider.valueChanged.connect(self.on_slider_changed)
        bottom_row.addWidget(self.frame_slider, stretch=1)
        
        self.frame_label = QLabel("Frame: 0/0 | Time: 0.00s")
        bottom_row.addWidget(self.frame_label)
        
        control_layout.addLayout(bottom_row)

    def create_visualization(self):
        """Create the PyVista visualization window."""
        # Create the plotter with parent=self.plotter_container
        self.plotter = BackgroundPlotter(show=False)

        self.plotter.render_window.SetDesiredUpdateRate(60)
        self.plotter.render_window.LineSmoothingOn()
        self.plotter.render_window.PolygonSmoothingOn()
        
        self.plotter_container.layout = QVBoxLayout()
        self.plotter_container.layout.addWidget(self.plotter.interactor)
        self.plotter_container.setLayout(self.plotter_container.layout)
        
        # Configure plotter
        self.plotter.enable_terrain_style()
        self.plotter.enable_anti_aliasing()
        self.plotter.add_axes()
        
        # Add floor
        floor = pv.Plane(
            center=(0, 0, 0),
            direction=(0, 1, 0),
            i_size=20,
            j_size=20
        )
        self.plotter.add_mesh(
            floor, 
            color='lightgray', 
            show_edges=True,
            edge_color='gray',
            opacity=0.5
        )
        
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

    def open_file(self):
        """Open and parse a JSON file with simulation data."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open JSON File", "", "JSON Files (*.json)"
        )
        
        if not file_path:
            return
            
        try:
            with open(file_path, 'r') as f:
                raw_data = json.load(f)
                
            # Clear previous data
            self.reset_visualization()
            
            # Parse objects data
            for obj in raw_data.get("objects", []):
                parsed_obj = {
                    "id": int(obj["id"]),
                    "type": str(obj["type"]),
                    "color": np.array(obj.get("color", [0.5, 0.5, 0.5]), dtype=np.float32)
                }
                
                if obj["type"] == "box":
                    parsed_obj["scale"] = np.array(obj.get("scale", [1.0, 1.0, 1.0]), dtype=np.float32)
                elif obj["type"] == "sphere":
                    parsed_obj["radius"] = float(obj.get("radius", 0.5))
                    
                self.parsed_objects.append(parsed_obj)
            
            # Pre-parse frames data for faster access
            for frame in raw_data.get("frames", []):
                frame_states = {}
                for state in frame.get("states", []):
                    obj_id = int(state["id"])
                    frame_states[obj_id] = {
                        "position": np.array(state.get("position", [0, 0, 0]), dtype=np.float32),
                        "rotation": np.array(state.get("rotation", [0, 0, 0, 1]), dtype=np.float32)
                    }
                self.parsed_frames.append(frame_states)
            
            self.current_frame = 0
            self.frame_slider.setRange(0, len(self.parsed_frames) - 1 if self.parsed_frames else 0)
            self.update_frame_label()
            
            # Create initial meshes for all objects
            self.initialize_objects()
            self.plot_frame_data()
            
        except Exception as e:
            print(f"Error loading file: {e}")

    def reset_visualization(self):
        """Reset visualization state."""
        for actor in self.actors.values():
            self.plotter.remove_actor(actor)
        self.actors.clear()
        self.original_meshes.clear()
        self.parsed_objects.clear()
        self.parsed_frames.clear()
        self.current_frame = 0

    def initialize_objects(self):
        """Create initial meshes for all objects."""
        for obj in self.parsed_objects:
            obj_id = obj["id"]
            
            if obj["type"] == "box":
                mesh = pv.Cube()
                mesh.scale(obj["scale"], inplace=True)
                self.original_meshes[obj_id] = mesh.copy()
            elif obj["type"] == "sphere":
                mesh = pv.Sphere(radius=obj["radius"])
                self.original_meshes[obj_id] = mesh.copy()
            
            # Create actor with initial position/rotation (will be updated in plot_frame_data)
            actor = self.plotter.add_mesh(
                mesh,
                color=obj["color"],
                smooth_shading=False,
                reset_camera=False,
                name=str(obj_id)
            )
            self.actors[obj_id] = actor

    def plot_frame_data(self):
        """Update objects on screen using pre-parsed data."""
        if not self.parsed_frames or self.current_frame >= len(self.parsed_frames):
            return
            
        frame_states = self.parsed_frames[self.current_frame]
        
        for obj in self.parsed_objects:
            obj_id = obj["id"]
            if obj_id not in frame_states:
                continue
                
            state = frame_states[obj_id]
            position = state["position"]
            rotation = state["rotation"]
            actor = self.actors[obj_id]
            
            # Get the original mesh (without transformations)
            mesh = self.original_meshes[obj_id]
            
            # Create transformation
            transform = vtk.vtkTransform()
            transform.PostMultiply()
            
            # Apply rotation if needed
            if not np.allclose(rotation, [0, 0, 0, 1]):
                mesh_rotation = R.from_quat(rotation)
                angle = np.degrees(mesh_rotation.magnitude())
                if angle > 0:
                    axis = mesh_rotation.as_rotvec() / mesh_rotation.magnitude()
                    transform.RotateWXYZ(angle, *axis)
            
            # Apply translation
            transform.Translate(position)
            
            # Update actor transformation
            actor.SetUserTransform(transform)
            actor.GetProperty().SetColor(obj["color"])
            
            # Force render update for smooth animation
            self.plotter.render()

    def toggle_play(self):
        """Toggle animation playback."""
        if not self.parsed_frames:
            return
            
        self.is_playing = not self.is_playing
        self.play_button.setText("Pause" if self.is_playing else "Play")
        
        if self.is_playing:
            self.animation_timer.start()
        else:
            self.animation_timer.stop()

    def reverse_playback(self):
        """Reverse the playback direction."""
        self.play_direction *= -1
        if self.play_direction == -1:
            self.reverse_button.setStyleSheet("background-color: red")
        else:
            self.reverse_button.setStyleSheet("")

    def set_playback_speed(self, value):
        """Set the playback speed multiplier."""
        self.playback_speed = value / 10.0  # Slider range is 1-50, we want 0.1-5.0

    def step_frame(self, step):
        """Advance or rewind the animation by the given number of frames."""
        if not self.parsed_frames:
            return
            
        new_frame = self.current_frame + (step * self.play_direction)
        max_frame = len(self.parsed_frames) - 1
        
        if new_frame > max_frame:
            new_frame = 0
        elif new_frame < 0:
            new_frame = max_frame
            
        if new_frame != self.current_frame:
            self.current_frame = new_frame
            self.frame_slider.setValue(self.current_frame)
            self.update_frame_label()
            self.plot_frame_data()

    def on_slider_changed(self, value):
        """Handle slider changes to navigate frames."""
        if value != self.current_frame and 0 <= value < len(self.parsed_frames):
            self.current_frame = value
            self.update_frame_label()
            self.plot_frame_data()

    def update_frame_label(self):
        """Update the frame information label."""
        if not self.parsed_frames:
            self.frame_label.setText("Frame: 0/0 | Time: 0.00s")
            return
            
        total_frames = len(self.parsed_frames)
        time = self.current_frame * 0.016  # Approximate time based on frame count
        self.frame_label.setText(
            f"Frame: {self.current_frame + 1}/{total_frames} | Time: {time:.2f}s"
        )

    def update_animation(self):
        """Update animation frame based on playback speed."""
        if not self.is_playing or not self.parsed_frames:
            return
            
        # Calculate frames to skip based on playback speed
        frames_to_advance = max(1, int(self.playback_speed))
        
        for _ in range(frames_to_advance):
            new_frame = self.current_frame + self.play_direction
            max_frame = len(self.parsed_frames) - 1
            
            if new_frame > max_frame:
                new_frame = 0
            elif new_frame < 0:
                new_frame = max_frame
                
            self.current_frame = new_frame
        
        self.frame_slider.setValue(self.current_frame)
        self.update_frame_label()
        self.plot_frame_data()

    def closeEvent(self, event):
        """Handle window close event."""
        self.animation_timer.stop()
        if hasattr(self, 'plotter'):
            self.plotter.close()
        event.accept()

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    visualizer = PhysXVisualizer()
    visualizer.show()
    sys.exit(app.exec_())