#version 430

#define PI 3.14159265359
#define MAX_NUMEL 15
#define DB true

out vec4 fragColor;
uniform vec2 resolution;
uniform float time;

uniform float BPM = 160.;
uniform float f_base;
uniform float f_mod;
uniform float R_base;
uniform float numel;

//-------------------------------------
// Some coloring function
//-------------------------------------
vec3 redYellowGreen(float t)
{
    if(t < 0.5) {
        float subT = t / 0.5;
        return mix(vec3(1, 0, 0), vec3(1, 1, 0), subT);
    } else {
        float subT = (t - 0.5) / 0.5;
        return mix(vec3(1, 1, 0), vec3(0, 1, 0), subT);
    }
}

void pR(inout vec2 p, float a) {
	p = cos(a)*p + sin(a)*vec2(p.y, -p.x);
}

//-------------------------------------
// 1) Complex utility
//-------------------------------------
vec2 cpxAdd(vec2 a, vec2 b) {
    return a + b; 
}

vec2 cpxMul(vec2 a, vec2 b) {
    return vec2(a.x*b.x - a.y*b.y, a.x*b.y + a.y*b.x);
}

vec2 cpxExp(float phase) {
    return vec2(cos(phase), sin(phase));
}

vec2 cpxConj(vec2 a) {
    return vec2(a.x, -a.y);
}

//-------------------------------------
// 2) Dot product with conjugation
//-------------------------------------
vec2 cpxVecDotConj(in vec2 a[MAX_NUMEL], in vec2 b[MAX_NUMEL], int size) {
    // sum_{i=0..size-1} conj(a[i]) * b[i]
    vec2 sum = vec2(0.0);
    for(int i = 0; i < size; i++) {
        vec2 product = cpxMul(cpxConj(a[i]), b[i]);
        sum = cpxAdd(sum, product);
    }
    return sum;
}

//-------------------------------------
// 3) log10 implementation
//-------------------------------------
float myLog10(float x) {
    return log(x) * 0.4342944819;  // 1.0 / ln(10)
}

//-------------------------------------
// 4) Main image
//-------------------------------------
void main()
{
    //----------------------------------
    // A) Convert screen coords -> uv
    //----------------------------------
    vec2 uv = (gl_FragCoord.xy * 2.0 - resolution.xy) / resolution.y; 
    
    float BPT = time/60.*BPM;
    
    pR(uv, BPT/2.); //rotation of xy plane, just for visual trippyness
    
    //----------------------------------
    // B) Choose N dynamically
    //----------------------------------
    int N = int(floor(numel));
    
    //----------------------------------
    // C) Constants / geometry
    //----------------------------------
    float R = R_base + .3 * sin(BPT/3.);
    float freq_Hz = f_base + f_mod*sin(BPT);
    float omega   = 2.0 * PI * freq_Hz; 
    float c       = 343.0;
    
    // Single source at center
    vec2 src_pos = vec2(0.0);//  + vec2(0.2*sin(time), 0.2*cos(time)); //uncomment me!
    
    // We keep arrays at their max size = 10
    // but we'll only fill the first N elements
    vec2 arrayPositions[MAX_NUMEL];
    vec2 weights[MAX_NUMEL];

    //----------------------------------
    // D) Build array positions & weights
    //----------------------------------
    for(int n = 0; n < N; n++){
        float theta_n = 2.0 * PI * float(n) / float(N);
        arrayPositions[n] = vec2(R*cos(theta_n), R*sin(theta_n));
        
        float dist = length(arrayPositions[n] - src_pos);
        dist = max(dist, 1e-6);
        weights[n] = cpxExp((omega / c) * dist) * (1.0 / (4.0 * PI * dist));
    }
    
    // The rest of the array slots are unused or 0
    // but we won't read them since we always loop up to N

    //----------------------------------
    // E) Normalize weights => wDAS
    //----------------------------------
    vec2 normVal = cpxVecDotConj(weights, weights, N);
    float wNorm  = length(normVal);
    vec2 wDAS[MAX_NUMEL];
    for(int n = 0; n < N; n++){
        wDAS[n] = weights[n] * (1.0 / wNorm);
    }

    //----------------------------------
    // F) Evaluate beam at uv
    //----------------------------------
    vec2 steering_uv[MAX_NUMEL];
    for(int n = 0; n < N; n++){
        float dist_uv = length(arrayPositions[n] - uv);
        dist_uv = max(dist_uv, 1e-6);
        steering_uv[n] = cpxExp((omega / c) * dist_uv)
                         * (1.0 / (4.0 * PI * dist_uv));
    }
    
    //  | wDAS^H * steering_uv |
    vec2 dotVal  = cpxVecDotConj(wDAS, steering_uv, N);
    float amplitude = length(dotVal);

    //----------------------------------
    // G) Optional dB mapping
    //----------------------------------
    if(DB){
        amplitude = max(amplitude, 1e-12);
        float dB  = 20.0 * myLog10(amplitude);
        float dB_min = -30.0;
        float dB_max = +6.0;
        float t = (dB - dB_min)/(dB_max - dB_min);
        amplitude = clamp(t, 0.0, 1.0);
    }

    //----------------------------------
    // H) Final color
    //----------------------------------
    vec3 color = redYellowGreen(amplitude);
    fragColor = vec4(color, 1.0);
}
