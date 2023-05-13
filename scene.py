from direct.showbase.ShowBase import ShowBase
from panda3d.bullet import BulletRigidBodyNode
from panda3d.bullet import BulletPlaneShape, BulletCylinderShape
from panda3d.core import Vec3, Point3, LColor, BitMask32
from panda3d.core import PandaNode, NodePath, TransparencyAttrib


PATH_SKY = 'models/blue-sky/blue-sky-sphere'
PATH_STONE = 'models/cylinder/cylinder'
TEXTURE_STONE = 'textures/envir-rock1.jpg'
PATH_SEA = 'models/bump/bump'


class Foundation(NodePath):

    def __init__(self):
        super().__init__(BulletRigidBodyNode('foundation'))
        stone = base.loader.load_model(PATH_STONE)
        stone.set_texture(
            base.loader.load_texture(TEXTURE_STONE), 1)
        stone.reparent_to(self)
        end, tip = stone.get_tight_bounds()
        self.node().add_shape(BulletCylinderShape((tip - end) / 2))
        self.set_scale(7)
        self.set_collide_mask(BitMask32.bit(2))
        self.set_pos(Point3(-2, 12, -10))


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
        super().__init__(PandaNode('scene'))
        sky = Sky()
        sky.reparent_to(self)
        sea = Sea()
        sea.reparent_to(self)

        self.foundation = Foundation()
        self.foundation.reparent_to(self)
        world.attach(self.foundation.node())

        self.surface = WaterSurface()
        self.surface.reparent_to(self)
        world.attach(self.surface.node())

        self.bottom = WaterBottom()
        self.bottom.reparent_to(self)
        world.attach(self.bottom.node())

        self.reparent_to(base.render)


if __name__ == '__main__':
    base = ShowBase()
    base.disableMouse()
    base.camera.setPos(10, -40, 10)  # 20, -20, 5
    # base.camera.setPos(-2, 12, 30)  # 20, -20, 5
    # base.camera.setP(-80)
    base.camera.lookAt(-2, 12, 10)  # 5, 0, 3
    scene = Scene()
    base.run()