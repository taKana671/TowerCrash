from panda3d.core import NodePath, TransparencyAttrib
from panda3d.core import Shader
from panda3d.core import Point3, CardMaker


class StartScreen:

    def __init__(self):
        self.alpha = 1.0
        self.create_color_gradient()

    def create_color_gradient(self):
        cm = CardMaker('gradient')
        cm.set_frame(0, 256, 0, 256)
        self.color_plane = NodePath(cm.generate())
        self.color_plane.look_at(0, 1, 0)
        self.color_plane.set_transparency(TransparencyAttrib.MAlpha)
        self.color_plane.set_pos(Point3(-128, -50, 0))  # Point3(-128, -128, -2)
        self.color_plane.flatten_strong()

        self.color_plane.set_shader(
            Shader.load(Shader.SL_GLSL, 'shaders/color_v.glsl', 'shaders/color_f.glsl')
        )
        props = base.win.get_properties()
        self.color_plane.set_shader_input('u_resolution', props.get_size())
        self.color_plane.set_shader_input('alpha', self.alpha)

    def set_up(self):
        self.color_plane.reparent_to(base.render)

    def tear_down(self):
        self.color_plane.detach_node()

    def appear(self, dt):
        if self.alpha == 1.0:
            return True

        self.alpha += dt * 0.1
        if self.alpha > 1.0:
            self.alpha = 1.0

        self.color_plane.set_shader_input('alpha', self.alpha)

    def disappear(self, dt):
        if self.alpha == 0.0:
            return True

        self.alpha -= dt * 0.1
        if self.alpha < 0.0:
            self.alpha = 0.0

        self.color_plane.set_shader_input('alpha', self.alpha)
