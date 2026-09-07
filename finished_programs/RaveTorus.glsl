#version 430

out vec4 fragColor;

uniform float circ_speed;
uniform float v_ripp_freq;
uniform float v_wiggle;
uniform float v_freq;
uniform float h_band_freq;
uniform float white_space;

uniform vec2 resolution;
uniform float time;

float torusSDF(vec3 p, float radius){  
     return length( vec2( length(p.xz) - 1., p.y) ) - radius;   
}

float frac(float v)
{
    return v - floor(v);
}


void main()
{
    vec2 uv = (gl_FragCoord.xy * 2.0 - resolution.xy) / resolution.y; 
    vec2 uv_ = uv;
    float t = time * .2;
    
    uv *= mat2(cos(t),-sin(t), sin(t), cos(t)); // camera rotation
    
    //camera code
    vec3 ro = vec3(0,0,-1);  // camera position - ray origin
    vec3 lookat = mix(vec3(0),vec3(-.7,0,-.7), sin(t*1.56)*.5+.5);// steering point of camera
    float zoom = mix(.2, .7, sin(t)*.5+.5); // audio mod: field of view
    
    // we need to deine the three directions with respect to the camera POV:
    // we use a forward vector which points toward the virtual screen, a right and an up component
    // we use the cross product, which always yields an orthogonal vector wrt the plane defined by the input vectors
    vec3 f = normalize(lookat-ro), // forward vector: look direction camera
        r = normalize(cross(vec3(0,1,0), f)), //right vector: points to the right of the  forward vector
        u = cross(f,r), // up vector: points up wrt the forward vector
        c = ro + f*zoom, //camera center
        i = c + uv.x * r + uv.y * u, // intersection point, where camera ray intersects the virtual screen
        rd = normalize(i-ro);

    float radius = mix(.3, .9, sin(t*.5)*.5+.5);//radius of toroid
    // Ray Marcher
    float dS, dO; 
    vec3 p; 
    for(int i = 0; i < 100; i++){
        p = ro + dO*rd;
        dS = - (torusSDF(p, radius)); //the minus is needed to get "inside" the torus
        if(dS < .001) break;
        dO += dS;
    }
    
    vec3 col = vec3(0.0);
    // if the ray marcher hits something ( i.e., the dS is small )
    // take the points on the sufrace of the torus ( p inside the if. ) and draw on the surface
    if(dS < .001){
        float x = atan(p.x, p.z) + t * circ_speed;             // from -pi to pi
        float y = atan(length(p.xz) - 1., p.y); // from -pi to pi
        float bands = sin(sin(y*floor(v_freq)+ v_wiggle * t)+x*floor(v_ripp_freq)); // 10. 20. modulable by audio
        float ripples = sin((x*10.-y*30.)*3.)*.5+.5;
        float waves = sin(x*2.-y*floor(h_band_freq) + t * 37.);
        
        float b1 = smoothstep(-.2, .2, bands);
        float b2 = smoothstep(-.2, .2, bands-frac(white_space)); //.5 narrows the white part (audioMOD)
        
        float m = b1*(1. - b2);
        m = max(m, ripples * b2 * max(0., waves));
        m +=max(0., waves * .3 * b2);
        
        col += m;
        col = smoothstep(.0, 0.1, col);
        
    }

    // Output to screen
    fragColor = vec4(col,1.0);

}