#version 330 core
/* ----  uniforms supplied from Python  ---------------------------------- */
uniform vec2  resolution;      // set by ShaderController →  ‘resolution’
uniform float time;            //                         →  ‘time’
uniform int   frame;           // optional, for effects needing iFrame

/* optional textures (bind 0…3 exactly like on ShaderToy) */
uniform sampler2D noiseTex;    // slot 0 – 256×256 RG noise (was iChannel0)
uniform sampler2D indexTex;    // slot 2 – 256×1   1-D noise (was iChannel2)
uniform sampler2D fontTex;     // slot 3 – 256×256 ASCII atlas (was iChannel3)

uniform float ACID_FREQ;  // optional, frequency for noise functions
uniform float BALLS;  // optional, frequency for noise functions
uniform float ITERS; 

/* convenience aliases so the original code is almost unchanged */
#define iResolution   resolution
#define iTime         time
#define iFrame        frame
#define iChannel0     noiseTex
#define iChannel2     indexTex
#define iChannel3     fontTex

/* ------------------ shared helpers (COMMON) --------------------------- */
#define pi 3.14159265358979323846
#define xor(a,b,c)    min(max(a,-(b)+c),max(b,-(a)))
float opSmoothUnion(float d1,float d2,float k){
    float h = clamp(0.5+0.5*(d2-d1)/k,0.0,1.0);
    return mix(d2,d1,h)-k*h*(1.0-h);
}
float sdSegment(vec2 p,vec2 a,vec2 b){
    vec2 pa=p-a, ba=b-a;
    float h=clamp(dot(pa,ba)/dot(ba,ba),0.0,1.0);
    return length(pa-ba*h);
}

/* ------------------- tiny helpers used everywhere --------------------- */
float sdBox(vec2 c,vec2 s){ c=abs(c)-s; return max(c.x,c.y); }
#define rot(a)  mat2(cos(a),-sin(a),sin(a),cos(a))
#define pmod(p,a) mod(p,a)-0.5*a

/* -------------- noise helpers (from Buffer A & Image) ----------------- */
float noise(vec3 p_){
    float n=0., amp = ACID_FREQ;
    vec4 p=vec4(p_,11.);
    p.xy*=rot(1.4*iTime/4.); p.x*=3.;
    for(float i=0.; i<6.; i++){
        p.yz*=rot(.5); p.xz*=rot(2.5+i); p.wy*=rot(2.5-i);
        p+=cos(p*1.+vec4(3,2,1,1.))*amp*.5;
        n+=dot(sin(p),cos(p))*amp;
        amp*=0.7; p*=1.5;
    }
    return sin(n*2.);
}
/* lightweight 1-D noise lookup used by text-scramble */
vec4 n14(float f){
    return texture(iChannel0,
                   vec2(mod(floor(f),256.),floor(f/256.))/256.);
}

/* ---------------------- Easing / text helpers ------------------------- */
float eass(float p,float g){
    float s=p*0.45;
    for(float i=0.; i<g; i++) s=smoothstep(0.,1.,s);
    return s;
}
/* bitmap-font text SDF builder (unchanged from Buffer A) */
float text(vec2 p,float[9] chars,float spacing,float s,bool isAbs,
           float absWidth,float opacity,bool scrobble,float offs){
    p*=s; p.x*=1.-spacing;
    vec2 id=floor(p*8.*2.);
    p=mod(p,1./16.);
    p.x=p.x/(1.-spacing)+1./16./8.;
    float ch=chars[int(id.x)];
    ch-=32.;
    if(scrobble)
        ch += floor(15. * n14(id.x + (iTime + sin(id.x))*24.).y*pow(abs(sin(iTime + id.x*0.2)),14.) ) ;
    if(scrobble)
        ch += 0.*floor(15. * n14(id.x + (iTime + sin(id.x))*24.).y * (2. - 1.)* (1. - eass((iTime - + id.x*1./16. - 3.)*1.,3.)) ) ;
    float t;
    if(abs(id.y)<1. && id.x>=0. && id.x<9. && ch<200.){

        vec2 st = p + vec2(mod(ch,16.), -floor(ch/16.)) / 16.0;
        st.y = - st.y;
        vec4 letter = texture(iChannel3, st);
    
        t = letter.g - opacity;
        if(abs(p.x-1./16./2.)>1./16./2.) t=1e4;
        t/=s*10.1;
    }else t=1e5;
    if(isAbs) t=abs(t)-absWidth;
    return t;
}

