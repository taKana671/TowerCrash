from direct.showbase.ShowBase import ShowBase
from panda3d.bullet import BulletRigidBodyNode
from panda3d.bullet import BulletPlaneShape, BulletCylinderShape
from panda3d.core import Vec3, Point3, LColor, BitMask32
from panda3d.core import PandaNode, NodePath, CardMaker, TransparencyAttrib


PATH_SKY = 'models/blue-sky/blue-sky-sphere'
PATH_STONE = 'models/cylinder/cylinder'
TEXTURE_STONE = 'textures/envir-rock1.jpg'
PATH_SEA = 'models/bump/bump'


class Foundation(NodePath):

    def __init__(self, name):
        super().__init__(BulletRigidBodyNode(name))
        self.reparentTo(base.render)
        self.name = name
        stone = base.loader.loadModel(PATH_STONE)
        stone.setTexture(
            base.loader.loadTexture(TEXTURE_STONE), 1)
        stone.reparentTo(self)
        end, tip = stone.getTightBounds()
        self.node().addShape(BulletCylinderShape((tip - end) / 2))
        self.setScale(7)
        self.setCollideMask(BitMask32.bit(2))
        self.setPos(Point3(-2, 12, -10))


class Sky(NodePath):

    def __init__(self, name):
        super().__init__(PandaNode(name))
        self.reparentTo(base.render)
        self.name = name
        sky = base.loader.loadModel(PATH_SKY)
        sky.setColor(2, 2, 2, 1)
        sky.setScale(0.02)
        sky.reparentTo(self)


class WaterSurface(NodePath):

    def __init__(self, name):
        super().__init__(BulletRigidBodyNode(name))
        self.reparentTo(base.render)
        self.name = name
        self.setCollideMask(BitMask32.bit(3))
        self.node().addShape(BulletPlaneShape(Vec3.up(), 0))


class WaterBottom(NodePath):

    def __init__(self, name):
        super().__init__(BulletRigidBodyNode(name))
        self.reparentTo(base.render)
        self.name = name
        self.setCollideMask(BitMask32.bit(4))
        self.node().addShape(BulletPlaneShape(Vec3.up(), -10))


class Sea(NodePath):

    def __init__(self, name):
        super().__init__(PandaNode(name))
        self.reparentTo(base.render)
        self.name = name
        sea = base.loader.loadModel(PATH_SEA)
        sea.reparentTo(self)
        self.setTransparency(TransparencyAttrib.M_alpha)
        self.setScale(13)
        self.setPos(-2, 12, 0.5)
        self.setColor(LColor(0.25, 0.41, 1, 0.3))
        self.setR(180)


class Scene:

    def __init__(self):
        self.sky = Sky('sky')
        self.sea = Sea('sea')
        self.foundation = Foundation('foundation')
        self.surface = WaterSurface('waterSurface')
        self.bottom = WaterBottom('waterBottom')

    def setup(self, physical_world):
        physical_world.attachRigidBody(self.surface.node())
        physical_world.attachRigidBody(self.foundation.node())
        physical_world.attachRigidBody(self.bottom.node())



if __name__ == '__main__':
    base = ShowBase()
    base.disableMouse()
    base.camera.setPos(10, -40, 10)  # 20, -20, 5
    # base.camera.setPos(-2, 12, 30)  # 20, -20, 5
    # base.camera.setP(-80)
    base.camera.lookAt(-2, 12, 10)  # 5, 0, 3
    scene = Scene()
    base.run()