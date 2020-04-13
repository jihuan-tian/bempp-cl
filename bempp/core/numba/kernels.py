from bempp.api.utils.helpers import numba_decorate as _numba_decorate

import numba as _numba
import numpy as _np

M_INV_4PI = 1.0 / (4 * _np.pi)


def select_numba_kernels(operator_descriptor, mode="regular"):
    """Select the Numba kernels."""
    assembly_functions_singular = {
        "default_scalar": default_scalar_singular_kernel,
        "laplace_hypersingular": laplace_hypersingular_singular,
    }

    assembly_functions_regular = {
        "default_scalar": default_scalar_regular_kernel,
        "laplace_hypersingular": laplace_hypersingular_regular,
    }

    assembly_functions_sparse = {"default_sparse": default_sparse_kernel}

    kernel_functions_regular = {
        "laplace_single_layer": laplace_single_layer_regular,
        "laplace_double_layer": laplace_double_layer_regular,
        "laplace_adjoint_double_layer": laplace_adjoint_double_layer_regular,
        "helmholtz_single_layer": helmholtz_single_layer_regular,
    }

    kernel_functions_singular = {
        "laplace_single_layer": laplace_single_layer_singular,
        "laplace_double_layer": laplace_double_layer_singular,
        "laplace_adjoint_double_layer": laplace_adjoint_double_layer_singular,
        "helmholtz_single_layer": helmholtz_single_layer_singular,
    }

    kernel_functions_sparse = {"l2_identity": l2_identity_kernel}

    if mode == "regular":
        return (
            assembly_functions_regular[operator_descriptor.assembly_type],
            kernel_functions_regular[operator_descriptor.kernel_type],
        )
    elif mode == "singular":
        return (
            assembly_functions_singular[operator_descriptor.assembly_type],
            kernel_functions_singular[operator_descriptor.kernel_type],
        )
    elif mode == "sparse":
        return (
            assembly_functions_sparse[operator_descriptor.assembly_type],
            kernel_functions_sparse[operator_descriptor.kernel_type],
        )
    else:
        raise ValueError("mode must be one of 'singular', 'regular' or 'sparse'.")


@_numba.jit(
    nopython=True, parallel=False, error_model="numpy", fastmath=True, boundscheck=False
)
def get_global_points(grid_data, elements, local_points):
    """Get global points."""
    npoints = local_points.shape[1]
    nelements = len(elements)
    output = _np.empty((3, nelements * npoints), dtype=grid_data.vertices.dtype)
    for index, element in enumerate(elements):
        output[:, npoints * index : npoints * (1 + index)] = grid_data.local2global(
            element, local_points
        )
    return output


@_numba.jit(
    nopython=True, parallel=False, error_model="numpy", fastmath=True, boundscheck=False
)
def get_normals(grid_data, nrepetitions, elements, multipliers):
    """Get normals to be repeated n times per element."""
    output = _np.empty((3, nrepetitions * len(elements)), dtype=grid_data.normals.dtype)
    for index, element in enumerate(elements):
        for dim in range(3):
            for n in range(nrepetitions):
                output[dim, nrepetitions * index + n] = (
                    grid_data.normals[element, dim] * multipliers[element]
                )

    return output


@_numba.jit(
    nopython=True, parallel=False, error_model="numpy", fastmath=True, boundscheck=False
)
def elements_adjacent(elements, index1, index2):
    """Check if two elements are adjacent."""
    return (
        elements[0, index1] == elements[0, index2]
        or elements[0, index1] == elements[1, index2]
        or elements[0, index1] == elements[2, index2]
        or elements[1, index1] == elements[0, index2]
        or elements[1, index1] == elements[1, index2]
        or elements[1, index1] == elements[2, index2]
        or elements[2, index1] == elements[0, index2]
        or elements[2, index1] == elements[1, index2]
        or elements[2, index1] == elements[2, index2]
    )


@_numba.jit(
    nopython=True, parallel=False, error_model="numpy", fastmath=True, boundscheck=False
)
def laplace_single_layer_regular(
    test_point, trial_points, test_normal, trial_normals, kernel_parameters
):
    """Laplace single layer for regular kernels."""
    npoints = trial_points.shape[1]
    dtype = trial_points.dtype
    output = _np.zeros(npoints, dtype=dtype)
    m_inv_4pi = dtype.type(M_INV_4PI)
    for i in range(3):
        for j in range(npoints):
            output[j] += (trial_points[i, j] - test_point[i]) ** 2
    for j in range(npoints):
        output[j] = m_inv_4pi / _np.sqrt(output[j])
    return output


