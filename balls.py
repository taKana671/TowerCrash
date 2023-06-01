import math
import random

import numpy as np
from direct.interval.IntervalGlobal import Sequence, Parallel, Func
from panda3d.core import NodePath
from panda3d.core import Vec3, BitMask32, Point3
from panda3d.bullet import BulletRigidBodyNode, BulletSphereShape

from bubble import Bubbles
from tower import Colors
from create_geomnode import Sphere


PATH_TEXTURE_MULTI = 'textures/multi.jpg'
PATH_TEXTURE_TWOTONE = 'textures/two_tone.jpg'


class ColorBall:

    def __init__(self, world):
        self.bubbles = Bubbles()
        self.ball = None

        self.normal_ball = NormalBall()
        world.attach(self.normal_ball.node())

        self.multi_ball = MultiColorBall()
        world.attach(self.multi_ball.node())

        self.twotone_ball = TwoToneBall()
        world.attach(self.twotone_ball.node())

    def initialize(self, tower):
        if self.ball is not None and self.ball.has_parent():
            self.detach_ball()
        self.tower = tower
        self.used = False

    def setup(self, pos, parent, normal=True):
        b = 5 if normal else \
            7 if not self.used else 6

        match n := random.randint(0, b):
            case 6:
                self.ball = self.multi_ball
            case 7:
                self.used = True
                self.ball = self.twotone_ball
            case _:
                self.ball = self.normal_ball
                color = Colors.get_rgba(n)
                self.ball.set_color(color)

        self.ball.set_pos(pos)
        self.ball.set_hpr(Vec3(95, 0, 30))
        self.ball.reparent_to(parent)

    def detach_ball(self):
        self.ball.detach_node()

    def aim_at(self, clicked_pt, block):
        self.target_pt = clicked_pt
        self.target_block = block

        start_pt = self.ball.get_pos()
        end_pt = self.ball.get_parent().get_relative_point(base.render, clicked_pt)

        mid = (start_pt + end_pt) / 2
        mid.z += 10

        self.control_pts = [start_pt, mid, end_pt]
        self.total_dt = 0

    def bernstein(self, n, k, t):
        coef = math.factorial(n) / (math.factorial(k) * math.factorial(n - k))
        return coef * t ** k * (1 - t) ** (n - k)

    def bezier_curve(self, dt):
        n = len(self.control_pts) - 1
        px = py = pz = 0

        for i in range(len(self.control_pts)):
            b = self.bernstein(n, i, self.total_dt)
            px += np.dot(b, self.control_pts[i][0])
            py += np.dot(b, self.control_pts[i][1])
            pz += np.dot(b, self.control_pts[i][2])

        return Point3(px, py, pz)

    def move(self, dt):
        self.total_dt += dt
        if self.total_dt > 1:
            self.total_dt = 1

        pt = self.bezier_curve(dt)
        self.ball.set_pos(pt)
        self.ball.set_p(self.ball.get_p() + 360 * dt)

        if self.total_dt == 1:
            return False
        return True

    def hit(self):
        self.detach_ball()
        self.ball.hit(self.target_pt, self.target_block, self.bubbles, self.tower)


class Balls(NodePath):

    def __init__(self, name):
        super().__init__(BulletRigidBodyNode(name))
        self.model = Sphere()
        self.model.reparent_to(self)
        end, tip = self.model.get_tight_bounds()
        size = tip - end
        self.node().add_shape(BulletSphereShape(size.z / 2))
        self.set_collide_mask(BitMask32.bit(3))
        self.set_scale(0.2)
        self.node().set_kinematic(True)


class NormalBall(Balls):

    def __init__(self):
        super().__init__('normal_ball')

    def hit(self, clicked_pos, block, bubbles, tower):
        blocks = []
        if self.getColor() == block.getColor():
            tower.get_neighbors(block, block.getColor(), blocks)

        para = Parallel(bubbles.get_sequence(self.getColor(), clicked_pos))

        for block in blocks:
            pos = block.getPos(base.render)
            para.append(Sequence(
                Func(tower.clean_up, block),
                bubbles.get_sequence(self.getColor(), pos))
            )
        para.start()


class MultiColorBall(Balls):

    def __init__(self):
        super().__init__('multicolor_ball')
        self.model.setTexture(base.loader.loadTexture(PATH_TEXTURE_MULTI), 1)

    def _hit(self, color, bubbles, tower):
        for block in tower.judge_colors(lambda x: x.getColor() == color):
            pos = block.getPos(base.render)
            yield Sequence(Func(tower.clean_up, block),
                           bubbles.get_sequence(color, pos))

    def hit(self, clicked_pos, block, bubbles, tower):
        color = block.getColor()
        Parallel(
            bubbles.get_sequence(color, clicked_pos),
            *[seq for seq in self._hit(color, bubbles, tower)]
        ).start()


class TwoToneBall(Balls):

    def __init__(self):
        super().__init__('twotone_ball')
        self.model.setTexture(base.loader.loadTexture(PATH_TEXTURE_TWOTONE), 1)

    def _hit(self, color, bubbles, tower):
        for block in tower.judge_colors(lambda x: x.getColor() != color):
            pos = block.getPos(base.render)
            color = block.getColor()
            yield Sequence(Func(tower.clean_up, block),
                           bubbles.get_sequence(color, pos))

    def hit(self, clicked_pos, block, bubbles, tower):
        color = block.getColor()
        Parallel(
            bubbles.get_sequence(Colors.random_select(), clicked_pos),
            *[seq for seq in self._hit(color, bubbles, tower)]
        ).start()
