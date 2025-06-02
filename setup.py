import os
from setuptools import setup, find_packages

def read_readme():
    with open("README.md", "r", encoding="utf-8") as fh:
        return fh.read()
    
with open(os.path.join(os.path.dirname(__file__), "requirements.txt"), "r", encoding="utf-8-sig") as f:
    required_packages = f.read().splitlines()

setup(
    name="StreamingCommunity",
    version="3.0.9",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    author="Lovi-0",
    url="https://github.com/Lovi-0/StreamingCommunity",
    packages=find_packages(include=["StreamingCommunity", "StreamingCommunity.*"]),
    install_requires=required_packages,
    python_requires='>=3.8',
    entry_points={
        "console_scripts": [
            "streamingcommunity=StreamingCommunity.run:main",
        ],
    },
    include_package_data=True,
    keywords="streaming community",
    project_urls={
        "Bug Reports": "https://github.com/Lovi-0/StreamingCommunity/issues",
        "Source": "https://github.com/Lovi-0/StreamingCommunity",
    }
) 