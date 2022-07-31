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

    def __init__(self, center):
        super().__init__(PandaNode('foundation'))
        self.setPos(center)  # Point3(-2, 12, 0.3)
        self.reparentTo(base.render)

        self.target_cylinder = None

    def create_cylinder(self, pos, color, tag):
        np = NodePath(BulletRigidBodyNode('cylinter'))
        np.reparentTo(self)
        cylinder = base.loader.loadModel(PATH_CYLINDER)

        cylinder.find('**/Cylinder').node().setIntoCollideMask(BitMask32.bit(1))
        cylinder.find('**/Cylinder').node().setTag('cylinder', tag)
        # render/foundation/cylinter/cylinder.egg/Cylinder

        cylinder.reparentTo(np)
        end, tip = cylinder.getTightBounds()
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
                cylinder = self.create_cylinder(pt, Colors.select(), str(i * 3 + j))
                physical_world.attachRigidBody(cylinder.node())
                self.cylinders[i][j] = cylinder

    def get_collision_pt(self, tag, surface_pt):
        i = tag // 3
        j = tag % 3
        self.target_cylinder = self.cylinders[i][j]
        # self.target_cylinder.node().setActive(True)
        return self.getPos() + self.target_cylinder.getPos() + surface_pt


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

        self.node().setIntoCollideMask(BitMask32.bit(1))
        self.node().setMass(10)
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

        self.mouse_dragging = False
        self.mouse_grabbed = False

        self.accept('mouse1', self.click)
        self.accept('mouse1-up', self.release)
        self.taskMgr.add(self.update, 'update')

    def create_tower(self):
        center = Point3(-2, 12, 0.3)
        self.tower = CylinderTower(center)
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
        self.mouse_dragging = False
        self.mouse_grabbed = False

        if self.mouseWatcherNode.hasMouse():
            mouse_pos = self.mouseWatcherNode.getMouse()
            self.picker_ray.setFromLens(self.camNode, mouse_pos.getX(), mouse_pos.getY())
            self.picker.traverse(self.tower)

            if self.handler.getNumEntries() > 0:
                self.handler.sortEntries()
                entry = self.handler.getEntry(0)
                tag = int(entry.getIntoNode().getTag('cylinder'))
                surface_pt = entry.getSurfacePoint(entry.getIntoNodePath())
                self.ball.destination = self.tower.get_collision_pt(tag, surface_pt)

                print('tag', tag)
                print('collision_pt', self.ball.destination)
                self.mouse_grabbed = True
            else:
                self.mouse_x = 0
                self.mouse_dragging = True

    def release(self):
        self.mouse_dragging = False

    def update(self, task):
        dt = globalClock.getDt()
        velocity = 0

        if self.mouse_grabbed:
            self.mouse_grabbed = False
            self.ball.move()
        if self.mouse_dragging:
            mouse_x = self.mouseWatcherNode.getMouse().getX()
            if (delta := mouse_x - self.mouse_x) < 0:
                velocity -= 90
            elif delta > 0:
                velocity += 90
            self.mouse_x = mouse_x

        if rotation_angle := velocity * dt:
            self.tower.setH(self.tower.getH() + rotation_angle)

        # if self.tower.target_cylinder:
        #     result = self.physical_world.contactTestPair(self.ball.node(), self.tower.target_cylinder.node())
        #     if result.getNumContacts() > 0:
        #         print('Collid')

        result = self.physical_world.contactTest(self.scene.ground.node())
        for c in result.getContacts():
            print(c.getNode0())
            if c.getNode0().getName() == 'cylinder':
                c.getNode0().setMass(0)


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

