import vtk
import numpy as np
from scipy.spatial.transform import Rotation as R

class MatrixTransform:
    @staticmethod
    def SetTransform(position: list, rotation: list):
        transform = vtk.vtkTransform()
        transform.PostMultiply()
            
        if not np.allclose(rotation, [0, 0, 0, 1]):
            mesh_rotation = R.from_quat(rotation)
            angle = np.degrees(mesh_rotation.magnitude())
            if angle > 0:
                axis = mesh_rotation.as_rotvec() / mesh_rotation.magnitude()
                transform.RotateWXYZ(angle, *axis)
            
        transform.Translate(position)

        return transform