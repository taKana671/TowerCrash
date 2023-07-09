import array
import math

from panda3d.core import Vec3, Point3
from panda3d.core import NodePath
from panda3d.core import Geom, GeomNode, GeomTriangles
from panda3d.core import GeomVertexFormat, GeomVertexData, GeomVertexArrayFormat


class GeomRoot(NodePath):

    def __init__(self):
        geomnode = self.create_geomnode()
        super().__init__(geomnode)
        self.set_two_sided(True)

    def create_format(self):
        arr_format = GeomVertexArrayFormat()
        arr_format.add_column('vertex', 3, Geom.NTFloat32, Geom.CPoint)
        arr_format.add_column('color', 4, Geom.NTFloat32, Geom.CColor)
        arr_format.add_column('normal', 3, Geom.NTFloat32, Geom.CColor)
        arr_format.add_column('texcoord', 2, Geom.NTFloat32, Geom.CTexcoord)
        fmt = GeomVertexFormat.register_format(arr_format)
        return fmt

    def create_geomnode(self):
        fmt = self.create_format()
        vdata_values = array.array('f', [])
        prim_indices = array.array('H', [])

        vertex_count = self.get_vertices(vdata_values, prim_indices)

        vdata = GeomVertexData('geom_vertex', fmt, Geom.UHStatic)
        vdata.unclean_set_num_rows(vertex_count)
        vdata_mem = memoryview(vdata.modify_array(0)).cast('B').cast('f')
        vdata_mem[:] = vdata_values

        prim = GeomTriangles(Geom.UHStatic)
        prim_array = prim.modify_vertices()
        prim_array.unclean_set_num_rows(len(prim_indices))
        prim_mem = memoryview(prim_array).cast('B').cast('H')
        prim_mem[:] = prim_indices

        node = GeomNode('geomnode')
        geom = Geom(vdata)
        geom.add_primitive(prim)
        node.add_geom(geom)
        return node


class CylinderGeom(GeomRoot):
    """Create a geom node of cylinder.
       Args:
            radius (float): the radius of the cylinder; cannot be negative;
            segs_c (int): subdivisions of the mantle along a circular cross-section; mininum is 3;
            height (int): length of the cylinder;
            segs_a (int): subdivisions of the mantle along the axis of rotation; minimum is 1;
    """

    def __init__(self, radius=0.5, segs_c=20, height=1, segs_a=2):
        self.radius = radius
        self.segs_c = segs_c
        self.height = height
        self.segs_a = segs_a
        self.color = (1, 1, 1, 1)
        super().__init__()

    def cap_vertices(self, delta_angle, bottom=True):
        z = 0 if bottom else self.height

        # vertex and uv of the center
        yield ((0, 0, z), (0.5, 0.5))

        # vertex and uv of triangles
        for i in range(self.segs_c):
            angle = delta_angle * i
            c = math.cos(angle)
            s = math.sin(angle)
            x = self.radius * c
            y = self.radius * s
            u = 0.5 + c * 0.5
            v = 0.5 - s * 0.5
            yield ((x, y, z), (u, v))

    def create_bottom_cap(self, delta_angle, vdata_values, prim_indices):
        normal = (0, 0, -1)

        # bottom cap center and triangle vertices
        for vertex, uv in self.cap_vertices(delta_angle, bottom=True):
            vdata_values.extend(vertex)
            vdata_values.extend(self.color)
            vdata_values.extend(normal)
            vdata_values.extend(uv)

        # the vertex order of the bottom cap vertices
        for i in range(self.segs_c - 1):
            prim_indices.extend((0, i + 2, i + 1))
        prim_indices.extend((0, 1, self.segs_c))

        return self.segs_c + 1

    def create_mantle(self, index_offset, delta_angle, vdata_values, prim_indices):
        vertex_count = 0

        # mantle triangle vertices
        for i in range(self.segs_a + 1):
            z = self.height * i / self.segs_a
            v = i / self.segs_a

            for j in range(self.segs_c + 1):
                angle = delta_angle * j
                x = self.radius * math.cos(angle)
                y = self.radius * math.sin(angle)
                normal = Vec3(x, y, 0.0).normalized()
                u = j / self.segs_c
                vdata_values.extend((x, y, z))
                vdata_values.extend(self.color)
                vdata_values.extend(normal)
                vdata_values.extend((u, v))

            vertex_count += self.segs_c + 1

            # the vertex order of the mantle vertices
            if i > 0:
                for j in range(self.segs_c):
                    px = index_offset + i * (self.segs_c + 1) + j
                    prim_indices.extend((px, px - self.segs_c - 1, px - self.segs_c))
                    prim_indices.extend((px, px - self.segs_c, px + 1))

        return vertex_count

    def create_top_cap(self, index_offset, delta_angle, vdata_values, prim_indices):
        normal = (0, 0, 1)

        # top cap center and triangle vertices
        for vertex, uv in self.cap_vertices(delta_angle, bottom=False):
            vdata_values.extend(vertex)
            vdata_values.extend(self.color)
            vdata_values.extend(normal)
            vdata_values.extend(uv)

        # the vertex order of top cap vertices
        for i in range(index_offset + 1, index_offset + self.segs_c):
            prim_indices.extend((index_offset + self.segs_c, i - 1, i))
        prim_indices.extend((index_offset + self.segs_c, index_offset, index_offset + self.segs_c - 1))

        return self.segs_c + 1

    def get_vertices(self, vdata_values, prim_indices):
        delta_angle = 2 * math.pi / self.segs_c
        vertex_count = 0

        # create vertices of the bottom cap, mantle and top cap.
        vertex_count += self.create_bottom_cap(delta_angle, vdata_values, prim_indices)
        vertex_count += self.create_mantle(vertex_count, delta_angle, vdata_values, prim_indices)
        vertex_count += self.create_top_cap(vertex_count, delta_angle, vdata_values, prim_indices)

        return vertex_count


