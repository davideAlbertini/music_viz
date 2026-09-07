#version 430

#define PI 3.14159265
#define TAU (2*PI)
#define PHI (sqrt(5)*0.5 + 0.5)

out vec4 fragColor;

uniform vec2 resolution;
uniform float time;

const float FOV =  0.9;
const int MAX_STEPS = 256;
const float MAX_DIST = 500.0;
const float EPSILON = 0.001;
const float BLUR = .0001;
const float BASE = .05;

uniform float cone_disp;
//ray params
uniform float wiggle_speed;
uniform float rotation;
uniform float ray_amp;
uniform float ray_freq;
uniform float freq;
//Spiral Params
uniform float radial_pos;
uniform float radial_pos_delta;
uniform float zoom_in;

// Maximum/minumum elements of a vector
float vmax(vec2 v) {
	return max(v.x, v.y);
}

float vmax(vec3 v) {
	return max(max(v.x, v.y), v.z);
}

float vmax(vec4 v) {
	return max(max(v.x, v.y), max(v.z, v.w));
}


float fPlane(vec3 p, vec3 n, float distanceFromOrigin) {
	return dot(p, n) + distanceFromOrigin;
}

////////////////////////////////////////////////////////////////
//             PRIMITIVE DISTANCE FUNCTIONS
////////////////////////////////////////////////////////////////

// Box: correct distance to corners
float fBox(vec3 p, vec3 b) {
	vec3 d = abs(p) - b;
	return length(max(d, vec3(0))) + vmax(min(d, vec3(0)));
}

// Cylinder standing upright on the xz plane
float fCylinder(vec3 p, float r, float height) {
	float d = length(p.xz) - r;
	d = max(d, abs(p.y) - height);
	return d;
}

float fTorus( vec3 p, vec2 t )
{
    return length( vec2(length(p.xz)-t.x,p.y) )-t.y;
}

// Cone with correct distances to tip and base circle. Y is up, 0 is in the middle of the base.
float fCone(vec3 p, float radius, float height) {
	vec2 q = vec2(length(p.xz), p.y);
	vec2 tip = q - vec2(0, height);
	vec2 mantleDir = normalize(vec2(height, radius));
	float mantle = dot(tip, mantleDir);
	float d = max(mantle, -q.y);
	float projected = dot(tip, vec2(mantleDir.y, -mantleDir.x));
	
	// distance to tip
	if ((q.y > height) && (projected < 0.)) {
		d = max(d, length(tip));
	}
	
	// distance to base ring
	if ((q.x > radius) && (projected > length(vec2(height, radius)))) {
		d = max(d, length(q - vec2(radius, 0)));
	}
	return d;
}

////////////////////////////////////////////////////////////////
//                DOMAIN MANIPULATION OPERATORS
////////////////////////////////////////////////////////////////
// Rotate around a coordinate axis (i.e. in a plane perpendicular to that axis) by angle <a>.
void pR(inout vec2 p, float a) {
	p = cos(a)*p + sin(a)*vec2(p.y, -p.x);
}

////////////////////////////////////////////////////////////////
//             OBJECT COMBINATION OPERATORS
////////////////////////////////////////////////////////////////

float opUnion( float d1, float d2 )
{
    return min(d1,d2);
}
float opSubtraction( float d1, float d2 )
{
    return max(-d1,d2);
}

vec2 fOpUnion(vec2 res1, vec2 res2){
// returns the closestbetween 2 objects ( distance and ID ) 
    return (res1.x < res2.x) ? res1 : res2;
}

////////////////////////////////////////////////////////////////
//             2D GRAPHICS
////////////////////////////////////////////////////////////////

//TRANSFORMS
vec2 rotate(vec2 pos, float theta){
    pos.x = pos.x * cos(theta) - pos.y * sin(theta);
    pos.y = pos.x * sin(theta) + pos.y * cos(theta);
    return pos;
}

/////////////////////////////////////////////////////////////////
//            FUNCTIONS
/////////////////////////////////////////////////////////////////

