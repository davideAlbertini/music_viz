import moderngl_window as mglw
import moderngl as mgl
import numpy as np
from queue import Empty

from shader_config import ShaderConfig

class ShaderController(mglw.WindowConfig):
    window_size = 1024, 576
    resource_dir = 'programs'
    target_fps = 30

    # Class-level attributes to pass parameters
    shader_config = None
    audio_features = None
    audio_features_queue = None
  
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Shader configuration and shared resources
        self.parameters = self.shader_config.get_all_uniforms()

        # Create screen-aligned quad
        self.quad = mglw.geometry.quad_fs()

        # Load shader program
        self.prog = self.load_program(vertex_shader='vertex_shader.glsl',
                                      fragment_shader='fragment_shader.glsl')
        
        # check if shader_config.texture dict is not empty
        if self.shader_config.textures:
            # Load textures and bind them to the shader
            ctx = 0
            for name, path in self.shader_config.textures.items(): 
                self.tex = self.load_texture_2d(path)
                self.tex.filter = (mgl.LINEAR, mgl.LINEAR)
                self.tex.swizzle = ('GGGG')  # Set swizzle to (1.0, 1.0) for all channels
                self.tex.use(location=ctx)    
                self.set_uniform(name, ctx)  
                ctx +=1  

        # Set initial shader uniforms
        self.set_uniform('resolution', self.window_size)

    def calculate_shader_parameters(self):
        calculated_params = {}
        for uniform_name, data in self.parameters.items():
            base_value = data["base_value"]
            weights = np.array(data["weights"])
            weighted_sum = np.dot(weights, self.audio_features)
            calculated_params[uniform_name] = base_value + weighted_sum
        return calculated_params

    def update_uniforms(self):
        calculated_params = self.calculate_shader_parameters()
        for uniform_name, value in calculated_params.items():
            self.set_uniform(uniform_name, value)

    def set_uniform(self, uniform_name, value):
        try:
            self.prog[uniform_name] = value
        except KeyError:
            print(f"Uniform {uniform_name} not used in shader")

    def on_render(self, time, frame_time):

        w, h = self.wnd.size                      # current window size
        if (w, h) != getattr(self, "window_size", (None, None)):
            self.window_size = (w, h)             # remember it
            self.ctx.viewport = (0, 0, w, h)      # draw over whole window
            self.set_uniform('resolution', self.window_size)  # re-centre shader

        self.ctx.clear()

        # Update 'time' uniform with the current time
        self.set_uniform('time', time)

        # Update audio features and shader uniforms
        try:
            if self.audio_features_queue:
                self.audio_features = self.audio_features_queue.get_nowait()
        except Empty:
            pass

        self.update_uniforms()
        self.quad.render(self.prog)
    
        # ------------------------------------------------------------
    # called automatically every time the OS / user resizes the window
    def resize(self, width: int, height: int):
        # 1️⃣ let the context draw into the new full window
        self.ctx.viewport = (0, 0, width, height)
        # 2️⃣ remember the new size in case you need it elsewhere
        self.window_size = (width, height)
        # 3️⃣ update the shader uniform so all coords stay centred
        self.set_uniform('resolution', self.window_size)


    def __del__(self):
        self.feature_extractor.stop()
        self.feature_extractor.join()
        self.stream.stop_stream()
        self.stream.close()
        self.p.terminate()


    


    

 
