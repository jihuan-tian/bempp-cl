"""Various built-in test shapes."""

import numpy as _np

def get_gmsh_file():
    """
    Create a new temporary gmsh file.

    Return a 3-tuple (geo_file,geo_name,msh_name), where
    geo_file is a file descriptor to an empty .geo file, geo_name is
    the corresponding filename and msh_name is the name of the
    Gmsh .msh file that will be generated.

    """
    import os
    import tempfile
    import bempp.api

    geo, geo_name = tempfile.mkstemp(
        suffix='.geo', dir=bempp.api.TMP_PATH, text=True)
    geo_file = os.fdopen(geo, "w")
    msh_name = os.path.splitext(geo_name)[0] + ".msh"
    return (geo_file, geo_name, msh_name)


def __generate_grid_from_gmsh_string(gmsh_string):
    """Return a grid from a string containing a gmsh mesh"""
    import os
    import tempfile

    if bempp.api.mpi_rank == 0:
        # First create the grid.
        handle, fname = tempfile.mkstemp(
            suffix='.msh', dir=bempp.api.TMP_PATH, text=True)
        with os.fdopen(handle, "w") as f:
            f.write(gmsh_string)
    grid = bempp.api.import_grid(fname)
    bempp.api.mpi_comm.Barrier()
    if bempp.api.mpi_rank == 0:
        os.remove(fname)
    return grid


def __generate_grid_from_geo_string(geo_string):
    """Helper routine that implements the grid generation
    """
    import os
    import subprocess
    import bempp.api

    def msh_from_string(geo_string):
        """Create a mesh from a string."""
        gmsh_command = bempp.api.GMSH_PATH
        if gmsh_command is None:
            raise RuntimeError("Gmsh is not found. Cannot generate mesh")
        f, geo_name, msh_name = get_gmsh_file()
        f.write(geo_string)
        f.close()

        fnull = open(os.devnull, 'w')
        cmd = gmsh_command + " -2 " + geo_name
        try:
            subprocess.check_call(
                cmd, shell=True, stdout=fnull, stderr=fnull)
        except:
            print("The following command failed: " + cmd)
            fnull.close()
            raise
        os.remove(geo_name)
        fnull.close()
        return msh_name

    msh_name = msh_from_string(geo_string)
    grid = bempp.api.import_grid(msh_name)
    os.remove(msh_name)
    return grid

def regular_sphere(refine_level):
    """
    Create a regular sphere with a given refinement level.

    Starting from an octahedron with 8 elements the grid is
    refined in each step by subdividing each element into
    four new elements, to create a sphere approximation.

    The number of elements in the final sphere is given as
    8 * 4**refine_level.

    The maximum allowed refinement level is 9.

    """
    from bempp.api.grid.grid import Grid
    import os
    import numpy as np

    if refine_level > 9:
        raise ValueError("'refine_level larger than 9 not supported.")

    filename = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), "regular_spheres.npz"
    )

    spheres = np.load(filename)
    return Grid(spheres["v" + str(refine_level)], spheres["e" + str(refine_level)])


def cube(length=1, origin=(0, 0, 0), h=0.1):
    """
    Return a cube mesh.

    Parameters
    ----------
    length : float
        Side length of the cube.
    origin : tuple
        Coordinates of the origin (bottom left corner)
    h : float
        Element size.

    """
    cube_stub = """
    Point(1) = {orig0,orig1,orig2,cl};
    Point(2) = {orig0+l,orig1,orig2,cl};
    Point(3) = {orig0+l,orig1+l,orig2,cl};
    Point(4) = {orig0,orig1+l,orig2,cl};
    Point(5) = {orig0,orig1,orig2+l,cl};
    Point(6) = {orig0+l,orig1,orig2+l,cl};
    Point(7) = {orig0+l,orig1+l,orig2+l,cl};
    Point(8) = {orig0,orig1+l,orig2+l,cl};

    Line(1) = {1,2};
    Line(2) = {2,3};
    Line(3) = {3,4};
    Line(4) = {4,1};
    Line(5) = {1,5};
    Line(6) = {2,6};
    Line(7) = {3,7};
    Line(8) = {4,8};
    Line(9) = {5,6};
    Line(10) = {6,7};
    Line(11) = {7,8};
    Line(12) = {8,5};

    Line Loop(1) = {-1,-4,-3,-2};
    Line Loop(2) = {1,6,-9,-5};
    Line Loop(3) = {2,7,-10,-6};
    Line Loop(4) = {3,8,-11,-7};
    Line Loop(5) = {4,5,-12,-8};
    Line Loop(6) = {9,10,11,12};

    Plane Surface(1) = {1};
    Plane Surface(2) = {2};
    Plane Surface(3) = {3};
    Plane Surface(4) = {4};
    Plane Surface(5) = {5};
    Plane Surface(6) = {6};

    Physical Surface(1) = {1};
    Physical Surface(2) = {2};
    Physical Surface(3) = {3};
    Physical Surface(4) = {4};
    Physical Surface(5) = {5};
    Physical Surface(6) = {6};

    Surface Loop (1) = {1,2,3,4,5,6};

    Volume (1) = {1};

    Mesh.Algorithm = 6;
    """

    cube_geometry = (
        "l = " + str(length) + ";\n" +
        "orig0 = " + str(origin[0]) + ";\n" +
        "orig1 = " + str(origin[1]) + ";\n" +
        "orig2 = " + str(origin[2]) + ";\n" +
        "cl = " + str(h) + ";\n" + cube_stub)

    return __generate_grid_from_geo_string(cube_geometry)

