import pandas as pd
import numpy as np
import utils
import logging

logger = logging.getLogger(__name__)


class Developer(object):
    """
    Pass the dataframe that is returned by feasibility here

    Can also be a dictionary where keys are building forms and values are
    the individual data frames returned by the proforma lookup routine.

    Parameters
    ----------
    feasibility : DataFrame or dict
        Results from SqftProForma lookup method
    forms : string or list
        One or more of the building forms from the pro forma specification -
        e.g. "residential" or "mixedresidential" - these are configuration
        parameters passed previously to the pro forma.  If more than one form
        is passed the forms compete with each other (based on profitability)
        for which one gets built in order to meet demand.
    parcel_size : series
        The size of the parcels.  This was passed to feasibility as well,
        but should be passed here as well.  Index should be parcel_ids.
    ave_unit_size : series
        The average residential unit size around each parcel - this is
        indexed by parcel, but is usually a disaggregated version of a
        zonal or accessibility aggregation.
    current_units : series
        The current number of units on the parcel.  Is used to compute the
        net number of units produced by the developer model.  Many times
        the developer model is redeveloping units (demolishing them) and
        is trying to meet a total number of net units produced.
    year : int
        The year of the simulation - will be assigned to 'year_built' on the
        new buildings
    bldg_sqft_per_job : float (default 400.0)
        The average square feet per job for this building form.
    min_unit_size : float
        Values less than this number in ave_unit_size will be set to this
        number.  Deals with cases where units are currently not built.
    max_parcel_size : float
        Parcels larger than this size will not be considered for
        development - usually large parcels should be specified manually
        in a development projects table.
    drop_after_build : bool
        Whether or not to drop parcels from consideration after they
        have been chosen for development.  Usually this is true so as
        to not develop the same parcel twice.
    residential: bool
        If creating non-residential buildings set this to false and
        developer will fill in job_spaces rather than residential_units
    num_units_to_build: optional, int
        If num_units_to_build is passed, build this many units rather than
        computing it internally by using the length of agents adn the sum of
        the relevant supply columin - this trusts the caller to know how to
        compute this.

    """

    def __init__(self, feasibility, forms, target_units,
                 parcel_size, ave_unit_size, current_units,
                 year=None, bldg_sqft_per_job=400.0,
                 min_unit_size=400, max_parcel_size=200000,
                 drop_after_build=True, residential=True,
                 num_units_to_build=None):

        if isinstance(feasibility, dict):
            feasibility = pd.concat(feasibility.values(),
                                    keys=feasibility.keys(), axis=1)
        self.feasibility = feasibility
        self.forms = forms
        self.target_units = target_units
        self.parcel_size = parcel_size
        self.ave_unit_size = ave_unit_size
        self.current_units = current_units
        self.year = year
        self.bldg_sqft_per_job = bldg_sqft_per_job
        self.min_unit_size = min_unit_size
        self.max_parcel_size = max_parcel_size
        self.drop_after_build = drop_after_build
        self.residential = residential
        self.num_units_to_build = num_units_to_build

    @classmethod
    def from_yaml(cls, feasibility, forms, target_units,
                  parcel_size, ave_unit_size, current_units,
                  year=None, yaml_str=None, str_or_buffer=None):
        """
        Parameters
        ----------
        yaml_str : str, optional
            A YAML string from which to load model.
        str_or_buffer : str or file like, optional
            File name or buffer from which to load YAML.

        Returns
        -------
        Developer object
        """
        cfg = utils.yaml_to_dict(yaml_str, str_or_buffer)

        model = cls(
            feasibility, forms, target_units,
            parcel_size, ave_unit_size, current_units,
            year, cfg['bldg_sqft_per_job'],
            cfg['min_unit_size'], cfg['max_parcel_size'],
            cfg['drop_after_build'], cfg['residential']
        )

        logger.debug('loaded Developer model from YAML')
        return model

    @property
    def to_dict(self):
        """
        Return a dict representation of a SqftProForma instance.

        """
        attributes = ['bldg_sqft_per_job',
                      'min_unit_size', 'max_parcel_size',
                      'drop_after_build', 'residential']

        results = {}
        for attribute in attributes:
            results[attribute] = self.__dict__[attribute]

        return results

    def to_yaml(self, str_or_buffer=None):
        """
        Save a model representation to YAML.

        Parameters
        ----------
        str_or_buffer : str or file like, optional
            By default a YAML string is returned. If a string is
            given here the YAML will be written to that file.
            If an object with a ``.write`` method is given the
            YAML will be written to that object.

        Returns
        -------
        j : str
            YAML is string if `str_or_buffer` is not given.

        """
        logger.debug('serializing Developer model to YAML')
        return utils.convert_to_yaml(self.to_dict, str_or_buffer)

    @staticmethod
    def _max_form(f, colname):
        """
        Assumes dataframe with hierarchical columns with first index equal to
        the use and second index equal to the attribute.

        e.g. f.columns equal to::

            mixedoffice   building_cost
                          building_revenue
                          building_size
                          max_profit
                          max_profit_far
                          total_cost
            industrial    building_cost
                          building_revenue
                          building_size
                          max_profit
                          max_profit_far
                          total_cost
        """
        df = f.stack(level=0)[[colname]].stack().unstack(level=1).reset_index(
            level=1, drop=True)
        return df.idxmax(axis=1)

    def keep_form_with_max_profit(self, forms=None):
        """
        This converts the dataframe, which shows all profitable forms,
        to the form with the greatest profit, so that more profitable
        forms outcompete less profitable forms.

        Parameters
        ----------
        forms: list of strings
            List of forms which compete which other.  Can leave some out.

        Returns
        -------
        Nothing.  Goes from a multi-index to a single index with only the
        most profitable form.
        """
        f = self.feasibility

        if forms is not None:
            f = f[forms]

        if len(f) > 0:
            mu = self._max_form(f, "max_profit")
            indexes = [tuple(x) for x in mu.reset_index().values]
        else:
            indexes = []
        df = f.stack(level=0).loc[indexes]
        df.index.names = ["parcel_id", "form"]
        df = df.reset_index(level=1)
        return df

    def _get_dataframe_of_buildings(self):

        if self.forms is None:
            df = self.feasibility
        elif isinstance(self.forms, list):
            df = self.keep_form_with_max_profit(self.forms)
        else:
            df = self.feasibility[self.forms]
        return df

    def _remove_infeasible_buildings(self, df):

        df = df[df.max_profit_far > 0]
        self.ave_unit_size[
            self.ave_unit_size < self.min_unit_size
        ] = self.min_unit_size
        df["ave_unit_size"] = self.ave_unit_size
        df["parcel_size"] = self.parcel_size
        df['current_units'] = self.current_units
        df = df[df.parcel_size < self.max_parcel_size]

        df['residential_units'] = (df.residential_sqft /
                                   df.ave_unit_size).round()
        df['job_spaces'] = (df.non_residential_sqft /
                            self.bldg_sqft_per_job).round()

        return df

    def _calculate_net_units(self, df):

        if self.residential:
            df['net_units'] = df.residential_units - df.current_units
        else:
            df['net_units'] = df.job_spaces - df.current_units
        return df[df.net_units > 0]

    @staticmethod
    def _calculate_probabilities(df, profit_to_prob_func):

        if profit_to_prob_func:
            p = profit_to_prob_func(df)
        else:
            df['max_profit_per_size'] = df.max_profit / df.parcel_size
            p = df.max_profit_per_size.values / df.max_profit_per_size.sum()
        return p, df

    def _buildings_to_build(self, df, p):

        if df.net_units.sum() < self.target_units:
            print "WARNING THERE WERE NOT ENOUGH PROFITABLE UNITS TO " \
                  "MATCH DEMAND"
            build_idx = df.index.values
        elif self.target_units <= 0:
            build_idx = []
        else:
            # we don't know how many developments we will need, as they differ
            # in net_units. If all developments have net_units of 1 than we
            # need target_units of them. So we choose the smaller of available
            # developments and target_units.
            choices = np.random.choice(df.index.values,
                                       size=min(len(df.index),
                                                self.target_units),
                                       replace=False, p=p)
            tot_units = df.net_units.loc[choices].values.cumsum()
            ind = int(np.searchsorted(tot_units, self.target_units,
                                      side="left")) + 1
            build_idx = choices[:ind]

        return build_idx

    def _drop_built_buildings(self, build_idx):

        if self.drop_after_build:
            self.feasibility = self.feasibility.drop(build_idx)

    def _prepare_new_buildings(self, df, build_idx):

        new_df = df.loc[build_idx]
        new_df.index.name = "parcel_id"

        if self.year is not None:
            new_df["year_built"] = self.year

        if not isinstance(self.forms, list):
            # form gets set only if forms is a list
            new_df["form"] = self.forms

        new_df["stories"] = new_df.stories.apply(np.ceil)

        return new_df.reset_index()

    def pick(self, profit_to_prob_func=None):
        """
        Choose the buildings from the list that are feasible to build in
        order to match the specified demand.

        Parameters
        ----------
        profit_to_prob_func: function
            As there are so many ways to turn the development feasibility
            into a probability to select it for building, the user may pass
            a function which takes the feasibility dataframe and returns
            a series of probabilities.  If no function is passed, the behavior
            of this method will not change

        Returns
        -------
        None if there are no feasible buildings
        new_buildings : dataframe
            DataFrame of buildings to add.  These buildings are rows from the
            DataFrame that is returned from feasibility.
        """

        if len(self.feasibility) == 0:
            # no feasible buildings, might as well bail
            return

        # Get DataFrame of potential buildings from SqFtProForma steps
        df = self._get_dataframe_of_buildings()
        df = self._remove_infeasible_buildings(df)
        df = self._calculate_net_units(df)

        if len(df) == 0:
            print "WARNING THERE ARE NO FEASIBLE BUILDING TO CHOOSE FROM"
            return

        print "Sum of net units that are profitable: {:,}".\
            format(int(df.net_units.sum()))

        # Generate development probabilities and pick buildings to build
        p, df = self._calculate_probabilities(df, profit_to_prob_func)
        build_idx = self._buildings_to_build(df, p)

        # Drop built buildings from self.feasibility attribute if desired
        self._drop_built_buildings(build_idx)

        # Prep DataFrame of new buildings
        new_df = self._prepare_new_buildings(df, build_idx)

        return new_df


