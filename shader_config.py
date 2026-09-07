import json
from typing import Dict, List, NamedTuple

import json
import os

class ShaderConfig:

    def __init__(self, name, textures: Dict[str, str]):
        
        self.name = name
        self.parameters_path = f'./shader_configs/{name}.json'
        self.textures = textures

        with open(self.parameters_path, 'r') as f:
            data = json.load(f)
        self.parameters = data["parameters"]


    def get_uniform_names(self):
        return list(self.parameters.keys())
    

    def get_uniform_data(self, uniform_name):
        return self.parameters[uniform_name]
    

    def get_all_uniforms(self):
        return self.parameters
    
    
    def save(self, file_path: str | None = None):
        target = file_path or self.file_path
        with open(target, "w", encoding="utf-8") as f:
            json.dump({"parameters": self.parameters}, f, indent=4)
      
