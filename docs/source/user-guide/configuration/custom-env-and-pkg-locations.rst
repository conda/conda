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
the folder ``/nfs/volume/user`` with more disk space is writable,
the best way to configure this is by adding the following entries to the
``.condarc`` file in the user's home directory:

   .. code-block:: yaml

      envs_dirs:
        - /nfs/volume/user/conda_envs
      pkgs_dirs:
        - /nfs/volume/user/conda_pkgs

In the example above, we tell conda to use the folder ``/nfs/volume/user/conda_envs``
to store all of the environments we create, and we tell conda to use
``/nfs/volume/user/conda_pkgs`` to store all of the packages that we download.

To save even more space, the contents of ``/nfs/volume/user/conda_pkgs`` will be
hard linked to the environments in ``/nfs/volume/user/conda_envs`` when possible.
This means that ``pkgs_dirs`` will normally take up the most space for a conda
installation. But, when hard linking is not possible, the files will be copied
over to the environment which means each new environment increases the amount
of disk space taken. To ensure this hard linking works properly, we recommend
to always store the ``envs_dirs`` and ``pkgs_dirs`` on the same mounted volume.
