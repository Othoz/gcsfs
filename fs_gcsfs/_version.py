import subprocess
import logging

try:
    __version__ = subprocess.check_output(["git", "describe"]).decode().strip()
except subprocess.CalledProcessError:
    logging.error("Please only import {} from within a git repository with at least one tagged commit".format(__file__))
    __version__ = "unknown"