float Rays(vec2 uv, float ray_amp, float ray_freq, float wiggle_speed, float rotation, float freq){
    float d = length(uv);
    float theta_rot = ray_amp * sin(ray_freq * d +  wiggle_speed * time);
    theta_rot += time * rotation;
    pR(uv, theta_rot);
    float col = cos(freq * acos(uv.x / d ));
    return smoothstep(BASE-BLUR,BASE+BLUR,col); 
}

float frac(float v)
{
    return v - floor(v);
}

float spiral(vec2 uv, float ecc_x, float ecc_y, float zoom_in, float ccw){  
    float d = length(uv);
    float theta = atan( ecc_y * uv.y, ecc_x * uv.x) / 6.28; 
    // time varying pixel color
    float col = frac(d / zoom_in - theta + sign (ccw) * time);
    return smoothstep(BASE-BLUR+.2,BASE+BLUR+.2,col);
}

vec3 drawBackground(vec2 uv){
    
    //spiral params
    float ecc_x_mov = 1.3 + 0.5 * sin(time) + 0.5 * sin(time) * sin(time); 
    float ecc_y_mov = 1.3 + 0.5 * cos(time) + 0.5 * cos(time) * cos(time);
    
    float col = Rays(uv, ray_amp, ray_freq, wiggle_speed, rotation, freq);
    
    // do foreground spiral
    float r = length(vec2(uv.x, uv.y));
    if(r < radial_pos ){
        if(r < radial_pos - radial_pos_delta){
          col = spiral(uv, ecc_y_mov, ecc_x_mov, zoom_in, -1.0); 
        }else{
          col = 0.0;
        }
    }
    
    return vec3(col);
}

vec2 loudspeakerDist(vec3 p, float cone_disp){

    // Louspeaker body
    float box = fBox(p, vec3(1., 2., .5));
    
    //loudspeaker hole
    vec3 p_hole = p + vec3(0.,0.,0.8);
    pR(p_hole.yz, PI/2.);
    float hole = fCylinder(p_hole, 0.8, 2.);    

    //loudspeaker cone
    vec3 p_cone = p + vec3(0., 0., 0.53 + 0.03*cone_disp);
    pR(p_cone.yz, PI/2.);
    float coneDist = fCone(p_cone, 0.8, 0.3);
    
    vec3 p_cone_hole = p_cone + vec3(0.,.01, 0.);
    float coneHoleDist = fCone(p_cone_hole, 0.7, 0.3);
    float cone = opSubtraction(coneHoleDist, coneDist);
    
    //loudspeaker bulb
    vec3 p_bulb = p + vec3(0., 0., 0.25 + 0.05*cone_disp);
    float bulb = length(p_bulb) - .25;
    
    //loudspearer rim
    vec3 p_torus = p + vec3(0.,0.,0.52);
    pR(p_torus.yz, PI/2.);
    float rim = fTorus(p_torus, vec2(0.8,0.05));

    //loudspeaker tweeter hole
    vec3 p_tweet = p * vec3(1.,1.,0.1) + vec3(0., -1.4, 0.5);    
    float tweet = fBox(p_tweet, vec3(0.6, 0.25, 0.51));

    // result
    float ls_dist = opSubtraction(hole, box);
    ls_dist = opUnion(ls_dist, cone);
    ls_dist = opUnion(ls_dist, rim);
    ls_dist = opUnion(ls_dist, bulb);
    ls_dist = opSubtraction(tweet, ls_dist);
    
    return vec2(ls_dist, 1.0);
}


vec2 map(vec3 p){
// this function contains the distance functions of all objects and returns the closest one
// using the union operator

    // plane 
    float planeDist = fPlane(p, vec3(0., 1., 0.), 1.);
    float planeID = 2.0;
    vec2 plane = vec2(planeDist, planeID);
    
    float spacing = 3.;
    vec2 loudspeaker1 = loudspeakerDist(p + vec3(spacing,0.,0.), cone_disp);
    vec2 loudspeaker2 = loudspeakerDist(p + vec3(-spacing,0.,0.), cone_disp);
    
    vec2 res = fOpUnion(plane, loudspeaker1);
    res = fOpUnion(res, loudspeaker2);
    return res;
    
}

