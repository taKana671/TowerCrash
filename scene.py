from direct.showbase.ShowBase import ShowBase
from panda3d.bullet import BulletRigidBodyNode
from panda3d.bullet import BulletPlaneShape, BulletCylinderShape, BulletConvexHullShape
from panda3d.core import Vec3, Point3, LColor, BitMask32, LVecBase2f
from panda3d.core import PandaNode, NodePath, TransparencyAttrib


from panda3d.bullet import BulletHeightfieldShape, ZUp
from panda3d.core import ShaderTerrainMesh, Shader, load_prc_file_data
from panda3d.core import SamplerState, ShaderTerrainMesh
from panda3d.core import CardMaker, TextureStage, BitMask32
from panda3d.core import TransparencyAttrib, CullFaceAttrib
from panda3d.core import Vec3, Point3, Texture, Fog
from panda3d.core import NodePath, Plane, PlaneNode, PandaNode
from direct.interval.LerpInterval import LerpTexOffsetInterval
from panda3d.core import Filename
from panda3d.core import PNMImage


from create_geomnode import Cylinder


load_prc_file_data("", """
    textures-power-2 none
    gl-coordinate-system default
    window-title Panda3D Walking In BulletWorld
    filled-wireframe-apply-shader true
    stm-max-views 8
    stm-max-chunk-count 2048""")


PATH_SKY = 'models/blue-sky/blue-sky-sphere'
PATH_STONE = 'models/cylinder/cylinder'
TEXTURE_STONE = 'textures/envir-rock1.jpg'
PATH_SEA = 'models/bump/bump'


class Foundation(NodePath):

    def __init__(self):
        super().__init__(BulletRigidBodyNode('foundation'))
        # stone = base.loader.load_model(PATH_STONE)
        stone = Cylinder()
        stone.set_texture(
            base.loader.load_texture(TEXTURE_STONE), 1)
        stone.reparent_to(self)
        
        # end, tip = stone.get_tight_bounds()
        # self.node().add_shape(BulletCylinderShape((tip - end) / 2))

        shape = BulletConvexHullShape()
        shape.add_geom(stone.node().get_geom(0))
        self.node().add_shape(shape)

        self.set_scale(20)
        self.set_collide_mask(BitMask32.bit(2))
        
        # self.set_p(180)
        self.set_pos(Point3(0, 0, -15))
        # self.set_pos(Point3(-2, 12, -10))


class Sky(NodePath):

    def __init__(self):
        super().__init__(PandaNode('sky'))
        sky = base.loader.load_model(PATH_SKY)
        sky.set_color(2, 2, 2, 1)
        sky.set_scale(0.02)
        sky.reparent_to(self)


class WaterSurface(NodePath):

    def __init__(self):
        super().__init__(BulletRigidBodyNode('water_surface'))
        self.set_collide_mask(BitMask32.bit(3))
        self.node().add_shape(BulletPlaneShape(Vec3.up(), 0))


class WaterBottom(NodePath):

    def __init__(self):
        super().__init__(BulletRigidBodyNode('water_bottom'))
        self.set_collide_mask(BitMask32.bit(4))
        self.node().add_shape(BulletPlaneShape(Vec3.up(), -10))


class Sea(NodePath):

    def __init__(self):
        super().__init__(PandaNode('sea'))
        sea = base.loader.load_model(PATH_SEA)
        sea.reparent_to(self)
        self.set_transparency(TransparencyAttrib.M_alpha)
        self.set_scale(13)
        self.set_pos(-2, 12, 0.5)
        self.set_color(LColor(0.25, 0.41, 1, 0.3))
        self.set_r(180)


