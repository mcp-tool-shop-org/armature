"""A backend that renders arithmetic instead of pixels.

It exists so the gate tests can drive **the real `run_export`** — the actual function
that performs the write — without Blender. A gate tested through a copy of itself is
not tested; this drives the production call path.

The synthetic subject is a filled rectangle at a known place in the frame with a known
depth ramp, so the expected mask bbox is exact and G4 can be pushed red on purpose.
"""

import numpy as np


class FakeBackend:
    name = "fake"

    def __init__(self, width, height, *, box=(10, 20, 60, 90), z_near=2.0, z_far=5.0,
                 lie_about_bbox=False, breathe=0.0, moves=False):
        self.width = width
        self.height = height
        self.box = box
        self.z_near = z_near
        self.z_far = z_far
        self.lie_about_bbox = lie_about_bbox
        self.breathe = breathe
        # `moves` reports whether the subject's geometry changes between frames — G6's
        # quantity. The default is False and that is the honest default: this backend's
        # box is in the same place every frame, so a per-frame spec driven by it SHOULD
        # trip G6. That is the failure G6 exists for, reproduced without Blender.
        self.moves = moves
        self.prepared = False

    def prepare(self, spec, asset_path, width, height, work_dir, need_normal):
        self.prepared = True
        self.need_normal = need_normal
        return {"fake": True, "asset": asset_path}

    def render_frame(self, index, count):
        w, h = self.width, self.height
        x0, y0, x1, y1 = self.box
        alpha = np.zeros((h, w), dtype=np.float64)
        alpha[y0 : y1 + 1, x0 : x1 + 1] = 1.0

        # Depth ramps left (near) to right (far). `breathe` widens the near/far window
        # frame by frame, which is what P3 is about.
        grow = 1.0 + self.breathe * (index / max(count - 1, 1))
        near, far = self.z_near, self.z_near + (self.z_far - self.z_near) * grow
        z = np.full((h, w), 1e10, dtype=np.float64)
        ramp = np.linspace(near, far, x1 - x0 + 1)
        z[y0 : y1 + 1, x0 : x1 + 1] = ramp[None, :]

        normal_world = None
        if self.need_normal:
            normal_world = np.zeros((h, w, 3), dtype=np.float64)
            normal_world[..., 2] = 1.0

        projected = (x0, y0, x1, y1)
        if self.lie_about_bbox:
            projected = (0, 0, w - 1, h - 1)

        return {
            "z": z,
            "alpha": alpha,
            "normal_world": normal_world,
            "cam_rot_3x3": np.eye(3),
            "projected_bbox": projected,
            "azimuth_deg": 360.0 * index / count,
            "camera_matrix": np.eye(4).tolist(),
            "scene_frame": 1 + index,
            "geometry_signature": f"frame{index}" if self.moves else "static-subject",
        }

    def provenance(self):
        return {"backend": "fake", "numpy": np.__version__}


def make_spec(tmp_path, width=64, height=96, count=9, channels=("depth", "normal", "mask", "edge")):
    asset = tmp_path / "subject.glb"
    asset.write_bytes(b"glTF\x02\x00\x00\x00not-a-real-glb")
    return {
        "spec_version": 1,
        "name": "unit",
        "generator": "wan-vace",
        "asset": {"path": str(asset)},
        "resolution": {"width": width, "height": height},
        "frames": {"count": count, "fps": 16},
        "channels": list(channels),
    }
