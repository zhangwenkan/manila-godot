shader_type spatial;
render_mode cull_disabled;
uniform sampler2D detail_noise : repeat_enable, filter_linear_mipmap;
varying vec3 wp;
float bank(float z) {
    float t=clamp((z+18.7)/(-26.0+18.7),0.0,1.0);
    return 7.8+1.45*sin(z*.12)+.48*sin(z*.29)-21.0*t*t*(3.0-2.0*t);
}
void vertex() { wp=(MODEL_MATRIX*vec4(VERTEX,1.0)).xyz; }
void fragment() {
    float d=wp.x-bank(wp.z);
    float n=texture(detail_noise,wp.xz*.38).r;
    float fine=texture(detail_noise,wp.xz*6.0).r;
    float path=5.8+.5*sin(wp.z*.16)+.3*sin(wp.z*.37);
    float access=min(min(min(abs(wp.z+24.0),abs(wp.z+10.0)),min(abs(wp.z-7.0),abs(wp.z-20.0))),
        min(min(abs(wp.z-34.0),abs(wp.z-44.0)),min(abs(wp.z-55.0),min(abs(wp.z-65.0),abs(wp.z-77.0)))));
    float grass=smoothstep(3.05,3.18,d+(n-.5)*.48);
    grass*=smoothstep(.9,1.18,abs(d-path)+(n-.5)*.40);
    if(d<9.0){grass*=smoothstep(.82,1.10,access+(n-.5)*.4);}
    // Sandy working paths, a narrow exposed bank, and broad green ground.
    vec3 sand=vec3(.60,.41,.19);
    vec3 green=vec3(.10,.20,.025);
    float bank_soil=smoothstep(2.45,2.8,d)*(1.0-smoothstep(3.05,3.2,d))*(1.0-smoothstep(.2,.65,grass))*smoothstep(.9,1.3,access);
    sand=mix(sand,vec3(.25,.145,.07),bank_soil*.75);
    ALBEDO=mix(sand,green,grass)*(.92+.13*n+.045*fine);
    ROUGHNESS=.94;
    SPECULAR=.12;
}
