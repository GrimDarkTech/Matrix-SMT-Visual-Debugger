from bson import loads

class ReplayPlayer:
    def __init__(self):
        self.objects: list = None
        self.frames: list = None
        self.current_frame: int = 0
        self.number_of_frames: int = 0
        self.is_playing: bool = False
        self.speed: float = 1.0
        self.direction: int = 1  # 1 = forward, -1 = backward

    def load_replay(self, filepath):
        with open(filepath, 'rb') as f:
            data = loads(f.read()) 

            self.frames = data.get("frames", [])
            self.objects = data.get("objects", [])
        self.current_frame = 0
        self.number_of_frames = len(self.frames)

    def get_current_frame_data(self):
        if not self.frames:
            return None
        return self.frames[self.current_frame]
        
    def step(self):
        if not self.frames:
            return
        max_frame = len(self.frames) - 1
        self.current_frame = (self.current_frame + self.direction) % (max_frame + 1)