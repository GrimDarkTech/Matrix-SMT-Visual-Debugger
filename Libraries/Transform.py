import vtk
from math import atan2, asin, pi

class MatrixTransform:
    @staticmethod
    def SetTransform(position: list, rotation: list):
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
    def to_axis_angle(rotation: list) -> tuple:
        """Конвертирует кватернион в ось и угол (в радианах)."""
        qx, qy, qz, qw = rotation
        angle_rad = 2 * atan2((qx**2 + qy**2 + qz**2)**0.5, qw)
        if angle_rad == 0:
            return 0, [1, 0, 0]  # Нулевое вращение - произвольная ось
        
        norm = (qx**2 + qy**2 + qz**2)**0.5
        axis = [qx / norm, qy / norm, qz / norm]
        return angle_rad, axis