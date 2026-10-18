import numpy as np
import pandas as pd

def to_dzn_330300(model, instance):
    """Serialize the 3-30-300 formats."""
    common = (
        'len', 'top_k', 'alpha_yard', 'beta_streets', 'gamma_330300',
        'delta', 'tree_density_street', 'tree_density_yard',
        'canopy_density_street', 'canopy_density_yard', 'street_space',
        'ext_space', 'green_space', 'num_areas', 'num_trees',
        'macro_factors', 'full_space',
    )
    criterion_30 = (
        'n_rel_30', 'rel30_cell', 'rel30_area',
        'rel30_cell_share', 'rel30_required_canopy',
    )
    if model == 'std_330300':
        fields = common + (
            'n_rel_3', 'rel3_cell', 'rel3_area', 'rel3_count_req1',
            'rel3_count_req2', 'rel3_count_req3', 'rel3_deficit_area',
            'n_rel_30', 'rel30_cell', 'rel30_area', 'rel30_cell_share',
            'rel30_required_canopy', 'n_rel_300', 'rel300_cell',
            'rel300_area', 'rel300_gain_count', 'rel300_deficit_area',
            'rel3_offset', 'rel30_offset', 'rel300_offset',
        )
    else:
        fields = common + (
            'n_buildings_3', 'total_deficit_3', 'n_rel_3', 'rel3_cell',
            'rel3_building', 'rel3_offset', 'required_trees_3',
        ) + criterion_30 + (
            'n_buildings_300', 'total_deficit_300', 'n_rel_300',
            'rel300_cell', 'rel300_building', 'rel300_offset',
        )
    if not isinstance(instance, dict):
        raise TypeError('Sparse 3-30-300 instances must be dictionaries')
    data = dict(instance)
    for n in (3, 30, 300):
        data.setdefault(f'n_rel_{n}', len(data[f'rel{n}_cell']))
    missing = [field for field in fields if field not in data]
    if missing:
        raise ValueError(f'Missing MiniZinc parameters: {missing}')
    integer_scalars = {
        'len', 'top_k', 'n_rel_3', 'n_rel_30', 'n_rel_300',
        'n_buildings_3', 'n_buildings_300', 'total_deficit_3',
        'total_deficit_300',
    }
    integer_arrays = {
        'rel3_cell', 'rel3_area', 'rel3_count_req1', 'rel3_count_req2',
        'rel3_count_req3', 'rel3_building', 'rel3_offset',
        'required_trees_3', 'rel30_cell', 'rel30_area',
        'rel300_cell', 'rel300_area', 'rel300_gain_count',
        'rel300_building', 'rel300_offset', 'rel30_offset',
    }
    lines = []
    for name in fields:
        value = data[name]
        if isinstance(value, (list, tuple, np.ndarray, pd.Series)):
            converter = int if name in integer_arrays else float
            formatted = '[' + ', '.join(
                str(converter(v)) if converter is int else repr(float(v))
                for v in value
            ) + ']'
        elif name in integer_scalars:
            formatted = str(int(value))
        else:
            formatted = repr(float(value))
        lines.append(f'{name} = {formatted};')
    # Keep the old dedicated serializer's trailing newline convention.
    return '\n'.join(lines) + ('\n\n' if model == 'std_330300' else '\n')


