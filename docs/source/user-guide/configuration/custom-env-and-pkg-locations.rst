========================================================
Using Custom Locations for Environment and Package Cache
========================================================

For any given conda installation, the two largest folders in terms of
disk space are often the ``envs`` and ``pkgs`` folders
that store created environments and downloaded packages, respectively.
If the location where conda is installed has limited disk
space and another location with more disk space is available on the
same computer, we can change where conda saves its environments and
packages with the settings ``envs_dirs`` and ``pkgs_dirs``, respectively.

Assuming conda is installed in the user's home directory and the
the folder ``/volume/user`` with more disk space is writable,
the best way to configure this is by adding the following entries to the
``.condarc`` file in the user's home directory:

   .. code-block:: yaml

      envs_dirs:
        - /volume/user/conda_envs
      pkgs_dirs:
        - /volume/user/conda_pkgs

In the example above, we tell conda to use the folder ``/volume/user/conda_envs``
to store all of the environments we create, and we tell conda to use
``/volume/user/conda_pkgs`` to store all of the packages that we download.

To save even more space, the contents of ``/volume/user/conda_pkgs`` will be
hard linked to the environments in ``/volume/user/conda_envs`` when possible.
When it is not possible, the files will be copied over to the environment.
