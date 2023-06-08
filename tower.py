import itertools
import math
import random
from enum import Enum

from panda3d.bullet import BulletCylinderShape, BulletBoxShape, BulletConvexHullShape
from panda3d.bullet import BulletRigidBodyNode
from panda3d.core import PandaNode, NodePath, TransformState
from panda3d.core import Vec3, LColor, BitMask32, Point3

from create_geomnode import CylinderGeom, CubeGeom, TriangularPrismGeom


towers = []


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
    def random_select(cls):
        """Randomly choose a color except for GRAY to return it (LVecBase4f).
        """
        n = random.randint(0, 5)
        color = cls(n)
        return color.rgba

    @classmethod
    def get_rgba(cls, n):
        if n <= 5:
            color = cls(n)
            return color.rgba
        else:
            return cls.select()


class Tower(NodePath):

    def __init__(self, world, rows, columns, foundation, pos):
        super().__init__(PandaNode('tower'))
        self.rows = rows
        self.cols = columns
        self.foundation = foundation
        self.world = world

        self.tower_top = self.rows - 1
        self.inactive_top = self.rows - 9

        self.floater = NodePath('floater')
        self.floater.reparent_to(self)
        self.blocks = NodePath('blocks')
        self.blocks.reparent_to(self)

        self.set_pos(pos)
        self.reparent_to(self.foundation)

    def build(self):
        self.build_tower()

        # Activate blocks in 8 rows from the top.
        for r in range(self.tower_top, self.inactive_top, -1):
            for block in self.find_blocks(r):
                self.activate(block)
                self.floater.set_z(block.get_z())

    def attach_block(self, block):
        self.world.attach(block.node())
        block.node().set_mass(0)
        block.node().deactivation_enabled = True

    def activate(self, block):
        block.clear_color()
        block.set_color(Colors.random_select())
        block.node().deactivation_enabled = False
        block.node().set_mass(1)

    def find_blocks(self, row):
        for i in range(self.cols):
            name = str(row * self.cols + i)
            if not (block := self.blocks.find(name)).is_empty():
                yield block

    def update(self):
        top_block = max(
            (b for b in self.blocks.get_children() if b.node().is_active()),
            key=lambda x: x.get_z()
        )
        top_row = int(top_block.get_z() / self.block_h) + 1

        if (activate_rows := self.tower_top - top_row) > 0:
            for _ in range(activate_rows):
                if self.inactive_top >= 0:
                    for block in self.find_blocks(self.inactive_top):
                        self.activate(block)
                    self.inactive_top -= 1
                    self.floater.set_z(self.floater.get_z() - self.block_h)

            self.tower_top = top_row

    def clean_up(self, block):
        """block (NodePath)
        """
        self.world.remove(block.node())
        block.remove_node()

    def get_neighbors(self, block, color, blocks):
        blocks.append(block)

        for con in self.world.contact_test(block.node(), use_filter=True).get_contacts():
            if (neighbor_nd := con.get_node1()) != self.foundation.node():
                neighbor = NodePath(neighbor_nd)
                if neighbor not in blocks and neighbor.get_color() == color:
                    self.get_neighbors(neighbor, color, blocks)

    def judge_colors(self, judge_color):
        """Args:
                judge_color: lambda
        """
        for block in self.blocks.get_children():
            if block.node().is_active() and judge_color(block):
                yield block

    def remove_all_blocks(self):
        for block in self.blocks.get_children():
            self.clean_up(block)

    def clear_foundation(self, bubbles):
        result = self.world.contact_test(self.foundation.node())

        for con in result.get_contacts():
            block = NodePath(con.get_node1())
            bubbles.get_sequence(block.get_color(), block.get_pos()).start()
            self.clean_up(block)


class RegisteredTower(Tower):

    def __init_subclass__(cls):
        super().__init_subclass__()
        if 'build_tower' not in cls.__dict__:
            raise NotImplementedError(
                f"Subclasses should implement 'build_tower'. {cls.__name__} has no build_tower.")
        if 'level' not in cls.__dict__:
            raise NotImplementedError(
                f"Subclasses should implement 'level'. {cls.__name__} has no level.")

        towers.append(cls)


