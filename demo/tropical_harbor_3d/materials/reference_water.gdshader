shader_type spatial;
render_mode blend_mix, depth_draw_never, cull_disabled;
uniform sampler2D water_noise : repeat_enable, filter_linear_mipmap;
uniform sampler2D reflection_tex : source_color, repeat_disable, filter_linear;
uniform vec4 boats[3];
uniform vec2 stern_directions[3];
uniform float study_time = 0.0;
uniform vec3 deep_color : source_color = vec3(0.035, 0.29, 0.52);
uniform vec3 near_color : source_color = vec3(0.035, 0.58, 0.62);
uniform vec3 foam_color : source_color = vec3(0.72, 0.87, 0.83);
varying vec3 wp;
float coast(float z) {
    float t=clamp((z+18.7)/(-26.0+18.7),0.0,1.0);
    return 7.8+1.45*sin(z*.12)+.48*sin(z*.29)-21.0*t*t*(3.0-2.0*t);
}
void vertex() {
    wp=(MODEL_MATRIX*vec4(VERTEX,1.0)).xyz;
    float strength=smoothstep(.4,4.0,coast(wp.z)-wp.x);
    VERTEX.y+=(sin(wp.x*.66+wp.z*.43+study_time*.72)*.025+sin(wp.z*1.15-wp.x*.28+study_time*.93)*.016+sin(wp.x*.28+wp.z*.19+study_time*.64)*.035)*strength;
    wp=(MODEL_MATRIX*vec4(VERTEX,1.0)).xyz;
}
void fragment() {
    float d=coast(wp.z)-wp.x;
    float noise=texture(water_noise,wp.xz*.085+vec2(study_time*.006,-study_time*.002)).r;
    float broad=texture(water_noise,wp.xz*.025+vec2(.1,.7)).g;
    float near_weight=1.0-smoothstep(2.0,15.0,d+broad*2.5);
    vec3 col=mix(deep_color,near_color,near_weight);
    col*=.94+.09*noise+.055*sin(wp.x*.85+wp.z*1.2+noise*3.0+study_time*.65);
    vec2 grad=vec2(cos(wp.x*.66+wp.z*.43+study_time*.72)*.0165-cos(wp.z*1.15-wp.x*.28+study_time*.93)*.00448,
        cos(wp.x*.66+wp.z*.43+study_time*.72)*.01075+cos(wp.z*1.15-wp.x*.28+study_time*.93)*.0184);
    NORMAL=normalize(mat3(VIEW_MATRIX)*vec3(-grad.x,1.0,-grad.y));
    // Sparse short white strokes, broken up by the flowing surface.
    vec2 cell=floor(wp.xz*vec2(1.9,1.2));
    float hash=fract(sin(dot(cell,vec2(127.1,311.7)))*43758.5453);
    vec2 local=fract(wp.xz*vec2(1.9,1.2)+vec2(study_time*.06,study_time*.015));
    float streak=(1.0-smoothstep(.012,.035,abs(local.y-.52)))*(1.0-smoothstep(.09,.27,abs(local.x-.5)));
    float sparkle=streak*smoothstep(.91,.98,hash)*(.35+.3*sin(study_time+hash*20.0));
    float edge_width=.025+.025*noise;
    float foam=(1.0-smoothstep(edge_width,edge_width+.04,abs(d-.09-.045*sin(wp.z*1.7+study_time*.9))))*.65;
    for(int i=0;i<3;i++){
        if(boats[i].w<0.0){continue;}
        vec2 stern=stern_directions[i];
        vec2 delta=wp.xz-boats[i].xz;
        vec2 r=vec2(dot(delta,vec2(stern.y,-stern.x)),dot(delta,stern));
        float e=length(vec2(r.x/.86,r.y/2.37));
        float contact=(1.0-smoothstep(.020,.09,abs(e-1.0)))*.52;
        float wake=(1.0-smoothstep(.025,.12,abs(abs(r.x)-(.72+(r.y-2.0)*.21))))*smoothstep(1.9,2.5,r.y)*(1.0-smoothstep(2.6,7.0,r.y))*max(boats[i].w,0.0)*.48;
        foam=max(foam,max(contact,wake));
    }
    vec2 uv=vec2(1.0-SCREEN_UV.x,SCREEN_UV.y)+grad*.035+vec2(noise-.5,noise-.5)*.003;
    vec4 refl=texture(reflection_tex,uv);
    col=mix(col,refl.rgb,refl.a*.18*(1.0-foam));
    ALBEDO=mix(col,foam_color,clamp(foam+sparkle,0.0,.85));
    EMISSION=foam_color*sparkle*.20;
    ROUGHNESS=.34;
    SPECULAR=.30;
    ALPHA=mix(.78,.98,smoothstep(.2,4.0,d))*smoothstep(-.02,.14,d);
}
