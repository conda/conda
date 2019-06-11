Conda configuration
===================

.. program-output:: cd .. && python -c 'import os; import sys; src_dir = here = os.path.abspath(os.path.dirname("../setup.py")); sys.path.insert(0, src_dir); import conda.cli.main_config; print(conda.cli.main_config.describe_all_parameters())'
   :shell:
