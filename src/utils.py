"""Serialize TALEA model parameters into MiniZinc .dzn files.

Each model has a declarative parameter schema. All models share a single
formatter; the original models may still pass positional tuples while the
3-30-300 models pass named dictionaries.
"""

import numpy as np
import pandas as pd


_BASE_ARRAYS = (
    'street_space', 'ext_space', 'green_space', 'num_areas',
    'num_trees', 'macro_factors', 'full_space',
)

_330300_MODELS = ('std_330300', 'std_330300_maxcoverage')
_330300_COMMON = (
    'len', 'top_k', 'alpha_yard', 'beta_streets', 'gamma_330300',
    'delta', 'tree_density_street', 'tree_density_yard',
    'canopy_density_street', 'canopy_density_yard',
) + _BASE_ARRAYS

_CRITERION_30 = (
    'n_rel_30', 'rel30_cell', 'rel30_area',
    'rel30_cell_share', 'rel30_required_canopy',
)

_MODEL_FIELDS = {
    'std': ('len', 'top_k', 'beta_streets', 'alpha_yard') + _BASE_ARRAYS,
    'diff': ('len', 'top_k', 'beta_streets', 'alpha_yard', 'alpha_uhei')
            + _BASE_ARRAYS + ('uhei',),
    'inverse_uhei': (
        'len', 'top_k', 'beta_streets', 'alpha_yard',
        'inverse_uhei_95p', 'inverse_uhei_5p',
    ) + _BASE_ARRAYS,
    'ndvi': (
        'len', 'top_k', 'beta_streets', 'alpha_yard',
        'ndvi_norm_max', 'ndvi_norm_min',
    ) + _BASE_ARRAYS + ('ndvi',),
    'std_330300': _330300_COMMON + (
        'n_rel_3', 'rel3_cell', 'rel3_area', 'rel3_count_req1',
        'rel3_count_req2', 'rel3_count_req3', 'rel3_deficit_area',
    ) + _CRITERION_30 + (
        'n_rel_300', 'rel300_cell', 'rel300_area',
        'rel300_gain_count', 'rel300_deficit_area',
        'rel3_offset', 'rel30_offset', 'rel300_offset',
    ),
    'std_330300_maxcoverage': _330300_COMMON + (
        'n_buildings_3', 'total_deficit_3', 'n_rel_3',
        'rel3_cell', 'rel3_building', 'rel3_offset', 'required_trees_3',
    ) + _CRITERION_30 + (
        'n_buildings_300', 'total_deficit_300', 'n_rel_300',
        'rel300_cell', 'rel300_building', 'rel300_offset',
    ),
}

_INTEGER_SCALARS = {
    'len', 'top_k', 'n_rel_3', 'n_rel_30', 'n_rel_300',
    'n_buildings_3', 'n_buildings_300', 'total_deficit_3',
    'total_deficit_300',
}
_INTEGER_ARRAYS = {
    'rel3_cell', 'rel3_area', 'rel3_count_req1', 'rel3_count_req2',
    'rel3_count_req3', 'rel3_building', 'rel3_offset',
    'required_trees_3', 'rel30_cell', 'rel30_area',
    'rel300_cell', 'rel300_area', 'rel300_gain_count',
    'rel300_building', 'rel300_offset', 'rel30_offset',
}


def _format_dzn_value(name, value):
    if isinstance(value, (list, tuple, np.ndarray, pd.Series)):
        cast = int if name in _INTEGER_ARRAYS else float
        return '[' + ', '.join(
            str(cast(v)) if cast is int else repr(float(v))
            for v in value
        ) + ']'
    if name in _INTEGER_SCALARS:
        return str(int(value))
    return repr(float(value))


def to_dzn(model, instance):
    """Serialize parameters for one model using its declared MiniZinc schema.

    The original models pass positional tuples; 3-30-300 models pass dicts.
    Model-specific relations are retained unchanged, including their order.
    """
    if model not in _MODEL_FIELDS:
        raise ValueError(f'Unknown MiniZinc model: {model}')

    fields = _MODEL_FIELDS[model]
    if isinstance(instance, dict):
        data = dict(instance)
    else:
        if model in _330300_MODELS:
            raise TypeError('Sparse 3-30-300 instances must be dictionaries')
        if len(instance) != len(fields):
            raise ValueError(f'{model} expects {len(fields)} parameters, got {len(instance)}')
        data = dict(zip(fields, instance))

    if model in _330300_MODELS:
        for n in (3, 30, 300):
            rel_cells = f'rel{n}_cell'
            if rel_cells in data:
                data.setdefault(f'n_rel_{n}', len(data[rel_cells]))

    missing = [name for name in fields if name not in data]
    if missing:
        raise ValueError(f'Missing MiniZinc parameters: {missing}')

    return '\n'.join(
        f'{name} = {_format_dzn_value(name, data[name])};'
        for name in fields
    ) + '\n'

def density_per_area(gdf_area, df_dens):
    """Compute population density in each grid cell by weighted intersection."""
    cells_values = gdf_area['id'].unique()
    num_cells = len(cells_values)
    df_out = pd.DataFrame(columns=['id', 'density'])
    for i in range(num_cells):
        temp_df = gdf_area.loc[gdf_area['id'] == cells_values[i]]
        tot_space = np.ceil(100 * temp_df.intersect_area_statistica.sum()) / 100
        tot_space = tot_space if tot_space <= 10000 else 10000.0
        temp_sum = 0
        for _, row in temp_df.iterrows():
            code = row['codice_area_statistica']
            temp_dens = df_dens[df_dens['Codice Area Statistica'] == code]
            density = float(temp_dens['Densità'].values[0])
            temp_sum += density * row['intersect_area_statistica']
        df_out.loc[len(df_out)] = [cells_values[i], temp_sum / tot_space]
    return df_out


def macro_factor_per_area(gdf_area, gdf_macro):
    """Compute area-weighted macro factors for each cell."""
    cells_values = gdf_area['id'].unique()
    num_cells = len(cells_values)
    out = np.zeros((num_cells, ), dtype=float)
    for i in range(num_cells):
        temp_df = gdf_area.loc[gdf_area['id'] == cells_values[i]]
        tot_space = np.ceil(100 * temp_df.intersect_area_statistica.sum()) / 100
        tot_space = tot_space if tot_space <= 10000 else 10000.0
        temp_sum = 0
        for row in temp_df.itertuples():
            temp_factor = gdf_macro[gdf_macro['codice_area_statistica'] == row.codice_area_statistica]['macro_utility_factor'].values[0]
            temp_sum += temp_factor * row.intersect_area_statistica
        out[i] = temp_sum / 10000
    return out


def full_space_per_area(gdf_area):
    """Compute the available area of each grid cell."""
    cells_values = gdf_area['id'].unique()
    num_cells = len(cells_values)
    out = np.zeros((num_cells, ), dtype=float)
    for i in range(num_cells):
        temp_df = gdf_area.loc[gdf_area['id'] == cells_values[i]]
        temp_sum = np.ceil(100 * temp_df.intersect_area_statistica.sum()) / 100
        out[i] = temp_sum if temp_sum <= 10000 else 10000.0
    return out


def csr_offsets(sorted_ids, n_groups):
    """Build 1-based MiniZinc CSR offsets from sorted group IDs."""
    counts = np.bincount(sorted_ids, minlength=n_groups + 1)[1:]
    offsets = np.concatenate(([1], 1 + np.cumsum(counts)))
    assert offsets[-1] == len(sorted_ids) + 1
    assert np.array_equal(np.repeat(np.arange(1, n_groups + 1), counts), sorted_ids)
    return offsets