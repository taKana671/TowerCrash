from enum import Enum, auto

from direct.gui.DirectGui import OnscreenText, Plain, OnscreenImage, DirectButton
from direct.interval.IntervalGlobal import Sequence, Parallel, Func, Wait
from direct.showbase.ShowBaseGlobal import globalClock
from direct.showbase.ShowBase import ShowBase
from panda3d.bullet import BulletSphereShape
from panda3d.bullet import BulletWorld, BulletDebugNode
from panda3d.core import PandaNode, NodePath, TextNode, TransparencyAttrib
from panda3d.core import Vec3, LColor, BitMask32, Point3, Quat
from panda3d.core import AmbientLight, DirectionalLight

from bubble import Bubbles
from scene import Scene
from tower import towers, Colors, Block


PATH_SPHERE = "models/sphere/sphere"
PATH_TEXTURE_BALL = 'textures/multi.jpg'
PATH_START_SCREEN = 'images/start.png'
CHECK_REPEAT = 0.2
WAIT_COUNT = 5


class Ball(Enum):

    DELETED = auto()
    READY = auto()
    MOVE = auto()


class Game(Enum):

    PLAY = auto()
    GAMEOVER = auto()
    START = auto()


class ColorBall(NodePath):

    def __init__(self):
        super().__init__(PandaNode('ball'))
        self.reparentTo(base.render)
        self.start_pos = Point3(5.5, -21, 0)
        self.start_hpr = Vec3(95, 0, 30)
        self.bubbles = Bubbles()
        self.special = SpecialBall(self.bubbles)
        self.normal = NormalBall(self.bubbles)
        self.ball = None

        self.ball_number = OnscreenText(
            style=Plain,
            pos=(-0.02, -0.98),
            align=TextNode.ACenter,
            scale=0.1,
            mayChange=True
        )

    def initialize(self, tower):
        self.tower = tower
        self.cnt = 0
        if self.ball is not None and self.ball.hasParent():
            self._delete()
        self.state = None
        self.pos = self.start_pos
        self.hpr = self.start_hpr
        self.ball_number.setText('')

    def setup(self, color, camera_z):
        if color:
            self.ball = self.normal
            self.ball.setColor(color)
        else:
            self.ball = self.special

        self.pos.z = camera_z - 1.5
        self.ball.setPos(self.pos)
        self.ball.setHpr(self.hpr)
        self.ball.reparentTo(self)
        self.state = Ball.READY
        # show the number of throwing a ball.
        self.cnt += 1
        self.ball_number.reparentTo(base.aspect2d)
        self.ball_number.setText(str(self.cnt))

    def _delete(self):
        self.ball.detachNode()
        self.state = Ball.DELETED

    def move(self, clicked_pos, block):
        self.state = Ball.MOVE
        self.ball_number.detachNode()

        Sequence(
            self.ball.posInterval(0.5, clicked_pos),
            Func(self._delete),
            Func(self.ball.hit, clicked_pos, block, self.tower)
        ).start()

    def reposition(self, rotation_angle=None, vertical_distance=None):
        if rotation_angle:
            self.pos = self.tower.rotate(self.ball, rotation_angle)
            self.ball.setPos(self.pos)
            self.hpr.x = self.ball.getH() + rotation_angle
            self.ball.setHpr(self.hpr)
        if vertical_distance:
            self.pos.z -= vertical_distance
            self.ball.setZ(self.pos.z)


class NormalBall(NodePath):

    def __init__(self, bubbles):
        super().__init__(PandaNode('normalBall'))
        ball = base.loader.loadModel(PATH_SPHERE)
        ball.reparentTo(self)
        self.setScale(0.2)
        self.bubbles = bubbles

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


class SpecialBall(NodePath):

    def __init__(self, bubbles):
        super().__init__(PandaNode('specialBall'))
        ball = base.loader.loadModel(PATH_SPHERE)
        ball.setTexture(base.loader.loadTexture(PATH_TEXTURE_BALL), 1)
        ball.reparentTo(self)
        self.setScale(0.2)
        self.bubbles = bubbles

    def _hit(self, color, tower):
        for block in tower.get_same_colors(color):
            pos = block.getPos()
            yield Sequence(Func(tower.clean_up, block),
                           self.bubbles.get_sequence(color, pos))

    def hit(self, clicked_pos, block, tower):
        color = block.getColor()
        Parallel(
            self.bubbles.get_sequence(Colors.select(), clicked_pos),
            *[seq for seq in self._hit(color, tower)]
        ).start()


