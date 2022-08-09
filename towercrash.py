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

from bubble import Bubbles
from scene import Scene


PATH_CYLINDER = "models/cylinder/cylinder"


class State(Enum):

    ACTIVE = auto()
    STAY = auto()
    DROPPED = auto()

    DELETED = auto()
    READY = auto()
    MOVE = auto()


GRAY = LColor(0.25, 0.25, 0.25, 1)


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
        self.data = [[None for _ in range(cols)] for _ in range(rows)]

    def __iter__(self):
        for i, j in itertools.product(range(self.rows), range(self.cols)):
            yield self.data[i][j]

    def __call__(self, i):
        for block in self.data[i]:
            yield block

    def __len__(self):
        return len(self.data)

    def find(self, node_name):
        j = int(node_name) % 3
        i = int(node_name) // 3

        return self.data[i][j]


class CylinderTower:

    def __init__(self, center, stories, foundation):
        self.root = NodePath(PandaNode('cylinderTower'))
        self.root.reparentTo(base.render)

        self.center = center  # Point3(-2, 12, 0.3)
        self.foundation = foundation
        self.blocks = Blocks(3, stories)
        self.axis = Vec3.up()
        self.tower_top = stories - 1
        self.inactive_top = int(stories * 2 / 3) - 1
        self.block_h = 2.5

    def get_attrib(self, i):
        if i <= self.inactive_top:
            return GRAY, State.STAY
        else:
            return Colors.select(), State.ACTIVE

    def build(self, physical_world):
        edge = 1.5                     # the length of one side
        ok = edge / 2 / math.sqrt(3)   # the length of line OK, O: center of triangle

        for i in range(len(self.blocks)):
            h = self.block_h * (i + 1)
            if i % 2 == 0:
                points = [Point3(edge / 2, -ok, h), Point3(-edge / 2, -ok, h), Point3(0, ok * 2, h)]
            else:
                points = [Point3(-edge / 2, ok, h), Point3(edge / 2, ok, h), Point3(0, -ok * 2, h)]

            for j, pt in enumerate(points):
                color, state = self.get_attrib(i)
                cylinder = Cylinder(self.root, pt + self.center, str(i * 3 + j), color, state)
                physical_world.attachRigidBody(cylinder.node())

                if state == state.STAY:
                    cylinder.node().setMass(0)
                self.blocks.data[i][j] = cylinder

    def rotate_around(self, angle):
        self.foundation.setH(self.foundation.getH() + angle)
        q = Quat()
        q.setFromAxisAngle(angle, self.axis.normalized())

        for block in self.blocks:
            # if block.state in {State.ACTIVE, State.STAY}:
            if block.state in {State.ACTIVE, State.STAY} and not block.is_dropping:
                r = q.xform(block.getPos() - self.center)
                pos = self.center + r
                block.setPos(pos)

    def set_active(self):
        cnt = 0

        if self.tower_top >= 8:
            for i in range(self.tower_top, -1, -1):
                if all(block.is_collapsed() for block in self.blocks(i)):
                    for block in self.blocks(self.inactive_top):
                        block.state = State.ACTIVE
                        block.clearColor()
                        block.setColor(Colors.select())
                        block.node().setMass(1)
                    self.tower_top -= 1
                    self.inactive_top -= 1
                    cnt += 1
                    continue
                break
        else:
            for i in range(self.tower_top, -1, -1):
                for block in self.blocks(i):
                    _ = block.is_collapsed()

        return cnt


class Cylinder(NodePath):

    def __init__(self, root, pos, name, color, state):
        super().__init__(BulletRigidBodyNode(name))
        self.reparentTo(root)
        cylinder = base.loader.loadModel(PATH_CYLINDER)
        cylinder.reparentTo(self)
        end, tip = cylinder.getTightBounds()
        self.setCollideMask(BitMask32.bit(1) | BitMask32.bit(2))
        self.node().addShape(BulletCylinderShape((tip - end) / 2))
        self.node().setMass(1)
        self.setScale(0.7)
        self.setColor(color)
        self.setPos(pos)

        self.state = state
        self.origianl_pos = pos
        self.is_dropping = False

    def is_collapsed(self):
        if abs(self.origianl_pos.z - self.getZ()) > 0.5:
            self.is_dropping = True
            return True
        return False
        
        # return abs(self.origianl_pos.z - self.getZ()) > 0.5

    def move(self, pos):
        self.node().setActive(True)
        impulse = Vec3.forward() * random.randint(1, 5)
        self.node().applyImpulse(impulse, pos)


