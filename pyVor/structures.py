# !/usr/bin/env python3

"""Data structures. Enough said."""

from random import shuffle
# We could seed with /dev/urandom, but
# "O(n log(n)) for PPT adversaries" is not an important feature
from pyVor.primitives import Point
from pyVor.predicates import ccw, incircle
from pyVor.utils import circumcenter


def outer_face_pts(dimension):
    """Get some points whose simplex contains all of R^{dimension}

    This ought to be a triangulation method, I guess.
    But I'm leaving it here for now.

    (This is all the standard basis vectors, plus the vector of all -1s. Er,
    but points, not vectors.)
    """
    coords = [0] * (dimension + 1)
    results = []
    for i in range(dimension):
        # Generate a standard basis vector
        coords[i] = 1
        results.append(Point(*coords))
        coords[i] = 0
    results.append(Point(*(-1 for i in range(dimension)), 0))
    return results


class GeneralPositionError(Exception):
    """For when the input isn't in general position.

    Obviously it's better to handle the input properly. This is a stand-in.
    """
    def __init__(self, *args):
        super().__init__("Points not in general position", *args)


class DelaunayTriangulation:
    """A Delaunay triangulation of a finite point set."""

    class Vertex:
        """Vertices of the simplicial complex, with an order imposed.

        Incidence is not implemented at this time. I doubt it will be.

        Never reassign the point attribute, since you'll change the hash.
        """
        def __init__(self, point):
            if not isinstance(point, Point):
                raise ValueError
            self.point = point

        def __gt__(self, other):
            # return hash(self) > hash(other)
            return other < self

        def __lt__(self, other):
            """Lexicographic comparator"""
            for mine, theirs in zip(self.point, other.point):
                if mine == theirs:
                    continue
                return mine < theirs
            return False

        def __le__(self, other):
            # return hash(self) <= hash(other)
            return (self.point == other.point or
                    self < other)

        def __ge__(self, other):
            # return hash(self) >= hash(other)
            return other < self

        def __str__(self):
            """Return a string representation of this Vertex"""
            return 'Vertex({})'.format(str(self.point))

        # def __eq__(self, other):  # I'd prefer pointer comparison
        #    return self.point == other.point

        def __hash__(self):
            return hash(self.point)

    class Face:
        """The best faces you've ever seen"""

        def __init__(self, vertices, initial_half_facets=None):
            self.vertices = frozenset(vertices)
            self.half_facets = initial_half_facets or {}
            for vertex in self.vertices:
                if vertex in self.half_facets:
                    # Make sure all the halffacets have self as a face
                    self.half_facets[vertex].change_face(vertex, self)
                else:
                    self.half_facets[vertex] = DelaunayTriangulation.HalfFacet(
                        vertex,
                        [vert for vert in self.vertices if vert != vertex],
                        self)
            # self.vertices = set(self.vertices)  # my new favorite data type

        def __str__(self):
            """ """
            s = ""
            for vert in self.vertices:
                s += str(vert.point) + ", "

            return s[:-2]

        def __repr__(self):
            return self.__str__()

        def points(self):
            """Iterate through the points.

            (If you want the vertices, just do self.vertices)
            """
            return [vert.point for vert in self.vertices]

        def iter_facets(self):
            """Iterate through the half-facets.

            Face.half_facets.values() should be replaced with this everywhere
            you see it.
            """
            return self.half_facets.values()

        def __hash__(self):
            """Hash, based only on the vertices contained here."""
            return hash(self.vertices)

    class HalfFacet:
        """Better than a Facet. Also, the pun is honestly by accident.

        Supports lineside, twin, iteration of points or vertices,
        and opposite (i.e. the vertex opposite this HF).
        """

        def __init__(self, opposite, vertices, face, twin=None):
            """Constructor. See class docstring"""
            self.face = face
            self._vertices = frozenset(vertices)  # could store implicitly
            self.opposite = opposite
            if twin and twin.side:
                # Save a little time.
                self.side = -1 * twin.side
            else:
                self.side = ccw(*self.points(), opposite.point)
            if self.side == 0:
                raise GeneralPositionError
            self.twin = twin

        def __hash__(self):
            return hash(self._vertices)

        def __eq__(self, other):
            return self.vertices() == other.vertices()

        def is_infinite(self):
            """Does the edge contain infinite points?"""
            points = self.points()
            for point in points:
                if point[-1] == 0:
                    return True
            return False

        def vertices(self):
            """get the vertices, which may be stored implicitly"""
            return self._vertices

        def points(self):
            """Get a list of points in this halffacet"""
            return [vert.point for vert in self.vertices()]

        def lineside(self, point):
            """Return 1, 0, or -1 respectively if the given point is:
            On the same side as self.opposite
            Co(hyper)planer with this facet
            On the other side of this facet
            """
            # Needs adjustment if we allow _side to be 0
            return ccw(*self.points(), point) * self.side

        def change_face(self, opposite, face):
            """Switch the incidence properties of this halffacet"""
            # Needs to be changed if we start allowing _side == 0
            # assert isinstance(opposite, DelaunayTriangulation.Vertex)
            self.opposite = opposite
            self.face = face

        def locally_delaunay(self, alt_vertex=None):
            """Return True if locally delaunay (including or not including
            weird boundary conditions (include for the first try))

            if no vertex given, use self.opposite

            Of course weird things will happen if the given vertex is on the
            wrong side.
            """
            if not self.twin:
                # We're bordering on the infinite, so to speak.
                return True
            if not alt_vertex:
                alt_vertex = self.opposite
            # Use self.twin.side to correct for the orientation of self.twin
            result = self.twin.side * incircle(
                *self.twin.points(), self.twin.opposite.point,
                alt_vertex.point)
            return result <= 0  # strict inequality might not halt, I think

        def __str__(self):
            return ':'.join([
                str(key) + str(value) for key, value in self.__dict__.items()
                if not isinstance(value, type(self))])

    def __init__(self, points, randomize=True, homogeneous=True,
                 # location_visualizer=None, draw_circle=None,
                 # draw_triangulation=None,
                 # highlight_edge=None,
                 gui=None):  # visualization=False, delete_edge=None

        """Construct the delaunay triangulation of the point list"""
        if not homogeneous:
            points = [pt.lift(lambda x: 1) for pt in points]
            homogeneous = True  # just for emphasis
        dimension = len(points[0]) - 1  # -1 because homogenous
        outer_face = [*map(self.Vertex, outer_face_pts(dimension))]
        # The resulting "outer face" contains every point in R^d
        self.faces = set([self.Face(outer_face)])
        self.vertices = set(outer_face)
        self.facets = set()
        self.gui = gui
        # self.gui.draw_point_locate = location_visualizer  # ???
        # self.gui.draw_circle = draw_circle
        # self.gui.draw_triangulation = draw_triangulation
        # self.gui.highlight_edge = highlight_edge
        # self.gui.visualization = visualization
        # self.gui.delete_edge = delete_edge
        if randomize:
            shuffle(points)  # randomize this thing (in place)
        self.point_history = []  # per request of gui folks
        for point in points:
            self.delaunay_add(point)

    def __str__(self):
        """ Have the string representation be JSON """
        return str([[face] for face in self.faces])

    def __repr__(self):
        return self.__str__()

    def delaunay_add(self, point, homogeneous=True):
        """Add a point and then recover the delaunay property"""
        # print('\n{}'.format(len(self.faces)))
        if homogeneous is False:
            point = point.lift(lambda x: 1)
        if point in self.point_history:
            return
        self.point_history.append(point)
        # dead_face = self.locate(point)
        hf_stack = set(self._face_shatter(self.locate(point)))
        if self.gui and self.gui.visualization:
            for facet in hf_stack:
                if not facet.is_infinite():
                    self.gui.highlight_edge(facet)
        # already_processed = set()
        new_vert = self.Vertex(point)
        self.vertices.add(new_vert)
        # (bisect_left(self.vertices, new_vert), new_vert)
        ld_halffacets = set()  # locally delaunay halffacets
        while hf_stack:
            free_facet = hf_stack.pop()
            # if free_facet in already_processed:
            #     print('useful')  # Never got printed.
            #     continue
            # else:
            #     already_processed.add(free_facet)
            if free_facet.locally_delaunay(new_vert):
                ld_halffacets.add(free_facet)
                # Do gui things. This all ought to be refactored so that
                # we just return a list and the GUI decides what to do
                # with it.
                if (self.gui and self.gui.visualization and
                        free_facet.twin and not free_facet.is_infinite()):
                    self.gui.highlight_edge(free_facet, color="red",
                                            tag="highlight_edge", add=False)
                    self.gui.draw_circle(free_facet.twin.face, sleep=True)
            else:
                # Add them all to the queue/stack/stueue/quack
                if free_facet.twin.face not in self.faces:
                    continue
                facets = self._facet_pop(free_facet, free_facet.twin.face)
                hf_stack.update(facets)
                # More gui things
                if self.gui and self.gui.visualization:
                    for facet in facets:
                        if not facet.is_infinite():
                            self.gui.highlight_edge(facet)
                if (self.gui and self.gui.visualization and free_facet.twin and
                        not free_facet.is_infinite()):
                    self.gui.draw_triangulation(self)
                    self.gui.highlight_edge(free_facet, color="red",
                                            tag="highlight_edge", add=False)
                    self.gui.draw_circle(free_facet.twin.face, color="red",
                                         delete=True, sleep=True)
                    self.gui.delete_edge(free_facet)
            if self.gui and self.gui.visualization:
                self.gui.draw_triangulation(self, sleep=True)
        new_faces = []
        for halffacet in ld_halffacets:
            # I have to link up all these edges now
            new_faces.append(self.Face(
                [*halffacet.vertices(), new_vert],
                initial_half_facets={new_vert: halffacet}))
        # Now link the halffaces to their twins, by brute force
        for face_0 in new_faces:
            for face_1 in new_faces:  # j in range(i+1, len(new_faces)):
                diff = face_0.vertices.symmetric_difference(
                    face_1.vertices)
                if len(diff) == 2:
                    # Note that one vertex must be from each, since
                    # they have the same number of vertices
                    link_us = []
                    for vert in diff:
                        if vert in face_0.vertices:
                            link_us.append(face_0.half_facets[vert])
                        else:
                            link_us.append(face_1.half_facets[vert])
                    # Now link them
                    link_us[0].twin = link_us[1]
                    link_us[1].twin = link_us[0]
        # [face for face in new_faces if face not in self.faces])
        if self.gui and self.gui.visualization:
            self.gui.draw_triangulation(self, clear=True)
        self.faces.update(new_faces)

    def _face_shatter(self, face):
        """Remove a face from self.faces and return all of its HalfFacets.

        (We shall do science to them.)
        """
        self.faces.remove(face)  # constant time set operation win!
        return face.iter_facets()

    def _facet_pop(self, facet, fsopuwmcd=None):
        """Push a pin through the facet and out into the twin face, shattering
        facet.twin.face and also getting rid of facet and facet.twin.

        Or explicitly specify the face to shatter if you like.

        "face_so_other_people_understand_what_my_code_does" is the kwarg.
        """
        if not fsopuwmcd:
            fsopuwmcd = facet.twin.face
        return [fct for fct in self._face_shatter(fsopuwmcd) if fct !=
                facet.twin]

    def locate(self, point):
        """Point location with visibility walk"""
        not_done = True
        current_face = self._arbitrary_face()
        while not_done:
            if self.gui and self.gui.visualization:
                self.gui.draw_point_locate(current_face)
            not_done = False
            for halffacet in current_face.iter_facets():
                if halffacet.lineside(point) == -1:
                    current_face = halffacet.twin.face
                    not_done = True
                    break
        return current_face

    def test_is_delaunay(self):
        """Make sure every facet is locally delaunay."""
        for face in self.faces:
            for halffacet in face.iter_facets():
                if not halffacet.locally_delaunay():
                    # print(halffacet)
                    return False
        return True

    def face_point_sets(self, homogeneous=False):
        """Return a set containing a bunch of frozensets of points.

        Of course the frozensets represent the faces of the triangulation.
        """
        result = set()
        # hidden_vertices = frozenset(
        #   [self.Vertex(point) for point in outer_face_pts(self.dimension())])
        # for face in self.faces:
        #     if face.vertices.isdisjoint(hidden_vertices):
        #         result.add(frozenset([
        #             vert.point[slice(None) if homogeneous else slice(-1)]
        #             for vert in face.vertices]))
        #     else:
        #         print("It works a little")

        hidden_points = frozenset(outer_face_pts(self.dimension()))
        for face in self.faces:
            # [slice(None) if homogeneous else slice(-1)]
            subresult = frozenset([
                vert.point for vert in face.vertices])
            if hidden_points.isdisjoint(subresult):
                result.add(frozenset([
                    point[slice(None) if homogeneous else slice(-1)]
                    for point in subresult]))
        return result

    def dimension(self):
        """get the dimension in some standard way"""
        # -1 because homogeneous
        return len(next(iter(self.vertices)).point) - 1

    def _arbitrary_face(self):
        """Get an arbitrary face of the triangulation"""
        return next(iter(self.faces))  # Hideous

    # def set_visualize(self, val):
    #     self.gui.visualization = val

    def get_facets(self):
        """A getter, for whatever reason"""
        return self.facets

