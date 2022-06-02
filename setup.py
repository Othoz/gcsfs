import os
from setuptools import setup

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, "README.rst"), encoding="utf-8") as f:
    long_description = "\n" + f.read()


if __name__ == "__main__":
    setup(
        name="fs-gcsfs",
        use_scm_version=True,
        author="Othoz GmbH",
        author_email="wiesner@othoz.com",
        description="A PyFilesystem interface to Google Cloud Storage",
        long_description=long_description,
        long_description_content_type="text/x-rst",
        keywords=["pyfilesystem", "filesystem", "google", "gcs", "google cloud storage"],
        url="https://github.com/Othoz/gcsfs",
        project_urls={
            "Bug Tracker": "https://github.com/Othoz/gcsfs/issues",
            "Documentation": "http://fs-gcsfs.readthedocs.io/en/latest/",
        },
        packages=["fs_gcsfs"],
        license="MIT",
        python_requires=">=3.5",
        setup_requires=['setuptools_scm'],
        install_requires=[
            "fs~=2.2",  # require at least 2.2 since we are using functions such as readbytes() and writebytes() that have been introduced in 2.2
            "google-cloud-storage>=1.0",  # but 1.x and 2.x work. The major change in 2.x was to drop Python 2 support which fs-gcsfs does not support anyways.
            "urllib3~=1.25",
            "packaging>=20.0",  # does not use semver so there's no need to restrict to a fixed major version
            "requests~=2.20"
        ],
        entry_points={
            "fs.opener": [
                "gs = fs_gcsfs.opener:GCSFSOpener",
            ]
        },
        classifiers=[
            "Development Status :: 4 - Beta",
            "Intended Audience :: Developers",
            "License :: OSI Approved :: MIT License",
            "Operating System :: OS Independent",
            "Programming Language :: Python",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.5",
            "Programming Language :: Python :: 3.6",
            "Programming Language :: Python :: 3.7",
            "Programming Language :: Python :: 3.8",
            "Programming Language :: Python :: Implementation",
            "Topic :: System :: Filesystems",
        ],
    )
