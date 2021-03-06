Examples
========

These examples presuppose familiarity with UrbanSim and its typical workflows.
See the basic introduction_ and examples_ from UrbanSim's documentation.

Starter Repository: urbansim_parcels
------------------------------------
The `urbansim_parcels`_ repository was built as a new "starter model" that
provides boilerplate code to take advantage of new features in this developer
model. See installation details in the `readme <urbansim_parcels_>`_.

Repository Structure
~~~~~~~~~~~~~~~~~~~~
The ``urbansim_parcels`` repository is structured in three directories:

- ``/urbansim_parcels`` is the actual Python package that contains the core
  modules with code that interfaces with UrbanSim and the developer model.
  Those that have used ``urbansim_defaults`` or other starter models will
  find the structure very similar.
- ``/sd_example`` and ``/sf_example`` are directories containing an example
  regional model that uses much of the functionality provided in the
  "base" modules (e.g. ``urbansim_parcels/models.py``) but also add their own
  custom models or utility functions (e.g. ``sd_example/custom_models.py``)
  that overwrite certain Orca registrations from the base model.
  These examples also come with their own configurations and data.
  More information on the example models below.


Example Regions
~~~~~~~~~~~~~~~
- **San Diego**: This is a relatively fully-featured model built off of
  San Diego's openly shared data and model code from the sandiego_urbansim_
  repository in UDST. This model includes Pandana network accessibility
  variables. The data that comes with the repository is a small subset of the
  full data; download instructions for the full dataset are provided in the
  `readme <urbansim_parcels_>`_. Note: The data is not guaranteed to be up to
  date, and model code has been modified from the original repo.
- **San Francisco**: This is based off of the sanfran_urbansim_ repository that
  has long been used as a simple integration test for the UrbanSim library.
  Its features have been modified to work with this new developer model.

Simulation Examples
-------------------

Base Simulation
~~~~~~~~~~~~~~~

Running ``simulate.py`` in either example directory runs the model for each
region with minimal changes from the previous starter models. The major
difference is that model steps have been modified to work with the new
developer model. For example, both examples pull configurations for the
SqFtProForma model from ``configs/proforma.yaml``, taking advantage of the
new I/O features.

Adding a Development Pipeline
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The addition of a development pipeline and related helper functions is one of
two major improvements in this starter model. The ``simulate_pipeline.py``
script in either example directory runs a simulation in which, after the
price models and location choice models are run:

- Parcels larger than a certain size are split into smaller chunks and
  go through their own pro forma and development models. Qualifying
  development sites are added to the pipeline.
- All other parcels are assessed for profitability in the pro forma model.
- These parcels are added to the pipeline according to the developer model.
- Projects in the pipeline are "built" by adding the correct sites to the
  buildings table.

This workflow introduces some new data structures:

- **Pipeline**: DataFrame indexed by ``project_id`` that contains information
  about how many sites are contained in a project, and when the project is
  due to be completed.
- **Sites**: The individual piece of land that a building may be built on. This
  is the unit that the pro forma and developer models operate on, and sites
  are linked to a ``project_id`` and a ``parcel_id``. A site may be the
  same as a parcel, could contain multiple parcels, and multiple sites can be
  within a parcel. These are contained in the dev_sites table in these
  examples.

.. note::
   The current versions of the pipeline and sites tables support nested sites
   within parcels, but *not* sites that contain multiple parcels. This is an
   important feature that we plan to add soon.

The ``feasibility_with_pipeline`` step in the simulation script is the
first place to examine the new functionality. This step calls the function
of the same name in ``urbansim_parcels/models.py``, and passes
the ``pipeline=True`` argument to the helper function:
::

   @orca.step('feasibility_with_pipeline')
   def feasibility_with_pipeline(parcels,
                                 parcel_sales_price_sqft_func,
                                 parcel_is_allowed_func):
       utils.run_feasibility(parcels,
                             parcel_sales_price_sqft_func,
                             parcel_is_allowed_func,
                             pipeline=True,
                             cfg='proforma.yaml')


