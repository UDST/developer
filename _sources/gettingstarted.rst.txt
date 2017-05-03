Getting Started
===============

.. note::
   This package is in alpha and is actively under development. Please feel
   free to report bugs or suggest improvements (see `Reporting bugs and contributing`_)

Dependencies
^^^^^^^^^^^^

The developer model depends on the following libraries, most of which are in Anaconda:

* `numpy <http://numpy.org>`__ >= 1.8.0
* `orca <https://github.com/UDST/orca>`__ >= 1.1
* `pandas <http://pandas.pydata.org>`__ >= 0.15
* `urbansim <http://github.com/UDST/urbansim>`__ >= 3.0

Development Version
^^^^^^^^^^^^^^^^^^^

The developer model can be installed from our
`development repository <https://github.com/urbansim/developer>`__
using `pip <https://pip.pypa.io/en/latest/>`__, a Python package manager.
pip is included with Anaconda so you should now be able to open a terminal
and run the following command to install UrbanSim::

    pip install -U https://github.com/urbansim/developer/archive/master.zip

This will download the repo and install the remaining dependencies not
included in Anaconda. You will need to have git credentials configured since
this is currently a private repository.

Developer Install
^^^^^^^^^^^^^^^^^

If you are going to be developing this package you will want to fork the
`GitHub repository <https://github.com/urbansim/developer>`_ and clone
your fork to your computer. Then run ``python setup.py develop`` to install
this package in developer mode. In this mode you won't have to reinstall it
every time you make changes.

Reporting bugs and contributing
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Please report any bugs you encounter via `GitHub Issues <https://github.com/urbansim/developer/issues>`__, or contribute your code
from a fork or branch by using a Pull Request and request a review so it can be considered as an addition to the codebase.