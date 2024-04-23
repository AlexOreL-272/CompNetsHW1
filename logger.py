from datetime import datetime
import threading


class Logger:
    """
        Class for logging
    """

    def __init__(self, filename):
        """
            Construct a logger
            filename: (string) name of the file to log to
        """

        self.mu = threading.Lock()

        self.filename = filename
        with open(self.filename, "w") as f:
            f.truncate(0)
            f.write("Starting logging...\n")

    def log(self, msg):
        """
            Log a message
            msg: (string) message to log
        """

        self.mu.acquire()
        with open(self.filename, "a") as f:
            f.write(
                f"===> ({threading.current_thread().name}) ({datetime.now()}) {msg}\n")
        self.mu.release()
