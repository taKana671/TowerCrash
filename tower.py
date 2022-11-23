import itertools
import math
import random
from collections import UserList
from enum import Enum, auto

from panda3d.bullet import BulletCylinderShape, BulletBoxShape, BulletConvexHullShape
from panda3d.bullet import BulletRigidBodyNode
from panda3d.core import PandaNode, NodePath, TransformState
from panda3d.core import Quat, Vec3, LColor, BitMask32, Point3


PATH_CYLINDER = "models/cylinder/cylinder"
PATH_CUBE = 'models/cube/cube'
PATH_TRIANGLE = 'models/trianglular-prism/trianglular-prism'


towers = []


class Block(Enum):

    ACTIVE = auto()
    INACTIVE = auto()
    INWATER = auto()
    DELETE = auto()


class Colors(int, Enum):

    RED = (0, LColor(1, 0, 0, 1))
    BLUE = (1, LColor(0, 0, 1, 1))
    YELLOW = (2, LColor(1, 1, 0, 1))
    GREEN = (3, LColor(0, 0.5, 0, 1))
    VIOLET = (4, LColor(0.54, 0.16, 0.88, 1))
    MAGENTA = (5, LColor(1, 0, 1, 1))
    MULTI = (6, None)
    TWOTONE = (7, None)
    GRAY = (8, LColor(0.25, 0.25, 0.25, 1))

    def __new__(cls, id_, rgba):
        obj = int.__new__(cls, id_)
        obj._value_ = id_
        obj.rgba = rgba
        return obj

    @classmethod
    def select(cls, b=5):
        n = random.randint(0, b)
        color = cls(n)
        return color.rgba if color.rgba else color.name


class Blocks(UserList):

    def __init__(self, cols, rows):
        self.cols = cols
        self.rows = rows
        data = [[None for _ in range(cols)] for _ in range(rows)]
        super().__init__(data)

    def __iter__(self):
        for i, j in itertools.product(reversed(range(self.rows)), range(self.cols)):
            if self.data[i][j]:
                yield self.data[i][j]

    def __call__(self, i):
        for block in self.data[i]:
            if block:
                yield block

    def __setitem__(self, key, value):
        r, c = self.get_index(key)
        self.data[r][c] = value

    def get_index(self, name):
        r = int(name) // self.cols
        c = int(name) % self.cols
        return r, c

    def find(self, node_name):
        r, c = self.get_index(node_name)
        return self.data[r][c]


class Tower(NodePath):

    def __init__(self, world, stories, foundation, blocks):
        super().__init__(PandaNode('tower'))
        self.reparentTo(base.render)
        self.foundation = foundation
        self.world = world
        self.blocks = blocks
        self.axis = Vec3.up()
        # self.center = Point3(-2, 12, 1.0)
        pt = self.foundation.getPos()
        pt.z = 1.0
        self.center = pt  # Point3(-2, 12, 1.0)
        self.tower_top = stories - 1
        self.inactive_top = stories - 9

    def get_attrib(self, i):
        if i <= self.inactive_top:
            return Colors.GRAY.rgba, Block.INACTIVE
        else:
            return Colors.select(), Block.ACTIVE

    def attach_block(self, state, block):
        self.world.attachRigidBody(block.node())

        if state == state.ACTIVE:
            block.node().deactivation_enabled = False
        else:
            block.node().setMass(0)
            block.node().deactivation_enabled = True

    def activate(self):
        top_block = max(
            (b for b in self.blocks if b.state == Block.ACTIVE),
            key=lambda x: x.getZ())
        tower_top_now = int(top_block.getZ() / self.block_h) - 1

        if (activate_rows := self.tower_top - tower_top_now) <= 0:
            return 0

        if self.inactive_top >= 0:
            for _ in range(activate_rows):
                for block in self.blocks(self.inactive_top):
                    block.state = Block.ACTIVE
                    block.clearColor()
                    block.setColor(Colors.select())
                    block.node().deactivation_enabled = False
                    block.node().setMass(1)
                self.inactive_top -= 1
        self.tower_top = tower_top_now
        return activate_rows

    def rotate(self, obj, rotation_angle):
        q = Quat()
        q.setFromAxisAngle(rotation_angle, self.axis.normalized())
        r = q.xform(obj.getPos() - self.center)
        rotated_pos = self.center + r
        return rotated_pos

    def clean_up(self, block):
        self.blocks[block.node().getName()] = None
        self.world.remove(block.node())
        block.removeNode()

    def floating(self, result):
        for name in set(con.getNode0().getName() for con in result.getContacts()):
            block = self.blocks.find(name)
            if block.state != Block.INWATER:
                block.state = Block.INWATER
                block.node().deactivation_enabled = True

    def sink(self, result):
        for name in set(con.getNode0().getName() for con in result.getContacts()):
            block = self.blocks.find(name)
            self.clean_up(block)

    def get_neighbors(self, block, color, blocks):
        block.state = Block.DELETE
        blocks.append(block)
        result = self.world.contactTest(block.node())

        for name in set(con.getNode1().getName() for con in result.getContacts()):
            if name != self.foundation.name:
                neighbor = self.blocks.find(name)
                if neighbor not in blocks and neighbor.getColor() == color:
                    self.get_neighbors(neighbor, color, blocks)

    def judge_colors(self, judge_color):
        for block in self.blocks:
            if block.state == Block.ACTIVE and judge_color(block):
                block.state = Block.DELETE
                yield block

    def remove_blocks(self):
        for block in self.blocks:
            self.clean_up(block)

    def clear_foundation(self, bubbles):
        result = self.world.contactTest(self.foundation.node())

        for name in set(con.getNode1().getName() for con in result.getContacts()):
            block = self.blocks.find(name)
            bubbles.get_sequence(block.getColor(), block.getPos()).start()
            self.clean_up(block)


