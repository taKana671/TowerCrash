import itertools
import math
import random
from enum import Enum

from panda3d.bullet import BulletCylinderShape, BulletBoxShape, BulletConvexHullShape
from panda3d.bullet import BulletRigidBodyNode
from panda3d.core import PandaNode, NodePath, TransformState
from panda3d.core import Quat, Vec3, LColor, BitMask32, Point3

from create_geomnode import Cylinder

PATH_CYLINDER = "models/cylinder/cylinder"
PATH_CUBE = 'models/cube/cube'
PATH_TRIANGLE = 'models/trianglular-prism/trianglular-prism'


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

    def __init__(self, world, rows, columns, foundation):
        super().__init__(PandaNode('tower'))
        self.rows = rows
        self.cols = columns
        self.foundation = foundation
        self.world = world
        # self.center = Point3(0, 0, 10)
        self.tower_top = self.rows - 1
        self.inactive_top = self.rows - 9

        self.floater = NodePath('floater')
        self.floater.reparent_to(self)
        self.blocks = NodePath('blocks')
        self.blocks.reparent_to(self)

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
            name = str(row * 7 + i)
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

        for con in self.world.contact_test(block.node()).get_contacts():
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
                f"Subclasses should implement 'build'. {cls.__name__} has no build.")
        if 'level' not in cls.__dict__:
            raise NotImplementedError(
                f"Subclasses should implement 'level'. {cls.__name__} has no level.")

        towers.append(cls)


class TwinTower(RegisteredTower):

    level = 20

    def __init__(self, stories, foundation, world):
        super().__init__(world, stories, 7, foundation)
        self.cylinder_slim = CylinderBlock('cylinder_slim', Vec3(0.1, 0.1, 0.15))
        self.cylinder_wide = CylinderBlock('cylinder_wide', Vec3(0.25, 0.25, 0.15))

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

        self.set_pos(Vec3(0, 0, 1.075))

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

    def build_tower(self):
        # After a block has attached to the world, change its mass to 0.
        for i in range(self.rows):
            h = self.block_h * i
            for j, (pt, expand) in enumerate(self.block_position(i % 2 == 0, h)):
                cylinder = self.cylinder_wide.copy_to(self.blocks) if expand else self.cylinder_slim.copy_to(self.blocks)
                cylinder.set_name(str(i * self.cols + j))
                cylinder.set_color(Colors.GRAY.rgba)
                cylinder.set_pos(pt)
                self.attach_block(cylinder)

# (Pdb) self.blocks[0][0]
# render/scene/foundation/tower/0
# (Pdb) first = self.blocks
# (Pdb) first = self.blocks[0][0]
# (Pdb) first.get_pos()
# LPoint3f(-0.3, 0.05, 0)
# (Pdb) top = self.blocks[23][3]
# (Pdb) top
# render/scene/foundation/tower/164
# (Pdb) top.get_pos()
# LPoint3f(0.25, -0.057735, 3.45)
# (Pdb) 3.45 / 23
# 0.15
# (Pdb) top.get_pos(base.render)
# LPoint3f(5, -1.1547, 75.5)
# (Pdb) first.get_pos(base.render)
# LPoint3f(-6, 1, 6.5)
# (Pdb) 75.5 - 6.5
# 69.0
# (Pdb) 69 / 23
# 3.0


# class ThinTower(RegisteredTower):

#     level = 20

#     def __init__(self, stories, foundation, world):
#         super().__init__(world, stories, foundation, Blocks(7, stories))
#         self.block_h = 2.3
#         self.edge = 2.3
#         self.even_row = [-0.5, -1.5, -2.5, 0.5, 1.5, 2.5]
#         self.odd_row = [0, -1, -2, -2.75, 1, 2, 2.75]

#     def build(self):
#         for i in range(len(self.blocks)):
#             h = self.block_h * (i + 1)
#             points = self.even_row if not i % 2 else self.odd_row
#             for j, pt in enumerate(points):
#                 color, state = self.get_attrib(i)
#                 pos = Point3(self.edge * pt, 0, h) + self.center
#                 sx = 0.35 if i % 2 and j in {3, 6} else 0.7
#                 rect = Rectangle(self, pos, str(i * self.blocks.cols + j), color, state, sx)
#                 self.attach_block(state, rect)
#                 self.blocks[i][j] = rect


# class CylinderTower(RegisteredTower):

#     level = 35

#     def __init__(self, stories, foundation, world):
#         super().__init__(world, stories, foundation, Blocks(18, stories))
#         self.block_h = 2.45
#         self.radius = 4
#         self.pts2d_even = [(x, y) for x, y in self.block_position(0, 360, 20)]
#         self.pts2d_odd = [(x, y) for x, y in self.block_position(10, 360, 20)]

