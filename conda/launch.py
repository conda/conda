HOST = "127.0.0.1"
PORT = 5007

def launch(notebook, server=None):
    """ launch the app view of the specified notebook, using a server.
        If the server is not specified, assume localhsot and (try to)
        start it.
    """

    import ipyapp
    import webbrowser
    from os.path import abspath

    if not server:
        ipyapp.start_local_server(port=PORT)
        server = "http://{host}:{port}".format(host=HOST, port=PORT)

    nbpath = abspath(notebook)
    webbrowser.open("{prefix}/?nbfile={nbpath}".format(prefix=server, nbpath=nbpath)
