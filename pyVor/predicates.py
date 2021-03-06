#!/usr/bin/env python3

"""This is a collection of linear predicate implementations."""

from pyVor.primitives import Matrix, Point, Vector


def ccw(*points, homogeneous=True):
    """tests if triangle a, b, c is oriented counterclockwise.

    Returns 1 if ccw, 0 if colinear, -1 if cw.

    Also does the scary analogous n-dimensional test, which
    essentially tests if, from the perspective of the last point,
    the other points appear to be well-oriented according
    to the (n-1)-dimensional test.
    """
    if not homogeneous:
        mtrx = Matrix(*[pt.lift(lambda v: 1).to_vector() for pt in points])
    else:
        mtrx = None
        for pt in points:
            if pt[-1] == 1:
                # We need at list one non-infinite point
                # for this to work normally
                mtrx = Matrix(*[pt.to_vector() for pt in points])
                break
    if mtrx is not None:
        return mtrx.sign_det()
    # If all points have 0 for extended homogeneous coordinate,
    # win by using the ccw test for one dimension higher:
    return ccw(*points,
               Point(*(0 for i in range(len(points[0]) - 1)), -1),
               homogeneous=False)


def incircle(*points, homogeneous=True):
    """Returns 1 if the last point is inside the circle defined by the other
    three, -1 if outside, and 0 if all cocircular.
    The points are interpreted as having extended homogenious
    coordinates unless homogeneous=False is passed.
    """

    if homogeneous:
        # The points already have homogeneous coordinates
        vectors = [pt.to_vector() for pt in points]
    else:
        # We'll give each point a homogeneous coordinate of 1
        vectors = [(pt.to_vector()).lift() for pt in points]

    tmp = []
    for v in vectors:
        if v[-1] == 0:
            v *= 1000000000
            v += Vector(*([0] * (len(v) - 1)), 1)
        tmp.append(v)
    vectors = tmp

    vectors = [vector.lift(lambda v: v[:-1].norm_squared())
               for vector in vectors]
    # At this point we could switch the last two elements of each
    # vector to get the matrix we want to test. But we can
    # also just use the fact that if you swap 2 rows of a
    # matrix, the sign of the determinant is flipped. So:
    return - Matrix(*vectors).sign_det()