def to_dzn(model, instance):
    """Convert an instance into MiniZinc data format."""
    if model in ('std_330300', 'std_330300_maxcoverage'):
        return to_dzn_330300(model, instance)
    if model == 'std':
        num_cells, top_k, beta_streets, alpha_yard, street_space, ext_space, green_space, num_areas, num_trees, macro_factors, full_space = instance
    elif model == 'diff':
        num_cells, top_k, beta_streets, alpha_yard, alpha_uhei, street_space, ext_space, green_space, num_areas, num_trees, macro_factors, full_space, uhei = instance
    elif model == 'inverse_uhei':
        num_cells, top_k, beta_streets, alpha_yard, inverse_uhei_95p, inverse_uhei_5p, street_space, ext_space, green_space, num_areas, num_trees, macro_factors, full_space = instance
    elif model == 'ndvi':
        num_cells, top_k, beta_streets, alpha_yard, ndvi_norm_max, ndvi_norm_min, street_space, ext_space, green_space, num_areas, num_trees, macro_factors, full_space, ndvi = instance
    else:
        raise ValueError(f'Unknown MiniZinc model: {model}')

    num_cells_str = 'len = ' + str(num_cells) + ';\n'
    top_k_str = 'top_k = ' + str(top_k) + ';\n'
    beta_streets_str = 'beta_streets = ' + str(beta_streets) + ';\n'
    alpha_yard_str = 'alpha_yard = ' + str(alpha_yard) + ';\n'
    street_space_str = 'street_space = [ '
    ext_space_str = 'ext_space = [ '
    green_space_str = 'green_space = [ '
    num_areas_str = 'num_areas = [ '
    num_trees_str = 'num_trees = [ '
    macro_factors_str = 'macro_factors = [ '
    full_space_str = 'full_space = [ '
    for i in range(num_cells):
        if i == num_cells - 1:
            street_space_str += str(street_space[i]) + ' ];\n'
            ext_space_str += str(ext_space[i]) + ' ];\n'
            green_space_str += str(green_space[i]) + ' ];\n'
            num_areas_str += str(num_areas[i]) + ' ];\n'
            num_trees_str += str(num_trees[i]) + ' ];\n'
            macro_factors_str += str(macro_factors[i]) + ' ];\n'
            full_space_str += str(full_space[i]) + ' ];\n'
        else:
            street_space_str += str(street_space[i]) + ', '
            ext_space_str += str(ext_space[i]) + ', '
            green_space_str += str(green_space[i]) + ', '
            num_areas_str += str(num_areas[i]) + ', '
            num_trees_str += str(num_trees[i]) + ', '
            macro_factors_str += str(macro_factors[i]) + ', '
            full_space_str += str(full_space[i]) + ', '

    if model == 'std':
        text = num_cells_str + top_k_str + beta_streets_str + alpha_yard_str + street_space_str + ext_space_str + green_space_str + num_areas_str + num_trees_str + macro_factors_str + full_space_str
    elif model == 'diff':
        alpha_uhei_str = 'alpha_uhei = ' + str(alpha_uhei) + ';\n'
        uhei_str = 'uhei = [ '
        for i in range(num_cells):
            if i == num_cells - 1:
                uhei_str += str(uhei[i]) + ' ];\n'
            else:
                uhei_str += str(uhei[i]) + ', '
        text = num_cells_str + top_k_str + beta_streets_str + alpha_yard_str + alpha_uhei_str + street_space_str + ext_space_str + green_space_str + num_areas_str + num_trees_str + macro_factors_str + full_space_str + uhei_str
    elif model == 'inverse_uhei':
        inverse_uhei_95p_str = 'inverse_uhei_95p = ' + str(inverse_uhei_95p) + ';\n'
        inverse_uhei_5p_str = 'inverse_uhei_5p = ' + str(inverse_uhei_5p) + ';\n'
        text = num_cells_str + top_k_str + beta_streets_str + alpha_yard_str + inverse_uhei_95p_str + inverse_uhei_5p_str + street_space_str + ext_space_str + green_space_str + num_areas_str + num_trees_str + macro_factors_str + full_space_str
    elif model == 'ndvi':
        ndvi_norm_max_str = 'ndvi_norm_max = ' + str(ndvi_norm_max) + ';\n'
        ndvi_norm_min_str = 'ndvi_norm_min = ' + str(ndvi_norm_min) + ';\n'
        ndvi_str = 'ndvi = [ '
        for i in range(num_cells):
            if i == num_cells - 1:
                ndvi_str += str(ndvi[i]) + ' ];\n'
            else:
                ndvi_str += str(ndvi[i]) + ', '
        text = num_cells_str + top_k_str + beta_streets_str + alpha_yard_str + ndvi_norm_max_str + ndvi_norm_min_str + street_space_str + ext_space_str + green_space_str + num_areas_str + num_trees_str + macro_factors_str + full_space_str + ndvi_str
    return text


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