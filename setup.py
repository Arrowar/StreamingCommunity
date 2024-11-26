from setuptools import setup


def read_readme():
    with open("README.md", "r", encoding="utf-8") as fh:
        return fh.read()
    
with open("requirements.txt", "r", encoding="utf-8-sig") as f:
    required_packages = f.read().splitlines()
    print(required_packages)

setup(
    name="StreamingCommunity",
    version="1.7.5",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    author="Lovi-0",
    url="https://github.com/Lovi-0/StreamingCommunity",
    packages=["StreamingCommunity"],
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
