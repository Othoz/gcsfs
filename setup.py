from setuptools import setup
from fs_gcsfs.__version__ import __version__

if __name__ == "__main__":
    setup(
        name='fs-gcsfs',
        author="Othoz",
        description="A PyFilesystem interface to Google Cloud Storage",
        url="https://github.com/Othoz/gcsfs",
        license="MIT",
        version=__version__,
        python_requires=">=3.5",
        install_requires=[
            "fs~=2.1.0"
        ],
        entry_points={
            'fs.opener': [
                'gs = fs_gcsfs.opener:GCSFSOpener',
            ]
        },
        packages=["fs_gcsfs"],
    )