/* ------------------ cyclic noise variant used in Buffer A ------------- */
float noiseGrid(vec3 p_){
    float n=0., amp=1.; vec4 p=vec4(p_,11.);
    for(float i=0.; i<2.; i++){
        p.yz*=rot(.5); p.xz*=rot(2.5+i); p.wy*=rot(2.5-i);
        p+=cos(p*1.+vec4(3,2,1,1.))*amp*.5;
        n+=dot(sin(p),cos(p))*amp;
        amp*=0.5; p*=1.5;
    }
    return n;
}

/* ===================================================================== */
/* -------------------------  BUFFER  A -------------------------------- */
/* ===================================================================== */
vec3 bufferA(vec2 fragCoord){
    vec2 uv=(fragCoord-0.5*iResolution.xy)/iResolution.y;
    vec3 col=vec3(0.);               /* base colour */
    vec3 baseCol=col;
    vec3 c=vec3(0.,0.511,0.2)*0.7;

    /* shift UV for left-hand pane ------------------------------------ */
    uv.x-=0.725+0.04;

    /* ---- GRID block ------------------------------------------------- */
    {
        vec2 p=uv; p.y-=0.08; p.x+=0.35;
        float bdb=sdBox(p,vec2(0.35));
        p*=rot(sin(length(p)*15.+iTime)*0.2*smoothstep(0.,-0.4,bdb));
        float d=1e5, w=0.001;
        float biters= floor(ITERS) + floor (ITERS*(1.*max(sin(iTime*1.),-0.5)));
        float lastb=0.;
        for(float i=0.; i<biters; i++){
            float b=sdBox(p,vec2(mod(exp(-i/10.),1.)*0.35));
            if(i==biters-1.) lastb=b;
            d=min(d,abs(b));
        }
        float itersLines=10.;
        for(float i=0.; i<itersLines; i++){
            vec2 q=p*rot(i/itersLines*pi+1./itersLines*pi/2.);
            d=min(d,abs(q.x));
        }
        float outBox=smoothstep(fwidth(uv.y),0.,bdb);
        float inBox=smoothstep(fwidth(uv.y),0.,-lastb);
        col=mix(col,c,inBox*outBox*smoothstep(fwidth(uv.y),0.,d-w));
        col=mix(col,c,smoothstep(fwidth(uv.y),0.,abs(bdb)-w));
    }

    /* ---- MEATBALLS -------------------------------------------------- */
    {
        float d=1e5; vec2 p=uv; p.y-=0.08; p.x+=0.35;
        for(float i=0.; i<BALLS; i++){
            float m=i+iTime;
            d=opSmoothUnion(d,
                            length(p-vec2(cos(m*cos(i)),sin(m))*0.2)-
                            0.05*(1.+0.5*sin(m*1.5)),0.1);
        }
        float ballFill=smoothstep(fwidth(d),0.,d);
        col=mix(col,baseCol,ballFill);
        col=mix(col,c,smoothstep(fwidth(d),0.,abs(d)));
        col=mix(col,c,ballFill*
                      smoothstep(-0.03,0.,d)*
                      texture(iChannel0,p*0.3).x*2.*
                      smoothstep(0.0,0.01,
                                 dot(vec2(-1),vec2(dFdx(d),dFdy(d)))));
    }

    /* ---- GRAD LINE -------------------------------------------------- */
    {
        vec2 p=uv; p.y+=0.38; p.x+=0.35;
        float bd=sdBox(p-vec2(0,0.06),vec2(0.35,0.02));
        float bdb=sdBox(p-vec2(0.0,-0.001),vec2(0.35,0.005));
        float d=bd;
        col=mix(col,c,smoothstep(fwidth(uv.y),0.,d)*
                     smoothstep(0.0,0.24+sin(iTime)*0.1,
                                smoothstep(-0.3,2.,p.x)*
                                texture(iChannel0,p*0.3).x*2.));
        d=abs(bd);
        col=mix(col,c,smoothstep(fwidth(uv.y),0.,d));
        col=mix(col,c,smoothstep(fwidth(uv.y),0.,bdb));
    }

    /* restore right-hand side coords ---------------------------------- */
    uv.x+=0.725+0.85;

    /* ---- SWIRLY ----------------------------------------------------- */
    {
        vec2 p=uv; float sc=2.5;
        p.x-=0.66; p.y-=0.35; p*=sc;
        float cd=sdBox(p,vec2(0.4,0.2));
        p*=rot(sin(length(p)*10.*sin(iTime)+iTime+sin(iTime))*2.);
        p=vec2(atan(p.x,p.y)/pi,length(p));
        float fw=fwidth(p.x)*.5; if(cd>0.) fw=0.;
        p.x=pmod(p.x,1./3.);
        float d=cd; d=max(d,-abs(p.x)+0.1); d/=sc;
        col=mix(col,c,smoothstep(fw,0.,d));
        col=mix(col,c,smoothstep(fwidth(cd),0.,abs(cd)));
    }

    /* ---- TEXT ------------------------------------------------------- */
    {
        float sc=2.25;
        vec2 p=uv-vec2(0.23,-0.45);
        float b=sdBox(p-vec2(0.21,-0.03),vec2(0.20,0.07));
        p.x*=1.; p.y*=0.95; p*=sc;
        float iters=6.;
        float lt=1e5;
        for(float i=0.; i<iters; i++){
            p.y-=0.04;
            float us_c=143.;
            float t=text(p,float[9](us_c,us_c,us_c,132.,113.,10.,
                                    us_c,us_c,us_c),
                         -0.5,0.4,true,0.,0.5+i/iters*0.1,false,i);
            if(i==0.)
                t=text(p,float[9](us_c,us_c,us_c,132.,113.,10.,
                                  us_c,us_c,us_c),
                       -0.5,0.4,false,0.,0.5,false,i);
            t-=0.004; t/=sc;
            lt=min(lt,t);
        }
        col=mix(col,c,smoothstep(fwidth(uv.y),0.,lt));
    }

    /* ---- DOTS ------------------------------------------------------- */
    {
        float sc=1.9;
        vec2 p=uv-vec2(0.03,-0.33); p*=sc;
        float t=1e5, iters=7.;
        for(float i=0.; i<iters; i++){
            vec2 a=vec2(0.,0.6);
            a.y+=max(sin(i+2.6+iTime)-0.5,0.)*0.1;
            vec2 b=a;
            t=xor(t,abs(sdSegment(p,a,b)-0.01*
                        max(sin(i+iTime*2.),0.4)),
                  0.05*(0.5+0.5*sin(i+iTime*5.+sin(iTime+i))));
            p.y+=0.12;
        }
        t/=sc;
        col=mix(col,c,smoothstep(fwidth(uv.y),0.,t));
    }

    return col;
}

