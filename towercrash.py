import sys
from enum import Enum, auto

from direct.gui.DirectGui import OnscreenText, Plain
from direct.showbase.ShowBaseGlobal import globalClock
from direct.showbase.ShowBase import ShowBase
from panda3d.bullet import BulletWorld, BulletDebugNode
from panda3d.core import NodePath, TextNode
from panda3d.core import load_prc_file_data
from panda3d.core import Vec3, BitMask32, Point3

from balls import ColorBall
from lights import BasicAmbientLight, BasicDayLight
from scene import Scene
from start_screen import StartScreen
from tower import towers


load_prc_file_data("", """
    textures-power-2 none
    gl-coordinate-system default
    window-title Panda3D Tower Crash
    filled-wireframe-apply-shader true
    stm-max-views 8
    stm-max-chunk-count 2048""")


class Game(Enum):

    READY = auto()
    START = auto()
    PLAY = auto()
    THROW = auto()
    HIT = auto()
    JUDGE = auto()
    GAMEOVER = auto()


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
        self.wait_count = 5
        self.tower_num = 0

        self.world = BulletWorld()
        self.world.set_gravity(Vec3(0, 0, -9.81))
        self.debug = self.render.attach_new_node(BulletDebugNode('debug'))
        self.world.set_debug_node(self.debug.node())

        self.ambient_light = BasicAmbientLight()
        self.directional_light = BasicDayLight()

        self.scene = Scene(self.world)
        self.scene.reparent_to(self.render)

        self.navigator = NodePath('navigator')
        self.navigator.reparent_to(self.render)
        self.camera.reparent_to(self.navigator)

        self.ball = ColorBall(self.world)
        self.ball_number_display = BallNumberDisplay()

        self.start_screen = StartScreen()
        self.start_screen.set_up()
        self.start_new_game()

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
        self.state = None
        self.click = False
        self.dragging = False
        self.before_mouse_x = None

        if self.tower_num >= len(towers):
            self.tower_num = 0

        tower = towers[self.tower_num]
        self.tower = tower(24, self.scene.foundation, self.world)
        self.tower.build()

        self.camera_highest_z = self.tower.floater.get_z(self.render)
        self.navigator.set_pos_hpr(Point3(0, 0, self.camera_lowest_z), Vec3(0, 0, 0))
        self.camera.set_pos(0, -70, 0)  # -64 70
        self.camera.look_at(0, 0, self.camera_lowest_z + 4 * 2.5)

        self.ball.initialize(self.tower)
        self.ball_cnt = self.tower.level

    def setup_ball(self):
        start_pos = Point3(0, -60, -0.8)
        self.ball.setup(start_pos, self.navigator)

        # show the number of throwing a ball.
        self.ball_number_display.reparent_to(self.aspect2d)
        self.ball_number_display.setText(str(self.ball_cnt))

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

    def choose_block(self, mouse_pos):
        near_pos = Point3()
        far_pos = Point3()
        self.camLens.extrude(mouse_pos, near_pos, far_pos)

        from_pos = self.render.get_relative_point(self.cam, near_pos)
        to_pos = self.render.get_relative_point(self.cam, far_pos)
        result = self.world.ray_test_closest(from_pos, to_pos, BitMask32.bit(1))

        if result.hasHit():
            if (nd := result.get_node()).is_active():
                clicked_pt = result.get_hit_pos()
                block = NodePath(nd)
                self.ball.aim_at(clicked_pt, block)
                return True

    def mouse_click(self):
        self.dragging = True
        self.dragging_start_time = globalClock.get_frame_time()

    def mouse_release(self):
        if globalClock.get_frame_time() - self.dragging_start_time < 0.2:
            self.click = True
        self.dragging = False
        self.before_mouse_x = None

    def rotate_camera(self, mouse_x, dt):
        if self.before_mouse_x is None:
            self.before_mouse_x = mouse_x

        angle = 0

        if (delta := mouse_x - self.before_mouse_x) < 0:
            angle += 90   # rotate leftward
        elif delta > 0:
            angle -= 90   # rotate rightward

        angle *= dt
        self.navigator.set_h(self.navigator.get_h() + angle)
        self.before_mouse_x = mouse_x

    def move_down_camera(self, dt):
        if self.navigator.get_z() > self.camera_lowest_z:
            distance = 10 * dt
            self.navigator.set_z(self.navigator.get_z() - distance)

    def _start(self, task):
        self.state = Game.READY
        return task.done

    def start_new_game(self):
        self.initialize_game()
        self.taskMgr.do_method_later(3, self._start, 'start')

    def clean_sea_bottom(self):
        for con in self.world.contact_test(self.scene.bottom.node()).get_contacts():
            block = NodePath(con.get_node0())
            self.tower.clean_up(block)

    def update(self, task):
        dt = globalClock.getDt()
        self.scene.water_camera.setMat(
            self.cam.getMat(self.render) * self.scene.clip_plane.getReflectionMat())

        match self.state:
            case Game.READY:
                if self.start_screen.disappear(dt):
                    self.start_screen.tear_down()
                    self.state = Game.START

            case Game.START:
                if not self.moveup_camera(dt):
                    self.setup_ball()
                    self.state = Game.PLAY

            case Game.GAMEOVER:
                if self.start_screen.appear(dt):
                    if self.tower.tower_top <= 1:
                        self.tower_num += 1
                    self.tower.remove_all_blocks()
                    self.start_new_game()

            case Game.PLAY:
                if self.mouseWatcherNode.has_mouse():
                    mouse_pos = self.mouseWatcherNode.get_mouse()

                    if self.click:
                        if self.choose_block(mouse_pos):
                            self.ball_number_display.detach_node()
                            self.ball_cnt -= 1
                            self.state = Game.THROW
                        self.click = False

                    if self.dragging:
                        if globalClock.get_frame_time() - self.dragging_start_time >= 0.2:
                            self.rotate_camera(mouse_pos.x, dt)

            case Game.THROW:
                if not self.ball.move(dt):
                    self.state = Game.HIT

            case Game.HIT:
                self.ball.hit()
                self.state = Game.JUDGE

            case Game.JUDGE:
                if self.ball_cnt > 0 and self.tower.tower_top > 1:
                    self.setup_ball()
                    self.state = Game.PLAY
                else:
                    self.start_screen.set_up()
                    self.state = Game.GAMEOVER

        self.tower.update()
        self.clean_sea_bottom()

        if self.navigator.get_z() > self.tower.floater.get_z(self.render):
            self.move_down_camera(dt)

        self.world.do_physics(dt)
        return task.cont


if __name__ == '__main__':
    game = TowerCrash()
    game.run()