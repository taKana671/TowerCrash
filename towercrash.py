import sys
from enum import Enum, auto

import numpy as np
from direct.gui.DirectGui import OnscreenText, Plain, OnscreenImage, DirectButton
from direct.interval.IntervalGlobal import Sequence, Parallel, Func, Wait
from direct.showbase.ShowBaseGlobal import globalClock
from direct.showbase.ShowBase import ShowBase
# from panda3d.bullet import BulletSphereShape
from panda3d.bullet import BulletWorld, BulletDebugNode
from panda3d.core import PandaNode, NodePath, TextNode, TransparencyAttrib
from panda3d.core import Vec3, LColor, BitMask32, Point3, Quat

from direct.showbase.InputStateGlobal import inputState


from balls import ColorBall
from bubble import Bubbles
from lights import BasicAmbientLight, BasicDayLight
from scene import Scene
from tower import towers, Colors


PATH_START_SCREEN = 'images/start.png'
CHECK_REPEAT = 0.2
WAIT_COUNT = 5


class Ball(Enum):

    DELETED = auto()
    READY = auto()
    MOVE = auto()
    MOVING = auto()


class Game(Enum):

    PLAY = auto()
    GAMEOVER = auto()
    START = auto()
    CLEAR = auto()
    THROW = auto()

    HIT = auto()
    SETUP = auto()


class BallNumberDisplay(OnscreenText):

    def __init__(self):
        super().__init__(
            style=Plain,
            pos=(-0.02, -0.98),
            align=TextNode.ACenter,
            scale=0.1,
            mayChange=True
        )