/* ===================================================================== */
/* ---------------------------  IMAGE  --------------------------------- */
/* ===================================================================== */
vec3 finalImage(vec2 fragCoord, vec3 bufCol){
    vec2 uv=(fragCoord-0.5*iResolution.xy)/iResolution.y;
    vec3 col=vec3(0.0);

    /* subtle coordinate warp */
    vec2 warp=650.*noise(vec3(uv*0.5,5.))/iResolution.xy;
    vec2 warpedCoord=fragCoord+warp;

    /* use the buffer result instead of sampling it from iChannel0 */
    col=bufCol;

    /* darken based on secondary noise */
    float no=noise(vec3(uv*2.,35.));
    col=mix(col,vec3(0.0),
            smoothstep(0.,0.5,
                       max(noise(vec3(uv*2.2+0.1,35.))-0.5,0.))*0.4);

    /* glow pulse */
    col=mix(col,vec3(1.0),
            smoothstep(0.,5.,max(no-0.4,0.))*0.8);

    /* extra 1-D noise (optional) */
    float n1d=texelFetch(iChannel2,
                         ivec2(mod(fragCoord+vec2(float(iFrame)*0.,0.),256.)),
                         0).x*0.2;

    /* tonemap / gamma-ish */
    col=pow(max(col,0.),vec3(0.4545));
    col+=smoothstep(1.,0.,length(col))*0.01;
    col-=smoothstep(0.,1.,length(col))*0.05;

    return col;
}

/* ===================================================================== */
/* -----------------------------  MAIN  -------------------------------- */
/* ===================================================================== */
out vec4 fragColor;
void main(){
    vec2 fragCoord=gl_FragCoord.xy;

    /* first, simulate Buffer A for this fragment */
    vec3 bufCol=bufferA(fragCoord);

    /* then the original Image pass, using bufCol instead of tex fetch */
    vec3 col=finalImage(fragCoord,bufCol);

    fragColor=vec4(col,1.0);
}
