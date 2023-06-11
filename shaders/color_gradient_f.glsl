#version 300 es
precision highp float;

out vec4 fragColor;
uniform float osg_FrameTime;
uniform vec2 u_resolution;

uniform float alpha;


void main(){
    vec2 uv = gl_FragCoord.xy / u_resolution.xy;
    vec4 startColor = vec4(0.254, 0.568, 0.921, alpha);
    vec4 endColor = vec4(0.913, 0.941, 0.980, alpha);

    // vec4 startColor = vec4(0.658, 0.792, 0.941, 1.0);
    // vec4 endColor = vec4(0.913, 0.941, 0.980, 1.0);

    float currentAngle = -(osg_FrameTime * 36.0);
    vec2 origin = vec2(0.5, 0.5);
    uv -= origin;
    
    float angle = radians(90.0) - radians(currentAngle) + atan(uv.y, uv.x);

    float len = length(uv);
    uv = vec2(cos(angle) * len, sin(angle) * len) + origin;
	    
    fragColor = mix(startColor, endColor, smoothstep(0.0, 1.0, uv.x));
}