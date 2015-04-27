import re
from conda.cli import common
from conda.resolve import normalized_version
try:
    from binstar_client import errors
    from binstar_client.utils import get_binstar
except ImportError:
    get_binstar = None

ENVIRONMENT_TYPE = 'env'


def can_download(handle):
    return re.match("^(.+)/(.+)$", handle)


def is_installed():
    return get_binstar is not None


def get(handle, filename, json):
    username, packagename = handle.split('/', 1)

    if not is_installed():
        common.error_and_exit("The binstar client must be installed to perform this action")

    binstar = get_binstar()
    try:
        package = binstar.package(username, packagename)
    except errors.NotFound:
            common.error_and_exit("The package %s/%s was not found on binstar. "
                                  "(If this is a private package, you may need to be logged in to see it."
                                  "Run 'binstar login')" %
                                  (username, packagename),
                                  json=json)

    file_data = [data for data in package['files'] if data['type'] == ENVIRONMENT_TYPE]
    if not len(file_data):
            common.error_and_exit("There are no environment.yaml files in the package %s/%s" %
                                  (username, packagename),
                                  json=json)

    versions = {normalized_version(d['version']):d['version'] for d in file_data}
    latest_version = versions[max(versions)]

    file_data = [data for data in package['files'] if data['version'] == latest_version]

    req = binstar.download(username, packagename, latest_version, file_data[0]['basename'])

    if req is None:
        common.error_and_exit("An error occurred wile downloading the file %s" %
                              file_data[0]['download_url'],
                              json=json)

    print("Successfully fetched %s/%s (wrote %s)" %
          (username, packagename, filename))

    return req.raw.read()
