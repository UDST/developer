# UrbanSim Developer Model

## Notes from offline session:

* Refactored initialization and configuration for SqftProForma.
    * Deleted `SqftProFormaConfig` object
    * Moved config docstrings to `SqftProForma` object
    * Added configs as object attributes
    * Added `check_if_reasonable` and `_convert_types` methods, along with
    `tiled_parcel_sizes` attribute to main `SqftProForma`
    constructor method (i.e. `__init__`)
    * Copied and modified yamlio functions from urbansim/utils/yamlio.py to
    this package's `utils.py`
    * Created `get_defaults` static method to return the dictionary of
    default values (values copied from previous `SqftProFormaConfig` object)
    * Created `from_defaults` class method for instantiating a new
    `SqftProForma` object from default values (uses dict above).
    **Important: this replaces the old way of instantiating the pro forma model
    with default values (i.e. `pf = SqftProForma()`). You can no longer
    instantiate this model without arguments. This is consistent with other models.**
    * Created `from_yaml` method, based on DCM version
    * Created `to_dict` method, based on DCM version. This unconverts
    several attributes from the `_convert_types` step.
    * Created `to_yaml` method, based on DCM version.
    * Added unit tests for the three bullet points above, modified other
    unit tests to work with this format. Deleted one redundant unit test.

## To dos:
* Generalize residential_to_yearly
* Move simple zoning to interior pro forma code
* Move other configurations to pro forma attributes/configs