@_numba.jit(
    nopython=True, parallel=False, error_model="numpy", fastmath=True, boundscheck=False
)
def laplace_double_layer_regular(
    test_point, trial_points, test_normal, trial_normals, kernel_parameters
):
    """Laplace double layer for regular kernels."""
    npoints = trial_points.shape[1]
    dtype = trial_points.dtype
    output = _np.zeros(npoints, dtype=dtype)
    diff = _np.empty((3, npoints), dtype=dtype)
    dist = _np.zeros(npoints, dtype=dtype)
    m_inv_4pi = dtype.type(M_INV_4PI)
    for i in range(3):
        for j in range(npoints):
            diff[i, j] = trial_points[i, j] - test_point[i]
            dist[j] += diff[i, j] * diff[i, j]
    for j in range(npoints):
        dist[j] = _np.sqrt(dist[j])
    for i in range(3):
        for j in range(npoints):
            output[j] += diff[i, j] * trial_normals[i, j]
    for j in range(npoints):
        output[j] *= -m_inv_4pi / (dist[j] * dist[j] * dist[j])
    return output


@_numba.jit(
    nopython=True, parallel=False, error_model="numpy", fastmath=True, boundscheck=False
)
def laplace_adjoint_double_layer_regular(
    test_point, trial_points, test_normal, trial_normals, kernel_parameters
):
    """Laplace adjoint double layer for regular kernels."""
    npoints = trial_points.shape[1]
    dtype = trial_points.dtype
    output = _np.zeros(npoints, dtype=dtype)
    diff = _np.empty((3, npoints), dtype=dtype)
    dist = _np.zeros(npoints, dtype=dtype)
    m_inv_4pi = dtype.type(M_INV_4PI)
    for i in range(3):
        for j in range(npoints):
            diff[i, j] = trial_points[i, j] - test_point[i]
            dist[j] += diff[i, j] * diff[i, j]
    for j in range(npoints):
        dist[j] = _np.sqrt(dist[j])
    for i in range(3):
        for j in range(npoints):
            output[j] += diff[i, j] * test_normal[i]
    for j in range(npoints):
        output[j] *= m_inv_4pi / (dist[j] * dist[j] * dist[j])
    return output


@_numba.jit(
    nopython=True, parallel=False, error_model="numpy", fastmath=True, boundscheck=False
)
def laplace_single_layer_singular(
    test_points, trial_points, test_normals, trial_normals, kernel_parameters
):
    """Laplace single layer for singular kernels."""
    npoints = trial_points.shape[1]
    dtype = trial_points.dtype
    output = _np.zeros(npoints, dtype=dtype)
    m_inv_4pi = dtype.type(M_INV_4PI)
    for i in range(3):
        for j in range(npoints):
            output[j] += (trial_points[i, j] - test_points[i, j]) ** 2
    for j in range(npoints):
        output[j] = m_inv_4pi / _np.sqrt(output[j])
    return output


@_numba.jit(
    nopython=True, parallel=False, error_model="numpy", fastmath=True, boundscheck=False
)
def laplace_double_layer_singular(
    test_points, trial_points, test_normals, trial_normals, kernel_parameters
):
    """Laplace double layer for singular kernels."""
    npoints = trial_points.shape[1]
    dtype = trial_points.dtype
    output = _np.zeros(npoints, dtype=dtype)
    diff = _np.empty((3, npoints), dtype=dtype)
    dist = _np.zeros(npoints, dtype=dtype)
    m_inv_4pi = dtype.type(M_INV_4PI)
    for i in range(3):
        for j in range(npoints):
            diff[i, j] = trial_points[i, j] - test_points[i, j]
            dist[j] += diff[i, j] * diff[i, j]
    for j in range(npoints):
        dist[j] = _np.sqrt(dist[j])
    for i in range(3):
        for j in range(npoints):
            output[j] += diff[i, j] * trial_normals[i, j]
    for j in range(npoints):
        output[j] *= -m_inv_4pi / (dist[j] * dist[j] * dist[j])
    return output