class Scene(NodePath):

    def __init__(self, world):
    # def __init__(self):
        super().__init__(PandaNode('scene'))
        self.sky = Sky()
        self.sky.reparent_to(self)
        
        # sea = Sea()
        # sea.reparent_to(self)

        # base.setBackgroundColor(0.5, 0.8, 0.9)

        self.foundation = Foundation()
        self.foundation.reparent_to(self)
        world.attach(self.foundation.node())

        self.surface = WaterSurface()
        self.surface.reparent_to(self)
        world.attach(self.surface.node())

        self.bottom = WaterBottom()
        self.bottom.reparent_to(self)
        world.attach(self.bottom.node())

        self.create_water()
        # self.create_fog()

        # self.reparent_to(base.render)

    def create_fog(self):
        fog = Fog("fog")
        fog.set_mode(Fog.MExponentialSquared)
        # fog.set_color(128/255.0, 128/255.0, 128/255.0)
        color = (0.8, 0.8, 0.8)
        fog.set_color(*color)
        fog.set_exp_density(0.013)
        base.render.set_fog(fog)

        # pass
        # self.fog0color=(0.66,0.75,0.85,1.0)
        # base.setBackgroundColor(self.fog0color)
        # self.fog0=Fog('fog')
        # self.fog0.setColor(self.fog0color)
        # self.fog0.setMode(Fog.MExponentialSquared )
        # self.fog0.setExpDensity(0.0002)
        # base.render.setFog(self.fog0)



        # fog = Fog("fog")
        # fog.set_mode(Fog.MExponentialSquared)
        # fog.set_color(128/255.0, 128/255.0, 128/255.0)
        # fog.set_exp_density(0.013)
        # base.render.set_fog(fog)

       
        # color = (0.8, 0.8, 0.8)
        # exp_fog = Fog('sample_fog')
        # exp_fog.set_color(*color)
        # # exp_fog.set_mode(Fog.M_linear)
        # # exp_fog.setLinearOnsetPoint(0, -128, -100)
        # # exp_fog.set_linear_range(0, 100)
        # exp_fog.setLinearFallback(45, 160, 320)
        # np = self.surface.attach_new_node(exp_fog)

        # np = self.sky.attach_new_node(exp_fog)
        # base.render.set_fog(exp_fog)
        # self.sky.set_fog(exp_fog)
        # np.set_pos(0, 0, -5)

    def create_water(self):
        size = 512  # size of the wave buffer
        cm = CardMaker('plane')
        cm.set_frame(0, 256, 0, 256)
        self.water_plane = base.render.attach_new_node(cm.generate())
        self.water_plane.look_at(0, 0, -1)

        # pos = self.terrain.get_pos()
        # pos.z = -3
        # print(pos)
        self.water_plane.set_pos(Point3(-127.5, -127.5, 0))
        self.water_plane.flatten_strong()
        self.water_plane.set_shader(Shader.load(Shader.SL_GLSL, 'water_v.glsl', 'water_f.glsl'))
        
        # self.water_plane.set_shader(Shader.load(Shader.SL_GLSL, 'fog_v.glsl', 'fog_f.glsl'))
        self.water_plane.set_shader_input('size', size)
        self.water_plane.set_shader_input('normal_map', base.loader.load_texture('normal.png'))

        # self.props = self.win.get_properties()
        # self.water_plane.set_shader_input('u_resolution', self.props.get_size())

        # light_pos = (128.0, 300.0, 50.0, 500 * 500)
        light_pos = (-20, 300.0, 50.0, 500 * 500)    # (0, 128.0, 20.0, 500 * 500)
        light_color = (0.9, 0.9, 0.9, 1.0)
        self.water_plane.set_shader_input('light_pos', light_pos)      # render.setShaderInput('light_pos', light_pos)
        self.water_plane.set_shader_input('light_color', light_color)  # render.setShaderInput('light_color', light_color)
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

        # self.clip_plane = Plane(Vec3(0, 0, 1), Point3(0, 0, 0.5))
        self.clip_plane = Plane(Vec3(0, 0, 1), Point3(0, 0, -5))  # -4 and -5 are OK too. 
        clip_plane_node = base.render.attach_new_node(PlaneNode('water', self.clip_plane))
        tmp_node = NodePath('StateInitializer')
        tmp_node.set_clip_plane(clip_plane_node)
        tmp_node.set_attrib(CullFaceAttrib.make_reverse())

        self.water_camera.node().set_initial_state(tmp_node.get_state())
        self.water_plane.set_shader_input('camera', self.water_camera)
        self.water_plane.set_shader_input('reflection', reflect_tex)
        # self.water_plane.set_shader_input('u_resolution', self.water_buffer.get_size())




if __name__ == '__main__':
    base = ShowBase()
    base.disableMouse()
    base.camera.setPos(10, -40, 10)  # 20, -20, 5
    # base.camera.setPos(-2, 12, 30)  # 20, -20, 5
    # base.camera.setP(-80)
    base.camera.lookAt(-2, 12, 10)  # 5, 0, 3
    scene = Scene()
    base.run()