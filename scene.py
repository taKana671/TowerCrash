from panda3d.bullet import BulletRigidBodyNode
from panda3d.bullet import BulletPlaneShape, BulletConvexHullShape
from panda3d.core import Vec3, Point3, BitMask32, CardMaker
from panda3d.core import PandaNode, NodePath, TransparencyAttrib, CullFaceAttrib
from panda3d.core import Shader
from panda3d.core import Texture
from panda3d.core import Plane, PlaneNode

from create_geomnode import CylinderGeom


PATH_SKY = 'models/blue-sky/blue-sky-sphere'
TEXTURE_STONE = 'textures/envir-rock1.jpg'


class Foundation(NodePath):

    def __init__(self):
        super().__init__(BulletRigidBodyNode('foundation'))
        stone = CylinderGeom()
        stone.set_texture(
            base.loader.load_texture(TEXTURE_STONE), 1)
        stone.reparent_to(self)

        shape = BulletConvexHullShape()
        shape.add_geom(stone.node().get_geom(0))
        self.node().add_shape(shape)

        self.set_scale(20)
        self.set_collide_mask(BitMask32.bit(2))
        self.set_pos(Point3(0, 0, -15))


class Sky(NodePath):

    def __init__(self):
        super().__init__(PandaNode('sky'))
        sky = base.loader.load_model(PATH_SKY)
        sky.set_color(2, 2, 2, 1)
        sky.set_scale(0.02)
        sky.reparent_to(self)


class WaterBottom(NodePath):

    def __init__(self):
        super().__init__(BulletRigidBodyNode('water_bottom'))
        self.set_collide_mask(BitMask32.bit(4))
        self.node().add_shape(BulletPlaneShape(Vec3.up(), -10))


class Scene(NodePath):

    def __init__(self, world):
        super().__init__(PandaNode('scene'))
        self.sky = Sky()
        self.sky.reparent_to(self)

        self.foundation = Foundation()
        self.foundation.reparent_to(self)
        world.attach(self.foundation.node())

        self.bottom = WaterBottom()
        self.bottom.reparent_to(self)
        world.attach(self.bottom.node())

        self.create_water()

    def create_water(self):
        size = 512  # size of the wave buffer
        cm = CardMaker('plane')
        cm.set_frame(0, 256, 0, 256)
        self.water_plane = base.render.attach_new_node(cm.generate())
        self.water_plane.set_transparency(TransparencyAttrib.MAlpha)
        self.water_plane.look_at(0, 0, -1)

        self.water_plane.set_pos(Point3(-128, -128, 0))
        self.water_plane.flatten_strong()
        self.water_plane.set_shader(Shader.load(Shader.SL_GLSL, 'shaders/water_v.glsl', 'shaders/water_f.glsl'))
        self.water_plane.set_shader_input('size', size)
        self.water_plane.set_shader_input('normal_map', base.loader.load_texture('images/normal.png'))

        light_pos = (-20, 300.0, 50.0, 500 * 500)    # (0, 128.0, 20.0, 500 * 500)
        light_color = (0.9, 0.9, 0.9, 1.0)
        self.water_plane.set_shader_input('light_pos', light_pos)
        self.water_plane.set_shader_input('light_color', light_color)
        self.water_plane.hide(BitMask32.bit(1))

        self.water_buffer = base.win.make_texture_buffer('water', 512, 512)
        self.water_buffer.set_clear_color(base.win.get_clear_color())
        self.water_buffer.set_sort(-1)

        self.water_camera = base.make_camera(self.water_buffer)
        self.water_camera.reparent_to(base.render)
        self.water_camera.node().set_lens(base.camLens)
        self.water_camera.node().set_camera_mask(BitMask32.bit(1))

        reflect_tex = self.water_buffer.get_texture()
        reflect_tex.set_wrap_u(Texture.WMClamp)
        reflect_tex.set_wrap_v(Texture.WMClamp)

        self.clip_plane = Plane(Vec3(0, 0, 1), Point3(0, 0, -5))  # -4 and -5 are OK too. 
        clip_plane_node = base.render.attach_new_node(PlaneNode('water', self.clip_plane))
        tmp_node = NodePath('StateInitializer')
        tmp_node.set_clip_plane(clip_plane_node)
        tmp_node.set_attrib(CullFaceAttrib.make_reverse())

        self.water_camera.node().set_initial_state(tmp_node.get_state())
        self.water_plane.set_shader_input('camera', self.water_camera)
        self.water_plane.set_shader_input('reflection', reflect_tex)


# if __name__ == '__main__':
#     base = ShowBase()
#     base.disableMouse()
#     base.camera.setPos(10, -40, 10)  # 20, -20, 5
#     # base.camera.setPos(-2, 12, 30)  # 20, -20, 5
#     # base.camera.setP(-80)
#     base.camera.lookAt(-2, 12, 10)  # 5, 0, 3
#     scene = Scene()
#     base.run()