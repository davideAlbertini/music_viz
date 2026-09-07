#version 430

out vec4 fragColor;

#define FEATURE_DIM 6

uniform vec2 resolution;
uniform float time;
uniform float audio_features[FEATURE_DIM];
// uniforms for parameters previously computed by automate()
uniform float ecc_x;
uniform float ecc_y;
uniform float zoom_in;
uniform float thickness;
uniform float radial_pos;
uniform float radial_pos_delta;
uniform float zoom_in_balls;
uniform float num_balls;

void drawAudioParBars(vec2 uv, float audio_features[FEATURE_DIM]) {
    float startOfDebugArea = 0.9 * (resolution.x / resolution.y); //90% of x-axis length
    float debugAreaWidth =  0.1 * (resolution.x / resolution.y);
    float barWidth = debugAreaWidth / FEATURE_DIM;
    if(uv.x > startOfDebugArea){
        for (int i = 0; i < FEATURE_DIM; ++i) {
            float startOfBar = startOfDebugArea + i * barWidth;
            float endOfBar = startOfDebugArea + (i+1) * barWidth;
            if(uv.x > startOfBar && uv.x < endOfBar){
                if(uv.y > 0){   //use only the poitive y region for debug area
                    if(uv.y < audio_features[i]){
                        fragColor = vec4(0.2, 1.0, 0.2, 1.0);
                    }else{
                    fragColor = vec4(0.0, 0.0, 0.0, 0.01);
                    }  
                }
            }
        }
    }
}

float frac(float v)
{
    return v - floor(v);
}

vec2 rotate(vec2 pos, float theta){
    pos.x = pos.x * cos(theta) - pos.y * sin(theta);
    pos.y = pos.x * sin(theta) + pos.y * cos(theta);
    return pos;
}

float spiral(float x, float y, float ecc_x, float ecc_y, float zoom_in, float thickness, float ccw){
    
    float r = length(vec2(x, y));
    float theta = atan( ecc_y * y, ecc_x * x) / 6.28; 
    // time varying pixel color
    float col = frac(r / zoom_in - theta + sign (ccw) * time);
    return step(thickness,col);
}

void main()
{
    //-----------------------------INIT------------------------------------------
    // NORMALIZED PIXEL coordinates:
    // (y in {-1 ; 1} x in { -(resolution.x/resolution.y) ; (resolution.x/resolution.y)})
    vec2 uv = (gl_FragCoord.xy * 2.0 - resolution.xy) / resolution.y;  
    //---------------------------------------------------------------------------
    
    float col = 0.0;

    // background spiral setting
    float ecc_x_mov = ecc_x + 0.1 + ecc_x * sin(time); 
    float ecc_y_mov = ecc_y + 0.1 + ecc_y * cos(time); 
    // do background spiral
    col = spiral(uv.x, uv.y, ecc_x_mov, ecc_y_mov, zoom_in, thickness, 1.0);

    // do foreground spiral
    float r = length(vec2(uv.x, uv.y));
    if(r < radial_pos ){
        if(r < radial_pos - radial_pos_delta){
          col = spiral(uv.x, uv.y, ecc_y_mov, ecc_x_mov, zoom_in, thickness, -1.0); 
        }else{
          col = 0.0;
        }
    }
    
    // outgoing spiral balls
    float NUM_BALLS = floor(num_balls);
    vec2 center = vec2(mod(2.5 * time, 15.));
    for(float i = 0.; i< NUM_BALLS; i++){
        float angle_div = i * ( 180. / NUM_BALLS);
        center = rotate(center, angle_div );

        float r_c = length(vec2(uv.x-center.x, uv.y-center.y));
        if(r_c < 0.2 * length(center) + 0.03){
            if(r_c < 0.2 * length(center)){
                float theta = atan( ecc_y_mov * uv.y, ecc_x_mov * uv.x) / 6.28;
                col = frac(r_c / zoom_in_balls + theta - 2. * time);
                col = step(thickness,col);
            }else{
                col = 0.0;
            }
        }
    }

    // Output to screen
    fragColor = vec4(col, col, col, 1.0);

    drawAudioParBars(uv, audio_features);

}