#     def round_down(self, n):
#         str_n = str(n)
#         idx = str_n.find('.')
#         return float(str_n[:idx + 4])

#     def block_position(self, start, end, step):
#         for i in range(start, end, step):
#             rad = self.round_down(math.radians(i))
#             x = self.round_down(math.cos(rad) * self.radius)
#             y = self.round_down(math.sin(rad) * self.radius)
#             yield x, y

#     def build(self):
#         for i in range(len(self.blocks)):
#             points = self.pts2d_even if i % 2 == 0 else self.pts2d_odd
#             h = (self.block_h * (i + 1))

#             for j, (x, y) in enumerate(points):
#                 pt = Point3(x, y, h) + self.center
#                 color, state = self.get_attrib(i)
#                 cylinder = Cylinder(self, pt, str(i * self.blocks.cols + j), color, state)
#                 self.attach_block(state, cylinder)
#                 self.blocks[i][j] = cylinder


# class TripleTower(RegisteredTower):

#     level = 35

#     def __init__(self, stories, foundation, world):
#         super().__init__(world, stories, foundation, Blocks(12, stories))
#         self.block_h = 2.2  # 2.23
#         self.first_h = 2.46
#         self.centers = [Point3(-2, 8, 1.0), Point3(1.5, 13, 1.0), Point3(-5, 14, 1.0)]
#         edge = 2.536
#         half = edge / 2
#         ok = edge / 2 / math.sqrt(3)  # 0.7320801413324455
#         self.even_row = [(0, 0)]
#         self.odd_row = [(0, 0), (half, -ok), (-half, -ok), (0, ok * 2)]

#     def build(self):
#         for i in range(self.blocks.rows):
#             h = i * self.block_h + self.first_h

#             if i % 2 == 0:
#                 points = self.even_row
#                 expand = True
#             else:
#                 points = self.odd_row
#                 expand = False

#             for j, (center, (x, y)) in enumerate(itertools.product(self.centers, points)):
#                 color, state = self.get_attrib(i)
#                 pt = Point3(x, y, h) + center
#                 reverse = True if i % 2 and not j % 4 else False
#                 triangle = TriangularPrism(
#                     self, pt, str(i * self.blocks.cols + j), color, state, expand, reverse)
#                 self.attach_block(state, triangle)
#                 self.blocks[i][j] = triangle


# class CubicTower(RegisteredTower):

#     level = 35

#     def __init__(self, stories, foundation, world):
#         super().__init__(world, stories, foundation, Blocks(12, stories))
#         self.block_h = 2.3
#         self.edge = 1.15

#         self.points = [
#             [(-3, 3, "normal", 0), (-1, 3, "normal", 0), (1, 3, "normal", 0), (3, 3, "normal", 0), (3, 1, "normal", 0), (3, -1, "normal", 0),
#              (3, -3, "normal", 0), (1, -3, "normal", 0), (-1, -3, "normal", 0), (-3, -3, "normal", 0), (-3, -1, "normal", 0), (-3, 1, "normal", 0)],
#             [(-2.5, 3, "long", 0), (0, 3, "normal", 0), (2.5, 3, "long", 0), (3, 1.32, "short", 90), (3, 0, "short", 90), (3, -1.32, "short", 90),
#              (-2.5, -3, "long", 0), (0, -3, "normal", 0), (2.5, -3, "long", 0), (-3, 1.32, "short", 90), (-3, 0, "short", 90), (-3, -1.32, "short", 90)],
#             [(-1.32, 3, "short", 0), (0, 3, "short", 0), (1.32, 3, "short", 0), (3, 2.5, "long", 90), (3, 0, "normal", 0), (3, -2.5, "long", 90),
#              (1.32, -3, "short", 0), (0, -3, "short", 0), (-1.32, -3, "short", 0), (-3, -2.5, "long", 90), (-3, 0, "normal", 0), (-3, 2.5, "long", 90)]
#         ]

#     def build(self):
#         for i in range(self.blocks.rows):
#             h = self.block_h * (i + 1)
#             pts = self.points[i % 3]

#             for j, (x, y, scale, heading) in enumerate(pts):
#                 color, state = self.get_attrib(i)
#                 pt = Point3(x * self.edge, y * self.edge, h) + self.center
#                 cube = Cube(self, pt, str(i * self.blocks.cols + j), color, state, scale, heading)
#                 self.attach_block(state, cube)
#                 self.blocks[i][j] = cube


# class HShapedTower(RegisteredTower):

