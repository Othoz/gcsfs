import os
from setuptools import setup

from fs_gcsfs import __version__

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, "README.rst"), encoding="utf-8") as f:
    long_description = "\n" + f.read()


if __name__ == "__main__":
    setup(
        name="fs-gcsfs",
        version=__version__,
        author="Othoz GmbH",
        description="A PyFilesystem interface to Google Cloud Storage",
        long_description=long_description,
        long_description_content_type="text/x-rst",
        keywords=["pyfilesystem", "filesystem", "google", "gcs", "google cloud storage"],
        url="https://github.com/Othoz/gcsfs",
        packages=["fs_gcsfs"],
        license="MIT",
        python_requires=">=3.5",
        install_requires=[
            "fs~=2.0",  # TODO Test this + latest version with travis
            "google-cloud-storage~=1.0",  # TODO Test this + latest version with travis
        ],
        entry_points={
            "fs.opener": [
                "gs = fs_gcsfs.opener:GCSFSOpener",
            ]
        },
        classifiers=(
            "Development Status :: 4 - Beta",
            "Intended Audience :: Developers",
            "License :: OSI Approved :: MIT License",
            "Operating System :: OS Independent",
            "Programming Language :: Python",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.5",
            "Programming Language :: Python :: 3.6",
            "Programming Language :: Python :: 3.7",
            "Programming Language :: Python :: Implementation",
            "Topic :: System :: Filesystems",
        ),
    )