class RegisteredTower(Tower):

    def __init_subclass__(cls):
        super().__init_subclass__()
        if 'build' not in cls.__dict__:
            raise NotImplementedError(
                f"Subclasses should implement 'build'. {cls.__name__} has no build.")
        if 'level' not in cls.__dict__:
            raise NotImplementedError(
                f"Subclasses should implement 'level'. {cls.__name__} has no level.")

        towers.append(cls)


class TwinTower(RegisteredTower):

    level = 20

    def __init__(self, stories, foundation, world):
        super().__init__(world, stories, foundation, Blocks(7, stories))
        self.block_h = 2.45
        edge = 1.5                     # the length of one side
        half = edge / 2
        ok = edge / 2 / math.sqrt(3)   # the length of line OK, O: center of triangle

        self.l_center = Point3(-5, 12, 1.0)
        self.l_even = [(-half, half), (half, half), (-half, -half), (half, -half)]
        self.l_odd = [(0, 0)]

        self.r_center = Point3(1, 12, 1.0)
        self.r_even = [(half, -ok), (-half, -ok), (0, ok * 2)]
        self.r_odd = [(-half, ok), (half, ok), (0, -ok * 2)]

    def left_tower(self, even, h):
        if even:
            points = self.l_even
            expand = False
        else:
            points = self.l_odd
            expand = True

        for x, y in points:
            pt = Point3(x, y, h) + self.l_center
            yield (pt, expand)

    def right_tower(self, even, h):
        points = self.r_even if even else self.r_odd
        expand = False

        for x, y in points:
            pt = Point3(x, y, h) + self.r_center
            yield (pt, expand)

    def block_position(self, even, h):
        yield from self.left_tower(even, h)
        yield from self.right_tower(even, h)

    def build(self):
        for i in range(self.blocks.rows):
            h = self.block_h * (i + 1)
            for j, (pt, expand) in enumerate(self.block_position(i % 2 == 0, h)):
                color, state = self.get_attrib(i)
                cylinder = Cylinder(self, pt, str(i * self.blocks.cols + j), color, state, expand)
                self.attach_block(state, cylinder)
                self.blocks[i][j] = cylinder


class ThinTower(RegisteredTower):

    level = 20

    def __init__(self, stories, foundation, world):
        super().__init__(world, stories, foundation, Blocks(7, stories))
        self.block_h = 2.3
        self.edge = 2.3
        self.even_row = [-0.5, -1.5, -2.5, 0.5, 1.5, 2.5]
        self.odd_row = [0, -1, -2, -2.75, 1, 2, 2.75]

    def build(self):
        for i in range(len(self.blocks)):
            h = self.block_h * (i + 1)
            points = self.even_row if not i % 2 else self.odd_row
            for j, pt in enumerate(points):
                color, state = self.get_attrib(i)
                pos = Point3(self.edge * pt, 0, h) + self.center
                sx = 0.35 if i % 2 and j in {3, 6} else 0.7
                rect = Rectangle(self, pos, str(i * self.blocks.cols + j), color, state, sx)
                self.attach_block(state, rect)
                self.blocks[i][j] = rect