class TwinTower(RegisteredTower):

    level = 20

    def __init__(self, rows, foundation, world):
        super().__init__(world, rows, 7, foundation, Point3(0, 0, 1.075))
        self.cylinders = {
            'normal': Cylinder('normal', Vec3(0.1, 0.1, 0.15)),
            'wide': Cylinder('wide', Vec3(0.25, 0.25, 0.15))
        }

        self.block_h = 0.15
        diameter = 0.1
        rad = diameter / 2
        ok = diameter / 2 / math.sqrt(3)   # the length of line OK, O: center of triangle

        self.l_center = Point3(-0.25, 0, 0)
        self.l_even = [(-rad, rad), (rad, rad), (-rad, -rad), (rad, -rad)]
        self.l_odd = [(0, 0)]

        self.r_center = Point3(0.25, 0, 0)
        self.r_even = [(rad, -ok), (-rad, -ok), (0, ok * 2)]
        self.r_odd = [(-rad, ok), (rad, ok), (0, -ok * 2)]

    def left_tower(self, even, z):
        if even:
            points = self.l_even
            cylinder_type = 'normal'
        else:
            points = self.l_odd
            cylinder_type = 'wide'

        for x, y in points:
            pt = Point3(x, y, z) + self.l_center
            yield (pt, cylinder_type)

    def right_tower(self, even, z):
        points = self.r_even if even else self.r_odd
        cylinder_type = 'normal'

        for x, y in points:
            pt = Point3(x, y, z) + self.r_center
            yield (pt, cylinder_type)

    def block_position(self, even, z):
        yield from self.left_tower(even, z)
        yield from self.right_tower(even, z)

    def build_tower(self):
        # After a block has been attached to the world, change its mass to 0.
        for i in range(self.rows):
            z = self.block_h * i
            for j, (pt, cylinder_type) in enumerate(self.block_position(i % 2 == 0, z)):
                cylinder = self.cylinders[cylinder_type].copy_to(self.blocks)
                cylinder.set_name(str(i * self.cols + j))
                cylinder.set_color(Colors.GRAY.rgba)
                cylinder.set_pos(pt)
                self.attach_block(cylinder)


class ThinTower(RegisteredTower):

    level = 20

    def __init__(self, rows, foundation, world):
        super().__init__(world, rows, 7, foundation, Point3(0, 0, 1.075))
        self.half_rect = Cube('small_rect', Vec3(0.075, 0.075, 0.15))
        self.normal_rect = Cube('big_rect', Vec3(0.15, 0.075, 0.15))

        self.block_h = 0.15
        self.edge = 0.15
        self.even_row = [-0.5, -1.5, -2.5, 0.5, 1.5, 2.5]
        self.odd_row = [0, -1, -2, -2.75, 1, 2, 2.75]

    def build_tower(self):
        for i in range(self.rows):
            z = self.block_h * i
            points = self.even_row if not i % 2 else self.odd_row

            for j, pt in enumerate(points):
                pos = Point3(self.edge * pt, 0, z)
                rect = self.half_rect.copy_to(self.blocks) if i % 2 and j in {3, 6} \
                    else self.normal_rect.copy_to(self.blocks)
                rect.set_name(str(i * self.cols + j))
                rect.set_color(Colors.GRAY.rgba)
                rect.set_pos(pos)
                self.attach_block(rect)


class CylinderTower(RegisteredTower):

    level = 35

    def __init__(self, rows, foundation, world):
        super().__init__(world, rows, 18, foundation, Point3(0, 0, 1.075))
        self.cylinder = Cylinder('cylinder', Vec3(0.1, 0.1, 0.15))
        self.block_h = 0.15
        self.radius = 0.29
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

    def build_tower(self):
        for i in range(self.rows):
            points = self.pts2d_even if i % 2 == 0 else self.pts2d_odd
            z = self.block_h * i

            for j, (x, y) in enumerate(points):
                pt = Point3(x, y, z)
                cylinder = self.cylinder.copy_to(self.blocks)
                cylinder.set_name(str(i * self.cols + j))
                cylinder.set_color(Colors.GRAY.rgba)
                cylinder.set_pos(pt)
                self.attach_block(cylinder)


