import itertools
import math
import random
from enum import Enum, Flag, auto

from panda3d.bullet import BulletCylinderShape, BulletBoxShape, BulletConvexHullShape
from panda3d.bullet import BulletRigidBodyNode
from direct.interval.IntervalGlobal import Sequence, Func
from panda3d.core import PandaNode, NodePath, TransformState
from panda3d.core import Quat, Vec3, LColor, BitMask32, Point3


PATH_CYLINDER = "models/cylinder/cylinder"
PATH_CUBE = 'models/cube/cube'
PATH_TRIANGLE = 'models/trianglular-prism/trianglular-prism'


class Block(Flag):

    ACTIVE = auto()
    INACTIVE = auto()
    INWATER = auto()

    ROTATABLE = ACTIVE | INACTIVE


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
        if isinstance(key, str):
            r, c = self.get_index(key)
        elif isinstance(key, tuple):
            r, c = key
        else:
            raise TypeError()

        self.data[r][c] = value

    def __len__(self):
        return len(self.data)

    def get_index(self, name):
        r = int(name) // self.cols
        c = int(name) % self.cols
        return r, c

    def find(self, node_name):
        r, c = self.get_index(node_name)
        return self.data[r][c]


class Tower(NodePath):
    def __init__(self, stories, foundation, blocks):
        super().__init__(PandaNode('tower'))
        self.reparentTo(base.render)
        self.foundation = foundation
        self.blocks = blocks
        self.axis = Vec3.up()
        self.center = Point3(-2, 12, 1.0)
        self.tower_top = stories - 1
        self.inactive_top = stories - 9
        # self.inactive_top = int(stories * 2 / 3) - 1

    def get_attrib(self, i):
        if i <= self.inactive_top:
            return GRAY, Block.INACTIVE
        else:
            return Colors.select(), Block.ACTIVE

    def calc_distance(self, block):
        now_pos = block.getPos()
        dx = block.pos.x - now_pos.x
        dy = block.pos.y - now_pos.y
        dz = block.pos.z - now_pos.z

        return (dx ** 2 + dy ** 2 * dz ** 2) ** 0.5

    def is_collapsed(self, block, threshold=1.5):
        if abs(block.pos.getZ() - block.getZ()) > threshold:
            return True
        return False

    def set_active(self):
        cnt = 0
        if self.inactive_top >= 0:
            for i in range(self.tower_top, -1, -1):
                if all(self.is_collapsed(block) for block in self.blocks(i)):
                    for block in self.blocks(self.inactive_top):
                        block.state = Block.ACTIVE
                        block.clearColor()
                        block.setColor(Colors.select())
                        block.node().setMass(1)
                    self.inactive_top -= 1
                    self.tower_top -= 1
                    cnt += 1
                    continue
                break

        return cnt

    def crash(self, block, clicked_pos):
        n = random.randint(1, 5)
        print(n)
        block.node().setActive(True)
        if n == 1:
            impulse = Vec3.forward() * random.randint(1, 5)
            block.node().applyImpulse(impulse, clicked_pos)
        elif n == 2:
            block.node().applyForce(Vec3.forward() * 10, clicked_pos)
        else:
            block.node().applyCentralImpulse(Vec3.forward() * 10)


class CylinderTower(Tower):

    def __init__(self, stories, foundation):
        super().__init__(stories, foundation, Blocks(3, stories))
        self.block_h = 2.45

    def build(self, physical_world):
        edge = 1.5                     # the length of one side
        half = edge / 2
        ok = edge / 2 / math.sqrt(3)   # the length of line OK, O: center of triangle

        for i in range(len(self.blocks)):
            h = (self.block_h * (i + 1))

            if i % 2 == 0:
                points = [Point3(half, -ok, h), Point3(-half, -ok, h), Point3(0, ok * 2, h)]
            else:
                points = [Point3(-half, ok, h), Point3(half, ok, h), Point3(0, -ok * 2, h)]

            for j, pt in enumerate(points):
                color, state = self.get_attrib(i)
                cylinder = Cylinder(self, pt + self.center, str(i * 3 + j), color, state)
                physical_world.attachRigidBody(cylinder.node())

                if state == state.INACTIVE:
                    cylinder.node().setMass(0)
                self.blocks[i, j] = cylinder

    def rotate_around(self, angle):
        # Tried to use <nodepath>.setH() like self.foundation to rotate blocks,
        # but too slow.
        self.foundation.setH(self.foundation.getH() + angle)
        q = Quat()
        q.setFromAxisAngle(angle, self.axis.normalized())

        for block in self.blocks:
            if block.state in Block.ROTATABLE:
                r = q.xform(block.getPos() - self.center)
                block.setPos(self.center + r)