class CylinderTower(RegisteredTower):

    level = 35

    def __init__(self, stories, foundation, world):
        super().__init__(world, stories, foundation, Blocks(18, stories))
        self.block_h = 2.45
        self.radius = 4
        self.pts2d_even = [(x, y) for x, y in self.block_position(0, 360, 20)]
        self.pts2d_odd = [(x, y) for x, y in self.block_position(10, 360, 20)]

    def round_down(self, n):
        str_n = str(n)
        idx = str_n.find('.')
        return float(str_n[:idx + 4])

    def block_position(self, start, end, step):
        for i in range(start, end, step):
            rad = self.round_down(math.radians(i))
            x = self.round_down(math.cos(rad) * self.radius)
            y = self.round_down(math.sin(rad) * self.radius)
            yield x, y

    def build(self):
        for i in range(len(self.blocks)):
            points = self.pts2d_even if i % 2 == 0 else self.pts2d_odd
            h = (self.block_h * (i + 1))

            for j, (x, y) in enumerate(points):
                pt = Point3(x, y, h) + self.center
                color, state = self.get_attrib(i)
                cylinder = Cylinder(self, pt, str(i * self.blocks.cols + j), color, state)
                self.attach_block(state, cylinder)
                self.blocks[i][j] = cylinder


class TripleTower(RegisteredTower):

    level = 35

    def __init__(self, stories, foundation, world):
        super().__init__(world, stories, foundation, Blocks(12, stories))
        self.block_h = 2.2  # 2.23
        self.first_h = 2.46
        self.centers = [Point3(-2, 8, 1.0), Point3(1.5, 13, 1.0), Point3(-5, 14, 1.0)]
        edge = 2.536
        half = edge / 2
        ok = edge / 2 / math.sqrt(3)  # 0.7320801413324455
        self.even_row = [(0, 0)]
        self.odd_row = [(0, 0), (half, -ok), (-half, -ok), (0, ok * 2)]

    def build(self):
        for i in range(self.blocks.rows):
            h = i * self.block_h + self.first_h

            if i % 2 == 0:
                points = self.even_row
                expand = True
            else:
                points = self.odd_row
                expand = False

            for j, (center, (x, y)) in enumerate(itertools.product(self.centers, points)):
                color, state = self.get_attrib(i)
                pt = Point3(x, y, h) + center
                reverse = True if i % 2 and not j % 4 else False
                triangle = TriangularPrism(
                    self, pt, str(i * self.blocks.cols + j), color, state, expand, reverse)
                self.attach_block(state, triangle)
                self.blocks[i][j] = triangle


class CubicTower(RegisteredTower):

    level = 35

    def __init__(self, stories, foundation, world):
        super().__init__(world, stories, foundation, Blocks(12, stories))
        self.block_h = 2.3
        self.edge = 1.15

        self.points = [
            [(-3, 3, "normal", 0), (-1, 3, "normal", 0), (1, 3, "normal", 0), (3, 3, "normal", 0), (3, 1, "normal", 0), (3, -1, "normal", 0),
             (3, -3, "normal", 0), (1, -3, "normal", 0), (-1, -3, "normal", 0), (-3, -3, "normal", 0), (-3, -1, "normal", 0), (-3, 1, "normal", 0)],
            [(-2.5, 3, "long", 0), (0, 3, "normal", 0), (2.5, 3, "long", 0), (3, 1.32, "short", 90), (3, 0, "short", 90), (3, -1.32, "short", 90),
             (-2.5, -3, "long", 0), (0, -3, "normal", 0), (2.5, -3, "long", 0), (-3, 1.32, "short", 90), (-3, 0, "short", 90), (-3, -1.32, "short", 90)],
            [(-1.32, 3, "short", 0), (0, 3, "short", 0), (1.32, 3, "short", 0), (3, 2.5, "long", 90), (3, 0, "normal", 0), (3, -2.5, "long", 90),
             (1.32, -3, "short", 0), (0, -3, "short", 0), (-1.32, -3, "short", 0), (-3, -2.5, "long", 90), (-3, 0, "normal", 0), (-3, 2.5, "long", 90)]
        ]

    def build(self):
        for i in range(self.blocks.rows):
            h = self.block_h * (i + 1)
            pts = self.points[i % 3]

            for j, (x, y, scale, heading) in enumerate(pts):
                color, state = self.get_attrib(i)
                pt = Point3(x * self.edge, y * self.edge, h) + self.center
                cube = Cube(self, pt, str(i * self.blocks.cols + j), color, state, scale, heading)
                self.attach_block(state, cube)
                self.blocks[i][j] = cube


