from direct.showbase.ShowBase import ShowBase
from panda3d.bullet import BulletRigidBodyNode, BulletPlaneShape
from panda3d.core import Vec3, Point3
from panda3d.core import PandaNode, NodePath, CardMaker


PATH_GROUND = 'textures/ground.jpg'
PATH_SKY = "models/blue-sky/blue-sky-sphere"
PATH_STONE = 'models/stone/jump'
PLANT1_PATH = 'models/plant1/plants1'
PLANT3_PATH = 'models/plant3/plants3'
SHRUBBERY_PATH = 'models/shrubbery/shrubbery'


class Foundation(NodePath):

    def __init__(self):
        super().__init__(BulletRigidBodyNode('foundation'))
        self.reparentTo(base.render)
        self.create_foundation()

    def create_foundation(self):
        pos_hpr = [
            [Point3(4, -2, 2), Vec3(30, 180, -360)],
            [Point3(4, -2, 2), Vec3(30, 0, -360)],
            [Point3(7.26, -0.1, 2), Vec3(30, 180, 180)],
            [Point3(7.26, -0.1, 2), Vec3(30, 0, 180)]
        ]
        for pos, hpr in pos_hpr:
            stone = base.loader.loadModel(PATH_STONE)
            stone.setScale(0.01)
            stone.setHpr(hpr)
            stone.setPos(pos)
            stone.reparentTo(self)


class Sky(NodePath):

    def __init__(self):
        super().__init__(PandaNode('sky'))
        self.reparentTo(base.render)
        sky = base.loader.loadModel(PATH_SKY)
        sky.setColor(2, 2, 2, 1)
        sky.setScale(0.02)
        sky.reparentTo(self)


class Ground(NodePath):

    def __init__(self):
        super().__init__(BulletRigidBodyNode('ground'))
        self.reparentTo(base.render)
        grasses = self.create_grasses()
        grasses.reparentTo(self)
        self.node().addShape(BulletPlaneShape(Vec3.up(), 0))

    def create_grasses(self):
        grasses = NodePath(PandaNode('grass'))
        card = CardMaker('card')
        size = 2
        half = size / 2
        card.setFrame(-half, half, -half, half)
        max_card = 50

        for y in range(max_card):
            for x in range(max_card):
                g = grasses.attachNewNode(card.generate())
                g.setP(-90)
                g.setPos((x - max_card / 2) * size, (y - max_card / 2) * size, 0)
                # print((x - max_card / 2) * size, (y - max_card / 2) * size, 0)

        texture = base.loader.loadTexture(PATH_GROUND)
        grasses.setTexture(texture)
        grasses.flattenStrong()
        grasses.setPos(0, 40, 0)

        return grasses


class Plant(NodePath):

    def __init__(self):
        super().__init__(PandaNode('plant'))
        self.reparentTo(base.render)
        self.create_forest()

    def create_forest(self):
        plants = [
            (PLANT1_PATH, 0.3, Point3(-12, 36, 2), Vec3(45, 0, 0)),
            (PLANT1_PATH, 0.3, Point3(-16, 36, 2), Vec3(90, 0, 0)),
            (PLANT3_PATH, 0.1, Point3(-8, 36, 2), Vec3(60, 0, 0)),
            (PLANT3_PATH, 0.1, Point3(-4, 36, 2), Vec3(30, 0, 0)),
            (PLANT3_PATH, 0.1, Point3(0, 36, 2), Vec3(45, 0, 0)),
            (SHRUBBERY_PATH, 0.1, Point3(-8, 30, 2), Vec3(30, 30, 0)),
            (SHRUBBERY_PATH, 0.1, Point3(-4, 30, 2), Vec3(60, 30, 0)),
            (SHRUBBERY_PATH, 0.1, Point3(0, 30, 2), Vec3(90, 30, 0)),
        ]
        for path, scale, pos, hpr in plants:
            plant = base.loader.loadModel(path)
            plant.setScale(scale)
            plant.setPos(pos)
            plant.setHpr(hpr)
            plant.reparentTo(self)


class Scene:

    def __init__(self):
        Sky()
        Ground()
        Foundation()
        Plant()



if __name__ == '__main__':
    from window import Window
    base = ShowBase()
    # Window('game')
    # base.setBackgroundColor(0.5, 0.8, 1)
    base.disableMouse()

    base.camera.setPos(20, -18, 5)  # 20, -20, 5
    base.camera.lookAt(5, 0, 3)  # 5, 0, 3
    scene = Scene()
    base.run()