@_numba.jit(
    nopython=True, parallel=False, error_model="numpy", fastmath=True, boundscheck=False
)
def laplace_adjoint_double_layer_singular(
    test_points, trial_points, test_normals, trial_normals, kernel_parameters
):
    """Laplace adjoint double layer for singular kernels."""
    npoints = trial_points.shape[1]
    dtype = trial_points.dtype
    output = _np.zeros(npoints, dtype=dtype)
    diff = _np.empty((3, npoints), dtype=dtype)
    dist = _np.zeros(npoints, dtype=dtype)
    m_inv_4pi = dtype.type(M_INV_4PI)
    for i in range(3):
        for j in range(npoints):
            diff[i, j] = trial_points[i, j] - test_points[i, j]
            dist[j] += diff[i, j] * diff[i, j]
    for j in range(npoints):
        dist[j] = _np.sqrt(dist[j])
    for i in range(3):
        for j in range(npoints):
            output[j] += diff[i, j] * test_normals[i, j]
    for j in range(npoints):
        output[j] *= m_inv_4pi / (dist[j] * dist[j] * dist[j])
    return output


@_numba.jit(
    nopython=True, parallel=False, error_model="numpy", fastmath=True, boundscheck=False
)
def helmholtz_single_layer_regular(
    test_point, trial_points, test_normal, trial_normals, kernel_parameters
):
    """Helmholtz single layer for regular kernels."""
    wavenumber_real = kernel_parameters[0]
    wavenumber_imag = kernel_parameters[1]
    npoints = trial_points.shape[1]
    dtype = trial_points.dtype
    rad = _np.zeros(npoints, dtype=dtype)
    output_real = _np.zeros(npoints, dtype=dtype)
    output_imag = _np.zeros(npoints, dtype=dtype)
    m_inv_4pi = dtype.type(M_INV_4PI)
    for i in range(3):
        for j in range(npoints):
            rad[j] += (trial_points[i, j] - test_point[i]) ** 2
    for j in range(npoints):
        rad[j] = _np.sqrt(rad[j])
    for j in range(npoints):
        output_real[j] = _np.cos(wavenumber_real * rad[j]) * m_inv_4pi / rad[j]
        output_imag[j] = _np.sin(wavenumber_real * rad[j]) * m_inv_4pi / rad[j]
    if wavenumber_imag != 0:
        for j in range(npoints):
            output_real[j] *= _np.exp(-wavenumber_imag * rad[j])
            output_imag[j] *= _np.exp(-wavenumber_imag * rad[j])
    return output_real + 1j * output_imag


@_numba.jit(
    nopython=True, parallel=False, error_model="numpy", fastmath=True, boundscheck=False
)
def helmholtz_single_layer_singular(
    test_points, trial_points, test_normal, trial_normals, kernel_parameters
):
    """Helmholtz single layer for regular kernels."""
    wavenumber_real = kernel_parameters[0]
    wavenumber_imag = kernel_parameters[1]
    npoints = trial_points.shape[1]
    dtype = trial_points.dtype
    rad = _np.zeros(npoints, dtype=dtype)
    output_real = _np.zeros(npoints, dtype=dtype)
    output_imag = _np.zeros(npoints, dtype=dtype)
    m_inv_4pi = dtype.type(M_INV_4PI)
    for i in range(3):
        for j in range(npoints):
            rad[j] += (trial_points[i, j] - test_points[i, j]) ** 2
    for j in range(npoints):
        rad[j] = _np.sqrt(rad[j])
    for j in range(npoints):
        output_real[j] = _np.cos(wavenumber_real * rad[j]) * m_inv_4pi / rad[j]
        output_imag[j] = _np.sin(wavenumber_real * rad[j]) * m_inv_4pi / rad[j]
    if wavenumber_imag != 0:
        for j in range(npoints):
            output_real[j] *= _np.exp(-wavenumber_imag * rad[j])
            output_imag[j] *= _np.exp(-wavenumber_imag * rad[j])
    return output_real + 1j * output_imag


