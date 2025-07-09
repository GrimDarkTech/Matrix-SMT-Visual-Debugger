class ActorContainer:
    def __init__(self):
        self.actor = None 
        self.id: int = -1
        self.name: str = ""
        self.position: list = [0, 0, 0]
        self.rotation: list = [0, 0, 0, 0]
        self.metadata: str = ""
        self.instance: int = 9

class VectorContainer:
    def __init__(self):
        self.actor = None 
class RayContainer:
    def __init__(self):
        self.actor = None 