# _face_shatter delete face and return all facets of it. (As inner
# HalfFacets)

# face_pop(face, HalfFacet) - like face-shatter but one
# HalfFace is destroyed also (The image I have of this is like poking
# a pin into a Face through a certain facet.)

# def face_make(vertex, half_facet):
#     make the face defined by those two things and link everything all up
#     (Need to deal with linking the faces of the star together)

# half_facets solve the problem of storing an outer face. Nice.


class Voronoi:
    """A data structure primarily used for drawing the Voronoi diagram"""
    def __init__(self, triangulation):
        self.points = set()
        self.edges = set()
        finite_faces = (f for f in triangulation.faces if self._is_finite(f))
        for face in finite_faces:
            point = circumcenter(*face.points())
            self.points.add(point)
            for half_facet in face.iter_facets():
                if half_facet.twin:
                    adj_point = circumcenter(*half_facet.twin.face.points())
                    if not self._is_finite(half_facet.twin.face):
                        tmp_vec = ((adj_point.to_vector()[:-1]) *
                                   (1 / 1000000000))
                        adj_point = Point(*tmp_vec.to_array())
                        adj_point = adj_point.lift(lambda *args: 0)
                    self.edges.add(frozenset([point, adj_point]))

    def _is_finite(self, face):
        """Checks if the face is only made of finite points"""
        return [p[-1] for p in face.points()] == [1] * len(face.points())
