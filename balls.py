import math
from enum import Enum, auto

import numpy as np
from direct.gui.DirectGui import OnscreenText, Plain, OnscreenImage, DirectButton
from direct.interval.IntervalGlobal import Sequence, Parallel, Func, Wait
from panda3d.core import PandaNode, NodePath, TextNode, TransparencyAttrib
from panda3d.core import Vec3, LColor, BitMask32, Point3, Quat
from panda3d.bullet import BulletRigidBodyNode, BulletSphereShape


from create_geomnode import Sphere


# PATH_SPHERE = "models/sphere/sphere"
PATH_TEXTURE_MULTI = 'textures/multi.jpg'
PATH_TEXTURE_TWOTONE = 'textures/two_tone.jpg'
PATH_START_SCREEN = 'images/start.png'
CHECK_REPEAT = 0.2
WAIT_COUNT = 5


class Ball(Enum):

    DELETED = auto()
    READY = auto()
    MOVE = auto()
    MOVING = auto()


class ColorBall:

    def __init__(self, world, navigator, bubbles):
        # self.start_pos = Point3(0, -21, 0)
        self.start_pos = Point3(0, -60, 0)  # -50

        self.bubbles = bubbles
        self.start_hpr = Vec3(95, 0, 30)
        self.state = None
        self.move_idx = 0
        self.world = world
        self.navigator = navigator

        self.normal_ball = NormalBall(self.bubbles)
        self.world.attach(self.normal_ball.node())

        self.multi_ball = MultiColorBall(self.bubbles)
        self.world.attach(self.multi_ball.node())

        self.twotone_ball = TwoToneBall(self.bubbles)
        self.world.attach(self.twotone_ball.node())

    def initialize(self, tower):
        self.tower = tower

        if self.ball is not None and self.ball.hasParent():
            self._delete()
        self.used = False
        self.state = None
        self.state = None
        self.pos = self.start_pos
        self.hpr = self.start_hpr
        # self.ball_number.setText('')

    def setup(self, color):
        if color == 'MULTI':
            self.ball = self.multi_ball
        elif color == 'TWOTONE':
            self.used = True
            self.ball = self.twotone_ball
        else:
            self.ball = self.normal_ball
            self.ball.setColor(color)

        self.ball.set_pos(self.start_pos)
        self.ball.reparentTo(self.navigator)

        self.state = Ball.READY

    def _delete(self):
        self.detachNode()
        self.state = Ball.DELETED

    def move(self, clicked_pt, block):
        self.state = Ball.MOVE

        start_pt = self.ball.get_pos()
        end_pt = self.navigator.get_relative_point(base.render, clicked_pt)
        mid = (start_pt + end_pt) / 2
        mid.z += 10
        self.control_pts = [start_pt, mid, end_pt]
        self.total_dt = 0 
        
        # self.arr = self.bezier_curve2(self.ball.get_pos(), rel_pos)
        # self.px, self.py, self.pz = self.bezier_curve2(self.ball.get_pos(), rel_pos)
        
        
        # Sequence(
        #     # self.ball.posHprInterval(0.5, clicked_pos, Vec3(0, 360, 0)),
        #     self.ball.posHprInterval(0.5, rel_pos, Vec3(0, 360, 0)),
        #     Func(self._delete),
        #     Func(self.ball.hit, clicked_pos, block, self.tower)
        # ).start()

    
    def bernstein(self, n, k, t):
        coef = math.factorial(n) / (math.factorial(k) * math.factorial(n - k))
        return coef * t ** k * (1 - t) ** (n - k)

    def bezier_curve(self, dt):
        self.total_dt += dt

        if self.total_dt > 1:
            self.total_dt = 1

        n = len(self.control_pts) - 1
        px = py = pz = 0

        for i in range(len(self.control_pts)):
            b = self.bernstein(n, i, self.total_dt)
            px += np.dot(b, self.control_pts[i][0])
            py += np.dot(b, self.control_pts[i][1])
            pz += np.dot(b, self.control_pts[i][2])

        self.ball.set_pos(px, py, pz)

        if self.total_dt == 1:
            return True

  
    def moving(self):
        # pt = self.arr[self.move_idx]
        # self.ball.set_pos(pt[0], pt[1], pt[2])
        # self.move_idx += 1

        self.ball.set_pos(self.px[self.move_idx], self.py[self.move_idx], self.pz[self.move_idx])
        self.move_idx += 1
    
    # def bezier_curve2(self, q1, q2):
        # q3 = (q1 + q2) / 2
        # q3.z += 3
        
        # Q = [q1, q2, q3]
        # arr = []

        # t = np.arange(0, 1, 0.01)
        # for i in range(len(t)):
        #     pt = []
        #     P = np.dot((1 - t[i]) ** 2, Q[0]) + np.dot(2 * (1 - t[i]) * t[i], Q[1]) + np.dot(t[i] ** 2, Q[2])
        #     pt.append(P[0])
        #     pt.append(P[1])
        #     pt.append(P[2])
        #     arr.append(pt)
        #     # px.append(P[0])
        #     # py.append(P[1])
        #     # pz.append(P[2])
        # np_arr = np.array(arr)

        # return np.rot90(np_arr, 2)


    def bezier_curve2(self, q1, q2):
        # 点の座標
        # q1 = [0, -60, -1.5]
        # q2 = [2.58105, -5.59238, 18.1952]
        # q3 = [1.290525, -32.7962,  18.3476]
        q3 = (q1 + q2) / 2
        q3.z += 5
        
        Q = [q1, q3, q2]
    
        px = []
        py = []
        pz = []
        t = np.arange(0, 1, 0.01)
        for i in range(len(t)):
            P = np.dot((1 - t[i]) ** 2, Q[0]) + np.dot(2 * (1 - t[i]) * t[i], Q[1]) + np.dot(t[i] ** 2, Q[2])
            px.append(P[0])
            py.append(P[1])
            pz.append(P[2])
        return px, py, pz


    def reposition(self, rotation_angle=None, vertical_distance=None):
        if self.state == Ball.READY:
            if vertical_distance:
                self.pos.z -= vertical_distance
                self.ball.setZ(self.pos.z)


