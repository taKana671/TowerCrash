import itertools
import math
import random
from enum import Enum, Flag, auto

from panda3d.bullet import BulletCylinderShape, BulletBoxShape, BulletConvexHullShape
from panda3d.bullet import BulletRigidBodyNode
from direct.interval.IntervalGlobal import Sequence, Parallel, Func, Wait
from panda3d.core import PandaNode, NodePath, TransformState
from panda3d.core import Quat, Vec3, LColor, BitMask32, Point3

from bubble import Bubbles

PATH_CYLINDER = "models/cylinder/cylinder"
PATH_CUBE = 'models/cube/cube'
PATH_TRIANGLE = 'models/trianglular-prism/trianglular-prism'


class Block(Flag):

    ACTIVE = auto()
    INACTIVE = auto()
    INWATER = auto()
    DROPPING = auto()
    REPOSITIONED = auto()

    MOVABLE = ACTIVE | DROPPING | REPOSITIONED
    ROTATABLE = ACTIVE | INACTIVE | REPOSITIONED
    CLICKABLE = ACTIVE | REPOSITIONED
    DROP = DROPPING | INWATER | REPOSITIONED


class Colors(int, Enum):

    RED = (0, LColor(1, 0, 0, 1))
    BLUE = (1, LColor(0, 0, 1, 1))
    YELLOW = (2, LColor(1, 1, 0, 1))
    GREEN = (3, LColor(0, 0.5, 0, 1))
    VIOLET = (4, LColor(0.54, 0.16, 0.88, 1))
    MAGENTA = (5, LColor(1, 0, 1, 1))
    GRAY = (6, LColor(0.25, 0.25, 0.25, 1))

    def __new__(cls, id_, rgba):
        obj = int.__new__(cls, id_)
        obj._value_ = id_
        obj.rgba = rgba
        return obj

    @classmethod
    def select(cls, b=5):
        n = random.randint(0, b)
        return cls(n).rgba


class Blocks:

    def __init__(self, cols, rows):
        self.cols = cols
        self.rows = rows
        self.data = [[None for _ in range(cols)] for _ in range(rows)]

    def __iter__(self):
        for i, j in itertools.product(reversed(range(self.rows)), range(self.cols)):
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
    def __init__(self, world, stories, foundation, blocks):
        super().__init__(PandaNode('tower'))
        self.reparentTo(base.render)
        self.foundation = foundation
        self.world = world
        self.blocks = blocks
        self.axis = Vec3.up()
        self.center = Point3(-2, 12, 1.0)
        self.tower_top = stories - 1
        self.inactive_top = stories - 9
        # self.inactive_top = int(stories * 2 / 3) - 1

    def get_attrib(self, i):
        if i <= self.inactive_top:
            return Colors.GRAY.rgba, Block.INACTIVE
        else:
            return Colors.select(), Block.ACTIVE

    def calc_distance(self, block):
        now_pos = block.getPos()
        dx = block.pos.x - now_pos.x
        dy = block.pos.y - now_pos.y
        dz = block.pos.z - now_pos.z

        return (dx ** 2 + dy ** 2 * dz ** 2) ** 0.5

    def activate(self):
        cnt = 0
        for i in range(self.tower_top, -1, -1):
            if all(block.state in Block.DROP for block in self.blocks(i)):
                for block in self.blocks(self.inactive_top):
                    
                    block.node().deactivation_enabled = False
                    
                    block.state = Block.ACTIVE
                    block.clearColor()
                    block.setColor(Colors.select())
                    block.node().setMass(1)
                if self.inactive_top >= 0:
                    self.inactive_top -= 1
                    cnt += 1
                self.tower_top -= 1
                continue
            break
        return cnt

        # if self.inactive_top >= 0:
        #     for i in range(self.tower_top, -1, -1):
        #         if all(block.state in Block.COLLAPSED for block in self.blocks(i)):
        #             for block in self.blocks(self.inactive_top):
        #                 block.state = Block.ACTIVE
        #                 block.clearColor()
        #                 block.setColor(Colors.select())
        #                 block.node().setMass(1)
        #             self.inactive_top -= 1
        #             self.tower_top -= 1
        #             cnt += 1
        #             continue
        #         break
        # return cnt


    def crash(self, block, clicked_pos, camera_pos):
        vec = Vec3(-camera_pos.x, -camera_pos.y, camera_pos.z).normalized()
        block.node().setActive(True)
        if random.randint(1, 5) == 1:
            impulse = vec * random.randint(1, 5)
            block.node().applyImpulse(impulse, clicked_pos)
        else:
            block.node().applyCentralImpulse(vec * 20)

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

    def clean_up_all(self):
        bubbles = Bubbles()
        for block in self.blocks:
            color = block.getColor()
            self.clean_up(block)
        seq = bubbles.get_sequence(color, Point3(-2, 12, 3.5)) 
        seq.start()