class TripleTower(RegisteredTower):

    level = 35

    def __init__(self, rows, foundation, world):
        super().__init__(world, rows, 12, foundation, Point3(0, 0, 1.075))

        self.prisms = {
            'normal': TriangularPrism('normal', Vec3(0.15, 0.15, 0.15)),
            'wide': TriangularPrism('wide', Vec3(0.3, 0.3, 0.15))
        }

        self.block_h = 0.15  # 2.2  # 2.23
        self.centers = [Point3(0, 0.2, 0), Point3(-0.18, -0.2, 0), Point3(0.18, -0.2, 0)]

        edge = 0.15  # 2.536
        half = edge / 2
        ok = edge / 2 / math.sqrt(3)

        self.even_row = [(0, 0)]
        self.odd_row = [(0, 0), (half, -ok), (-half, -ok), (0, ok * 2)]

    def build_tower(self):
        for i in range(self.rows):
            z = i * self.block_h

            if i % 2 == 0:
                points = self.even_row
                prism_type = 'wide'
            else:
                points = self.odd_row
                prism_type = 'normal'

            for j, (center, (x, y)) in enumerate(itertools.product(self.centers, points)):
                prism = self.prisms[prism_type].copy_to(self.blocks)
                prism.set_name(str(i * self.cols + j))
                prism.set_color(Colors.GRAY.rgba)
                pos = Point3(x, y, z) + center

                if i % 2 and not j % 4:
                    prism.set_h(180)

                prism.set_pos(pos)
                self.attach_block(prism)


class CubicTower(RegisteredTower):

    level = 35

    def __init__(self, rows, foundation, world):
        super().__init__(world, rows, 12, foundation, Point3(0, 0, 1.075))

        self.rects = {
            'normal': Cube('normal', Vec3(0.15, 0.15, 0.15)),
            'short': Cube('short', Vec3(0.099, 0.15, 0.15)),
            'large': Cube('large', Vec3(0.219, 0.219, 0.15)),
            'long': Cube('long', Vec3(0.223, 0.15, 0.15))
        }
        self.block_h = 0.15
        self.edge = 0.075

        self.points = [
            [(-3, 3, 'normal', 0), (-1, 3, 'normal', 0), (1, 3, 'normal', 0), (3, 3, 'normal', 0), (3, 1, 'normal', 0), (3, -1, 'normal', 0),
             (3, -3, 'normal', 0), (1, -3, 'normal', 0), (-1, -3, 'normal', 0), (-3, -3, 'normal', 0), (-3, -1, 'normal', 0), (-3, 1, 'normal', 0)],
            [(-2.5, 3, 'long', 0), (0, 3, 'normal', 0), (2.5, 3, 'long', 0), (3, 1.32, 'short', 90), (3, 0, 'short', 90), (3, -1.32, 'short', 90),
             (-2.5, -3, 'long', 0), (0, -3, 'normal', 0), (2.5, -3, 'long', 0), (-3, 1.32, 'short', 90), (-3, 0, 'short', 90), (-3, -1.32, 'short', 90)],
            [(-1.32, 3, 'short', 0), (0, 3, 'short', 0), (1.32, 3, 'short', 0), (3, 2.5, 'long', 90), (3, 0, 'normal', 0), (3, -2.5, 'long', 90),
             (1.32, -3, 'short', 0), (0, -3, 'short', 0), (-1.32, -3, 'short', 0), (-3, -2.5, 'long', 90), (-3, 0, 'normal', 0), (-3, 2.5, 'long', 90)]
        ]

    def build_tower(self):
        for i in range(self.rows):
            z = self.block_h * i
            pts = self.points[i % 3]
            for j, (x, y, rect_type, h) in enumerate(pts):
                pt = Point3(x * self.edge, y * self.edge, z)
                rect = self.rects[rect_type].copy_to(self.blocks)
                rect.set_name(str(i * self.cols + j))
                rect.set_color(Colors.GRAY.rgba)
                rect.set_pos(pt)
                rect.set_h(h)
                self.attach_block(rect)


