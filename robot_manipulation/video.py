"""Optional real physics recording, streamed directly to FFmpeg."""
from pathlib import Path
import mujoco
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg


class Recorder:
    def __init__(self, env, path, fps=20):
        self.env, self.fps = env, fps
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.renderer = mujoco.Renderer(env.model, height=600, width=800)
        self.writer = imageio_ffmpeg.write_frames(str(path), (800, 600), fps=fps,
                                                  codec='libx264', quality=7, macro_block_size=8)
        self.writer.send(None)
        self.font = ImageFont.truetype('arial.ttf', 20)
        self.title = 'EE5110 Segment C | YCB + Franka Panda'
        self.status = 'Initialization'
        self.next_time = 0.
        card = Image.new('RGB', (800, 600), '#182532')
        draw = ImageDraw.Draw(card)
        for y, line in enumerate([self.title, 'Mesh-based grasp candidates + collision-checked IK',
                                  'Physical contact grasping: no weld or teleport',
                                  'Pick, lift, transport, release and verify',
                                  'Demonstration recording; see report for all trials']):
            draw.text((35, 150 + y * 50), line, font=self.font, fill='white')
        for _ in range(2 * fps):
            self.writer.send(np.asarray(card))

    def capture(self):
        if self.env.data.time < self.next_time:
            return
        self.next_time = self.env.data.time + 1 / self.fps
        self.renderer.update_scene(self.env.data, camera='overview')
        frame = Image.fromarray(self.renderer.render())
        draw = ImageDraw.Draw(frame)
        draw.rectangle((0, 0, 800, 70), fill='#182532')
        draw.text((12, 8), self.title, font=self.font, fill='white')
        draw.text((12, 37), f'{self.env.object_id} | {self.status}', font=self.font, fill='#8bd9c5')
        self.writer.send(np.asarray(frame))

    def reset_time(self):
        self.next_time = 0.

    def close(self):
        self.writer.close()
        self.renderer.close()
