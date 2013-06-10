import logging

from progressbar import Bar, ETA, FileTransferSpeed, Percentage, ProgressBar


fetch_progress = ProgressBar(
    widgets=['', ' ', Percentage(), ' ', Bar(), ' ', ETA(), ' ',
             FileTransferSpeed()])

progress = ProgressBar(widgets=['', ' ', Bar(), ' ', Percentage()])


class FetchProgressHandler(logging.Handler):

    def emit(self, record):
        if record.name == 'fetch.start':
            filename, maxval = record.msg
            fetch_progress.widgets[0] = filename
            fetch_progress.maxval = maxval
            fetch_progress.start()

        elif record.name == 'fetch.update':
            n = record.msg
            fetch_progress.update(n)

        elif record.name == 'fetch.stop':
            fetch_progress.finish()


class ProgressHandler(logging.Handler):

    def emit(self, record):
        if record.name == 'progress.start':
            progress.maxval = record.msg
            progress.start()

        elif record.name == 'progress.update':
            name, n = record.msg
            progress.widgets[0] = '[%-20s]' % name
            progress.update(n)

        elif record.name == 'progress.stop':
            progress.widgets[0] = '[      COMPLETE      ]'
            progress.finish()


def setup_handlers():
    fetch_prog_logger = logging.getLogger('fetch')
    fetch_prog_logger.setLevel(logging.INFO)
    fetch_prog_logger.addHandler(FetchProgressHandler())

    prog_logger = logging.getLogger('progress')
    prog_logger.setLevel(logging.INFO)
    prog_logger.addHandler(ProgressHandler())
