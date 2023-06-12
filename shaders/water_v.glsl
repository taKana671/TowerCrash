//GLSL
#version 140

uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat4 p3d_ModelViewMatrix;
uniform mat4 trans_model_to_clip_of_camera;

uniform mat4 p3d_ViewMatrix;
uniform float osg_FrameTime;
in vec2 p3d_MultiTexCoord0;
in vec4 p3d_Vertex;
out vec2 uv;
out vec2 time_uv1;
out vec2 time_uv2;
out vec4 reflect_uv;
out vec4 vpos;

uniform vec4 light_pos;
out vec4 pointLight;

void main()
    { 
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;        
    uv=p3d_MultiTexCoord0;
    time_uv1=p3d_MultiTexCoord0*4.0+osg_FrameTime*0.03;
    time_uv2=p3d_MultiTexCoord0*3.0-osg_FrameTime*0.04;
    vpos = p3d_ModelViewMatrix * p3d_Vertex;

    pointLight=p3d_ViewMatrix*vec4(light_pos.xyz, 1.0);       
    pointLight.w=light_pos.w;
    vec4 camclip = trans_model_to_clip_of_camera* p3d_Vertex; 
    reflect_uv = camclip * vec4(0.5,0.5,0.5,1.0) + camclip.w * vec4(0.5,0.5,0.5,0.0);    
    }
