import vtk
from math import atan2, acos, degrees
import numpy as np

class MatrixTransform:
    @staticmethod
    def set_transform(position: list, rotation: list):
        transform = vtk.vtkTransform()
        transform.PostMultiply()
        
        # Оптимизация: используем RotateWXYZ вместо трёх отдельных вращений
        angle_rad, axis = MatrixTransform.to_axis_angle(rotation)
        if angle_rad != 0:
            angle_deg = angle_rad * 57.29578  # Радианы -> градусы
            transform.RotateWXYZ(angle_deg, *axis)

        transform.Translate(position)
        return transform
    
    @staticmethod
    def set_transform_from_vector(position: list, direction: list):
        transform = vtk.vtkTransform()
        transform.PostMultiply()

        # Нормализуем вектор направления
        direction = np.array(direction, dtype=np.float64)
        magnitude = np.linalg.norm(direction)

        transform.Scale(1, magnitude, 1)

        if magnitude < 1e-6:
            direction = np.array([0, 0, 1])  # Направление по умолчанию - вперед
        else:
            direction = direction / magnitude
        
        # Исходное направление объекта (по умолчанию смотрит вперед по Z)
        default_direction = np.array([0, 1, 0])
        
        # Если направление уже совпадает с исходным, поворот не нужен
        if np.allclose(direction, default_direction):
            transform.Translate(position)
            return transform
        
        # Вычисляем ось и угол поворота
        axis = np.cross(default_direction, direction)
        if np.linalg.norm(axis) < 1e-6:
            # Направления противоположны (поворот на 180 градусов)
            axis = np.array([0, 1, 0])  # Поворачиваем вокруг Y
            angle_deg = 180
        else:
            axis = axis / np.linalg.norm(axis)
            angle_rad = acos(np.clip(np.dot(default_direction, direction), -1, 1))
            angle_deg = degrees(angle_rad)
        
        # Применяем поворот
        transform.RotateWXYZ(angle_deg, *axis)
        
        # Применяем перемещение
        transform.Translate(position)
        
        return transform
    
    @staticmethod
    def to_axis_angle(rotation: list) -> tuple:
        """Конвертирует кватернион в ось и угол (в радианах)."""
        qx, qy, qz, qw = rotation
        angle_rad = 2 * atan2((qx**2 + qy**2 + qz**2)**0.5, qw)
        if angle_rad == 0:
            return 0, [1, 0, 0]  # Нулевое вращение - произвольная ось
        
        norm = (qx**2 + qy**2 + qz**2)**0.5
        axis = [qx / norm, qy / norm, qz / norm]
        return angle_rad, axis