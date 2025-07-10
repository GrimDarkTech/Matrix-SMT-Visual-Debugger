import vtk
from math import atan2, acos, degrees
import numpy as np

class MatrixTransform:
    @staticmethod
    def set_transform(position: list, rotation: list):
        transform = vtk.vtkTransform()
        transform.PostMultiply()
        
        angle_rad, axis = MatrixTransform.to_axis_angle(rotation)
        if angle_rad != 0:
            angle_deg = angle_rad * 57.29578
            transform.RotateWXYZ(angle_deg, *axis)

        transform.Translate(position)
        return transform
    
    def set_transform_with_scale(position: list, rotation: list, scale: list):
        transform = vtk.vtkTransform()
        transform.PostMultiply()

        if(scale is not None):
            transform.Scale(scale[0], scale[1], scale[2])
        
        angle_rad, axis = MatrixTransform.to_axis_angle(rotation)
        if angle_rad != 0:
            angle_deg = angle_rad * 57.29578
            transform.RotateWXYZ(angle_deg, *axis)

        transform.Translate(position)
        return transform

    @staticmethod
    def set_transform_from_vector(position: list, direction: list):
        transform = vtk.vtkTransform()
        transform.PostMultiply()
        
        dir_vec = np.array(direction)
        magnitude = np.linalg.norm(dir_vec)
        if magnitude == 0:
            return transform
        
        transform.Scale(1, magnitude, 1)
        dir_vec = dir_vec / np.linalg.norm(dir_vec)
        
        original_dir = np.array([0.0, 1.0, 0.0])
        
        rotation_axis = np.cross(original_dir, dir_vec)
        if np.linalg.norm(rotation_axis) < 1e-6:
            if np.dot(original_dir, dir_vec) < 0:
                transform.RotateWXYZ(180, 1, 0, 0)
        else:
            rotation_axis = rotation_axis / np.linalg.norm(rotation_axis)
            rotation_angle = np.arccos(np.dot(original_dir, dir_vec))
            rotation_angle_deg = np.degrees(rotation_angle)
            transform.RotateWXYZ(rotation_angle_deg, *rotation_axis)
        
        transform.Translate(position)
        
        return transform
        
    @staticmethod
    def to_axis_angle(rotation: list) -> tuple:
        """Конвертирует кватернион в ось и угол (в радианах)."""
        qx, qy, qz, qw = rotation
        angle_rad = 2 * atan2((qx**2 + qy**2 + qz**2)**0.5, qw)
        if angle_rad == 0:
            return 0, [1, 0, 0]
        
        norm = (qx**2 + qy**2 + qz**2)**0.5
        axis = [qx / norm, qy / norm, qz / norm]
        return angle_rad, axis