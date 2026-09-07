import sys
import threading
import numpy as np
from queue import Queue
from PyQt5.QtWidgets import QApplication
import moderngl_window as mglw

import io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from audio_controller import AudioController
from shader_controller import ShaderController
from control_GUI import ShaderParameterPage 
from shader_config import ShaderConfig


if __name__ == '__main__':
    # Shared data structures
    audio_features = np.zeros(6,)  # Fixed to 6 MFCC coefficients
    audio_features_queue = Queue()

    shader_config = ShaderConfig(
        name='raveScreen',
        textures={
            'noiseTex': '../textures/noise.png',
            'indexTex': '../textures/n1d.png',
            'fontTex': '../textures/ascii.png',
        }
    )

    # Assign shared resources to ShaderController class attributes
    ShaderController.shader_config = shader_config
    ShaderController.audio_features = audio_features
    ShaderController.audio_features_queue = audio_features_queue

    # Initialize AudioController
    audio_controller = AudioController(
        './music/permute.wav',
        audio_features=audio_features,
        queue=audio_features_queue
    )

    # Start the audio controller thread
    audio_thread = threading.Thread(target=audio_controller.play_and_extract_features)
    audio_thread.start()

    # Start the shader window (using run_window_config)
    shader_thread = threading.Thread(target=lambda: mglw.run_window_config(ShaderController))
    shader_thread.start()

    # Initialize PyQt application and GUI
    app = QApplication(sys.argv)
    gui_window = ShaderParameterPage(audio_features, shader_config)
    gui_window.show()

    # Start the GUI event loop
    sys.exit(app.exec_())