@_numba.jit(
    nopython=True, parallel=False, error_model="numpy", fastmath=True, boundscheck=False
)
def l2_identity_kernel(
    grid_data,
    nshape_test,
    nshape_trial,
    element_index,
    elements,
    quad_points,
    quad_weights,
    trial_normals,
    test_normals,
    test_shapeset,
    trial_shapeset,
    result,
):

    local_test_fun_values = test_shapeset(quad_points)
    local_trial_fun_values = trial_shapeset(quad_points)

    nshape = nshape_test * nshape_trial
    dimension = local_test_fun_values.shape[0]
    n_quad_points = local_test_fun_values.shape[2]
    element = elements[element_index]
    integration_element = grid_data.integration_elements[element]

    for test_index in range(nshape_test):
        for trial_index in range(nshape_trial):
            for dim_index in range(dimension):
                for quad_index in range(n_quad_points):
                    result[
                        nshape * element_index + test_index * nshape_trial + trial_index
                    ] += (
                        local_test_fun_values[dim_index, test_index, quad_index]
                        * local_trial_fun_values[dim_index, trial_index, quad_index]
                        * quad_weights[quad_index]
                        * integration_element
                    )


@_numba.jit(
    nopython=True, parallel=True, error_model="numpy", fastmath=True, boundscheck=False
)
def default_sparse_kernel(
    grid_data,
    nshape_test,
    nshape_trial,
    elements,
    quad_points,
    quad_weights,
    test_normal_multipliers,
    trial_normal_multipliers,
    test_shapeset,
    trial_shapeset,
    kernel_evaluator,
    result,
):
    result_type = result.dtype
    n_quad_points = len(quad_weights)
    trial_normals = get_normals(
        grid_data, n_quad_points, elements, trial_normal_multipliers
    )
    test_normals = get_normals(
        grid_data, n_quad_points, elements, test_normal_multipliers
    )

    nelements = len(elements)
    nshape = nshape_test * nshape_trial

    for element_index in _numba.prange(nelements):
        kernel_evaluator(
            grid_data,
            nshape_test,
            nshape_trial,
            element_index,
            elements,
            quad_points,
            quad_weights,
            trial_normals,
            test_normals,
            test_shapeset,
            trial_shapeset,
            result,
        )


@_numba.jit(
    nopython=True, parallel=True, error_model="numpy", fastmath=True, boundscheck=False
)
def default_scalar_regular_kernel(
    test_grid_data,
    trial_grid_data,
    nshape_test,
    nshape_trial,
    test_elements,
    trial_elements,
    test_multipliers,
    trial_multipliers,
    test_global_dofs,
    trial_global_dofs,
    test_normal_multipliers,
    trial_normal_multipliers,
    quad_points,
    quad_weights,
    kernel_evaluator,
    kernel_parameters,
    grids_identical,
    test_shapeset,
    trial_shapeset,
    result,
):
    # Compute global points
    dtype = test_grid_data.vertices.dtype
    result_type = result.dtype
    n_quad_points = len(quad_weights)
    n_test_elements = len(test_elements)
    n_trial_elements = len(trial_elements)

    local_test_fun_values = test_shapeset(quad_points)
    local_trial_fun_values = trial_shapeset(quad_points)
    trial_normals = get_normals(
        trial_grid_data, n_quad_points, trial_elements, trial_normal_multipliers
    )
    trial_global_points = get_global_points(
        trial_grid_data, trial_elements, quad_points
    )

    factors = _np.empty(
        n_quad_points * n_trial_elements, dtype=trial_global_points.dtype
    )
    for trial_element_index in range(n_trial_elements):
        for trial_point_index in range(n_quad_points):
            factors[n_quad_points * trial_element_index + trial_point_index] = (
                quad_weights[trial_point_index]
                * trial_grid_data.integration_elements[
                    trial_elements[trial_element_index]
                ]
            )

    for i in _numba.prange(n_test_elements):
        test_element = test_elements[i]
        local_result = _np.zeros(
            (n_trial_elements, nshape_test, nshape_trial), dtype=result_type
        )
        test_global_points = test_grid_data.local2global(test_element, quad_points)
        test_normal = test_grid_data.normals[test_element]
        local_factors = _np.empty(
            n_trial_elements * n_quad_points, dtype=test_global_points.dtype
        )
        tmp = _np.empty(n_trial_elements * n_quad_points, dtype=result_type)
        is_adjacent = _np.zeros(n_trial_elements, dtype=_np.bool_)

        for trial_element_index in range(n_trial_elements):
            trial_element = trial_elements[trial_element_index]
            if grids_identical and elements_adjacent(
                test_grid_data.elements, test_element, trial_element
            ):
                is_adjacent[trial_element_index] = True

        for index in range(n_trial_elements * n_quad_points):
            local_factors[index] = (
                factors[index] * test_grid_data.integration_elements[test_element]
            )
        for test_point_index in range(n_quad_points):
            test_global_point = test_global_points[:, test_point_index]
            kernel_values = kernel_evaluator(
                test_global_point,
                trial_global_points,
                test_normal,
                trial_normals,
                kernel_parameters,
            )
            for index in range(n_trial_elements * n_quad_points):
                tmp[index] = kernel_values[index] * (
                    local_factors[index] * quad_weights[test_point_index]
                )

            for trial_element_index in range(n_trial_elements):
                if is_adjacent[trial_element_index]:
                    continue
                trial_element = trial_elements[trial_element_index]
                for test_fun_index in range(nshape_test):
                    for trial_fun_index in range(nshape_trial):
                        for quad_point_index in range(n_quad_points):
                            local_result[
                                trial_element_index, test_fun_index, trial_fun_index
                            ] += (
                                tmp[
                                    trial_element_index * n_quad_points
                                    + quad_point_index
                                ]
                                * local_trial_fun_values[
                                    0, trial_fun_index, quad_point_index
                                ]
                                * local_test_fun_values[
                                    0, test_fun_index, test_point_index
                                ]
                            )

        for trial_element_index in range(n_trial_elements):
            trial_element = trial_elements[trial_element_index]
            for test_fun_index in range(nshape_test):
                for trial_fun_index in range(nshape_trial):
                    result[
                        test_global_dofs[test_element, test_fun_index],
                        trial_global_dofs[trial_element, trial_fun_index],
                    ] += (
                        local_result[
                            trial_element_index, test_fun_index, trial_fun_index
                        ]
                        * test_multipliers[test_element, test_fun_index]
                        * trial_multipliers[trial_element, trial_fun_index]
                    )