class TowerCrash(ShowBase):

    def __init__(self):
        super().__init__()
        self.disableMouse()
        self.camera_lowest_z = 2.5
        self.tower_num = 0

        self.world = BulletWorld()
        self.world.setGravity(Vec3(0, 0, -9.81))

        self.setup_lights()
        self.scene = Scene()
        self.scene.setup(self.world)
        self.ball = ColorBall()
        self.start_screen = StartScreen(self)
        self.initialize_game()

        # *******************************************
        # collide_debug = self.render.attachNewNode(BulletDebugNode('debug'))
        # self.world.setDebugNode(collide_debug.node())
        # collide_debug.show()
        # *******************************************

        self.accept('mouse1', self.mouse_click)
        self.accept('mouse1-up', self.mouse_release)
        self.taskMgr.add(self.update, 'update')

    def create_tower(self):
        tower = towers[self.tower_num]
        self.tower = tower(24, self.scene.foundation, self.world)
        self.tower_num += 1
        if self.tower_num >= len(towers):
            self.tower_num = 0
        # self.tower = towers[2](24, self.scene.foundation, self.world)
        self.tower.build()

    def initialize_game(self):
        self.start_screen.reparentTo(self.aspect2d)
        self.state = None
        self.state = Game.PLAY
        self.camera_move_distance = 0
        self.wait_rotation = 0
        self.wait_start = 0
        self.timer = 0
        self.click = False

        self.create_tower()
        self.ball.initialize(self.tower)

        self.camera_highest_z = (self.tower.inactive_top + 1) * self.tower.block_h
        # self.camera.setPos(10, -20, 40)
        self.camera.setPos(10, -40, self.camera_lowest_z)  # 10, -40, 2.5
        self.camera.setP(10)
        self.camera.lookAt(-2, 12, self.camera_lowest_z + 4 * 2.5)

    def setup_camera(self):
        pos = self.tower.rotate(self.camera, 2)
        z = self.camera.getZ() + self.camera_highest_z / 180
        pos.z = z
        self.camera.setPos(pos)
        self.camera.setH(self.camera.getH() + 2)
        self.wait_start -= 2

    def setup_lights(self):
        ambient_light = self.render.attachNewNode(AmbientLight('ambientLight'))
        ambient_light.node().setColor(LColor(0.6, 0.6, 0.6, 1))
        self.render.setLight(ambient_light)

        directional_light = self.render.attachNewNode(DirectionalLight('directionalLight'))
        directional_light.node().getLens().setFilmSize(200, 200)
        directional_light.node().getLens().setNearFar(1, 100)
        directional_light.node().setColor(LColor(1, 1, 1, 1))
        directional_light.setPosHpr(Point3(0, 0, 30), Vec3(-30, -45, 0))
        directional_light.node().setShadowCaster(True)
        self.render.setShaderAuto()
        self.render.setLight(directional_light)

    def control_mouse(self):
        if self.mouseWatcherNode.hasMouse():
            mouse_pos = self.mouseWatcherNode.getMouse()
            near_pos = Point3()
            far_pos = Point3()
            self.camLens.extrude(mouse_pos, near_pos, far_pos)
            from_pos = self.render.getRelativePoint(self.camera, near_pos)
            to_pos = self.render.getRelativePoint(self.camera, far_pos)
            result = self.world.rayTestClosest(from_pos, to_pos, BitMask32.bit(1))

            if result.hasHit():
                node_name = result.getNode().getName()
                clicked_pos = result.getHitPos()

                if (block := self.tower.blocks.find(node_name)).state == Block.ACTIVE:
                    return clicked_pos, block

                print('node_name', node_name)
                print('collision_pt', clicked_pos)
            else:
                self.mouse_x = 0
                self.wait_rotation = globalClock.getFrameCount() + WAIT_COUNT
        return None

    def mouse_click(self):
        self.click = True

    def mouse_release(self):
        self.wait_rotation = 0

    def control_camera(self, dt, activated_rows):
        # control the rotation of camera.
        angle = 0
        if self.wait_rotation:
            mouse_x = self.mouseWatcherNode.getMouseX()
            if globalClock.getFrameCount() >= self.wait_rotation:
                if (delta := mouse_x - self.mouse_x) < 0:
                    angle += 90
                elif delta > 0:
                    angle -= 90
                angle *= dt
                rotated_pos = self.tower.rotate(self.camera, angle)
                self.camera.setPos(rotated_pos)
                self.camera.setH(self.camera.getH() + angle)
            self.mouse_x = mouse_x

        # control the vertical position of camera.
        distance = 0
        self.camera_move_distance += activated_rows * self.tower.block_h
        if self.camera_move_distance > 0:
            if self.camera.getZ() > self.camera_lowest_z:
                distance = 10 * dt
                self.camera.setZ(self.camera.getZ() - distance)
                self.camera_move_distance -= distance
        return angle, distance

    def game_over(self):
        self.tower.remove_blocks()
        self.initialize_game()

    def update(self, task):
        dt = globalClock.getDt()

        if self.state == Game.START:
            if self.wait_start:
                self.setup_camera()
            else:
                self.ball.setup(Colors.select(), self.camera.getZ())
                self.state = Game.PLAY

        if self.state == Game.GAMEOVER:
            if task.time >= self.timer:
                self.game_over()

        if self.state == Game.PLAY:
            if self.tower.tower_top == 0:
                self.timer = task.time + 3
                self.state = Game.GAMEOVER

            if self.click:
                if clicked := self.control_mouse():
                    self.ball.move(*clicked)
                self.click = False

            # control the blocks collided with a surface or a bottom.
            self.tower.floating(self.world.contactTest(self.scene.surface.node()))
            self.tower.sink(self.world.contactTest(self.scene.bottom.node()))

            activated_rows = 0
            if task.time >= self.timer:
                activated_rows = self.tower.activate()
                self.timer = task.time + CHECK_REPEAT

            rotation_angle, descent_distance = self.control_camera(dt, activated_rows)

            if self.ball.state == Ball.READY:
                self.ball.reposition(rotation_angle, descent_distance)
            if self.ball.state == Ball.DELETED:
                self.ball.setup(Colors.select(6), self.camera.getZ())

        self.world.doPhysics(dt)
        return task.cont


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

    def click(self):

        def _start():
            self.game.wait_start = 360
            self.game.state = Game.START

        self.detachNode()
        Sequence(
            Wait(0.5),
            Func(_start)
        ).start()


if __name__ == '__main__':
    game = TowerCrash()
    game.run()
    # base = ShowBase()
    # base.setBackgroundColor(1, 1, 1)
    # base.disableMouse()
    # base.camera.setPos(0, -10, 5)
    # base.camera.lookAt(0, 0, 0)
    # cylinder = Cylinder()
    # cylinder.setPos(0, 0, 0)
    # cylinder.setColor(LColor(1, 0, 1, 1))
    # base.run()