class TowerCrash(ShowBase):

    def __init__(self):
        super().__init__()
        self.disable_mouse()
        self.camera_lowest_z = 2.5
        self.tower_num = 0

        self.world = BulletWorld()
        self.world.set_gravity(Vec3(0, 0, -9.81))

        self.ambient_light = BasicAmbientLight()
        self.directional_light = BasicDayLight()
        self.scene = Scene(self.world)
        self.scene.reparent_to(self.render)

        self.navigator = NodePath('navigator')
        self.navigator.reparent_to(self.render)
        self.camera.reparent_to(self.navigator)

        self.bubbles = Bubbles()
        self.ball = ColorBall(self.world, self.navigator, self.bubbles)

        self.gameover_seq = Sequence(Wait(3))
        self.start_screen = StartScreen(self)

        self.ball_number_display = BallNumberDisplay()

        self.debug = self.render.attach_new_node(BulletDebugNode('debug'))
        self.world.set_debug_node(self.debug.node())


        self.initialize_game()

        # self.camera.set_p(-5)

        self.accept('z', self.test_move_camera, ['z', 'up'])
        self.accept('shift-z', self.test_move_camera, ['z', 'down'])
        self.accept('x', self.test_move_camera, ['x', 'up'])
        self.accept('shift-x', self.test_move_camera, ['x', 'down'])
        self.accept('y', self.test_move_camera, ['y', 'up'])
        self.accept('shift-y', self.test_move_camera, ['y', 'down'])
        self.accept('h', self.test_move_camera, ['h', 'up'])
        self.accept('shift-h', self.test_move_camera, ['h', 'down'])
        self.accept('p', self.test_move_camera, ['p', 'up'])
        self.accept('shift-p', self.test_move_camera, ['p', 'down'])
        self.accept('r', self.test_move_camera, ['r', 'up'])
        self.accept('shift-r', self.test_move_camera, ['r', 'down'])

        self.accept('escape', sys.exit)
        self.accept('d', self.toggle_debug)
        self.accept('mouse1', self.mouse_click)
        self.accept('mouse1-up', self.mouse_release)
        self.taskMgr.add(self.update, 'update')

    def toggle_debug(self):
        if self.debug.is_hidden():
            self.debug.show()
        else:
            self.debug.hide()

    def initialize_game(self):
        self.start_screen.reparentTo(self.aspect2d)
        self.state = None
        self.descent_distance = 0
        self.mouse_dragging = 0
        self.timer = 0
        self.click = False

        tower = towers[self.tower_num]
        # tower = towers[4]
        self.tower = tower(24, self.scene.foundation, self.world)
        # self.tower = tower(6, self.scene.foundation, self.world)
        self.tower.build()
        self.ball.initialize(self.tower)

        for _ in range(len(self.gameover_seq) - 1):
            self.gameover_seq.pop()

        self.camera_highest_z = self.tower.floater.get_z(self.render)
        self.navigator.set_pos_hpr(Point3(0, 0, self.camera_lowest_z), Vec3(0, 0, 0))
        self.camera.set_pos(0, -70, 0)  # -64
        self.camera.look_at(0, 0, self.camera_lowest_z + 4 * 2.5)

        # self.camera.set_pos(0, -64, self.camera_lowest_z)

        self.ball_cnt = self.tower.level

    def setup_ball(self):
        normal = True if self.ball_cnt >= 15 else False
        self.ball.setup(normal)
        # show the number of throwing a ball.
        self.ball_number_display.reparent_to(self.aspect2d)
        self.ball_number_display.setText(str(self.ball_cnt))
        self.ball_cnt -= 1

    def moveup_camera(self, dt):
        angle = dt * 100
        vertical_distance = 15 * dt

        if (h := self.navigator.get_h()) < 360:
            self.navigator.set_h(h + angle)
        elif h > 360:
            self.navigator.set_h(360)

        if (z := self.navigator.get_z()) < self.camera_highest_z:
            self.navigator.set_z(z + vertical_distance)
        elif z > self.camera_highest_z:
            self.navigator.set_z(self.camera_highest_z)

        if h == 360 and z == self.camera_highest_z:
            return False

        return True

    def control_mouse(self):
        if self.mouseWatcherNode.has_mouse():
            mouse_pos = self.mouseWatcherNode.get_mouse()
            near_pos = Point3()
            far_pos = Point3()
            self.camLens.extrude(mouse_pos, near_pos, far_pos)

            from_pos = self.render.get_relative_point(self.cam, near_pos)
            to_pos = self.render.get_relative_point(self.cam, far_pos)
            result = self.world.ray_test_closest(from_pos, to_pos, BitMask32.bit(1))

            if result.hasHit():
                if (nd := result.get_node()).is_active():
                    clicked_pos = result.get_hit_pos()
                    return clicked_pos, NodePath(nd)
            else:
                self.mouse_x = 0
                self.mouse_dragging = globalClock.get_frame_count() + WAIT_COUNT
        return None

    def mouse_click(self):
        self.click = True

    def mouse_release(self):
        self.mouse_dragging = 0

    def rotate_camera(self, dt):
        mouse_x = self.mouseWatcherNode.get_mouse_x()
        if globalClock.get_frame_count() >= self.mouse_dragging:
            angle = 0
            if (delta := mouse_x - self.mouse_x) < 0:
                angle += 90
            elif delta > 0:
                angle -= 90
            angle *= dt

            self.navigator.set_h(self.navigator.get_h() + angle)
        self.mouse_x = mouse_x

    def move_down_camera(self, dt):
        if self.navigator.get_z() > self.camera_lowest_z:
            distance = 10 * dt
            self.navigator.set_z(self.navigator.get_z() - distance)

    def clear(self):
        if self.tower.tower_top <= 1:
            self.gameover_seq.append(Func(self.tower.clear_foundation, self.bubbles))
        self.gameover_seq.append(Wait(2))
        self.gameover_seq.start()

    def game_over(self):
        # if self.tower.tower_top <= 0:
        if self.tower.tower_top <= 1:
            self.tower_num += 1
        if self.tower_num >= len(towers):
            self.tower_num = 0

        self.tower.remove_all_blocks()
        self.initialize_game()

    def clean_sea_bottom(self):
        for con in self.world.contact_test(self.scene.bottom.node()).get_contacts():
            block = NodePath(con.get_node0())
            self.tower.clean_up(block)

    def update(self, task):
        dt = globalClock.getDt()
        self.scene.water_camera.setMat(self.cam.getMat(self.render) * self.scene.clip_plane.getReflectionMat())

        if self.state == Game.START:
            if not self.moveup_camera(dt):
                self.setup_ball()
                self.state = Game.PLAY

        if self.state == Game.CLEAR:
            self.clear()
            self.state = Game.GAMEOVER

        if self.state == Game.GAMEOVER:
            if not self.gameover_seq.is_playing():
                self.game_over()

        if self.state == Game.PLAY:
            if self.click:
                if clicked := self.control_mouse():
                    self.ball.start(*clicked)
                    self.ball_number_display.detach_node()
                    # self.ball.state = Ball.MOVING
                    self.state = Game.THROW
                self.click = False

            # if self.tower.tower_top <= 0 or self.ball.cnt == 0:
            if self.tower.tower_top <= 1 or self.ball_cnt == 0:
                self.state = Game.CLEAR

            self.clean_sea_bottom()
            self.tower.update()

            if self.navigator.get_z() > self.tower.floater.get_z(self.render):
                self.move_down_camera(dt)

            if self.mouse_dragging:
                self.rotate_camera(dt)

            # if self.ball.state == Ball.DELETED and self.ball.cnt > 0:
            #     n = 7 if not self.ball.used else 6
            #     self.ball.setup(Colors.select(n))

        if self.state == Game.THROW:
            if self.ball.move(dt):
                # self.state = Game.HIT
                if self.ball_cnt > 0:
                    self.setup_ball()
                    self.state = Game.PLAY

        # if self.state == Game.HIT:
        #     self.ball.hit()
        #     self.state = Game.SETUP

        # if self.state == Game.SETUP:
        #     if self.ball_cnt > 0:
        #         if self.ball.is_detached():
        #             self.setup_ball()
        #             self.state = Game.PLAY



        self.world.do_physics(dt)
        return task.cont

    
    
    
    
    
    
    def test_move_camera(self, direction, move):
        if direction == 'z':
            z = self.camera.get_z()
            if move == 'up':
                self.camera.set_z(z + 2)
            elif move == 'down':
                self.camera.set_z(z - 2)

        if direction == 'y':
            y = self.camera.get_y()
            if move == 'up':
                self.camera.set_y(y + 2)
            elif move == 'down':
                self.camera.set_y(y - 2)

        if direction == 'x':
            x = self.camera.get_x()
            if move == 'up':
                self.camera.set_x(x + 2)
            elif move == 'down':
                self.camera.set_x(x - 2)

        if direction == 'h':
            h = self.camera.get_h()
            if move == 'up':
                self.camera.set_h(h + 2)
            elif move == 'down':
                self.camera.set_h(h - 2)

        if direction == 'p':
            p = self.camera.get_p()
            if move == 'up':
                self.camera.set_p(p + 2)
            elif move == 'down':
                self.camera.set_p(p - 2)

        if direction == 'r':
            r = self.camera.get_r()
            if move == 'up':
                self.camera.set_r(r + 2)
            elif move == 'down':
                self.camera.set_r(r - 2)

        # self.camera.look_at(-2, 12, 12.5)
        print(self.camera.get_pos(), self.camera.get_hpr())


class StartScreen(NodePath):

    def __init__(self, game):
        super().__init__(PandaNode('startScreen'))
        self.screen = OnscreenImage(
            image=PATH_START_SCREEN,
            parent=self,
            scale=(1.5, 1, 1),
            pos=(0, 0, 0)
        )
        self.button = DirectButton(
            pos=(0, 0, 0),
            scale=0.1,
            parent=self,
            frameSize=(-2, 2, -0.7, 0.7),
            frameColor=(0.75, 0.75, 0.75, 1),
            text="start",
            text_pos=(0, -0.3),
            command=self.click
        )
        self.game = game

    def _start(self):
        self.game.state = Game.START

    def click(self):
        self.detachNode()
        Sequence(Wait(0.5), Func(self._start)).start()


if __name__ == '__main__':
    game = TowerCrash()
    game.run()