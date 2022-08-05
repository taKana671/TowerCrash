import random

from direct.showbase.ShowBase import ShowBase
from panda3d.core import PandaNode, NodePath
from panda3d.core import Vec3, Point3
from direct.interval.IntervalGlobal import Sequence, Parallel, Func


PATH_BUBBLE = 'models/sphere/sphere'


class Bubbles(NodePath):

    def __init__(self, color, pos):
        super().__init__(PandaNode('bubbles'))
        self.reparentTo(base.render)
        self.pos = pos
        self.color = color
        self.numbers = [n for n in range(-3, 4) if n != 0]

    def create_bubble(self, name):
        bubble = base.loader.loadModel(PATH_BUBBLE)
        bubble.reparentTo(self)
        bubble.setPos(self.pos)
        bubble.setColor(self.color)
        bubble.setScale(0.01)

        return bubble

    def calc_delta(self):
        x = random.choice(self.numbers)
        y = -abs(random.choice(self.numbers))
        z = abs(random.choice(self.numbers))
        d1 = Vec3(x, y, z)
        d2 = Vec3(d1.x * 2, d1.y * 2, -d1.z)

        return d1, d2

    def create_seq(self):
        for i in range(8):
            bub = self.create_bubble(i)
            delta1, delta2 = self.calc_delta()

            yield Sequence(
                bub.posHprScaleInterval(0.5, bub.getPos() + delta1, bub.getHpr(), 0.1),
                bub.posHprScaleInterval(0.5, bub.getPos() + delta2, bub.getHpr(), 0.01),
            )

    def get_sequence(self):
        return Sequence(
            Parallel(*(seq for seq in self.create_seq())),
            Func(lambda: self.removeNode())
        )


if __name__ == '__main__':
    # from window import Window
    base = ShowBase()
    # Window('game')
    # base.setBackgroundColor(0.5, 0.8, 1)
    base.disableMouse()

    base.camera.setPos(20, -18, 20)  # 20, -20, 5
    base.camera.setP(-80)
    base.camera.lookAt(5, 3, 5)  # 5, 0, 3
    bubbles = Bubbles((1, 0, 0, 1), Point3(-2, 12, 1.0))
    bubbles.start()
    base.run()