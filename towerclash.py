import itertools
import math
import random
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

from bubble import Bubbles
from scene import Scene


PATH_CYLINDER = "models/cylinder/cylinder"
# PATH_CYLINDER = "models/alice-shapes--box/box"


class BlockState(Enum):

    ACTIVE = auto()
    STAY = auto()
    GROUNDED = auto()
    DELETED = auto()
    STOPPED = auto()


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


class Blocks:

    def __init__(self, cols, rows):
        self.cols = cols
        self.rows = rows
        self.blocks = [[None for _ in range(cols)] for _ in range(rows)]

    def __iter__(self):
        for i, j in itertools.product(range(self.rows), range(self.cols)):
            yield self.blocks[i][j]

    def __call__(self, i, j, item):
        self.blocks[i][j] = item

    def get_from_node_name(self, node_name):
        j = int(node_name) % 3
        i = int(node_name) // 3

        return self.blocks[i][j]


class CylinderTower:

    def __init__(self, center, stories, foundation):
        self.root = NodePath(PandaNode('cylinderTower'))
        self.center = center  # Point3(-2, 12, 0.3)
        self.stories = stories
        self.foundation = foundation
        self.axis = Vec3.up()
        self.root.reparentTo(base.render)

    def get_attrib(self, i):
        if i <= self.stories * 2 / 3:
            return LColor(0.25, 0.25, 0.25, 1), BlockState.STAY
        else:
            return Colors.select(), BlockState.ACTIVE

    def build(self, physical_world):
        self.blocks = Blocks(3, self.stories)
        edge = 1.5                     # the length of one side
        ok = edge / 2 / math.sqrt(3)   # the length of line OK, O: center of triangle 
        height = 2.5

        for i in range(self.stories):
            h = height * (i + 1)
            if i % 2 == 0:
                points = [Point3(edge / 2, -ok, h), Point3(-edge / 2, -ok, h), Point3(0, ok * 2, h)]
            else:
                points = [Point3(-edge / 2, ok, h), Point3(edge / 2, ok, h), Point3(0, -ok * 2, h)]

            for j, pt in enumerate(points):
                color, state = self.get_attrib(i)
                cylinder = Cylinder(self.root, pt + self.center, str(i * 3 + j), color, state)
                physical_world.attachRigidBody(cylinder.node())
                self.blocks(i, j, cylinder)

    def rotate_around(self, angle):
        self.foundation.setH(self.foundation.getH() + angle)
        q = Quat()
        q.setFromAxisAngle(angle, self.axis.normalized())

        for block in self.blocks:
            if block.state in {BlockState.ACTIVE, BlockState.STAY}:
                r = q.xform(block.getPos() - self.center)
                pos = self.center + r
                block.setPos(pos)


class Cylinder(NodePath):

    def __init__(self, root, pos, name, color, state):
        super().__init__(BulletRigidBodyNode(name))
        self.reparentTo(root)
        self.state = state
        cylinder = base.loader.loadModel(PATH_CYLINDER)
        cylinder.reparentTo(self)
        end, tip = cylinder.getTightBounds()
        self.setCollideMask(BitMask32.bit(1) | BitMask32.bit(2))
        self.node().addShape(BulletCylinderShape((tip - end) / 2))
        if self.state == BlockState.ACTIVE:
            self.node().setMass(1)
        self.setScale(0.7)
        self.setColor(color)
        self.setPos(pos)

    def move(self, pos):
        self.node().setActive(True)
        impulse = Vec3.forward() * random.randint(1, 5)
        self.node().applyImpulse(impulse, pos)


