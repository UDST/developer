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


def test_developer(simple_dev_inputs):
    pf = sqpf.SqFtProForma.from_defaults()
    out = pf.lookup("residential", simple_dev_inputs)
    feasibility = {'residential': out}

    parcel_size = pd.Series([1000, 1000, 1000], index=['a', 'b', 'c'])
    ave_unit_size = pd.Series([650, 650, 650], index=['a', 'b', 'c'])
    current_units = pd.Series([0, 0, 0], index=['a', 'b', 'c'])

    dev = developer.Developer(feasibility=feasibility,
                              form='residential')

    target_units = 10
    bldgs = dev.pick(target_units, parcel_size, ave_unit_size, current_units)
    assert len(bldgs) == 1

    target_units = 1000
    bldgs = dev.pick(target_units, parcel_size, ave_unit_size, current_units)
    assert len(bldgs) == 2

    dev = developer.Developer(feasibility=feasibility, form='residential',
                              residential=False)

    target_units = 2
    bldgs = dev.pick(target_units, parcel_size, ave_unit_size, current_units)
    assert bldgs is None

    target_units = 2
    bldgs = dev.pick(target_units, parcel_size, ave_unit_size, current_units)
    assert bldgs is None


def test_developer_dict_roundtrip(simple_dev_inputs):
    pf = sqpf.SqFtProForma.from_defaults()
    out = pf.lookup("residential", simple_dev_inputs)
    feasibility = {'residential': out}

    parcel_size = pd.Series([1000, 1000, 1000], index=['a', 'b', 'c'])
    ave_unit_size = pd.Series([650, 650, 650], index=['a', 'b', 'c'])
    current_units = pd.Series([0, 0, 0], index=['a', 'b', 'c'])

    dev1 = developer.Developer(feasibility=feasibility, form='residential')
    config1 = dev1.to_dict

    dev2 = developer.Developer(feasibility=feasibility, form='residential',
                               **config1)
    config2 = dev2.to_dict

    assert config1 == config2


def test_developer_yaml_roundtrip(simple_dev_inputs):

    if os.path.exists('test_dev_config.yaml'):
        os.remove('test_dev_config.yaml')

    pf = sqpf.SqFtProForma.from_defaults()
    out = pf.lookup("residential", simple_dev_inputs)
    feasibility = {'residential': out}

    parcel_size = pd.Series([1000, 1000, 1000], index=['a', 'b', 'c'])
    ave_unit_size = pd.Series([650, 650, 650], index=['a', 'b', 'c'])
    current_units = pd.Series([0, 0, 0], index=['a', 'b', 'c'])

    dev = developer.Developer(feasibility=feasibility, form='residential')
    with open('test_dev_config.yaml', 'wb') as yaml_file:
        dev.to_yaml(yaml_file)
        yaml_string = dev.to_yaml()

    dev_from_yaml_file = developer.Developer.from_yaml(
        feasibility=feasibility,
        form='residential',
        str_or_buffer='test_dev_config.yaml')
    assert dev.to_dict == dev_from_yaml_file.to_dict

    dev_from_yaml_string = developer.Developer.from_yaml(
        feasibility=feasibility,
        form='residential',
        yaml_str=yaml_string)
    assert dev.to_dict == dev_from_yaml_string.to_dict

    os.remove('test_dev_config.yaml')


def test_developer_compute_units_to_build(simple_dev_inputs):
    pf = sqpf.SqFtProForma.from_defaults()
    out = pf.lookup("residential", simple_dev_inputs)
    feasibility = {'residential': out}
    dev = developer.Developer(feasibility, 'residential')
    to_build = dev.compute_units_to_build(30, 30, .1)
    assert int(to_build) == 3


def test_developer_compute_forms_max_profit(simple_dev_inputs):
    pf = sqpf.SqFtProForma.from_defaults()
    out = pf.lookup("residential", simple_dev_inputs)
    feasibility = {'residential': out}
    dev = developer.Developer(feasibility, 'residential')
    dev.keep_form_with_max_profit()


def test_developer_merge():
    df1 = pd.DataFrame({'test': [1]}, index=[1])
    df2 = pd.DataFrame({'test': [1]}, index=[1])
    dev = developer.Developer.merge(df1, df2)
    # make sure index is unique
    assert dev.index.values[1] == 2