#     level = 30

#     def __init__(self, stories, foundation, world):
#         super().__init__(world, stories, foundation, Blocks(10, stories))
#         self.block_h = 2.3
#         self.edge = 1.15
#         # (x, y, sx, heading)
#         self.even_row = [
#             (-1, 0, 0.7, 0), (-3, 0, 0.7, 0), (1, 0, 0.7, 0), (3, 0, 0.7, 0),
#             (4.5, 0, 0.7, 90), (4.5, 2, 0.7, 90), (4.5, -2, 0.7, -92),
#             (-4.5, 0, 0.7, 90), (-4.5, 2, 0.7, 90), (-4.5, -2, 0.7, -92)]
#         self.odd_row = [
#             (0, 0, 0.7, 0), (-2, 0, 0.7, 0), (-4, 0, 0.7, 0), (2, 0, 0.7, 0), (4, 0, 0.7, 0),
#             (4.5, 1.75, 0.875, 90), (4.5, -1.75, 0.875, 90),
#             (-4.5, 1.75, 0.875, 90), (-4.5, -1.75, 0.875, 90)]

#     def build(self):
#         for i in range(len(self.blocks)):
#             h = self.block_h * (i + 1)
#             cols = self.even_row if not i % 2 else self.odd_row
#             for j, (x, y, sx, heading) in enumerate(cols):
#                 color, state = self.get_attrib(i)
#                 pos = Point3(x * self.edge, y * self.edge, h) + self.center
#                 rect = Rectangle(self, pos, str(i * self.blocks.cols + j), color, state, sx, heading)
#                 self.attach_block(state, rect)
#                 self.blocks[i][j] = rect


# class CrossTower(RegisteredTower):

#     level = 30

#     def __init__(self, stories, foundation, world):
#         super().__init__(world, stories, foundation, Blocks(9, stories))
#         self.block_h = 2.3
#         self.edge = 2.3
#         # (x, y, scale, heading)
#         self.even_row = [
#             (0, 0, 'normal', 0), (-1, 0, 'normal', 0), (-2, 0, 'normal', 0), (1, 0, 'normal', 0), (2, 0, 'normal', 0),
#             (0, 1, 'normal', 0), (0, 2, 'normal', 0), (0, -1, 'normal', 0), (0, -2, 'normal', 0)]
#         self.odd_row = [
#             (0, 0, 'large', 45), (-1.75, 0, 'long', 0), (1.75, 0, 'long', 0),
#             (0, -1.75, 'long', 90), (0, 1.75, 'long', 90)]

#     def build(self):
#         for i in range(self.blocks.rows):
#             h = self.block_h * (i + 1)
#             points = self.even_row if i % 2 == 0 else self.odd_row

#             for j, (x, y, scale, heading) in enumerate(points):
#                 color, state = self.get_attrib(i)
#                 pt = Point3(x * self.edge, y * self.edge, h) + self.center
#                 cube = Cube(self, pt, str(i * self.blocks.cols + j), color, state, scale, heading)
#                 self.attach_block(state, cube)
#                 self.blocks[i][j] = cube


# class CylinderBlock(NodePath):

#     def __init__(self, root, model, pos, name, color, state, expand=False):
#         super().__init__(BulletRigidBodyNode(name))
#         self.reparentTo(root)
#         # cylinder = base.loader.loadModel(PATH_CYLINDER)
#         cylinder = model.copy_to(self)
#         # cylinder.reparentTo(self)
#         end, tip = cylinder.getTightBounds()
#         self.node().addShape(BulletCylinderShape((tip - end) / 2))
#         n = 4 if int(name) > 24 else 3
#         self.setCollideMask(BitMask32.bit(1) | BitMask32.bit(2) | BitMask32.bit(n))
#         self.node().setMass(1)
#         if expand:
#             self.setScale(Vec3(0.4, 0.4, 0.35))
#         else:
#             self.setScale(0.2, 0.2, 0.35)
#         self.setColor(color)
#         self.setPos(pos)
#         self.state = state

class CylinderBlock(NodePath):

    def __init__(self, name, scale):
        super().__init__(BulletRigidBodyNode(name))
        self.cylinder = Cylinder()
        self.cylinder.set_transform(TransformState.make_pos(Vec3(0, 0, -0.5)))
        end, tip = self.cylinder.get_tight_bounds()
        self.node().add_shape(BulletCylinderShape((tip - end) / 2))
        self.setCollideMask(BitMask32.bit(1) | BitMask32.bit(2) | BitMask32.bit(4))
        self.node().setMass(1)
        self.set_scale(scale)
        self.cylinder.reparent_to(self)


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