class CylinderTower(Tower):

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
            h = (self.block_h * (i + 1))

            if i % 2 == 0:
                points = [Point3(x, y, h) for x, y in self.pts2d_even]
            else:
                points = [Point3(x, y, h) for x, y in self.pts2d_odd]

            for j, pt in enumerate(points):
                color, state = self.get_attrib(i)
                cylinder = Cylinder(
                    self, pt + self.center, str(i * self.blocks.cols + j), color, state)
                self.world.attachRigidBody(cylinder.node())

                if state == state.INACTIVE:
                    cylinder.node().setMass(0)

                self.blocks[i, j] = cylinder


class TwinTower(Tower):

    def __init__(self, stories, foundation, world):
        super().__init__(world, stories, foundation, Blocks(7, stories))
        self.block_h = 2.45
        self.l_center = Point3(-5, 12, 1.0)
        self.r_center = Point3(1, 12, 1.0)

    def left_tower(self, i, half, h):
        if i % 2 == 0:
            points = [
                Point3(-half, half, h),
                Point3(half, half, h),
                Point3(-half, -half, h),
                Point3(half, -half, h)
            ]
            expand = False
        else:
            points = [
                Point3(0, 0, h)
            ]
            expand = True

        for pt in points:
            yield (self.l_center, pt, expand)

    def right_tower(self, i, ok, half, h):
        expand = False

        if i % 2 == 0:
            points = [Point3(half, -ok, h), Point3(-half, -ok, h), Point3(0, ok * 2, h)]
        else:
            points = [Point3(-half, ok, h), Point3(half, ok, h), Point3(0, -ok * 2, h)]

        for pt in points:
            yield (self.r_center, pt, expand)

    def block_position(self, i, ok, half, h):
        yield from self.left_tower(i, half, h)
        yield from self.right_tower(i, ok, half, h)

    def build(self):
        edge = 1.5                     # the length of one side
        half = edge / 2
        ok = edge / 2 / math.sqrt(3)   # the length of line OK, O: center of triangle

        for i in range(self.blocks.rows):
            h = (self.block_h * (i + 1))
            for j, (center, pt, expand) in enumerate(self.block_position(i, ok, half, h)):
                color, state = self.get_attrib(i)
                cylinder = Cylinder(
                    self, pt + center, str(i * self.blocks.cols + j), color, state, expand)
                self.world.attachRigidBody(cylinder.node())

                if state == state.INACTIVE:
                    cylinder.node().setMass(0)

                self.blocks[i, j] = cylinder


class ThinTower(Tower):

    def __init__(self, stories, foundation, world):
        super().__init__(world, stories, foundation, Blocks(7, stories))
        self.block_h = 2.3
        self.even_row = [-0.5, -1.5, -2.5, 0.5, 1.5, 2.5]
        self.odd_row = [0, -1, -2, -2.75, 1, 2, 2.75]

    def build(self):
        edge = 2.3
        for i in range(len(self.blocks)):
            h = (self.block_h * (i + 1))
            cols = self.even_row if not i % 2 else self.odd_row
            for j, col in enumerate(cols):
                color, state = self.get_attrib(i)
                pos = Point3(edge * col, 0, h)
                shrink = True if i % 2 and j in {3, 6} else False
                rect = Rectangle(
                    self, pos + self.center, str(i * self.blocks.cols + j), color, state, shrink)
                self.world.attachRigidBody(rect.node())

                rect.node().deactivation_enabled = False
                # rect.node().setActive(False)
                if state == state.INACTIVE:
                    rect.node().setMass(0)
                    rect.node().deactivation_enabled = True
                self.blocks[i, j] = rect


class TripleTower(Tower):

    def __init__(self, stories, foundation, world):
        super().__init__(world, stories, foundation, Blocks(12, stories))
        self.block_h = 2.2  # 2.23
        self.centers = [Point3(-2, 8, 1.0), Point3(1.5, 13, 1.0), Point3(-5, 14, 1.0)]

    def build(self):
        edge = 2.536
        half = edge / 2
        ok = edge / 2 / math.sqrt(3)  # 0.7320801413324455
        first_h = 2.46

        for i in range(self.blocks.rows):
            h = i * self.block_h + first_h
            if i % 2:
                points = [
                    Point3(0, 0, h),
                    Point3(half, -ok, h),
                    Point3(-half, -ok, h),
                    Point3(0, ok * 2, h)
                ]
                expand = False
            else:
                points = [
                    Point3(0, 0, h)
                ]
                expand = True

            for j, (center, pt) in enumerate(itertools.product(self.centers, points)):
                color, state = self.get_attrib(i)
                reverse = True if i % 2 and not j % 4 else False
                triangle = TriangularPrism(
                    self, pt + center, str(i * self.blocks.cols + j), color, state, expand, reverse)
                self.world.attachRigidBody(triangle.node())

                if state == state.INACTIVE:
                    triangle.node().setMass(0)

                self.blocks[i, j] = triangle


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
