import sys
from enum import Enum, auto

from direct.gui.DirectGui import OnscreenText, Plain
from direct.showbase.ShowBaseGlobal import globalClock
from direct.showbase.ShowBase import ShowBase
from panda3d.bullet import BulletWorld, BulletDebugNode
from panda3d.core import NodePath, TextNode, TransparencyAttrib
from panda3d.core import Shader, load_prc_file_data
from panda3d.core import Vec3, BitMask32, Point3, CardMaker

from balls import ColorBall
from lights import BasicAmbientLight, BasicDayLight
from scene import Scene
from tower import towers


load_prc_file_data("", """
    textures-power-2 none
    gl-coordinate-system default
    window-title Panda3D Tower Crash
    filled-wireframe-apply-shader true
    stm-max-views 8
    stm-max-chunk-count 2048""")


class Game(Enum):

    INITIALIZE = auto()
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
        self.state = Game.INITIALIZE

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
        self.state = None
        self.dragging = 0
        self.click = False

        tower = towers[self.tower_num]
        # tower = towers[1]
        self.tower = tower(24, self.scene.foundation, self.world)
        self.tower.build()

        self.camera_highest_z = self.tower.floater.get_z(self.render)
        self.navigator.set_pos_hpr(Point3(0, 0, self.camera_lowest_z), Vec3(0, 0, 0))
        self.camera.set_pos(0, -70, 0)  # -64 70
        self.camera.look_at(0, 0, self.camera_lowest_z + 4 * 2.5)

        self.ball.initialize(self.tower)
        self.ball_cnt = self.tower.level

    def setup_ball(self):
        start_pos = Point3(0, -60, 0)  # -60
        # normal = True if self.ball_cnt >= 15 else False
        normal = False
        self.ball.setup(start_pos, self.navigator, normal)

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
        self.click = True

    def mouse_release(self):
        self.dragging = 0

    def rotate_camera(self, mouse_x, dt):
        angle = 0

        if (delta := mouse_x - self.mouse_x) < 0:
            # rotate leftward
            angle += 90
        elif delta > 0:
            # rotate rightward
            angle -= 90
        angle *= dt

        self.navigator.set_h(self.navigator.get_h() + angle)

    def move_down_camera(self, dt):
        if self.navigator.get_z() > self.camera_lowest_z:
            distance = 10 * dt
            self.navigator.set_z(self.navigator.get_z() - distance)

    def game_start(self, task):
        self.state = Game.READY
        return task.done

    def game_over(self, task):
        if self.tower.tower_top <= 1:
            self.tower_num += 1
        if self.tower_num >= len(towers):
            self.tower_num = 0

        self.tower.remove_all_blocks()
        self.state = Game.INITIALIZE

        return task.done

    def clean_sea_bottom(self):
        for con in self.world.contact_test(self.scene.bottom.node()).get_contacts():
            block = NodePath(con.get_node0())
            self.tower.clean_up(block)

    def update(self, task):
        dt = globalClock.getDt()
        self.scene.water_camera.setMat(self.cam.getMat(self.render) * self.scene.clip_plane.getReflectionMat())

        match self.state:
            case Game.INITIALIZE:
                self.initialize_game()
                self.taskMgr.do_method_later(3, self.game_start, 'game_start')

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
                    self.state = None
                    self.taskMgr.do_method_later(3, self.game_over, 'gameover')

            case Game.PLAY:
                if self.mouseWatcherNode.has_mouse():
                    mouse_pos = self.mouseWatcherNode.get_mouse()

                    if self.click:
                        if self.choose_block(mouse_pos):
                            self.ball_number_display.detach_node()
                            self.ball_cnt -= 1
                            self.state = Game.THROW
                        else:
                            self.mouse_x = 0
                            self.dragging = globalClock.get_frame_count() + self.wait_count
                        self.click = False

                    if 0 < self.dragging <= globalClock.get_frame_count():
                        self.rotate_camera(mouse_pos.x, dt)
                        self.mouse_x = mouse_pos.x

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


class StartScreen:

    def __init__(self):
        self.alpha = 1.0
        self.create_color_gradient()
        self.create_color_camera()

    def create_color_gradient(self):
        cm = CardMaker('gradient')
        cm.set_frame(0, 256, 0, 256)
        self.color_plane = NodePath(cm.generate())
        self.color_plane.look_at(0, 1, 0)
        self.color_plane.set_transparency(TransparencyAttrib.MAlpha)
        self.color_plane.set_pos(Point3(-128, -50, 0))  # Point3(-128, -128, -2)
        self.color_plane.flatten_strong()

        self.color_plane.set_shader(
            Shader.load(Shader.SL_GLSL, 'shaders/color_gradient_v.glsl', 'shaders/color_gradient_f.glsl')
        )
        props = base.win.get_properties()
        self.color_plane.set_shader_input('u_resolution', props.get_size())
        self.color_plane.set_shader_input('alpha', self.alpha)

    def create_color_camera(self):
        self.color_buffer = base.win.make_texture_buffer('gradieng', 512, 512)
        self.color_buffer.set_clear_color(base.win.get_clear_color())
        self.color_buffer.set_sort(-1)

        self.color_camera = base.make_camera(self.color_buffer)
        self.color_camera.node().set_lens(base.camLens)
        self.color_camera.node().set_camera_mask(BitMask32.bit(1))

    def set_up(self):
        self.color_plane.reparent_to(base.render)
        self.color_camera.reparent_to(base.render)

    def tear_down(self):
        self.color_plane.detach_node()
        self.color_camera.detach_node()

    def appear(self, dt):
        if self.alpha == 1.0:
            return True

        self.alpha += dt * 0.1
        if self.alpha > 1.0:
            self.alpha = 1.0

        self.color_plane.set_shader_input('alpha', self.alpha)

    def disappear(self, dt):
        if self.alpha == 0.0:
            return True

        self.alpha -= dt * 0.1
        if self.alpha < 0.0:
            self.alpha = 0.0

        self.color_plane.set_shader_input('alpha', self.alpha)


if __name__ == '__main__':
    game = TowerCrash()
    game.run()