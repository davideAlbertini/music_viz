import sys
import threading
from pathlib import Path

import moderngl_window as mglw
from PyQt5.QtWidgets import QApplication

from gui.main_window import ShaderParameterPage
from render.window_app import ShaderWindow
from session import VizSession
from shader_config import ShaderConfig

TRACK = "./music/Skee Mask - ISS011 - Stressmanagement - 02 Panic Button.wav"
PRESET = "speakerSun"
TEXTURES = {}

#: "online" analyses audio as it plays; "offline" pre-analyses the track and
#: looks features up by transport position, so they stay aligned under seeking.
MODE = "online"
ANALYSIS_RATE_HZ = 60.0


def main() -> int:
    if not Path(TRACK).is_file():
        print(f"Track not found: {TRACK}\nPut a 16-bit WAV there or edit TRACK in main.py.")
        return 1

    app = QApplication(sys.argv)

    config = ShaderConfig.load(PRESET, textures=TEXTURES)
    session = VizSession(TRACK, config, mode=MODE, analysis_rate_hz=ANALYSIS_RATE_HZ)

    ShaderWindow.session = session
    session.start()
    threading.Thread(
        target=lambda: mglw.run_window_config(ShaderWindow), name="ShaderWindow", daemon=True
    ).start()

    gui = ShaderParameterPage(session)
    gui.show()
    app.aboutToQuit.connect(session.close)
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