class Ball(NodePath):

    def __init__(self):
        super().__init__(PandaNode('ball'))
        ball = base.loader.loadModel('models/sphere/sphere')
        ball.reparentTo(self)
        self.setScale(0.2)
        self.state = None
        self.bubbles = Bubbles()

    def setup(self, camera_z):
        pos = Point3(5.5, -21, camera_z - 1.5)
        self.setPos(pos)
        self.setColor(Colors.select())
        self.reparentTo(base.render)
        self.state = State.READY

    def _delete(self):
        self.detachNode()
        self.state = State.DELETED

    def _hit(self, clicked_pos, block):
        para = Parallel(self.bubbles.get_sequence(self.getColor(), clicked_pos))

        if block.getColor() == self.getColor():
            para.append(Func(lambda: block.move(clicked_pos)))

        para.start()

    def move(self, clicked_pos, block):
        Sequence(
            self.posInterval(0.5, clicked_pos),
            Func(self._delete),
            Func(self._hit, clicked_pos, block)
        ).start()


class TowerCrash(ShowBase):

    def __init__(self):
        super().__init__()
        self.disableMouse()
        self.camera.setPos(10, -40, 10)  # 20, -18, 5
        self.camera.setP(10)
        # self.camera.lookAt(5, 3, 5)  # 5, 0, 3
        self.camera.lookAt(Point3(-2, 12, 10)) #10

        self.setup_lights()
        self.physical_world = BulletWorld()
        self.physical_world.setGravity(Vec3(0, 0, -9.81))

        self.scene = Scene()
        self.scene.setup(self.physical_world)
        self.create_tower()
        # self.camera.setPos(20, -18, 55)

        camera_z = (self.tower.inactive_top + 1) * 2.5
        look_z = camera_z + 4 * 2.5
        self.camera.setPos(Point3(10, -40, camera_z))
        self.camera.lookAt(Point3(-2, 12, look_z))
        self.camera_move_distance = 0

        self.ball = Ball()
        self.ball.setup(self.camera.getZ())

        self.dragging_duration = 0
        self.max_duration = 5

        self.accept('mouse1', self.click)
        self.accept('mouse1-up', self.release)
        self.taskMgr.add(self.update, 'update')

    def create_tower(self):
        center = Point3(-2, 12, 1.0)
        self.tower = CylinderTower(center, 24, self.scene.foundation)
        self.tower.build(self.physical_world)

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

                if (block := self.tower.blocks.find(node_name)).state == State.ACTIVE:
                    self.ball.state = State.MOVE
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
            if block.state == State.ACTIVE:
                result = self.physical_world.contactTest(block.node())

                for contact in result.getContacts():
                    if (name := contact.getNode1().getName()) == 'foundation':
                        block.is_dropping = False
                    elif name == 'waterSurface':
                        block.is_dropping = False
                        block.state = State.DROPPED


                    # if contact.getNode1().getName() in ('foundation', 'waterSurface'):
                    #     block.is_dropping = False

                    #     if contact.getNode1().getName() == 'waterSurface':
                    #         block.state = State.DROPPED
                        
        
        # for block in self.tower.blocks:
        #     if block.state == State.ACTIVE:
        #         result = self.physical_world.contactTestPair(
        #             self.scene.surface.node(), block.node()
        #         )
        #         if result.getNumContacts() > 0:
        #             block.state = State.DROPPED


        if self.ball.state == State.DELETED:
            self.ball.setup(self.camera.getZ())

        distance = 0
        if cnt := self.tower.set_active():
            self.camera_move_distance += cnt * 2.5

        if self.camera_move_distance > 0:
            if self.camera.getZ() > 2.5:
                distance += 10
                self.camera_move_distance -= distance * dt
                self.camera.setZ(self.camera.getZ() - distance * dt)

                if self.ball.state == State.READY:
                    self.ball.setZ(self.ball.getZ() - distance * dt)

        self.physical_world.doPhysics(dt)
        return task.cont


if __name__ == '__main__':
    game = TowerCrash()
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