def multitrace_cube(h=.1):
    """
    Definitition of a cube with an interface at z=.5.

    The normal direction at the interface shows into the
    positive z-direction and has the domain index
    and has the domain index 11. The lower half of the cube 
    is given through the segments [1, 2, 3, 4, 5, 6]. The
    top half of the cube is defined by the segments
    [6, 7, 8, 9, 10, 11]. For the upper half the normal
    direction of segment 6 shows in the interior of the domain.
    """
    stub = """
    Point(1) = {0, 0.0, 0, cl};
    Point(2) = {1, 0, 0, cl};
    Point(3) = {1, 1, 0, cl};
    Point(4) = {0, 1, 0, cl};
    Point(5) = {1, 0, 1, cl};
    Point(6) = {0, 1, 1, cl};
    Point(7) = {1, 1, 1, cl};
    Point(8) = {0, 0, 1, cl};
    Point(9) = {1, 0, .5, cl};
    Point(10) = {0, 1, .5, cl};
    Point(11) = {1, 1, .5, cl};
    Point(12) = {0, 0, .5, cl};
    Line(1) = {8, 5};
    Line(3) = {2, 1};
    Line(5) = {6, 7};
    Line(7) = {3, 4};
    Line(9) = {7, 5};
    Line(10) = {6, 8};
    Line(11) = {3, 2};
    Line(12) = {4, 1};
    Line(13) = {12, 9};
    Line(14) = {9, 11};
    Line(15) = {11, 10};
    Line(16) = {10, 12};
    Line(17) = {2, 9};
    Line(18) = {3, 11};
    Line(19) = {11, 7};
    Line(20) = {9, 5};
    Line(21) = {4, 10};
    Line(22) = {1, 12};
    Line(23) = {12, 8};
    Line(24) = {10, 6};
    Line Loop(1) = {3, -12, -7, 11};
    Plane Surface(1) = {1};
    Line Loop(3) = {14, 19, 9, -20};
    Plane Surface(3) = {3};
    Line Loop(4) = {13, 20, -1, -23};
    Plane Surface(4) = {4};
    Line Loop(6) = {12, 22, -16, -21};
    Plane Surface(6) = {6};
    Line Loop(7) = {16, 23, -10, -24};
    Plane Surface(7) = {7};
    Line Loop(9) = {7, 21, -15, -18};
    Plane Surface(9) = {9};
    Line Loop(10) = {15, 24, 5, -19};
    Plane Surface(10) = {10};
    Line Loop(11) = {16, 13, 14, 15};
    Plane Surface(11) = {11};
    Line Loop(12) = {1, -9, -5, 10};
    Plane Surface(12) = {12};
    Line Loop(13) = {-3, 17, -13, -22};
    Plane Surface(13) = {13};
    Line Loop(14) = {-11, 18, -14, -17};
    Plane Surface(14) = {14};
    Physical Surface(1) = {6};
    Physical Surface(2) = {13};
    Physical Surface(3) = {14};
    Physical Surface(4) = {9};
    Physical Surface(5) = {1};
    Physical Surface(6) = {11};
    Physical Surface(7) = {3};
    Physical Surface(8) = {10};
    Physical Surface(9) = {7};
    Physical Surface(10) = {4};
    Physical Surface(11) = {12};
    """
    geometry = ("cl = " + str(h) + ";\n" + stub)
    return __generate_grid_from_geo_string(geometry)

def reference_triangle():
    """Return a grid consisting of only the reference triangle."""
    from bempp.api.grid.grid import Grid

    vertices = _np.array([
        [0, 0, 0],
        [1, 0, 0],
        [0, 1, 0]
        ]).T
    
    elements = _np.array([[0, 1, 2]]).T

    return Grid(vertices, elements) 

