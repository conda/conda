import logging

from progressbar import Bar, ETA, FileTransferSpeed, Percentage, ProgressBar


progress = ProgressBar(
    widgets=['', ' ', Percentage(), ' ', Bar(), ' ', ETA(), ' ',
             FileTransferSpeed()])


class ConsoleProgressHandler(logging.Handler):

    def emit(self, record):
        if record.name == 'progress.start':
            d = record.msg
            progress.widgets[0] = d['filename']
            progress.maxval = d['maxval']
            progress.start()

        elif record.name == 'progress.update':
            n = record.msg
            progress.update(n)

        elif record.name == 'progress.stop':
            progress.finish()


def setup_handlers():
    prog_logger = logging.getLogger('progress')
    prog_logger.setLevel(logging.INFO)
    prog_logger.addHandler(ConsoleProgressHandler())