class HShapedTower(RegisteredTower):

    level = 30

    def __init__(self, rows, foundation, world):
        super().__init__(world, rows, 10, foundation, Point3(0, 0, 1.075))
        self.block_h = 0.15
        self.edge = 0.075
        self.rects = {
            'normal': Cube('normal', Vec3(0.15, 0.075, 0.15)),
            'large': Cube('large', Vec3(0.1875, 0.075, 0.15))
        }

        self.even_row = [
            (-1, 0, 'normal', 0), (-3, 0, 'normal', 0), (1, 0, 'normal', 0), (3, 0, 'normal', 0),
            (4.5, 0, 'normal', 90), (4.5, 2, 'normal', 90), (4.5, -2, 'normal', -92),
            (-4.5, 0, 'normal', 90), (-4.5, 2, 'normal', 90), (-4.5, -2, 'normal', -92)
        ]
        self.odd_row = [
            (0, 0, 'normal', 0), (-2, 0, 'normal', 0), (-4, 0, 'normal', 0), (2, 0, 'normal', 0), (4, 0, 'normal', 0),
            (4.5, 1.75, 'large', 90), (4.5, -1.75, 'large', 90), (-4.5, 1.75, 'large', 90), (-4.5, -1.75, 'large', 90)
        ]

    def build_tower(self):
        for i in range(self.rows):
            z = self.block_h * i
            cols = self.even_row if not i % 2 else self.odd_row
            for j, (x, y, rect_type, h) in enumerate(cols):
                pt = Point3(x * self.edge, y * self.edge, z)
                rect = self.rects[rect_type].copy_to(self.blocks)
                rect.set_name(str(i * self.cols + j))
                rect.set_color(Colors.GRAY.rgba)
                rect.set_pos(pt)
                rect.set_h(h)
                self.attach_block(rect)


class CrossTower(RegisteredTower):

    level = 30

    def __init__(self, rows, foundation, world):
        super().__init__(world, rows, 9, foundation, Point3(0, 0, 1.075))
        self.block_h = 0.15
        self.edge = 0.15

        self.rects = {
            'normal': Cube('normal', Vec3(0.15, 0.15, 0.15)),
            'large': Cube('large', Vec3(0.219, 0.219, 0.15)),
            'long': Cube('long', Vec3(0.223, 0.15, 0.15))
        }
        self.even_row = [
            (0, 0, 'normal', 0), (-1, 0, 'normal', 0), (-2, 0, 'normal', 0), (1, 0, 'normal', 0), (2, 0, 'normal', 0),
            (0, 1, 'normal', 0), (0, 2, 'normal', 0), (0, -1, 'normal', 0), (0, -2, 'normal', 0)]
        self.odd_row = [
            (0, 0, 'large', 45), (-1.75, 0, 'long', 0), (1.75, 0, 'long', 0),
            (0, -1.75, 'long', 90), (0, 1.75, 'long', 90)]

    def build_tower(self):
        for i in range(self.rows):
            z = self.block_h * i
            points = self.even_row if i % 2 == 0 else self.odd_row
            for j, (x, y, rect_type, h) in enumerate(points):
                pt = Point3(x * self.edge, y * self.edge, z)
                rect = self.rects[rect_type].copy_to(self.blocks)
                rect.set_name(str(i * self.cols + j))
                rect.set_color(Colors.GRAY.rgba)
                rect.set_pos(pt)
                rect.set_h(h)
                self.attach_block(rect)


class Cylinder(NodePath):

    def __init__(self, name, scale):
        super().__init__(BulletRigidBodyNode(name))
        self.cylinder = CylinderGeom()
        self.cylinder.set_transform(TransformState.make_pos(Vec3(0, 0, -0.5)))
        end, tip = self.cylinder.get_tight_bounds()
        self.node().add_shape(BulletCylinderShape((tip - end) / 2))
        self.set_collide_mask(BitMask32.bit(1) | BitMask32.bit(2) | BitMask32.bit(4))
        self.node().set_mass(1)
        self.set_scale(scale)
        self.cylinder.reparent_to(self)


class Cube(NodePath):

    def __init__(self, name, scale):
        super().__init__(BulletRigidBodyNode(name))
        self.cube = CubeGeom()
        end, tip = self.cube.get_tight_bounds()
        self.node().add_shape(BulletBoxShape((tip - end) / 2))
        self.set_collide_mask(BitMask32.bit(1) | BitMask32.bit(2) | BitMask32.bit(4))
        self.node().set_mass(1)
        self.set_scale(scale)
        self.cube.reparent_to(self)


class TriangularPrism(NodePath):

    def __init__(self, name, scale):
        super().__init__(BulletRigidBodyNode(name))
        self.prism = TriangularPrismGeom()
        shape = BulletConvexHullShape()
        geom = self.prism.node().get_geom(0)
        shape.add_geom(geom, TransformState.makeScale(scale * 0.98))

        self.node().add_shape(shape)
        self.set_collide_mask(BitMask32.bit(1) | BitMask32.bit(2) | BitMask32.bit(4))
        self.node().set_mass(1)
        self.prism.set_scale(scale)
        self.prism.reparent_to(self)