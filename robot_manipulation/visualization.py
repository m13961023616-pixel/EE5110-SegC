"""Optional offscreen render; PNG encoding uses only the Python standard library."""
import struct
import zlib
import mujoco


def save_snapshot(env, path):
    with mujoco.Renderer(env.model, height=600, width=800) as renderer:
        renderer.update_scene(env.data, camera='overview')
        rgb = renderer.render()

    def chunk(tag, payload):
        return struct.pack('>I', len(payload)) + tag + payload + struct.pack('>I', zlib.crc32(tag + payload) & 0xffffffff)

    height, width, _ = rgb.shape
    raw = b''.join(b'\0' + row.tobytes() for row in rgb)
    header = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
    path.write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', header) +
                     chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))