class Balls(NodePath):

    def __init__(self, name, bubbles):
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

    def __init__(self, bubbles):
        super().__init__('normal_ball', bubbles)

    def hit(self, clicked_pos, block, tower):
        blocks = []
        if self.getColor() == block.getColor():
            tower.get_neighbors(block, block.getColor(), blocks)
        para = Parallel(self.bubbles.get_sequence(self.getColor(), clicked_pos))

        for block in blocks:
            pos = block.getPos()
            para.append(Sequence(
                Func(tower.clean_up, block),
                self.bubbles.get_sequence(self.getColor(), pos))
            )
        para.start()


class MultiColorBall(Balls):

    def __init__(self, bubbles):
        super().__init__('multicolor_ball', bubbles)
        self.model.setTexture(base.loader.loadTexture(PATH_TEXTURE_MULTI), 1)

    def _hit(self, color, tower):
        for block in tower.judge_colors(lambda x: x.getColor() == color):
            pos = block.getPos()
            yield Sequence(Func(tower.clean_up, block),
                           self.bubbles.get_sequence(color, pos))

    def hit(self, clicked_pos, block, tower):
        color = block.getColor()
        Parallel(
            self.bubbles.get_sequence(color, clicked_pos),
            *[seq for seq in self._hit(color, tower)]
        ).start()


class TwoToneBall(Balls):

    def __init__(self, bubbles):
        super().__init__('twotone_ball', bubbles)
        self.model.setTexture(base.loader.loadTexture(PATH_TEXTURE_TWOTONE), 1)
       
    def _hit(self, color, tower):
        for block in tower.judge_colors(lambda x: x.getColor() != color):
            pos = block.getPos()
            color = block.getColor()
            yield Sequence(Func(tower.clean_up, block),
                           self.bubbles.get_sequence(color, pos))

    def hit(self, clicked_pos, block, tower):
        color = block.getColor()
        Parallel(
            self.bubbles.get_sequence(Colors.select(), clicked_pos),
            *[seq for seq in self._hit(color, tower)]
        ).start()


