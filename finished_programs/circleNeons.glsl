#version 430

out vec4 fragColor;

uniform vec2 resolution;
uniform float time;

uniform float p1;
uniform float fracPattern;
uniform float neonBrightness;

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
    
    float maxIter = 2.0 + floor(4.* (1 - p1));    //control fractal-ness
    
    for(float i=0.0; i<maxIter; i++){ 
    
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

}
