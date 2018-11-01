from setuptools import setup
import versioneer


if __name__ == "__main__":
    setup(
        name='fs-gcsfs',
        author="Othoz",
        description="A PyFilesystem interface to Google Cloud Storage",
        url="http://othoz.com",  # TODO This will become the Github Repo URL
        license="MIT",
        version=versioneer.get_version(),
        cmdclass=versioneer.get_cmdclass(),
        install_requires=[
            "fs~=2.1.0"
        ],
        entry_points={
            'fs.opener': [
                'gs = gcsfs.opener:GCSFSOpener',
            ]
        },
        packages=["gcsfs"],
        # By default setuptools tries to detect automagically if a package can be zipped. However,
        # a zipped package does seem to not work well with conda - so we force setuptools to not
        # zip the package
        zip_safe=False,
        # Missing: python_requires
    )
