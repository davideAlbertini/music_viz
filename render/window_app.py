"""Thin moderngl-window shell around :class:`ShaderRenderer`.

All it does is own a window, advance time, and pull the current feature frame
from whichever provider was injected.
"""
from __future__ import annotations

import moderngl_window as mglw

from render.renderer import ShaderRenderer
from shader_config import PROJECT_ROOT


class ShaderWindow(mglw.WindowConfig):
    gl_version = (3, 3)
    window_size = (1024, 576)
    resizable = True
    vsync = True
    title = "music_viz"

    # Injected before mglw.run_window_config().
    session = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._revision = self.session.config_revision
        self._reported: set[str] = set()
        self.renderer = ShaderRenderer(
            self.ctx, self.session.config, PROJECT_ROOT, size=self.wnd.size
        )

    def _reload_if_stale(self) -> None:
        """Swapping preset means a new program and textures; only the GL thread may do it."""
        session = self.session
        if session.config_revision == self._revision:
            return
        self._revision = session.config_revision
        try:
            renderer = ShaderRenderer(
                self.ctx, session.config, PROJECT_ROOT, size=self.wnd.size
            )
        except Exception as exc:
            print(f"Could not load shader '{session.config.name}': {exc}")
            return
        self.renderer.release()
        self.renderer = renderer

    def on_render(self, time: float, frame_time: float):
        try:
            self._reload_if_stale()

            if self.wnd.size != self.renderer.size:
                self.ctx.viewport = (0, 0, *self.wnd.size)
                self.renderer.set_size(*self.wnd.size)

            session = self.session
            provider = session.provider
            frame = (provider.get(session.transport.position) if provider is not None
                     else session.config.feature_set.empty_frame())
            uniforms = session.config.mappings.evaluate(frame, frame_time)
            self.renderer.render(time, uniforms)
        except Exception as exc:
            # One bad frame must not tear down the window; mglw aborts its loop on raise.
            key = f"{type(exc).__name__}: {exc}"
            if key not in self._reported:
                self._reported.add(key)
                print(f"Render error (suppressed further repeats): {key}")

    def on_resize(self, width: int, height: int):
        self.ctx.viewport = (0, 0, width, height)
        self.renderer.set_size(width, height)

    def on_close(self):
        self.renderer.release()
