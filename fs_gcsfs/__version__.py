import subprocess  # nosec

try:
    __version__ = subprocess.check_output(["git", "describe"]).decode().strip()  # nosec
except subprocess.CalledProcessError:
    print("Please only import {} from within a git repository with at least one tagged commit".format(__file__))
    __version__ = "unknown"