The ``pipeline`` argument ensures that feasibility is only assessed
(via the pro forma model) for parcels than do not contain any sites
associated with projects in the pipeline. The results of this are passed to
the next step, ``residential_developer_pipeline``, also with the
``pipeline=True`` argument:
::

   @orca.step('residential_developer_pipeline')
   def residential_developer_pipeline(feasibility, households, buildings, parcels,
                                      year, summary, form_to_btype_func,
                                      add_extra_columns_func):
       new_buildings = utils.run_developer(
           "residential",
           households,
           buildings,
           'residential_units',
           feasibility,
           parcels.parcel_size,
           parcels.ave_sqft_per_unit,
           parcels.total_residential_units,
           'res_developer.yaml',
           year=year,
           form_to_btype_callback=form_to_btype_func,
           add_more_columns_callback=add_extra_columns_func,
           pipeline=True)

       summary.add_parcel_output(new_buildings)


In this case, the ``pipeline`` argument ensures that when potential buildings
are selected for development, they are not immediately appended to the
buildings table, but added to the pipeline. The ``pipeline_utils`` module
contains helper functions that facilitate this process.

Additional details:

- Both of the example models are set up with Orca tables named ``pipeline`` and
  ``dev_sites``, which can be examined over the course of a simulation to see
  how sites are being added.
- The ``year_built`` column is currently added to sites based on the
  construction time used in the pro forma step. This is currently set up in
  ``utils.add_buildings()``.
- The ``add_more_columns_callback`` in ``utils.add_buildings()`` must be
  configured to add columns that match the columns of the original buildings
  table. See the "add_extra_columns" function in San Diego's custom model
  file for an example.
- In the San Diego example, the ``scheduled_development_events`` step is
  disabled, and instead, the scheduled development events are added to the
  pipeline upon loading data sources
  (see ``sd_example/custom_datasources.py``).


Using Occupancy Rates with Callback Functions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The other major improvement in this model is the ability to use callback
functions in several places to modify the behavior of the pro forma and
developer steps. The ``simulate_occupancy.py`` script for both of the
example regions provides one application of these features. Note that this
script does not use any of the pipeline features described above. We'll focus
on the San Diego implementation for this example.

For this example, we have a few goals:

- Monitor the occupancy of buildings in the region (by use and subgeography)
- Use the occupancy data to inform pro forma analysis. Buildings that are
  expected to have low occupancy should be expected to be less profitable.
- Change the developer model's rules to develop all buildings that meet a
  certain profitability threshold, rather than meeting a ``target_unit``
  number.

To monitor occupancy, we use UrbanSim's networks.from_yaml function to
calculate occupancy for residential and non-residential buildings for each
node in the Pandana network. This uses the ``occupancy_vars.yaml``
configuration in the San Diego example directory. Later, we will look up
these calculated occupancy values for each parcel using this node table.
::

   @orca.step('occupancy_vars_network')
   def occupancy_vars_network(year, net):

       oldest_year = year - 20
       building_occupancy = utils.building_occupancy(oldest_year)
       orca.add_table('building_occupancy', building_occupancy)

       res_mean = building_occupancy.occupancy_res.mean()
       print('Average residential occupancy in {} for buildings built'
             ' since {}: {:.2f}%'.format(year, oldest_year, res_mean * 100))

       nonres_mean = building_occupancy.occupancy_nonres.mean()
       print('Average non-residential occupancy in {} for buildings built'
             ' since {}: {:.2f}%'.format(year, oldest_year, nonres_mean * 100))

       nodes2 = networks.from_yaml(net, "occupancy_vars.yaml")
       nodes2 = nodes2.fillna(0)
       print(nodes2.describe())
       nodes = orca.get_table('nodes')
       nodes = nodes.to_frame().join(nodes2)
       orca.add_table("nodes", nodes)

To incorporate occupancy data in the pro forma step, we can pass three
additional arguments to the ``run_feasibility`` helpful function:
::

   @orca.step('feasibility_with_occupancy')
   def feasibility_with_occupancy(parcels,
                                  parcel_sales_price_sqft_func,
                                  parcel_is_allowed_func,
                                  parcel_occupancy_func,
                                  modify_df_occupancy,
                                  modify_revenues_occupancy):
       utils.run_feasibility(parcels,
                             parcel_sales_price_sqft_func,
                             parcel_is_allowed_func,
                             cfg='proforma.yaml',
                             modify_df=modify_df_occupancy,
                             modify_revenues=modify_revenues_occupancy,
                             parcel_custom_callback=parcel_occupancy_func)