@_numba.jit(
    nopython=True, parallel=True, error_model="numpy", fastmath=True, boundscheck=False
)
def laplace_hypersingular_regular(
    test_grid_data,
    trial_grid_data,
    nshape_test,
    nshape_trial,
    test_elements,
    trial_elements,
    test_multipliers,
    trial_multipliers,
    test_global_dofs,
    trial_global_dofs,
    test_normal_multipliers,
    trial_normal_multipliers,
    quad_points,
    quad_weights,
    kernel_evaluator,
    kernel_parameters,
    grids_identical,
    test_shapeset,
    trial_shapeset,
    result,
):
    # Compute global points
    dtype = test_grid_data.vertices.dtype
    result_type = result.dtype
    n_quad_points = len(quad_weights)
    n_test_elements = len(test_elements)
    n_trial_elements = len(trial_elements)

    local_test_fun_values = test_shapeset(quad_points)
    local_trial_fun_values = trial_shapeset(quad_points)
    trial_normals = get_normals(
        trial_grid_data, n_quad_points, trial_elements, trial_normal_multipliers
    )
    trial_global_points = get_global_points(
        trial_grid_data, trial_elements, quad_points
    )

    factors = _np.empty(
        n_quad_points * n_trial_elements, dtype=trial_global_points.dtype
    )
    for trial_element_index in range(n_trial_elements):
        for trial_point_index in range(n_quad_points):
            factors[n_quad_points * trial_element_index + trial_point_index] = (
                quad_weights[trial_point_index]
                * trial_grid_data.integration_elements[
                    trial_elements[trial_element_index]
                ]
            )

    reference_gradient = _np.array([[-1, 1, 0], [-1, 0, 1]], dtype=dtype)

    test_surface_curls_trans = _np.empty((n_test_elements, 3, 3), dtype=dtype)
    trial_surface_curls = _np.empty((n_trial_elements, 3, 3), dtype=dtype)

    for test_index in range(n_test_elements):
        test_element = test_elements[test_index]
        test_surface_gradients = (
            test_grid_data.jac_inv_trans[test_element] @ reference_gradient
        )
        for i in range(3):
            test_surface_curls_trans[test_index, i, :] = (
                _np.cross(
                    test_grid_data.normals[test_element], test_surface_gradients[:, i]
                )
                * test_multipliers[test_element]
            )

    for trial_index in range(n_trial_elements):
        trial_element = trial_elements[trial_index]
        trial_surface_gradients = (
            trial_grid_data.jac_inv_trans[trial_element] @ reference_gradient
        )
        for i in range(3):
            trial_surface_curls[trial_index, :, i] = (
                _np.cross(
                    trial_grid_data.normals[trial_element],
                    trial_surface_gradients[:, i],
                )
                * trial_multipliers[trial_element]
            )

    for i in _numba.prange(n_test_elements):
        test_element = test_elements[i]
        local_result = _np.zeros(
            (n_trial_elements, nshape_test, nshape_trial), dtype=result_type
        )
        test_global_points = test_grid_data.local2global(test_element, quad_points)
        test_normal = test_grid_data.normals[test_element]
        local_factors = _np.empty(
            n_trial_elements * n_quad_points, dtype=test_global_points.dtype
        )
        tmp = _np.empty(
            n_trial_elements * n_quad_points, dtype=test_global_points.dtype
        )
        is_adjacent = _np.zeros(n_trial_elements, dtype=_np.bool_)

        for trial_element_index in range(n_trial_elements):
            trial_element = trial_elements[trial_element_index]
            if grids_identical and elements_adjacent(
                test_grid_data.elements, test_element, trial_element
            ):
                is_adjacent[trial_element_index] = True

        for index in range(n_trial_elements * n_quad_points):
            local_factors[index] = (
                factors[index] * test_grid_data.integration_elements[test_element]
            )
        for test_point_index in range(n_quad_points):
            test_global_point = test_global_points[:, test_point_index]
            kernel_values = kernel_evaluator(
                test_global_point,
                trial_global_points,
                test_normal,
                trial_normals,
                kernel_parameters,
            )
            for index in range(n_trial_elements * n_quad_points):
                tmp[index] = (
                    local_factors[index]
                    * kernel_values[index]
                    * quad_weights[test_point_index]
                )

            for trial_element_index in range(n_trial_elements):
                if is_adjacent[trial_element_index]:
                    continue
                trial_element = trial_elements[trial_element_index]
                curl_product = (
                    test_surface_curls_trans[i]
                    @ trial_surface_curls[trial_element_index]
                )
                for test_fun_index in range(nshape_test):
                    for trial_fun_index in range(nshape_trial):
                        for quad_point_index in range(n_quad_points):
                            local_result[
                                trial_element_index, test_fun_index, trial_fun_index
                            ] += (
                                tmp[
                                    trial_element_index * n_quad_points
                                    + quad_point_index
                                ]
                                * curl_product[test_fun_index, trial_fun_index]
                            )

        for trial_element_index in range(n_trial_elements):
            trial_element = trial_elements[trial_element_index]
            for test_fun_index in range(nshape_test):
                for trial_fun_index in range(nshape_trial):
                    result[
                        test_global_dofs[test_element, test_fun_index],
                        trial_global_dofs[trial_element, trial_fun_index],
                    ] += (
                        local_result[
                            trial_element_index, test_fun_index, trial_fun_index
                        ]
                        * test_multipliers[test_element, test_fun_index]
                        * trial_multipliers[trial_element, trial_fun_index]
                    )