class HShapedTower(RegisteredTower):

    level = 30

    def __init__(self, stories, foundation, world):
        super().__init__(world, stories, foundation, Blocks(10, stories))
        self.block_h = 2.3
        self.edge = 1.15
        # (x, y, sx, heading)
        self.even_row = [
            (-1, 0, 0.7, 0), (-3, 0, 0.7, 0), (1, 0, 0.7, 0), (3, 0, 0.7, 0),
            (4.5, 0, 0.7, 90), (4.5, 2, 0.7, 90), (4.5, -2, 0.7, -92),
            (-4.5, 0, 0.7, 90), (-4.5, 2, 0.7, 90), (-4.5, -2, 0.7, -92)]
        self.odd_row = [
            (0, 0, 0.7, 0), (-2, 0, 0.7, 0), (-4, 0, 0.7, 0), (2, 0, 0.7, 0), (4, 0, 0.7, 0),
            (4.5, 1.75, 0.875, 90), (4.5, -1.75, 0.875, 90),
            (-4.5, 1.75, 0.875, 90), (-4.5, -1.75, 0.875, 90)]

    def build(self):
        for i in range(len(self.blocks)):
            h = self.block_h * (i + 1)
            cols = self.even_row if not i % 2 else self.odd_row
            for j, (x, y, sx, heading) in enumerate(cols):
                color, state = self.get_attrib(i)
                pos = Point3(x * self.edge, y * self.edge, h) + self.center
                rect = Rectangle(self, pos, str(i * self.blocks.cols + j), color, state, sx, heading)
                self.attach_block(state, rect)
                self.blocks[i][j] = rect


class CrossTower(RegisteredTower):

    level = 30

    def __init__(self, stories, foundation, world):
        super().__init__(world, stories, foundation, Blocks(9, stories))
        self.block_h = 2.3
        self.edge = 2.3
        # (x, y, scale, heading)
        self.even_row = [
            (0, 0, 'normal', 0), (-1, 0, 'normal', 0), (-2, 0, 'normal', 0), (1, 0, 'normal', 0), (2, 0, 'normal', 0),
            (0, 1, 'normal', 0), (0, 2, 'normal', 0), (0, -1, 'normal', 0), (0, -2, 'normal', 0)]
        self.odd_row = [
            (0, 0, 'large', 45), (-1.75, 0, 'long', 0), (1.75, 0, 'long', 0),
            (0, -1.75, 'long', 90), (0, 1.75, 'long', 90)]

    def build(self):
        for i in range(self.blocks.rows):
            h = self.block_h * (i + 1)
            points = self.even_row if i % 2 == 0 else self.odd_row

            for j, (x, y, scale, heading) in enumerate(points):
                color, state = self.get_attrib(i)
                pt = Point3(x * self.edge, y * self.edge, h) + self.center
                cube = Cube(self, pt, str(i * self.blocks.cols + j), color, state, scale, heading)
                self.attach_block(state, cube)
                self.blocks[i][j] = cube


class Cylinder(NodePath):

    def __init__(self, root, pos, name, color, state, expand=False):
        super().__init__(BulletRigidBodyNode(name))
        self.reparentTo(root)
        cylinder = base.loader.loadModel(PATH_CYLINDER)
        cylinder.reparentTo(self)
        end, tip = cylinder.getTightBounds()
        self.node().addShape(BulletCylinderShape((tip - end) / 2))
        n = 4 if int(name) > 24 else 3
        self.setCollideMask(BitMask32.bit(1) | BitMask32.bit(2) | BitMask32.bit(n))
        self.node().setMass(1)
        if expand:
            self.setScale(Vec3(1.7, 1.7, 0.7))
        else:
            self.setScale(0.7)
        self.setColor(color)
        self.setPos(pos)
        self.state = state


class Rectangle(NodePath):

    def __init__(self, root, pos, name, color, state, sx, heading=0):
        super().__init__(BulletRigidBodyNode(name))
        self.reparentTo(root)
        rect = base.loader.loadModel(PATH_CUBE)
        rect.reparentTo(self)
        end, tip = rect.getTightBounds()
        self.node().addShape(BulletBoxShape((tip - end) / 2))
        n = 3 if not int(name) % 10 else 4
        self.setCollideMask(BitMask32.bit(1) | BitMask32.bit(2) | BitMask32.bit(n))
        self.node().setMass(1)
        self.setScale(Vec3(sx, 0.35, 0.7))
        self.setColor(color)
        self.setPos(pos)
        self.setH(heading)
        self.state = state


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


class Cube(NodePath):

    scales = {
        'normal': Vec3(0.7, 0.7, 0.7),
        'short': Vec3(0.46, 0.7, 0.7),
        'large': Vec3(1.02, 1.02, 0.7),
        'long': Vec3(1.04, 0.7, 0.7),
    }

    def __init__(self, root, pos, name, color, state, scale, heading=0):
        super().__init__(BulletRigidBodyNode(name))
        self.reparentTo(root)
        cube = base.loader.loadModel(PATH_CUBE)
        cube.reparentTo(self)
        end, tip = cube.getTightBounds()
        self.node().addShape(BulletBoxShape((tip - end) / 2))
        n = 3 if not int(name) % 20 else 4
        self.setCollideMask(BitMask32.bit(1) | BitMask32.bit(2) | BitMask32.bit(n))
        self.node().setMass(1)
        self.setScale(Cube.scales[scale])
        self.setColor(color)
        self.setPos(pos)
        if heading:
            self.setH(heading)
        self.state = state