The ``parcel_custom_callback`` allows the user to modify the DataFrame of
parcels or sites that is passed to the pro forma lookup() method. In the
callback (registered as an Orca injectable) below, occupancies for each
parcel are looked up from the nodes table.

::

   @orca.injectable('parcel_occupancy_func', autocall=False)
   def parcel_average_occupancy(df, pf):
       for use in pf.uses:
           occ_var = 'occ_{}'.format(use)
           nodes = orca.get_table('nodes').to_frame([occ_var])
           df[occ_var] = misc.reindex(nodes[occ_var],
                                      orca.get_table('parcels').node_id)
       return df


The ``modify_df`` callback further modifies in the input DataFrame, but this
time inside the SqFtProForma object, so that it can use all of the object
attributes, like ``self.forms``. This callback calculates a weighted occupancy
for each parcel based on the mix of uses defined by its form.
::

   @orca.injectable('modify_df_occupancy', autocall=False)
   def modify_df_occupancy(self, form, df):
       occupancies = ['occ_{}'.format(use) for use in self.uses]
       if set(occupancies).issubset(set(df.columns.tolist())):
           df['weighted_occupancy'] = np.dot(
               df[occupancies],
               self.forms[form])
       else:
           df['weighted_occupancy'] = 1.0

       df = df.loc[df.weighted_occupancy > .50]

       return df

The ``modify_revenues`` callback then multiples the revenue array by
those weighted occupancies for each parcel, effectively taking away revenue
for vacant space in each parcel. This changes the profitability picture for the
region substantially.
::

   @orca.injectable('modify_revenues_occupancy', autocall=False)
   def modify_revenues_occupancy(self, form, df, revenues):
       return revenues * df.weighted_occupancy.values


Finally, we are also interested in changing the rules to develop buildings.
This is achieved by passing a callback function to the
``custom_selection_func`` parameter in the modified developer step below:

::

   @orca.step('residential_developer_profit')
   def residential_developer_profit(feasibility, households, buildings,
                                    parcels, year, summary,
                                    form_to_btype_func, add_extra_columns_func,
                                    res_selection):
       new_buildings = utils.run_developer(
           "residential",
           households,
           buildings,
           'residential_units',
           feasibility,
           parcels.parcel_size,
           parcels.ave_sqft_per_unit,
           parcels.total_residential_units,
           'res_developer.yaml',
           year=year,
           form_to_btype_callback=form_to_btype_func,
           add_more_columns_callback=add_extra_columns_func,
           custom_selection_func=res_selection)

       summary.add_parcel_output(new_buildings)


The ``res_selection`` callback function below filters the results of the pro
forma step for parcels that have a profit per square foot of more than $20,
and selects them for development. That's it - there is no reference to target
units that are typically involved.

::

   @orca.injectable('res_selection', autocall=False)
   def res_selection(self, df, p):
       min_profit_per_sqft = 20
       print("BUILDING ALL BUILDINGS WITH PROFIT > ${:.2f} / sqft"
             .format(min_profit_per_sqft))
       profitable = df.loc[df.max_profit_per_size > min_profit_per_sqft]
       build_idx = profitable.index.values
       return build_idx


This example provides a simple set of callback functions to demonstrate the
various ways users can now intervene in the real estate development process
in UrbanSim simulations. Of course, the particular implementations shown
here likely lead to unrealistic outcomes; each region should design callback
functions that mimic realistic behavior.

.. _introduction: http://udst.github.io/urbansim/gettingstarted.html#a-gentle-introduction-to-urbansim
.. _examples: http://udst.github.io/urbansim/examples.html
.. _urbansim_parcels: https://github.com/urbansim/urbansim_parcels
.. _sandiego_urbansim: https://github.com/udst/sandiego_urbansim
.. _sanfran_urbansim: https://github.com/udst/sanfran_urbansim