@_numba.jit(
    nopython=True, parallel=True, error_model="numpy", fastmath=True, boundscheck=False
)
def default_scalar_singular_kernel(
    grid_data,
    test_points,
    trial_points,
    quad_weights,
    test_elements,
    trial_elements,
    test_offsets,
    trial_offsets,
    weights_offsets,
    number_of_quad_points,
    test_normal_multipliers,
    trial_normal_multipliers,
    nshape_test,
    nshape_trial,
    test_shapeset,
    trial_shapeset,
    kernel_evaluator,
    kernel_parameters,
    result,
):
    """Singular evaluator."""

    dtype = grid_data.vertices.dtype
    nelements = len(test_elements)

    for index in _numba.prange(nelements):
        test_element = test_elements[index]
        trial_element = trial_elements[index]
        test_offset = test_offsets[index]
        trial_offset = trial_offsets[index]
        weights_offset = weights_offsets[index]
        npoints = number_of_quad_points[index]
        test_local_points = test_points[:, test_offset : test_offset + npoints]
        trial_local_points = trial_points[:, trial_offset : trial_offset + npoints]
        test_global_points = grid_data.local2global(test_element, test_local_points)
        trial_global_points = grid_data.local2global(trial_element, trial_local_points)
        test_fun_values = test_shapeset(
            test_points[:, test_offset : test_offset + npoints]
        )
        trial_fun_values = trial_shapeset(
            trial_points[:, trial_offset : trial_offset + npoints]
        )
        test_normals = get_normals(
            grid_data, npoints, [test_element], test_normal_multipliers
        )
        trial_normals = get_normals(
            grid_data, npoints, [trial_element], trial_normal_multipliers
        )
        kernel_values = kernel_evaluator(
            test_global_points,
            trial_global_points,
            test_normals,
            trial_normals,
            kernel_parameters,
        )
        for test_fun_index in range(nshape_test):
            for trial_fun_index in range(nshape_trial):
                for point_index in range(npoints):
                    result[
                        nshape_trial * nshape_test * index
                        + test_fun_index * nshape_trial
                        + trial_fun_index
                    ] += (
                        kernel_values[point_index]
                        * quad_weights[weights_offset + point_index]
                        * test_fun_values[0, test_fun_index, point_index]
                        * trial_fun_values[0, trial_fun_index, point_index]
                    )
                result[
                    nshape_trial * nshape_test * index
                    + test_fun_index * nshape_trial
                    + trial_fun_index
                ] *= (
                    grid_data.integration_elements[test_element]
                    * grid_data.integration_elements[trial_element]
                )


