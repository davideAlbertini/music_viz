#version 430

out vec4 fragColor;

#define FEATURE_DIM 6

uniform vec2 resolution;
uniform float time;
uniform float audio_features[FEATURE_DIM];
uniform float maxIter;
uniform float fracPattern;
uniform float neonBrightness;

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

vec3 palette( float t){
    vec3 a = vec3(0.5, 0.5, 0.5);
    vec3 b = vec3(0.5, 0.5, 0.5);
    vec3 c = vec3(1.0, 1.0, 1.0);
    vec3 d = vec3(0.263, 0.416, 0.557);
    return a + b*cos( 6.28318*(c*t+d) );
}

void main()
{
    //-----------------------------INIT------------------------------------------
    // NORMALIZED PIXEL coordinates:
    // (y in {-1 ; 1} x in { -(resolution.x/resolution.y) ; (resolution.x/resolution.y)})
    vec2 uv = (gl_FragCoord.xy * 2.0 - resolution.xy) / resolution.y;  
    //--------------------------------------------------------------------------- 
    vec2 uv0 = uv; 
    vec3 finalColor = vec3(0.0);
    
    float maxIter_int = floor(maxIter);    //control fractal-ness   
    for(float i=0.0; i<maxIter_int; i++){ 
    
        float aspectRatio = (resolution.x / resolution.y);
        uv = ( fract(fracPattern * uv) - 0.5)* aspectRatio;

        float d = length(uv) * exp(-length(uv0));

        vec3 col = palette(length(uv0) + (i + time) * .4); //dynamic palette swap

        d = sin(d*8. + time) / 8.;
        d = abs(d);
        d = pow(neonBrightness / d, 1.2); // this gives the neon brightness

        finalColor += col * d;
    }    
    
    // Output to screen
    fragColor = vec4(finalColor,1.0);

    drawAudioParBars(uv0, audio_features);

}
