Real Estate Development Models
==============================

.. note::
   This package builds on the existing `developer model <https://github.com/
   UDST/urbansim/tree/master/urbansim/developer/>`_ included in the UrbanSim
   library. Some of the key changes are highlighted here, but it may be helpful to
   refer to the old version's `documentation
   <http://udst.github.io/urbansim/developer/index.html>`_ for a more detailed
   comparison.

The real estate development models included in this module are designed to
implement pencil out pro formas, which generally measure the cash inflows and
outflows of a potential investment (in this case, real estate development)
with the outcome being some measure of profitability or return on investment.
Pro formas would normally be performed in a spreadsheet program (e.g. Excel),
but are implemented in vectorized Python implementations so that many (think
millions) of pro formas can be performed at a time.

The functionality is split into two modules - the square foot pro forma and
the developer model - as there are many use cases that call for the pro formas
without the developer model.  The ``sqftproforma`` module computes real
estate feasibility for a set of parcels dependent on allowed uses, prices,
and building costs, but does not actually *build* anything (both figuratively
and literally).  The ``develop`` module decides how much to build,
then picks among the set of feasible buildings attempting to meet demand,
and adds the new buildings to the set of current buildings.  Thus
``develop`` is primarily useful in the context of an urban forecast.

An example of the sample code required to generate the set of feasible
buildings is shown below.  This code comes from the ``utils`` module of the
`urbansim_parcels <https://github.com/urbansim/urbansim_parcels/sd_example>`_
San Diego demo.  Notice that the SqFtProForma is
first initialized and a DataFrame of parcels is tested for feasibliity (each
individual parcel is tested for feasibility).  Each *use* (e.g. retail, office,
residential, etc) is assigned a price per parcel, typically from empirical data
of currents rents and prices in the city but can be the result of forecast
rents and prices as well.  The ``lookup`` function is then called with a
specific building ``form`` and the pro forma returns whether that form is
profitable for each parcel.

A large number of assumptions enter in to the computation of profitability
and these are set in the `SqFtProForma <#developer.sqftproforma.SqFtProForma>`_
module, and include such things as the set of ``uses`` to model,
the mix of ``uses`` into ``forms``, the impact of parking requirements,
parking costs, building costs at different heights (taller buildings typically
requiring more expensive construction methods), the profit ratio required,
the building efficiency, parcel coverage, and cap rate to name a few. See
the API documentation for the complete list and detailed descriptions. The
newest version of this model allows for loading configurations from a YAML
file; the examples in the ``urbansim_parcels`` repository include a `YAML
file <https://github.com/urbansim/urbansim_parcels/blob/master/
sd_example/configs/proforma.yaml>`_ with default configurations.

Note that unit mixes don't typically enter in to the square foot pro forma
(hence the name). After discussions with numerous real estate developers,
we found that most developers thought first and foremost in terms of price and
cost per square foot and the arbitrage between, and second in terms of the
translation to unit sizes and mixes in a given market (also larger and
smaller units of a given unit type will typically lower and raise their
prices as stands to reason). Since getting data on unit mixes in the current
building stock is extremely difficult, most feasibility computations here
happen on a square foot basis and the ``developer`` model below handles the
translation to units. ::

    cfg = misc.config('proforma.yaml')

    pf = (sqftproforma.SqFtProForma.from_yaml(str_or_buffer=cfg)
          if cfg else sqftproforma.SqFtProForma.from_defaults())

    for use in pf.uses:
        parcels[use] = parcel_price_callback(use)

    feasibility = lookup_by_form(df, parcel_use_allowed_callback, pf, **kwargs)
    orca.add_table('feasibility', feasibility)

    d = {}
    for form in pf.config.forms:
        print "Computing feasibility for form %s" % form
        d[form] = pf.lookup(form, df[parcel_use_allowed_callback(form)])

    feasibility = pd.concat(d.values(), keys=d.keys(), axis=1)

    sim.add_table("feasibility", feasibility)


The ``develop`` module is responsible for picking among feasible buildings
in order to meet demand.  An example usage of the model is shown below - which
is also lifted from the `urbansim_parcels <https://github.com/urbansim/
urbansim_parcels/sd_example>`_ San Diego demo.

