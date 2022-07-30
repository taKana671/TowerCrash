import random
import math
from enum import Enum, auto

from direct.gui.DirectGui import OnscreenText, ScreenTitle
from direct.gui.DirectGui import DirectOptionMenu, DirectLabel, DirectButton
from direct.interval.IntervalGlobal import Sequence, Parallel, Func, Wait
from direct.showbase.InputStateGlobal import inputState
from direct.showbase.ShowBaseGlobal import globalClock
from direct.showbase.ShowBase import ShowBase

from panda3d.bullet import BulletSphereShape, BulletCylinderShape
from panda3d.bullet import BulletWorld, BulletRigidBodyNode

from panda3d.core import TextNode, PandaNode, NodePath
from panda3d.core import Quat, Vec3, LColor, BitMask32, Point3
from panda3d.core import AmbientLight, DirectionalLight
from panda3d.core import CollisionTraverser, CollisionNode
from panda3d.core import CollisionHandlerQueue, CollisionRay
from panda3d.core import WindowProperties

from scene import Scene


PATH_CYLINDER = "models/cylinder/cylinder"
# PATH_CYLINDER = "models/alice-shapes--box/box"


class Colors(Enum):

    RED = LColor(1, 0, 0, 1)
    BLUE = LColor(0, 0, 1, 1)
    YELLOW = LColor(1, 1, 0, 1)
    GREEN = LColor(0, 0.5, 0, 1)
    VIOLET = LColor(0.54, 0.16, 0.88, 1)
    MAGENTA = LColor(1, 0, 1, 1)

    @classmethod
    def select(cls):
        return random.choice([m.value for m in cls])


class CylinderTower(NodePath):

    def __init__(self):
        super().__init__(PandaNode('foundation'))
        self.reparentTo(base.render)

    def create_cylinder(self, pos, color):
        np = NodePath(BulletRigidBodyNode('cylinter'))
        np.reparentTo(self)
        cylinder = base.loader.loadModel(PATH_CYLINDER)
        cylinder.reparentTo(np)
        end, tip = cylinder.getTightBounds()
        np.node().addShape(BulletCylinderShape((tip - end) / 2))
        np.node().setMass(1)
        np.setScale(0.7)
        np.setColor(color)
        np.setPos(pos)

        return np

    def create_tower(self, center, physical_world):
        edge = 1.5                     # the length of one side
        ok = edge / 2 / math.sqrt(3)   # the length of line OK, O: center of triangle 
        height = 2.5

        for i in range(1, 5):
            h = height * i
            if i % 2 == 0:
                points = [Point3(edge / 2, -ok, h), Point3(-edge / 2, -ok, h), Point3(0, ok * 2, h)]
            else:
                points = [Point3(-edge / 2, ok, h), Point3(edge / 2, ok, h), Point3(0, -ok * 2, h)]

            for pt in points:
                cylinder = self.create_cylinder(pt + center, Colors.select())
                physical_world.attachRigidBody(cylinder.node())


class Ball(NodePath):

    def __init__(self):
        super().__init__(BulletRigidBodyNode('ball'))
        self.reparentTo(base.render)
        self.ball = base.loader.loadModel('models/sphere/sphere')
        self.ball.setScale(0.3)
        self.ball.setColor(Colors.YELLOW.value)
        self.ball.setPos(Point3(0, 0, -5))
        self.ball.reparentTo(self)
        end, tip = self.ball.getTightBounds()
        size = tip - end
        radius = size.z / 2
        self.node().addShape(BulletSphereShape(radius))


class TowerClash(ShowBase):

    def __init__(self):
        super().__init__()
        self.disableMouse()
        self.camera.setPos(20, -18, 10)  # 20, -20, 5
        self.camera.setHpr(0, -80, 0)
        self.camera.lookAt(5, 3, 5)  # 5, 0, 3
        self.setup_lights()
        self.setup_click_detection()
        self.physical_world = BulletWorld()
        self.physical_world.setGravity(Vec3(0, 0, -9.81))

        self.block_root = NodePath(PandaNode('blockRoot'))
        self.block_root.reparentTo(self.render)
        self.scene = Scene()
        self.create_tower()
        self.scene.setup(self.physical_world)

        self.accept('mouse1', self.click)
        self.taskMgr.add(self.update, 'update')

    def create_tower(self):
        cylinder_tower = CylinderTower()
        center = Point3(-2, 12, 0.3)
        cylinder_tower.create_tower(center, self.physical_world)

    def setup_click_detection(self):
        self.picker = CollisionTraverser()
        self.handler = CollisionHandlerQueue()

        self.picker_node = CollisionNode('mouseRay')
        self.picker_np = self.camera.attachNewNode(self.picker_node)
        self.picker_node.setFromCollideMask(BitMask32.bit(1))
        self.picker_ray = CollisionRay()
        self.picker_node.addSolid(self.picker_ray)
        self.picker.addCollider(self.picker_np, self.handler)

    def setup_lights(self):
        ambient_light = self.render.attachNewNode(AmbientLight('ambientLight'))
        ambient_light.node().setColor(LColor(0.6, 0.6, 0.6, 1))
        self.render.setLight(ambient_light)

        directional_light = self.render.attachNewNode(DirectionalLight('directionalLight'))
        directional_light.node().getLens().setFilmSize(200, 200)
        directional_light.node().getLens().setNearFar(1, 100)
        directional_light.node().setColor(LColor(1, 1, 1, 1))
        directional_light.setPosHpr(Point3(0, 0, 30), Vec3(-30, -45, 0))
        directional_light.node().setShadowCaster(True)
        self.render.setShaderAuto()
        self.render.setLight(directional_light)

    def click(self):
        if self.mouseWatcherNode.hasMouse():
            print('click')
            self.ball = Ball()
            self.ball.node().setMass(150)
            self.physical_world.attachRigidBody(self.ball.node())
            self.ball.ball.posInterval(0.2, Point3(0, 0, 1.8)).start()
            # self.block2.node().setActive(True)
            # force = Vec3.forward() * 100
            # self.block2.node().applyTorqueImpulse(force)
            # self.block2.node().applyCentralForce(force)
            # self.block2.node().applyForce(force, Point3(0, 0, 2.3))

            # pos = self.mouseWatcherNode.getMouse()
            # self.picker_ray.setFromLens(self.camNode, pos.getX(), pos.getY())
            # self.picker.traverse(self.block_root)

            # if self.handler.getNumEntries() > 0:
            #     self.handler.sortEntries()
            #     tag = int(self.handler.getEntry(0).getIntoNode().getTag('cylinder'))
            #     print(tag)
            #     ball = Ball()

    def update(self, task):
        self.physical_world.doPhysics(globalClock.getDt())
        return task.cont

if __name__ == '__main__':
    game = TowerClash()
    game.run()
    # base = ShowBase()
    # base.setBackgroundColor(1, 1, 1)
    # base.disableMouse()
    # base.camera.setPos(0, -10, 5)
    # base.camera.lookAt(0, 0, 0)
    # cylinder = Cylinder()
    # cylinder.setPos(0, 0, 0)
    # cylinder.setColor(LColor(1, 0, 1, 1))
    # base.run()

