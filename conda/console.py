import logging

from progressbar import Bar, ETA, FileTransferSpeed, Percentage, ProgressBar


fetch_progress = ProgressBar(
    widgets=['', ' ', Percentage(), ' ', Bar(), ' ', ETA(), ' ',
             FileTransferSpeed()])


class FetchProgressHandler(logging.Handler):

    def emit(self, record):
        if record.name == 'fetch.start':
            d = record.msg
            fetch_progress.widgets[0] = d['filename']
            fetch_progress.maxval = d['maxval']
            fetch_progress.start()

        elif record.name == 'fetch.update':
            n = record.msg
            fetch_progress.update(n)

        elif record.name == 'fetch.stop':
            fetch_progress.finish()


def setup_handlers():
    prog_logger = logging.getLogger('fetch')
    prog_logger.setLevel(logging.INFO)
    prog_logger.addHandler(FetchProgressHandler())