# class ColorBall(NodePath):

#     def __init__(self, bubbles, parent):
#         super().__init__(PandaNode('ball'))
#         # self.reparentTo(base.render)
#         self.navigator = parent
#         self.reparent_to(parent)

#         # self.start_pos = Point3(0, -21, 0)
#         self.start_pos = Point3(0, -60, 0)  # -50

#         self.start_hpr = Vec3(95, 0, 30)
#         self.normal_ball = NormalBall(bubbles)
#         self.multi_ball = MultiColorBall(bubbles)
#         self.twotone_ball = TwoToneBall(bubbles)
#         self.ball = None

#         self.move_idx = 0

#         self.ball_number = OnscreenText(
#             style=Plain,
#             pos=(-0.02, -0.98),
#             align=TextNode.ACenter,
#             scale=0.1,
#             mayChange=True
#         )

#     def initialize(self, tower):
#         self.tower = tower
#         self.cnt = self.tower.level
#         if self.ball is not None and self.ball.hasParent():
#             self._delete()
#         self.used = False
#         self.state = None
#         self.pos = self.start_pos
#         self.hpr = self.start_hpr
#         self.ball_number.setText('')

#     def setup(self, color, camera):
#         # if color == 'MULTI':
#         #     self.ball = self.multi_ball
#         # elif color == 'TWOTONE':
#         #     self.used = True
#         #     self.ball = self.twotone_ball
#         # else: 
#             # self.ball = self.normal_ball
#             # self.ball.setColor(color)

#         self.ball = self.normal_ball
#         self.ball.setColor(color)


#         self.pos.z = camera.getZ() - 1.5
#         self.ball.setPos(self.pos)
#         # print('setup ball pos', self.ball.get_pos())
#         # ball's initial h 95 - camera's initial h 12 = 83
#         self.hpr.x = camera.getH() + 83
#         self.ball.setHpr(self.hpr)
#         # self.ball.reparentTo(self)

#         self.ball.reparentTo(self.navigator)

#         self.state = Ball.READY
#         # show the number of throwing a ball.
#         self.ball_number.reparentTo(base.aspect2d)
#         self.ball_number.setText(str(self.cnt))

#     def _delete(self):
#         self.ball.detachNode()
#         self.state = Ball.DELETED

#     def move(self, clicked_pos, block):
#         self.cnt -= 1
#         self.state = Ball.MOVE
#         self.ball_number.detachNode()

#         # rel_pos = block.get_pos(base.render)
#         # relative_pos = base.render.get_relative_point(self.tower, clicked_pos)
#         # vec = base.render.get_relative_point(self.navigator, clicked_pos)
#         # diff = vec - clicked_pos
#         # clicked_pos = clicked_pos + diff
#         rel_pos = self.navigator.get_relative_point(base.render, clicked_pos)
        
#         # self.arr = self.bezier_curve2(self.ball.get_pos(), rel_pos)
#         self.px, self.py, self.pz = self.bezier_curve2(self.ball.get_pos(), rel_pos)
        
        
#         # Sequence(
#         #     # self.ball.posHprInterval(0.5, clicked_pos, Vec3(0, 360, 0)),
#         #     self.ball.posHprInterval(0.5, rel_pos, Vec3(0, 360, 0)),
#         #     Func(self._delete),
#         #     Func(self.ball.hit, clicked_pos, block, self.tower)
#         # ).start()

#     def moving(self):
#         # pt = self.arr[self.move_idx]
#         # self.ball.set_pos(pt[0], pt[1], pt[2])
#         # self.move_idx += 1

#         self.ball.set_pos(self.px[self.move_idx], self.py[self.move_idx], self.pz[self.move_idx])
#         self.move_idx += 1
    
#     # def bezier_curve2(self, q1, q2):
#         # q3 = (q1 + q2) / 2
#         # q3.z += 3
        
#         # Q = [q1, q2, q3]
#         # arr = []

