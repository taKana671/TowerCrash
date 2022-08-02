import itertools
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

    def __init__(self, center, foundation):
        super().__init__(PandaNode('foundation'))
        self.center = center  # Point3(-2, 12, 0.3)
        self.foundation = foundation
        self.axis = Vec3.up()
        self.reparentTo(base.render)
        self.target_cylinder = None

    def create_cylinder(self, pos, color, tag):
        np = NodePath(BulletRigidBodyNode(tag))
        np.reparentTo(self)
        cylinder = base.loader.loadModel(PATH_CYLINDER)
        cylinder.reparentTo(np)
        end, tip = cylinder.getTightBounds()
        np.setCollideMask(BitMask32.bit(1) | BitMask32.bit(2))
        np.node().addShape(BulletCylinderShape((tip - end) / 2))
        np.node().setMass(5)
        np.setScale(0.7)
        np.setColor(color)
        np.setPos(pos)

        return np

    def build(self, stories, physical_world):
        self.cylinders = [[None for _ in range(3)] for _ in range(stories)]
        edge = 1.5                     # the length of one side
        ok = edge / 2 / math.sqrt(3)   # the length of line OK, O: center of triangle 
        height = 2.5

        for i in range(stories):
            h = height * (i + 1)
            if i % 2 == 0:
                points = [Point3(edge / 2, -ok, h), Point3(-edge / 2, -ok, h), Point3(0, ok * 2, h)]
            else:
                points = [Point3(-edge / 2, ok, h), Point3(edge / 2, ok, h), Point3(0, -ok * 2, h)]

            for j, pt in enumerate(points):
                cylinder = self.create_cylinder(pt + self.center, Colors.select(), str(i * 3 + j))
                physical_world.attachRigidBody(cylinder.node())
                self.cylinders[i][j] = cylinder

    def rotate_around(self, angle):
        self.foundation.setH(self.foundation.getH() + angle)
        q = Quat()
        q.setFromAxisAngle(angle, self.axis.normalized())

        for i, j in itertools.product(range(5), range(3)):
            if cylinder := self.cylinders[i][j]:
                r = q.xform(cylinder.getPos() - self.center)
                pos = self.center + r
                cylinder.setPos(pos)


class Ball(NodePath):

    def __init__(self, pos, physical_world):
        super().__init__(BulletRigidBodyNode('ball'))
        self.reparentTo(base.render)
        ball = base.loader.loadModel('models/sphere/sphere')
        ball.reparentTo(self)
        end, tip = ball.getTightBounds()
        size = tip - end
        radius = size.z / 2
        self.node().addShape(BulletSphereShape(radius))
        self.setScale(0.2)
        self.setColor(Colors.select())
        self.setPos(pos)

        self.setCollideMask(BitMask32.bit(2))

        self.node().setMass(30)
        # self.node().setKinematic(True)
        physical_world.attachRigidBody(self.node())

        self.destination = None

    def move(self):
        self.posInterval(0.5, self.destination).start()
        # self.setPos(self.destination)


class TowerClash(ShowBase):

    def __init__(self):
        super().__init__()
        self.disableMouse()
        self.camera.setPos(20, -18, 10)  # 20, -20, 5
        self.camera.setHpr(0, -80, 0)
        # self.camera.lookAt(Point3(-2, 12, 0.3))
        self.camera.lookAt(5, 3, 5)  # 5, 0, 3

        self.setup_lights()
        self.setup_click_detection()
        self.physical_world = BulletWorld()
        self.physical_world.setGravity(Vec3(0, 0, -9.81))

        self.scene = Scene()
        self.create_tower()
        self.scene.setup(self.physical_world)

        self.ball = Ball(Point3(6, 0, 0.5), self.physical_world)

        self.dragging_duration = 0
        self.max_duration = 5
        self.mouse_grabbed = False

        self.accept('mouse1', self.click)
        self.accept('mouse1-up', self.release)
        self.taskMgr.add(self.update, 'update')

    def create_tower(self):
        center = Point3(-2, 12, 1.0)
        self.tower = CylinderTower(center, self.scene.foundation)
        self.tower.build(5, self.physical_world)

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

    def create_ball(self):
        self.ball = Ball(Point3(10, -10, 2))

    def click(self):
        self.dragging_duration = 0
        self.mouse_grabbed = False

        if self.mouseWatcherNode.hasMouse():
            mouse_pos = self.mouseWatcherNode.getMouse()
            near_pos = Point3()
            far_pos = Point3()
            self.camLens.extrude(mouse_pos, near_pos, far_pos)
            from_pos = self.render.getRelativePoint(self.camera, near_pos)
            to_pos = self.render.getRelativePoint(self.camera, far_pos)
            result = self.physical_world.rayTestClosest(from_pos, to_pos, BitMask32.bit(1))

            if result.hasHit():
                print('Hit!')
                tag = result.getNode().getName()
                dest = result.getHitPos()
                self.ball.destination = dest
                print('tag', tag)
                print('collision_pt', self.ball.destination)
                self.mouse_grabbed = True
            else:
                self.mouse_x = 0
                self.dragging_duration += 1

    def release(self):
        self.dragging_duration = 0

    def update(self, task):
        dt = globalClock.getDt()
        velocity = 0

        if self.mouse_grabbed:
            self.mouse_grabbed = False
            self.ball.move()
        if self.dragging_duration:
            mouse_x = self.mouseWatcherNode.getMouse().getX()
            if (delta := mouse_x - self.mouse_x) < 0:
                velocity -= 90
            elif delta > 0:
                velocity += 90
            self.mouse_x = mouse_x
            self.dragging_duration += 1

        if self.dragging_duration >= self.max_duration:
            self.tower.rotate_around(velocity * dt)

        for i, j in itertools.product(range(5), range(3)):
            if cylinder := self.tower.cylinders[i][j]:
                result = self.physical_world.contactTestPair(self.scene.ground.node(), cylinder.node())
                if result.getNumContacts() > 0:
                    self.tower.cylinders[i][j] = None

        self.physical_world.doPhysics(dt)
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