class SphereGeom(GeomRoot):
    """Create a geom node of sphere.
       Args:
            radius (int): the radius of sphere;
            segments (int): the number of surface subdivisions;
    """

    def __init__(self, radius=1.5, segments=22):
        self.radius = radius
        self.segments = segments
        self.color = (1, 1, 1, 1)
        super().__init__()

    def create_bottom_pole(self, vdata_values, prim_indices):
        # the bottom pole vertices
        normal = (0.0, 0.0, -1.0)
        vertex = (0.0, 0.0, -self.radius)

        for i in range(self.segments):
            u = i / self.segments
            vdata_values.extend(vertex)
            vdata_values.extend(self.color)
            vdata_values.extend(normal)
            vdata_values.extend((u, 0.0))

            # the vertex order of the pole vertices
            prim_indices.extend((i, i + self.segments + 1, i + self.segments))

        return self.segments

    def create_quads(self, index_offset, vdata_values, prim_indices):
        delta_angle = 2 * math.pi / self.segments
        vertex_count = 0

        # the quad vertices
        for i in range((self.segments - 2) // 2):
            angle_v = delta_angle * (i + 1)
            radius_h = self.radius * math.sin(angle_v)
            z = self.radius * -math.cos(angle_v)
            v = 2.0 * (i + 1) / self.segments

            for j in range(self.segments + 1):
                angle = delta_angle * j
                c = math.cos(angle)
                s = math.sin(angle)
                x = radius_h * c
                y = radius_h * s
                normal = Vec3(x, y, z).normalized()
                u = j / self.segments

                vdata_values.extend((x, y, z))
                vdata_values.extend(self.color)
                vdata_values.extend(normal)
                vdata_values.extend((u, v))

                # the vertex order of the quad vertices
                if i > 0 and j <= self.segments:
                    px = i * (self.segments + 1) + j + index_offset
                    prim_indices.extend((px, px - self.segments - 1, px - self.segments))
                    prim_indices.extend((px, px - self.segments, px + 1))

            vertex_count += self.segments + 1

        return vertex_count

    def create_top_pole(self, index_offset, vdata_values, prim_indices):
        vertex = (0.0, 0.0, self.radius)
        normal = (0.0, 0.0, 1.0)

        # the top pole vertices
        for i in range(self.segments):
            u = i / self.segments
            vdata_values.extend(vertex)
            vdata_values.extend(self.color)
            vdata_values.extend(normal)
            vdata_values.extend((u, 1.0))

            # the vertex order of the top pole vertices
            x = i + index_offset
            prim_indices.extend((x, x + 1, x + self.segments + 1))

        return self.segments

    def get_vertices(self, vdata_values, prim_indices):
        vertex_count = 0

        # create vertices of the bottom pole, quads, and top pole
        vertex_count += self.create_bottom_pole(vdata_values, prim_indices)
        vertex_count += self.create_quads(vertex_count, vdata_values, prim_indices)
        vertex_count += self.create_top_pole(vertex_count - self.segments - 1, vdata_values, prim_indices)

        return vertex_count


class CubeGeom(GeomRoot):
    """Create a geom node of cube.
        Arges:
            w (float): width; dimension along the x-axis; cannot be negative;
            d (float): depth; dimension along the y-axis; cannot be negative;
            h (float): height; dimension along the z-axis; cannot be negative;
            segs_w (int) the number of subdivisions in width;
            segs_d (int) the number of subdivisions in depth;
            segs_h (int) the number of subdivisions in height
    """

    def __init__(self, w=1.0, d=1.0, h=1.0, segs_w=2, segs_d=2, segs_h=2):
        self.w = w
        self.d = d
        self.h = h
        self.segs_w = segs_w
        self.segs_d = segs_d
        self.segs_h = segs_h
        self.color = (1, 1, 1, 1)
        super().__init__()

    def get_vertices(self, vdata_values, prim_indices):
        vertex_count = 0
        vertex = Point3()
        segs = (self.segs_w, self.segs_d, self.segs_h)
        dims = (self.w, self.d, self.h)

        # (fixed, outer loop, inner loop, normal, uv)
        side_idxes = [
            (2, 1, 0, 1, False),     # top
            (1, 0, 2, -1, False),    # front
            (0, 1, 2, 1, False),     # right
            (1, 0, 2, 1, True),      # back
            (0, 1, 2, -1, True),     # left
            (2, 1, 0, -1, False),    # bottom
        ]

        for a, (i0, i1, i2, n, reverse) in enumerate(side_idxes):
            segs1 = segs[i1]
            segs2 = segs[i2]
            dim1_start = dims[i1] * -0.5
            dim2_start = dims[i2] * -0.5

            normal = Vec3()
            normal[i0] = n
            vertex[i0] = dims[i0] * 0.5 * n

            for j in range(segs1 + 1):
                vertex[i1] = dim1_start + j / segs1 * dims[i1]
                v = j / segs1

                for k in range(segs2 + 1):
                    vertex[i2] = dim2_start + k / segs2 * dims[i2]
                    u = k / segs2
                    vdata_values.extend(vertex)
                    vdata_values.extend(self.color)
                    vdata_values.extend(normal)
                    vdata_values.extend((u, v))
                if j > 0:
                    for k in range(segs2):
                        idx = vertex_count + j * (segs2 + 1) + k
                        prim_indices.extend((idx, idx - segs2 - 1, idx - segs2))
                        prim_indices.extend((idx, idx - segs2, idx + 1))

            vertex_count += (segs1 + 1) * (segs2 + 1)

        return vertex_count


class TriangularPrismGeom(GeomRoot):
    """Create a geom node of cube.
        Arges:
            side (float) : side of triangle; cannot be negative;
            h (float): height; dimension along the z-axis; cannot be negative;
            segs_h (int) the number of subdivisions in height
    """

    def __init__(self, side=1.0, h=1.0, segs_h=2):
        self.side = side
        self.h = h
        self.segs_h = segs_h
        self.color = (1, 1, 1, 1)
        super().__init__()

    def create_caps(self, points, index_offset, vdata_values, prim_indices):
        vertex_count = 0
        normal = (0, 0, 1) if all(pt.z > 0 for pt in points) else (0, 0, -1)
        v = 0

        for i, pt in enumerate(points):
            u = i / (len(points) - 1)
            vdata_values.extend(pt)
            vdata_values.extend(self.color)
            vdata_values.extend(normal)
            vdata_values.extend((u, v))
            vertex_count += 1

        prim_indices.extend((index_offset, index_offset + 2, index_offset + 1))

        return vertex_count

    def create_sides(self, sides, index_offset, vdata_values, prim_indices):
        vertex_count = 0
        vertex = Point3()
        segs_u = len(sides)

        for a, pts in enumerate(sides):
            pts_cnt = len(pts)

            if pts[0].y < 0 and pts[1].y < 0:
                normal = (0, -1, 0)
            elif pts[0].x > 0:
                normal = (1, 0, 0)
            elif pts[1].x < 0:
                normal = (-1, 0, 0)

            for i in range(self.segs_h + 1):
                v = i / self.segs_h
                vertex.z = -self.h / 2 + i / self.segs_h * self.h

                for j in range(pts_cnt):
                    pt = pts[j]
                    vertex.x, vertex.y = pt.x, pt.y
                    u = (a + j) / segs_u

                    vdata_values.extend(vertex)
                    vdata_values.extend(self.color)
                    vdata_values.extend(normal)
                    vdata_values.extend((u, v))
                    vertex_count += 1

                if i > 0:
                    idx = index_offset + i * (1 + 1)
                    prim_indices.extend((idx, idx - 2, idx - 1))
                    prim_indices.extend((idx, idx - 1, idx + 1))

            index_offset += pts_cnt * (self.segs_h + 1)

        return vertex_count

    def get_vertices(self, vdata_values, prim_indices):
        half_s = self.side / 2
        half_h = self.h / 2

        top = [
            Point3(0, half_s / math.sqrt(3) * 2, half_h),
            Point3(-half_s, -half_s / math.sqrt(3), half_h),
            Point3(half_s, -half_s / math.sqrt(3), half_h)
        ]
        bottom = [
            Point3(0, half_s / math.sqrt(3) * 2, -half_h),
            Point3(-half_s, -half_s / math.sqrt(3), -half_h),
            Point3(half_s, -half_s / math.sqrt(3), -half_h)
        ]

        sides = [
            (bottom[1], bottom[2]),
            (bottom[2], bottom[0]),
            (bottom[0], bottom[1]),
        ]

        vertex_count = 0
        vertex_count += self.create_caps(top, vertex_count, vdata_values, prim_indices)
        vertex_count += self.create_sides(sides, vertex_count, vdata_values, prim_indices)
        vertex_count += self.create_caps(bottom, vertex_count, vdata_values, prim_indices)

        return vertex_count