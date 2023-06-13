from panda3d.core import NodePath, TransparencyAttrib
from panda3d.core import Shader
from panda3d.core import BitMask32, Point3, CardMaker


class StartScreen:

    def __init__(self):
        self.alpha = 1.0
        self.create_color_gradient()
        self.create_color_camera()

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

    def create_color_camera(self):
        self.color_buffer = base.win.make_texture_buffer('gradieng', 512, 512)
        self.color_buffer.set_clear_color(base.win.get_clear_color())
        self.color_buffer.set_sort(-1)

        self.color_camera = base.make_camera(self.color_buffer)
        self.color_camera.node().set_lens(base.camLens)
        self.color_camera.node().set_camera_mask(BitMask32.bit(1))

    def set_up(self):
        self.color_plane.reparent_to(base.render)
        self.color_camera.reparent_to(base.render)

    def tear_down(self):
        self.color_plane.detach_node()
        self.color_camera.detach_node()

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
