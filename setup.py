from setuptools import setup, find_packages

setup(
    name="hydrocron",
    version="0.1.0",
    description="A Python module for interacting with NASA Hydrocron PriorLake API products.",
    author="Alexander Marquez",
    packages=find_packages(),
    install_requires=[
        "pandas>=2.0.0",
        "geopandas>=0.14.0",
        "requests>=2.31.0",
    ],
    python_requires=">=3.9",
)
