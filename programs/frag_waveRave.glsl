#version 430

out vec4 fragColor;

#define FEATURE_DIM 6

uniform vec2 resolution;
uniform float time;
uniform float audio_features[FEATURE_DIM];
// uniforms for parameters previously computed by automate()
uniform float ecc_x;
uniform float ecc_y;
uniform float thickness;
uniform float zoom_in;
uniform float radial_pos;
uniform float zoom_in_balls;
//uniform float num_balls;
uniform float ray_amp;
uniform float ray_freq;
uniform float wiggle_speed;
uniform float rotation;
uniform float freq;

//UTILS

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

//TRANSFORMS
vec2 rotate(vec2 pos, float theta){
    pos.x = pos.x * cos(theta) - pos.y * sin(theta);
    pos.y = pos.x * sin(theta) + pos.y * cos(theta);
    return pos;
}

//SHAPES
float Band(float t, float start, float end, float blur){
    float step1 = smoothstep(start-blur, start+blur, t);
    float step2 = smoothstep(end+blur, end-blur, t);
    return step1 * step2;
}

float Rect(vec2 uv, float left, float right, float bottom, float top, float blur){
    float band1 = Band(uv.x, left, right, blur);
    float band2 = Band(uv.y, bottom, top, blur);
    return band1 * band2;
}

float WavesH(vec2 uv, float freq_x, float freq_y){
    float h_disp = 2. * cos(8.0 * time + freq_x * uv.x ) + cos(4. *time);
    return 2. * sin(h_disp + freq_y * uv.y);
}

float Spiral(vec2 uv, float ecc_x, float ecc_y, float zoom_in, float thickness, float ccw){
    float r = length(uv);
    float theta = atan( ecc_y * uv.y, ecc_x * uv.x) / 6.28; 
    return frac(r / zoom_in - theta + sign (ccw) * time);
}

float Rays(vec2 uv, float ray_amp, float ray_freq, float wiggle_speed, float rotation, float freq){
    float d = length(uv);
    float theta_rot = ray_amp * sin(ray_freq * d +  wiggle_speed * time);
    theta_rot += time * rotation;
    vec2 uv_r = rotate(uv, theta_rot);

    freq *= 3.14159; 
    float col = acos(uv_r.x / d ) / (3.14159);
    col = cos(freq * col);
    return smoothstep(0.0,0.18, col);
}


void main()
{
    //-----------------------------INIT------------------------------------------
    // NORMALIZED PIXEL coordinates:
    // (y in {-1 ; 1} x in { -(resolution.x/resolution.y) ; (resolution.x/resolution.y)})
    vec2 uv = (gl_FragCoord.xy * 2.0 - resolution.xy) / resolution.y;  
    //---------------------------------------------------------------------------
    
    float col = 0.0;
    float blur = 0.05;
    float t = time;
    vec2 uv_r = uv;
    
    // Print Rays
    col = Rays(uv_r, ray_amp, ray_freq, wiggle_speed, rotation, floor(freq));
    
    float ecc_x_mov = ecc_x + 0.2 + ecc_x * sin(t); 
    float ecc_y_mov = ecc_y + 0.2 + ecc_y * cos(t); 
    
    // Print spiral balls
    float NUM_BALLS = 5.;
    vec2 center = vec2(mod(0.5 * t, 5.));
    //center = rotate(center, time / 7.);
    for(float i = 0.; i< NUM_BALLS; i++){
        float angle_div = i * ( 3.141 / NUM_BALLS);
        center = rotate(center, angle_div + t / 10.);

        float r_c = length(vec2(uv.x-center.x, uv.y-center.y));
        if(r_c < 0.2 * length(center) + 0.03){
            if(r_c < 0.2 * length(center)){
                float theta = atan( ecc_y_mov * uv.y, ecc_x_mov * uv.x) / 6.28;
                col = frac(r_c / (zoom_in_balls/length(3.*center))  + theta - 2. * t);
                col = smoothstep(thickness-blur,thickness+blur,col);
            }else{
                col = 0.0;
            }
        }
    }
    
    // print Foreground spiral
    float r = length(vec2(uv.x, uv.y));
    if(r < radial_pos ){
        if(r < radial_pos - 0.05){
          col = Spiral(uv, ecc_y_mov, ecc_x_mov, zoom_in, thickness, -1.0); 
          col = smoothstep(0.3, 0.3 + blur, col);
        }else{
          col = 0.0;
        }
    }
    
    
    // Output to screen
    fragColor = vec4(vec3(col),1.0);

    //drawAudioParBars(uv, audio_features);
}