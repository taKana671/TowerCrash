from direct.showbase.ShowBase import ShowBase
# from panda3d.core import Vec3, Point3, BitMask32
from panda3d.core import PandaNode, NodePath

from direct.interval.IntervalGlobal import Sequence, Parallel, Func


PATH_BUBBLE = 'models/sphere/sphere'


class Bubbles(NodePath):

    def __init__(self, color, pos):
        super().__init__(PandaNode('bubbles'))
        self.reparentTo(base.render)
        self.pos = pos
        self.color = color

    def create_bubbles(self):
        for _ in range(5):
            bubble = base.loader.loadModel(PATH_BUBBLE)
            bubble.reparentTo(self)
            bubble.setPos(self.pos)
            bubble.setColor(self.color)
            bubble.setScale(0.01)
            yield bubble

    def create_seq(self, bub, delta1, delta2):
        return Sequence(
            bub.posHprScaleInterval(0.5, bub.getPos() + delta1, bub.getHpr(), 0.1),
            bub.posHprScaleInterval(0.5, bub.getPos() + delta2, bub.getHpr(), 0.01),
            Func(lambda: bub.removeNode())
        )    

    def start(self):
        deltas = [
            [(0, 0, 1), (0, 0, -1)],
            [(1, 0, 1), (2, 0, -1)],
            [(0, 1, 1), (0, 2, -1)], 
            [(-1, 0, 1), (-2, 0, -1)],
            [(0, -1, 1), (0, -2, -1)]
        ]
        self.bubbles = [bub for bub in self.create_bubbles()]
        Parallel(*[self.create_seq(bub, *delta) for bub, delta in zip(self.bubbles, deltas)]).start()


if __name__ == '__main__':
    # from window import Window
    base = ShowBase()
    # Window('game')
    # base.setBackgroundColor(0.5, 0.8, 1)
    base.disableMouse()

    base.camera.setPos(20, -18, 20)  # 20, -20, 5
    base.camera.setP(-80)
    base.camera.lookAt(5, 3, 5)  # 5, 0, 3
    bubbles = Bubbles()
    bubbles.start()
    base.run()