import random

from panda3d.core import PandaNode, NodePath
from panda3d.core import Vec3
from direct.interval.IntervalGlobal import Sequence, Parallel, Func

from create_geomnode import SphereGeom


class Bubbles:

    def __init__(self):
        self.numbers = [n for n in range(-5, 5) if n != 0]
        self.bubble = SphereGeom()

    def create_bubble(self, bubbles, color, pos):
        bubble = self.bubble.copy_to(bubbles)
        bubble.reparent_to(bubbles)
        bubble.set_pos(pos)
        bubble.set_color(color)
        bubble.set_scale(0.2)

        return bubble

    def calc_delta(self):
        x = random.choice(self.numbers)
        y = random.choice(self.numbers)
        z = abs(random.choice(self.numbers))
        d1 = Vec3(x, y, z)
        d2 = Vec3(d1.x * 2, d1.y * 2, -d1.z)

        return d1, d2

    def create_seq(self, bubbles, color, pos):
        for i in range(8):
            bub = self.create_bubble(bubbles, color, pos)
            delta1, delta2 = self.calc_delta()

            yield Sequence(
                bub.posHprScaleInterval(0.5, bub.get_pos() + delta1, bub.get_hpr(), 0.1),
                bub.posHprScaleInterval(0.5, bub.get_pos() + delta2, bub.get_hpr(), 0.01),
            )

    def get_sequence(self, color, pos):
        bubbles = NodePath(PandaNode('bubbles'))
        bubbles.reparent_to(base.render)

        return Sequence(
            Parallel(*(seq for seq in self.create_seq(bubbles, color, pos))),
            Func(lambda: bubbles.remove_node())
        )