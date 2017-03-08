import pandas as pd
import pytest
import os

from .. import sqftproforma as sqpf
from .. import developer


@pytest.fixture
def simple_dev_inputs():
    return pd.DataFrame(
        {'residential': [40, 40, 40],
         'office': [15, 18, 15],
         'retail': [12, 10, 10],
         'industrial': [12, 12, 12],
         'land_cost': [1000000, 2000000, 3000000],
         'parcel_size': [10000, 20000, 30000],
         'max_far': [2.0, 3.0, 4.0],
         'max_height': [40, 60, 80]},
        index=['a', 'b', 'c'])


@pytest.fixture
def feasibility(simple_dev_inputs):
    pf = sqpf.SqFtProForma.from_defaults()
    out = pf.lookup("residential", simple_dev_inputs)
    return {'residential': out}


@pytest.fixture
def base_args(feasibility):
    parcel_size = pd.Series([1000, 1000, 1000], index=['a', 'b', 'c'])
    ave_unit_size = pd.Series([650, 650, 650], index=['a', 'b', 'c'])
    current_units = pd.Series([0, 0, 0], index=['a', 'b', 'c'])

    return {'feasibility': feasibility,
            'parcel_size': parcel_size,
            'ave_unit_size': ave_unit_size,
            'current_units': current_units}


@pytest.fixture
def res(base_args):
    args = base_args.copy()
    args.update({'forms': 'residential'})
    return args


@pytest.fixture
def nonres(base_args):
    args = base_args.copy()
    args.update({'forms': 'office'})
    return args


def test_res_developer(res):

    dev = developer.Developer(target_units=10, **res)
    bldgs = dev.pick()
    assert len(bldgs) == 1
    assert len(dev.feasibility) == 2

    dev = developer.Developer(target_units=1000, **res)
    bldgs = dev.pick()
    assert len(bldgs) == 3

    dev = developer.Developer(target_units=2, residential=False, **res)
    bldgs = dev.pick()
    assert bldgs is None


@pytest.fixture
def res10(res):
    args = res.copy()
    args.update({'target_units': 10})
    return args


def test_developer_dict_roundtrip(res10):
    dev1 = developer.Developer(**res10)
    config1 = dev1.to_dict

    next_args = config1.copy()
    next_args.update(res10)

    dev2 = developer.Developer(**next_args)
    config2 = dev2.to_dict

    assert config1 == config2


def test_developer_yaml_roundtrip(res10):
    if os.path.exists('test_dev_config.yaml'):
        os.remove('test_dev_config.yaml')

    dev = developer.Developer(**res10)
    with open('test_dev_config.yaml', 'wb') as yaml_file:
        dev.to_yaml(yaml_file)
        yaml_string = dev.to_yaml()

    dev_from_yaml_file = developer.Developer.from_yaml(
        str_or_buffer='test_dev_config.yaml', **res10)
    assert dev.to_dict == dev_from_yaml_file.to_dict

    dev_from_yaml_string = developer.Developer.from_yaml(
        yaml_str=yaml_string, **res10)
    assert dev.to_dict == dev_from_yaml_string.to_dict

    os.remove('test_dev_config.yaml')


def test_developer_compute_forms_max_profit(res10):
    dev = developer.Developer(**res10)
    dev.keep_form_with_max_profit()


def test_developer_merge():
    df1 = pd.DataFrame({'test': [1]}, index=[1])
    df2 = pd.DataFrame({'test': [1]}, index=[1])
    dev = developer.Developer.merge(df1, df2)
    # make sure index is unique
    assert dev.index.values[1] == 2