class Ball(NodePath):

    def __init__(self, pos):
        super().__init__(PandaNode('ball'))
        ball = base.loader.loadModel('models/sphere/sphere')
        ball.reparentTo(self)
        self.setScale(0.2)
        self.pos = pos

    def setup(self):
        self.setPos(self.pos)
        self.setColor(Colors.select())
        self.reparentTo(base.render)

    def move(self, clicked_pos, block):
        bubbles = Bubbles(self.getColor(), clicked_pos)
        para = Parallel(Func(lambda: bubbles.start()))

        if block.getColor() == self.getColor():
            para.append(Func(lambda: block.move(clicked_pos)))

        Sequence(
            self.posInterval(0.5, clicked_pos),
            Func(lambda: self.detachNode()),
            para,
            Func(lambda: self.setup())
        ).start()


class TowerClash(ShowBase):

    def __init__(self):
        super().__init__()
        self.disableMouse()
        self.camera.setPos(20, -18, 10)  # 20, -20, 5
        # self.camera.setHpr(0, -80, 0)
        self.camera.lookAt(Point3(-2, 12, 0.3))
        self.camera.lookAt(5, 3, 5)  # 5, 0, 3

        self.setup_lights()
        self.setup_click_detection()
        self.physical_world = BulletWorld()
        self.physical_world.setGravity(Vec3(0, 0, -9.81))

        self.scene = Scene()
        self.scene.setup(self.physical_world)
        self.create_tower()
        self.camera.setPos(20, -18, 60)

        self.ball = Ball(Point3(6, 0, 50))
        self.ball.setup()

        self.dragging_duration = 0
        self.max_duration = 5

        self.accept('mouse1', self.click)
        self.accept('mouse1-up', self.release)
        self.taskMgr.add(self.update, 'update')

    def create_tower(self):
        center = Point3(-2, 12, 1.0)
        self.tower = CylinderTower(center, 24, self.scene.foundation)
        self.tower.build(self.physical_world)

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
        self.dragging_duration = 0

        if self.mouseWatcherNode.hasMouse():
            mouse_pos = self.mouseWatcherNode.getMouse()
            near_pos = Point3()
            far_pos = Point3()
            self.camLens.extrude(mouse_pos, near_pos, far_pos)
            from_pos = self.render.getRelativePoint(self.camera, near_pos)
            to_pos = self.render.getRelativePoint(self.camera, far_pos)
            result = self.physical_world.rayTestClosest(from_pos, to_pos, BitMask32.bit(1))

            if result.hasHit():
                node_name = result.getNode().getName()
                clicked_pos = result.getHitPos()

                block = self.tower.blocks.get_from_node_name(node_name)
                if block.state == BlockState.ACTIVE:
                    self.ball.move(clicked_pos, block)

                print('node_name', node_name)
                print('collision_pt', clicked_pos)
            else:
                self.mouse_x = 0
                self.dragging_duration += 1

    def release(self):
        self.dragging_duration = 0

    def update(self, task):
        dt = globalClock.getDt()
        velocity = 0

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

        for block in self.tower.blocks:
            if block.state == BlockState.ACTIVE:
                result = self.physical_world.contactTestPair(
                    self.scene.ground.node(), block.node()
                )
                if result.getNumContacts() > 0:
                    # print('ground', block.getName())
                    block.state = BlockState.GROUNDED

        for block in self.tower.blocks:
            if block.state == BlockState.GROUNDED:
                result = self.physical_world.contactTestPair(
                    self.scene.ground.node(), block.node()
                )

                if result.getNumContacts() == 0:
                    # print('stop', block.getName())
                    block.state = BlockState.STOPPED

                # for contact in result.getContacts():
                #     mp = contact.getManifoldPoint()
                #     pt = mp.getPositionWorldOnA()
                #     # if not (-50 <= pt.x <= 60 and -50 <= pt.y <= 60):  
                #     if pt.x < -50 or pt.x > 48 or pt.y < -50 or pt.y > 48:
                #         print(pt)
                #         block.state = BlockState.DELETED
                #         # block.node().setStatic(True)
                #         print('delete', block.getName())
                #         block.removeNode()
                #         block.state = BlockState.DELETED

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

