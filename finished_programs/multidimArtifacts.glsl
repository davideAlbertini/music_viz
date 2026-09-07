#version 430

#define PI 3.14159265359

out vec4 fragColor;
uniform vec2 resolution;
uniform float time;

// Tunables
uniform float BUMP_AMP;
uniform float MORPH_SPEED;
uniform float HUE_MIX;
uniform float NUM_DAODDS;
// Maximum and minimum radius for the spiral in the YZ-plane
uniform float MIN_RAD;
uniform float MAX_RAD;
uniform float END_X;

const float BPM      = 160.0;
const int   MAX_STEPS = 100;
const float EPS       = 0.01;
const float FAR_DIST  = 1e5;

vec3 hueRotate(vec3 col, float h)          // h in [0,1]
{
    const vec3 k = vec3(0.57735);          // 1/√3, unit diagonal
    float a = h * 6.28318;                 // 2π
    float c = cos(a), s = sin(a);
    return col * c + cross(k, col) * s + k * dot(k, col) * (1.0 - c);
}

vec3 erot(vec3 p, vec3 ax, float ro) {
    return mix(dot(p,ax)*ax,p,cos(ro))+sin(ro)*cross(ax,p);
}

float smin(float a, float b, float k) {
    float h = max(0.,k-abs(b-a))/k;
    return min(a,b)-h*h*h*k/6.;
}

vec4 wrot(vec4 p) {
    return vec4(dot(p,vec4(1)), p.yzw + p.zwy - p.wyz - p.xxx)/2.;
}

float t;
float doodad;
vec3 p2;

float doodadDist(vec3 p, float t_offset){

float d_time = t_offset + time;

p2 = erot(p, vec3(0,1,0), d_time);
p2 = erot(p2, vec3(0,0,1), d_time/3.);
p2 = erot(p2, vec3(1,0,0), d_time/5.);

float bpt = d_time/60.*BPM;
    vec4 p4 = vec4(p2,0);
    p4=mix(p4,wrot(p4),smoothstep(-.55,.55,sin(bpt/4.)));
    p4 =abs(p4);
    p4=mix(p4,wrot(p4),smoothstep(-.5,.5,sin(bpt/MORPH_SPEED)));

float fctr = smoothstep(-.5,.5,sin(bpt/4.));

float num_faciness = mix(.09,.3,fctr);      // default: 0.05, 0.07, fctr
float roundness = mix(-0.1,.22,fctr);       // default: -0.1,.2,    fctr
float scale = mix(.15,.45,fctr*fctr);        // default: .15,.55,    fctr
float shapeniess = .0;                    // default: 0.

doodad = length( max( abs(p4)- num_faciness, shapeniess ) + roundness ) - scale;

p.x += asin(sin(d_time/80.)*.99)*80.;

return doodad;

}

float scene(vec3 p) {
    float d = 1e5;
    
    // Period: how many seconds for each daodadd’s lifecycle (from emission to disappearing)
    float period = 45.0;
    // Define the start (far away) and end (past camera) positions along the travel axis (here the x-axis)
    float startX = - 6.* float(NUM_DAODDS);
    
    // Loop through daodadds and compute a travel parameter for each.
    for (int i = 0; i < NUM_DAODDS; i++) {
        float fi = float(i);
        // Phase offset between daodadds (staggered emission)
        float phaseOffset = period / float(NUM_DAODDS);
        // "travel" runs from 0 to 1 repeatedly for each daodadd.
        float travel = fract((time + fi * phaseOffset) / period);
        
        // Compute position along x: from startX (far) to END_X (past camera)
        float xPos = mix(startX, END_X, travel);
        // Let the spiral rotate several times over the travel.
        // Adding fi gives a little extra phase variation between daodadds.
        float angle = travel * 4.0 * PI + fi;
        // Optionally, interpolate the radius so that the spiral tightens or expands.
        float radius = mix(MAX_RAD, MIN_RAD, travel);
        // Compute the offset: x coordinate is along travel,
        // YZ plane provides the spiral pattern.
        vec3 offset = vec3(xPos, cos(angle) * radius, sin(angle) * radius);
        
        // Compute the SDF for this daodadd at the offset.
        float dtemp = doodadDist(p + offset, fi * 4.5);
        
        // Fade out daodadds when they near the end of their travel.
        // When travel approaches 1, we mix the distance toward a large number.
        float fade = smoothstep(0.8, 1.0, travel);
        dtemp = mix(dtemp, 1e5, fade);
        
        // Combine with the overall scene SDF using a smooth min
        d = smin(d, dtemp, 0.1);
    }
    
    return d;
}

// Computes normal from the SDF.
vec3 norm(vec3 p) {
    float precis = length(p) < 1. ? 0.005 : 0.01;
    mat3 k = mat3(p,p,p)-mat3(precis);
    return normalize(scene(p)-vec3(scene(k[0]),scene(k[1]),scene(k[2])));
}

void main()
{
    vec2 uv = (gl_FragCoord.xy-.5*resolution.xy)/resolution.y;

    float bpt = time/60.*BPM;
    float bp = mix(pow(sin(fract(bpt)*3.14/2.),20.)+floor(bpt), bpt,0.4);
    t = bp;
	
    vec3 cam = normalize(vec3(2.2,uv));
    vec3 init = vec3( BUMP_AMP * sin(0.5 * bp*PI), 0, 0);

    
    vec3 p = init;
    bool hit = false;
    float atten = 1.4;
    float tlen = 0.;
    float dist;
    bool trg = false;
    
    // ---------- Ray-march ----------
    for (int i = 0; i < MAX_STEPS; ++i)
    {
        dist = scene(p);

        if (dist < EPS) {          // --> abbiamo colpito la geometria
            hit = true;
            break;
        }
        if (tlen > FAR_DIST) {     // --> troppo lontano: esci
            break;
        }

        p    += cam * dist;
        tlen += dist;
    }

    // ---------- Sfondo: verde puro ----------
    if (!hit)
    {
        fragColor = vec4(0.0, 1.0, 0.0, 1.0);  
        return;                                 // <<<  salta tutto il resto
    }
    
    // Compute the surface normal at the final hit position.
    vec3 n = norm(p);
    // Reflect the camera ray 'cam' around the normal to get the reflection direction.
    vec3 r = reflect(cam,n);
    
    // Compute a specular factor 'fact' for highlights.
    // The expression normalizes the sine-modulated reflection vector to create a value that modulates brightness.
    float fact = length(sin(r*(4.))*.5+.5)/sqrt(3.)*.7+.3;
    fact += pow(fact,15.);
    // Quantize the diffuse term into discrete levels (e.g. 3 levels).
    float levels = 3.0;
    fact = floor(fact * levels) / levels;
    
    // Generate a base material color by blending between two colors.
    vec3  matcol = mix(vec3(0.0,0.8,0.8), vec3(0.8,0.0,0.8), HUE_MIX);
    matcol       = hueRotate(matcol, HUE_MIX);          // <<< new
    
    // Combine the material color with the specular factor and smoothstep value.
    // Also add a power term on 'fact' to boost bright specular highlights.
    vec3 col = matcol*fact;
    
    // Apply attenuation from the raymarching loop
    fragColor.xyz = col*atten;
    
    // Apply a gamma correction
    fragColor.xyz = sqrt(fragColor.xyz);

    // Clamp and smooth the final color values using smoothstep so they remain in a displayable range.
    fragColor.xyz = smoothstep(vec3(0), vec3(1.2), fragColor.xyz);
}
