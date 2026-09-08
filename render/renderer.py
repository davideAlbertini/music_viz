"""Window-independent shader renderer.

Owns nothing but a moderngl context, so the same object can drive an interactive
window today and a headless framebuffer for video export later.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Mapping

import moderngl as mgl
import numpy as np
from PIL import Image, ImageOps

FULLSCREEN_TRIANGLE_STRIP = np.array(
    [-1.0, -1.0, 0.0,
     +1.0, -1.0, 0.0,
     -1.0, +1.0, 0.0,
     +1.0, +1.0, 0.0],
    dtype="f4",
)

#: Supplied to every shader; not all of them declare these, which is fine.
OPTIONAL_UNIFORMS = {"time", "frame", "resolution"}


class ShaderRenderer:
    def __init__(self, ctx: mgl.Context, config, root_dir: Path | str, size=(1024, 576)):
        self.ctx = ctx
        self.config = config
        self.root = Path(root_dir)
        self.size = tuple(size)
        self.frame_index = 0
        self._missing_uniforms: set[str] = set()

        self.prog = self._load_program(config.program)
        self.vbo = ctx.buffer(FULLSCREEN_TRIANGLE_STRIP.tobytes())
        self.vao = ctx.vertex_array(self.prog, [(self.vbo, "3f", "in_position")])

        self.textures: Dict[str, mgl.Texture] = {}
        self._load_textures(config.textures)

        self.set_uniform("resolution", self.size)

    # -- resources ----------------------------------------------------------

    def _read(self, relative: str) -> str:
        return (self.root / relative).read_text(encoding="utf-8")

    def _load_program(self, program: Mapping[str, str]) -> mgl.Program:
        return self.ctx.program(
            vertex_shader=self._read(program["vertex"]),
            fragment_shader=self._read(program["fragment"]),
        )

    def _load_textures(self, textures: Mapping[str, object]) -> None:
        for unit, (name, entry) in enumerate(textures.items()):
            spec = {"path": entry} if isinstance(entry, str) else dict(entry)
            image = Image.open(self.root / spec["path"]).convert("RGBA")
            image = ImageOps.flip(image)
            tex = self.ctx.texture(image.size, 4, image.tobytes())
            tex.filter = (mgl.LINEAR, mgl.LINEAR)
            tex.swizzle = spec.get("swizzle", "GGGG")
            tex.repeat_x = tex.repeat_y = True
            tex.use(location=unit)
            self.set_uniform(name, unit)
            self.textures[name] = tex

    # -- uniforms -----------------------------------------------------------

    def set_uniform(self, name: str, value) -> None:
        try:
            self.prog[name] = value
        except KeyError:
            if name not in OPTIONAL_UNIFORMS and name not in self._missing_uniforms:
                self._missing_uniforms.add(name)
                print(f"Uniform '{name}' not used in shader")

    def set_size(self, width: int, height: int) -> None:
        self.size = (width, height)
        self.set_uniform("resolution", self.size)

    # -- drawing ------------------------------------------------------------

    def render(self, t: float, uniforms: Mapping[str, float], clear: bool = True) -> None:
        if clear:
            self.ctx.clear()
        self.set_uniform("time", t)
        self.set_uniform("frame", self.frame_index)
        for name, value in uniforms.items():
            self.set_uniform(name, value)
        for unit, tex in enumerate(self.textures.values()):
            tex.use(location=unit)
        self.vao.render(mgl.TRIANGLE_STRIP)
        self.frame_index += 1

    def release(self) -> None:
        for tex in self.textures.values():
            tex.release()
        self.textures.clear()
        self.vao.release()
        self.vbo.release()
        self.prog.release()
