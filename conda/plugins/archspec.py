from conda import plugins


@plugins.hookimp
def conda_cli_register_virtual_packages():
    from conda.core.index import get_archspec_name

    yield plugins.CondaVirtualPackage('archspec', get_archspec_name())
