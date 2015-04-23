from conda_env.utils.spec import Spec
from conda.cli import common
from conda.resolve import normalized_version
from binstar_client import errors
from binstar_client.utils import get_binstar


ENVIRONMENT_TYPE = 'env'


def download_environment_file(package_spec, filename, json=False):
    """
    Download an environment file from binstar

    :param package_spec: a binstar package specification string eg sean/environment1
    :param filename: The file name to write the environment yaml file to
    :param json: write json output
    """
    # TODO: check MD5 version requirement is in the spec
    # TODO: check MD5 of file before fetching it again

    binstar = get_binstar()

    spec = Spec(package_spec)

    if not spec.username:
        common.error_and_exit("Username is required for binstar "
                              "environment specification",
                              json=json)

    try:
        package = binstar.package(spec.username, spec.package_name)
    except errors.NotFound:
            common.error_and_exit(("The package %s/%s was not found on binstar. "
                                   "(If this is a private package, you may need to be logged in to see it. run 'binstar login')" %
                                   (spec.username, spec.package_name)),
                                  json=json)

    file_data = [data for data in package['files'] if data['type'] == ENVIRONMENT_TYPE]
    if not len(file_data):
            common.error_and_exit(("There are no environment.yaml files in the package %s/%s" %
                                   (spec.username, spec.package_name)),
                                  json=json)

    versions = {normalized_version(d['version']):d['version'] for d in file_data}
    latest_version = versions[max(versions)]

    file_data = [data for data in package['files'] if data['version'] == latest_version]

    req = binstar.download(spec.username, spec.package_name, latest_version, file_data[0]['basename'])

    if req is None:
        common.error_and_exit(("An error occurred wile downloading the file %s" %
                               (file_data[0]['download_url'])),
                              json=json)

    with open(filename, 'w') as fd:
        fd.write(req.raw.read())

    print("Successfully fetched %s/%s (wrote %s)" %
          (spec.username, spec.package_name, filename))