vec2 rayMarch(vec3 ro, vec3 rd){
// the rayMarch function returns a 2-dimensiona vector object in order to store
// the distance to the object in the X component, and get the object ID ( it's color) 
// in the Y component
    vec2 hit, object;
    for(int i = 0; i < MAX_STEPS; i++){
        // march the ray p ...
        vec3 p = ro + object.x * rd;
        // and compute distance from the objects
        hit = map(p);
        // update distance from the objects and ID
        object.x += hit.x;
        object.y = hit.y;
        // stop is object is hit ( really small distance ) or ray has travelled to far away
        if(abs(hit.x) < EPSILON || object.x > MAX_DIST) break;
    }
    return object;
}

vec3 getNormal(vec3 p) {
    vec2 e = vec2(EPSILON, 0.0);
    vec3 n = vec3(map(p).x) - vec3(map(p - e.xyy).x, map(p - e.yxy).x, map(p - e.yyx).x);
    return normalize(n);
}

vec3 getLight(vec3 p, vec3 rd, vec3 color){
// Lighting model based on the Lambert Law: 
// amount of reflected light is proportional to the scalar product of the vector
// directed to the light source and the normal to the surface
    vec3 lightPos = vec3(0., 20., -20.);
    vec3 L = normalize(lightPos - p); // vector from surface element directed to the light source
    vec3 N = getNormal(p);  
    
    // return N; //check normals
    // compute the Lambert Law
    vec3 diffuse = color * clamp(dot(L, N), 0.0, 1.0);
    
    // shadows
    float d = rayMarch(p + N * 0.02, normalize(lightPos)).x; // cast ray from surface point p towards the light and get distance
    // if the distance travelled from p to the ligth is lower that the distance from the point to the light, it means we've hit an object
    // which is obstructing the light, so we cast a shadow for point p
    if (d < length(lightPos - p)) return vec3(0.0);
    
    return diffuse;
}

vec3 getMaterial(vec3 p, float id) {
// Gives the color based on the ID of the hit object
    vec3 m;
    switch (int(id)) {
        case 1:
        m = vec3(0.1, 0.1, 0.1); break;
        case 2:
        m = vec3(1.); break;
    }
    return m;
}

void render(inout vec3 col, in vec2 uv){
    // sets ray origin
    vec3 ro = vec3(0.0, 0.0, -3.0);
    // sets ray directionS -> points towards xy plane 
    vec3 rd = normalize(vec3(uv, FOV));
    
    vec2 object = rayMarch(ro, rd);
    
    vec3 background = drawBackground(uv);
    
    if(object.x < MAX_DIST){
        vec3 p = ro + object.x * rd;
        vec3 material = getMaterial(p, object.y);
        col += getLight(p, rd, material);
        float blur = .0001;
        float base = .05;
        col = smoothstep(BASE-BLUR,BASE+BLUR,col); 
    }else{
        col = background;
    }
}

/////////////////////////////////////////////////////////////////
//            MAIN
/////////////////////////////////////////////////////////////////

void main()
{
    //-----------------------------INIT------------------------------------------
    // NORMALIZED PIXEL coordinates:
    // (y in {-1 ; 1} x in { -(resolution.x/resolution.y) ; (resolution.x/resolution.y)})
    vec2 uv = (gl_FragCoord.xy * 2.0 - resolution.xy) / resolution.y;  
    //--------------------------------------------------------------------------- 

    vec3 col;

    //AA setting
    int aa_factor = 2;
    
    // Supersampling - nxn grid within each pixel
    for(int x = 0; x < aa_factor; x++) {
        for(int y = 0; y < aa_factor; y++) {
            // Offset for each sample - shifts within the pixel grid
            vec2 offset = vec2(x, y) * (1. / float(aa_factor)) / resolution.y;
            // Adjusted UV for current sample
            vec2 sampleUV = uv + offset;
            // Render scene for this sample
            vec3 sampleColor;
            render(sampleColor, sampleUV);
            col += sampleColor;
        }
    }

    // Average the color from the samples
    col /= float(aa_factor * aa_factor);
    
    // gamma correction -- needed to adjust the lighting (make all brighter)
    col = pow(col, vec3(0.4545));

    // Output to screen
    fragColor = vec4(col,1.0);

}
