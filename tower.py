import itertools
import math
import random
from enum import Enum, Flag, auto

from panda3d.bullet import BulletCylinderShape, BulletBoxShape
from panda3d.bullet import BulletRigidBodyNode
from panda3d.core import PandaNode, NodePath
from panda3d.core import Quat, Vec3, LColor, BitMask32, Point3


PATH_CYLINDER = "models/cylinder/cylinder"


class Block(Flag):

    ACTIVE = auto()
    INACTIVE = auto()
    INWATER = auto()
    ONSTONE = auto()
    DROPPING = auto()

    ROTATABLE = ACTIVE | INACTIVE | ONSTONE
    TARGET = ACTIVE | ONSTONE | DROPPING
    DROPPED = ONSTONE | DROPPING


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
            if self.data[i][j]:
                yield self.data[i][j]

    def __call__(self, i):
        for block in self.data[i]:
            if block:
                yield block

    def __getitem__(self, key):
        r, c = key
        return self.data[r][c]

    def __setitem__(self, key, value):
        r, c = key
        self.data[r][c] = value

    def __len__(self):
        return len(self.data)

    def find(self, node_name):
        j = int(node_name) % self.cols
        i = int(node_name) // self.cols

        return self.data[i][j]


class Tower(NodePath):
    def __init__(self, center, stories, foundation, blocks):
        super().__init__(PandaNode('tower'))
        self.reparentTo(base.render)

        self.center = center  # Point3(-2, 12, 0.3)
        self.foundation = foundation
        self.blocks = blocks
        self.axis = Vec3.up()
        self.tower_top = stories - 1
        self.inactive_top = int(stories * 2 / 3) - 1

    def get_attrib(self, i):
        if i <= self.inactive_top:
            return GRAY, Block.INACTIVE
        else:
            return Colors.select(), Block.ACTIVE

    def calc_distance(self, block):
        now_pos = block.getPos()
        dx = block.origianl_pos.x - now_pos.x
        dy = block.origianl_pos.y - now_pos.y
        dz = block.origianl_pos.z - now_pos.z

        return (dx ** 2 + dy ** 2 * dz ** 2) ** 0.5

    def is_collapsed(self, block, threshold=1.5):
        if self.calc_distance(block) > threshold:
            block.state = Block.DROPPING
            return True
        return False

    def rotate_around(self, angle):
        # Tried to use <nodepath>.setH() like self.foundation to rotate blocks, 
        # but too slow.
        self.foundation.setH(self.foundation.getH() + angle)
        q = Quat()
        q.setFromAxisAngle(angle, self.axis.normalized())

        for block in self.blocks:
            if block.state in Block.ROTATABLE:
                r = q.xform(block.getPos() - self.center)
                pos = self.center + r
                block.setPos(pos)
                # block.setH(block.getH() + angle)

    def set_active(self):
        cnt = 0

        for i in range(self.tower_top, -1, -1):
            if all(self.is_collapsed(block) for block in self.blocks(i)):
                if i >= 8:
                    for block in self.blocks(self.inactive_top):
                        block.state = Block.ACTIVE
                        block.clearColor()
                        block.setColor(Colors.select())
                        block.node().setMass(1)
                    self.inactive_top -= 1
                    cnt += 1
                self.tower_top -= 1
                continue
            break

        return cnt

    def crash(self, block, clicked_pos):
        block.node().setActive(True)
        impulse = Vec3.forward() * random.randint(1, 5)
        block.node().applyImpulse(impulse, clicked_pos)


class CylinderTower(Tower):

    def __init__(self, center, stories, foundation):
        super().__init__(center, stories, foundation, Blocks(3, stories))
        self.block_h = 2.45

    def build(self, physical_world):
        edge = 1.5                     # the length of one side
        ok = edge / 2 / math.sqrt(3)   # the length of line OK, O: center of triangle

        for i in range(len(self.blocks)):
            h = (self.block_h * (i + 1))

            if i % 2 == 0:
                points = [Point3(edge / 2, -ok, h), Point3(-edge / 2, -ok, h), Point3(0, ok * 2, h)]
            else:
                points = [Point3(-edge / 2, ok, h), Point3(edge / 2, ok, h), Point3(0, -ok * 2, h)]

            for j, pt in enumerate(points):
                color, state = self.get_attrib(i)
                cylinder = Cylinder(self, pt + self.center, str(i * 3 + j), color, state)
                physical_world.attachRigidBody(cylinder.node())

                if state == state.INACTIVE:
                    cylinder.node().setMass(0)
                self.blocks[i, j] = cylinder


class ThinTower(Tower):

    def __init__(self, center, stories, foundation):
        super().__init__(center, stories, foundation, Blocks(7, stories))
        self.block_h = 2.3
        self.even_row = [-2.5, -1.5, -0.5, 0.5, 1.5, 2.5]
        self.odd_row = [-2.75, -2, -1, 0, 1, 2, 2.75]
        self.cols = [3, 2, 1, 0, 4, 5, 6]

    def build(self, physical_world):
        edge = 2.3
        for i in range(len(self.blocks)):
            h = (self.block_h * (i + 1))
            cols = self.even_row if not i % 2 else self.odd_row
            for j, col in enumerate(cols):
                color, state = self.get_attrib(i)
                pos = Point3(edge * col, 0, h)
                cube = Cube(self, pos + self.center, str(i * 7 + j), color, state)
                if i % 2 and (j == 0 or j == len(cols) - 1):
                    cube.setSx(cube.getSx() / 2)
                physical_world.attachRigidBody(cube.node())

                if state == state.INACTIVE:
                    cube.node().setMass(0)

                self.blocks[i, j] = cube

    def rotate_around(self, angle):
        self.foundation.setH(self.foundation.getH() + angle)
        q = Quat()
        q.setFromAxisAngle(angle, self.axis.normalized())

        for i in range(self.blocks.rows):
            for j in self.cols:
                if (block := self.blocks[i, j]) and block.state in Block.ROTATABLE:
                    r = q.xform(block.getPos() - self.center)
                    pos = self.center + r
                    block.setPos(pos)
                    block.setH(block.getH() + angle)


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


class Cube(NodePath):

    def __init__(self, root, pos, name, color, state):
        super().__init__(BulletRigidBodyNode(name))
        self.reparentTo(root)
        cylinder = base.loader.loadModel('models/cube/cube')
        cylinder.reparentTo(self)
        end, tip = cylinder.getTightBounds()
        self.setCollideMask(BitMask32.bit(1) | BitMask32.bit(2))
        self.node().addShape(BulletBoxShape((tip - end) / 2))
        self.node().setMass(3)
        # self.setScale(0.7)
        self.setScale(Vec3(0.7, 0.35, 0.7))
        self.setColor(color)
        self.setPos(pos)
        self.state = state
        self.origianl_pos = pos