#         # t = np.arange(0, 1, 0.01)
#         # for i in range(len(t)):
#         #     pt = []
#         #     P = np.dot((1 - t[i]) ** 2, Q[0]) + np.dot(2 * (1 - t[i]) * t[i], Q[1]) + np.dot(t[i] ** 2, Q[2])
#         #     pt.append(P[0])
#         #     pt.append(P[1])
#         #     pt.append(P[2])
#         #     arr.append(pt)
#         #     # px.append(P[0])
#         #     # py.append(P[1])
#         #     # pz.append(P[2])
#         # np_arr = np.array(arr)

#         # return np.rot90(np_arr, 2)


#     def bezier_curve2(self, q1, q2):
#         # 点の座標
#         # q1 = [0, -60, -1.5]
#         # q2 = [2.58105, -5.59238, 18.1952]
#         # q3 = [1.290525, -32.7962,  18.3476]
#         q3 = (q1 + q2) / 2
#         q3.z += 10
        
#         Q = [q1, q3, q2]
    
#         px = []
#         py = []
#         pz = []
#         t = np.arange(0, 1, 0.01)
#         for i in range(len(t)):
#             P = np.dot((1 - t[i]) ** 2, Q[0]) + np.dot(2 * (1 - t[i]) * t[i], Q[1]) + np.dot(t[i] ** 2, Q[2])
#             px.append(P[0])
#             py.append(P[1])
#             pz.append(P[2])
#         return px, py, pz


#     def reposition(self, rotation_angle=None, vertical_distance=None):
#         if self.state == Ball.READY:
#             if vertical_distance:
#                 self.pos.z -= vertical_distance
#                 self.ball.setZ(self.pos.z)


# class NormalBall(NodePath):

#     def __init__(self, bubbles):
#         super().__init__(PandaNode('normalBall'))
#         ball = base.loader.loadModel(PATH_SPHERE)
#         ball.reparentTo(self)
#         self.setScale(0.2)
#         self.bubbles = bubbles

#     def hit(self, clicked_pos, block, tower):
#         blocks = []
#         if self.getColor() == block.getColor():
#             tower.get_neighbors(block, block.getColor(), blocks)
#         para = Parallel(self.bubbles.get_sequence(self.getColor(), clicked_pos))

#         for block in blocks:
#             pos = block.getPos()
#             para.append(Sequence(
#                 Func(tower.clean_up, block),
#                 self.bubbles.get_sequence(self.getColor(), pos))
#             )
#         para.start()


# class MultiColorBall(NodePath):

#     def __init__(self, bubbles):
#         super().__init__(PandaNode('multiColorBall'))
#         ball = base.loader.loadModel(PATH_SPHERE)
#         ball.setTexture(base.loader.loadTexture(PATH_TEXTURE_MULTI), 1)
#         ball.reparentTo(self)
#         self.setScale(0.2)
#         self.bubbles = bubbles

#     def _hit(self, color, tower):
#         for block in tower.judge_colors(lambda x: x.getColor() == color):
#             pos = block.getPos()
#             yield Sequence(Func(tower.clean_up, block),
#                            self.bubbles.get_sequence(color, pos))

#     def hit(self, clicked_pos, block, tower):
#         color = block.getColor()
#         Parallel(
#             self.bubbles.get_sequence(color, clicked_pos),
#             *[seq for seq in self._hit(color, tower)]
#         ).start()


# class TwoToneBall(NodePath):

#     def __init__(self, bubbles):
#         super().__init__(PandaNode('twoToneBall'))
#         ball = base.loader.loadModel(PATH_SPHERE)
#         ball.setTexture(base.loader.loadTexture(PATH_TEXTURE_TWOTONE), 1)
#         ball.reparentTo(self)
#         self.setScale(0.2)
#         self.bubbles = bubbles

#     def _hit(self, color, tower):
#         for block in tower.judge_colors(lambda x: x.getColor() != color):
#             pos = block.getPos()
#             color = block.getColor()
#             yield Sequence(Func(tower.clean_up, block),
#                            self.bubbles.get_sequence(color, pos))

#     def hit(self, clicked_pos, block, tower):
#         color = block.getColor()
#         Parallel(
#             self.bubbles.get_sequence(Colors.select(), clicked_pos),
#             *[seq for seq in self._hit(color, tower)]
#         ).start()