@_numba.jit(
    nopython=True, parallel=True, error_model="numpy", fastmath=True, boundscheck=False
)
def laplace_hypersingular_singular(
    grid_data,
    test_points,
    trial_points,
    quad_weights,
    test_elements,
    trial_elements,
    test_offsets,
    trial_offsets,
    weights_offsets,
    number_of_quad_points,
    test_normal_multipliers,
    trial_normal_multipliers,
    nshape_test,
    nshape_trial,
    test_shapeset,
    trial_shapeset,
    kernel_evaluator,
    kernel_parameters,
    result,
):
    """Singular evaluator."""

    dtype = grid_data.vertices.dtype
    nelements = len(test_elements)

    reference_gradient = _np.array([[-1, 1, 0], [-1, 0, 1]], dtype=dtype)

    for index in _numba.prange(nelements):
        test_element = test_elements[index]
        trial_element = trial_elements[index]
        test_offset = test_offsets[index]
        trial_offset = trial_offsets[index]
        weights_offset = weights_offsets[index]
        npoints = number_of_quad_points[index]
        test_local_points = test_points[:, test_offset : test_offset + npoints]
        trial_local_points = trial_points[:, trial_offset : trial_offset + npoints]
        test_global_points = grid_data.local2global(test_element, test_local_points)
        trial_global_points = grid_data.local2global(trial_element, trial_local_points)
        test_fun_values = test_shapeset(
            test_points[:, test_offset : test_offset + npoints]
        )
        trial_fun_values = trial_shapeset(
            trial_points[:, trial_offset : trial_offset + npoints]
        )

        test_surface_gradient = (
            grid_data.jac_inv_trans[test_element] @ reference_gradient
        )
        trial_surface_gradient = (
            grid_data.jac_inv_trans[trial_element] @ reference_gradient
        )

        test_normal = (
            grid_data.normals[test_element] * test_normal_multipliers[test_element]
        )
        trial_normal = (
            grid_data.normals[trial_element] * trial_normal_multipliers[trial_element]
        )

        test_surface_curl_trans = _np.empty((3, 3), dtype=dtype)
        trial_surface_curl = _np.empty((3, 3), dtype=dtype)

        for fun_index in range(3):
            test_surface_curl_trans[fun_index, :] = _np.cross(
                test_normal, test_surface_gradient[:, fun_index]
            )
            trial_surface_curl[:, fun_index] = _np.cross(
                trial_normal, trial_surface_gradient[:, fun_index]
            )

        surface_curl_products = test_surface_curl_trans @ trial_surface_curl

        kernel_values = kernel_evaluator(
            test_global_points,
            trial_global_points,
            test_normal,
            trial_normal,
            kernel_parameters,
        )

        for test_fun_index in range(nshape_test):
            for trial_fun_index in range(nshape_trial):
                for point_index in range(npoints):
                    result[
                        nshape_trial * nshape_test * index
                        + test_fun_index * nshape_trial
                        + trial_fun_index
                    ] += (
                        kernel_values[point_index]
                        * quad_weights[weights_offset + point_index]
                    )
                result[
                    nshape_trial * nshape_test * index
                    + test_fun_index * nshape_trial
                    + trial_fun_index
                ] *= (
                    grid_data.integration_elements[test_element]
                    * grid_data.integration_elements[trial_element]
                    * surface_curl_products[test_fun_index, trial_fun_index]
                )