This module provides a simple utility to compute the number of units (or
amount of floorspace) to build. The developer model itself is agnostic to which parcels
the user passes it, and the user is responsible for knowing at which level of
geography demand is assumed to operate. The developer model then chooses
which buildings to "build." Previous workflows have typically involved
selecting buildings based on random choice weighted by profitability, with an
expected vacancy rate acting as a control on the number of buildings built. In
this version, there are new features that allow a bit more control over this
process (see `Callback Access to Development Selection`_).

The only remaining steps are then "bookkeeping" in the sense that some
additional fields might need to be added (``year_built`` or a conversion from
developer ``forms`` to ``building_type_ids``). Finally the new buildings
and old buildings need to be merged in such a way that the old ids are
preserved and not duplicated (new ids are assigned at the max of the old
ids+1 and then incremented from there). If using a development pipeline,
utility functions in `urbansim_parcels` provide a way to properly add
new buildings to the pipeline, rather than directly to the building table.
::

    cfg = misc.config('developer.yaml')
    target_units = (num_units_to_build
                    or compute_units_to_build(len(agents),
                                              buildings[supply_fname].sum(),
                                              target_vacancy))

    dev = develop.Developer.from_yaml(feasibility.to_frame(), forms,
                                      target_units, parcel_size,
                                      ave_unit_size, current_units,
                                      year, str_or_buffer=cfg)

    new_buildings = dev.pick(profit_to_prob_func, custom_selection_func)

    if year is not None:
        new_buildings["year_built"] = year

    if form_to_btype_callback is not None:
        new_buildings["building_type_id"] = new_buildings["form"].\
            apply(form_to_btype_callback)

    all_buildings = dev.merge(buildings.to_frame(buildings.local_columns),
                              new_buildings[buildings.local_columns])

    sim.add_table("buildings", all_buildings)

.. toctree::
   :maxdepth: 2

Major Changes
~~~~~~~~~~~~~

Input/Output
^^^^^^^^^^^^
There are now methods in the ``SqFtProForma`` and ``Developer`` classes to
load with configurations in a similar way to other `UrbanSim models
<http://udst.github.io/urbansim/models/statistical.html#yaml-persistence>`_.
The pro forma and developer model configurations can be saved as YAML files and
loaded again at another time. Use the ``to_yaml`` and ``from_yaml`` methods
to save files to disk and load them back as configurations. The ``SqFtProForma``
class also has a ``from_defaults`` method to load default values.
Here’s an example of loading a pro forma model from defaults and saving custom
settings back to YAML:
::

   proforma = SqFtProForma.from_defaults()
   proforma.to_yaml('proforma.yaml')

   # Make changes manually to YAML file

   new_proforma = SqFtProForma.from_yaml('modified_proforma.yaml')


Construction Financing
^^^^^^^^^^^^^^^^^^^^^^
One missing piece in profit calculations in the previous version of the model
is the fact that typically, real estate developers must secure financing
to fund the construction of buildings, and the cost of interest and fees must
be taken into account when calculating the final profitability of the building.

Several new attributes have been added to the SqFtProForma object. Default
values in dictionary format are below. For more information on each of these
attributes, see `API documentation <#developer.sqftproforma.SqFtProForma>`_.
::

   'construction_months': {
     'industrial': [12.0, 14.0, 18.0, 24.0],
     'office': [12.0, 14.0, 18.0, 24.0],
     'residential': [12.0, 14.0, 18.0, 24.0],
     'retail': [12.0, 14.0, 18.0, 24.0]},
   'construction_sqft_for_months': [10000, 20000, 50000, np.inf],
   'loan_to_cost_ratio': .7,
   'drawdown_factor': .6,
   'interest_rate': .05,
   'loan_fees': .02

In this version of the pro forma model, "total development cost" is derived
from the total building cost, along with the attributes above:
::

   # total_construction_costs calculated above
   loan_amount = total_construction_costs * self.loan_to_cost_ratio
   interest = (loan_amount
              * self.drawdown_factor
              * (self.interest_rate / 12 * months))
   points = loan_amount * self.loan_fees
   total_financing_costs = interest + points
   total_development_costs = (total_construction_costs
                             + total_financing_costs)

