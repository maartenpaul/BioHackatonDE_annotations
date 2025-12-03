from setuptools import setup, find_packages

setup(
    name="biohack_utils",
    version="0.0.1",
    packages=find_packages(include=['biohack_utils', 'biohack_utils.*']),
    entry_points={
        "console_scripts": [
            "biohack_utils.delete_anns = biohack_utils.delete_annotations:main",
        ]
    }
)