class ThinTower(Tower):

    def __init__(self, stories, foundation):
        super().__init__(stories, foundation, Blocks(7, stories))
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
                shrink = True if i % 2 and (j == 0 or j == len(cols) - 1) else False
                rect = Rectangle(self, pos + self.center, str(i * 7 + j), color, state, shrink)
                physical_world.attachRigidBody(rect.node())

                if state == state.INACTIVE:
                    rect.node().setMass(0)

                self.blocks[i, j] = rect

    def rotate_around(self, angle):
        self.foundation.setH(self.foundation.getH() + angle)
        q = Quat()
        q.setFromAxisAngle(angle, self.axis.normalized())

        for i in range(self.blocks.rows):
            for j in self.cols:
                if (block := self.blocks[i, j]) and block.state in Block.ROTATABLE:
                    r = q.xform(block.getPos() - self.center)
                    block.setPos(self.center + r)
                    block.setH(block.getH() + angle)


class TripleTower(Tower):

    def __init__(self, stories, foundation):
        super().__init__(stories, foundation, Blocks(12, stories))
        self.block_h = 2.2  # 2.23
        self.centers = [Point3(-2, 8, 1.0), Point3(1.5, 13, 1.0), Point3(-5, 14, 1.0)]

    def build(self, physical_world):
        edge = 2.536
        half = edge / 2
        ok = edge / 2 / math.sqrt(3)  # 0.7320801413324455
        first_h = 2.46

        for i in range(self.blocks.rows):
            h = i * self.block_h + first_h
            if i % 2:
                points = [Point3(0, 0, h), Point3(half, -ok, h), Point3(-half, -ok, h), Point3(0, ok * 2, h)]
                expand = False
            else:
                points = [Point3(0, 0, h)]
                expand = True

            for j, (center, pt) in enumerate(itertools.product(self.centers, points)):
                print(i, j, i * 12 + j, center, pt)
                color, state = self.get_attrib(i)
                reverse = True if i % 2 and not j % 4 else False
                triangle = TriangularPrism(self, pt + center, str(i * 12 + j), color, state, expand, reverse)
                physical_world.attachRigidBody(triangle.node())

                if state == state.INACTIVE:
                    triangle.node().setMass(0)

                self.blocks[i, j] = triangle

    def rotate_around(self, angle):
        self.foundation.setH(self.foundation.getH() + angle)
        q = Quat()
        q.setFromAxisAngle(angle, self.axis.normalized())

        for i in range(self.blocks.rows):
            for block in self.blocks(i):
                if block.state in Block.ROTATABLE:
                    r = q.xform(block.getPos() - self.center)
                    block.setPos(self.center + r)
                    block.setH(block.getH() + angle)


class Cylinder(NodePath):

    def __init__(self, root, pos, name, color, state):
        super().__init__(BulletRigidBodyNode(name))
        self.reparentTo(root)
        cylinder = base.loader.loadModel(PATH_CYLINDER)
        cylinder.reparentTo(self)
        end, tip = cylinder.getTightBounds()
        self.node().addShape(BulletCylinderShape((tip - end) / 2))
        n = 4 if int(name) > 24 else 3
        self.setCollideMask(BitMask32.bit(1) | BitMask32.bit(2) | BitMask32.bit(n))
        self.node().setMass(1)
        self.setScale(0.7)
        self.setColor(color)
        self.setPos(pos)
        self.state = state
        self.pos = pos


class Rectangle(NodePath):

    def __init__(self, root, pos, name, color, state, shrink):
        super().__init__(BulletRigidBodyNode(name))
        self.reparentTo(root)
        cylinder = base.loader.loadModel(PATH_CUBE)
        cylinder.reparentTo(self)
        end, tip = cylinder.getTightBounds()
        self.node().addShape(BulletBoxShape((tip - end) / 2))
        n = 3 if not int(name) % 10 else 4
        self.setCollideMask(BitMask32.bit(1) | BitMask32.bit(2) | BitMask32.bit(n))
        self.node().setMass(1)
        sx = 0.35 if shrink else 0.7
        self.setScale(Vec3(sx, 0.35, 0.7))
        self.setColor(color)
        self.setPos(pos)
        self.state = state
        self.pos = pos


class TriangularPrism(NodePath):

    def __init__(self, root, pos, name, color, state, expand, reverse):
        super().__init__(BulletRigidBodyNode(name))
        self.reparentTo(root)
        prism = base.loader.loadModel(PATH_TRIANGLE)
        geom_scale = Vec3(1.4, 0.7, 1.4) if expand else 0.7
        geom = prism.findAllMatches('**/+GeomNode').getPath(0).node().getGeom(0)
        shape = BulletConvexHullShape()
        shape.addGeom(geom, TransformState.makeScale(geom_scale))
        self.node().setMass(1.0)
        self.node().addShape(shape)
        n = 3 if int(name) % 20 == 0 else 4
        self.setCollideMask(BitMask32.bit(1) | BitMask32.bit(2) | BitMask32.bit(n))
        hpr = Vec3(180, -90, 0) if reverse else Vec3(0, -90, 0)
        self.setHpr(hpr)
        self.setPos(pos)
        self.setColor(color)
        prism_scale = Vec3(0.44, 0.22, 0.44) if expand else 0.22
        prism.setScale(prism_scale)
        prism.reparentTo(self)
        self.state = state
        self.pos = pos
