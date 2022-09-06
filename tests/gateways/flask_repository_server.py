"""
Flask-based conda repository server for testing.

Change contents to simulate an updating repository.
"""

import flask

app = flask.Flask(__name__)

# flask.send_from_directory(directory, path, **kwargs)
# Send a file from within a directory using send_file().
@app.route("/<subdir>/<path:name>")
def download_file(subdir, name):
    # conditional=True is the default
    return flask.send_from_directory(
        app.config['UPLOAD_FOLDER'], name
    )