Callback Access to Profit Calculation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
In the core of the pro forma module, profitability for a set of potential
development sites (typically parcels) is calculated in a set of steps:

#. Read DataFrame of development sites.
#. Based on key columns in DataFrame, generate NumPy array of costs, with sites as columns and potential floor-to-area ratios (FARs) as rows.
#. Generate NumPy array of revenues with the same structure as costs.
#. Subtract costs from revenues to calculate profit (for every site, for every FAR).
#. For each site, pick the most profitable FAR, and return values for that FAR, including development costs, construction time, etc.

In the previous version of this model, the only control the user had into this
calculation was through values in the initial DataFrame. In this new version,
users can now pass callback functions to the ``lookup()`` method to
adjust the calculation at different stages, using the following parameters:

- ``modify_df``: Modify the input DataFrame. This can of course be done before passing into the pick() method, but this allows columns to be calculated using attributes of the Developer object.
- ``modify_costs``, ``modify_revenues``, and ``modify_profit``: Modify the NumPy ndarrays that represent costs and revenues for each sites and FAR.

There are specific parameters that each of these callback functions must
include; see `documentation <#developer.sqftproforma.SqFtProForma.lookup>`_
for details. For example, let's look at one result based on a test parcel
dataset:
::

   pf = SqFtProForma.from_defaults()
   pf.lookup('residential', df)

This simple lookup produces this result (table is simplified for example):

====== ========== ========== ==========
parcel cost       revenue    profit
====== ========== ========== ==========
a       4,922,490  8,960,000  4,037,510
b      13,821,510 26,880,000 13,058,490
c      28,805,616 53,760,000 24,954,384
====== ========== ========== ==========

Let's say we believe that revenues will be additionally reduced by 20% due to
an external factor, for all sites in this region. We can apply a simple
intervention to this calculation using a callback.
::

   def revenue_callback(self, form, df, revenues):
       revenues = revenues * .8
       return revenues

   pf.lookup('residential', df, modify_revenues=revenue_callback)

This gives us an identical cost column, but changes to the revenue and profit:

====== ========== ========== ==========
parcel cost       revenue    profit
====== ========== ========== ==========
a       4,922,490  7,168,000  2,245,510
b      13,821,510 21,504,000  7,682,490
c      28,805,616 43,008,000 14,202,384
====== ========== ========== ==========

Callback Access to Development Selection
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The previous version of the developer model has the following rules for
selecting parcels to build, based on a number of ``target_units`` to build,
and a probability associated with each development site, which can be generated
using a custom function:

#. If number of profitable sites is less than ``target_units``, build all sites
#. If ``target_units`` is 0 or less, build no sites
#. If number of profitable sites is greater than ``target_units``, select a number of sites equal to ``target_units`` based on probability (calculated from profitability unless otherwise defined)

In this version, users can pass a callback function to circumvent this entire
process and select sites based on entirely custom logic, using information
in the DataFrame passed to the ``pick()`` method. The following example
passes a function that selects all developments that have a profit per square
foot larger than 10:

::

   dev = develop.Developer.from_yaml(feasibility.to_frame(), forms,
                                target_units, parcel_size,
                                ave_unit_size, current_units,
                                year, str_or_buffer=cfg)

   def custom_selection(self, df, p):
       min_profit_per_sqft = 10
       print("BUILDING ALL BUILDINGS WITH PROFIT > ${:.2f} / sqft"
             .format(min_profit_per_sqft))
       profitable = df.loc[df.max_profit_per_size > min_profit_per_sqft]
       build_idx = profitable.index.values
       return build_idx

   new_buildings = dev.pick(custom_selection_func=custom_selection)

As with the previous set of callback functions, there is a strict set of
parameters that are required. See `documentation
<#developer.develop.Developer.pick>`_ for details.

Square Foot Pro Forma API
~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: developer.sqftproforma
   :members:

Developer Model API
~~~~~~~~~~~~~~~~~~~

.. automodule:: developer.develop
   :members:
