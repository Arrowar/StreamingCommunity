import os
import re
from setuptools import setup, find_packages

# Variable
base_path = os.path.abspath(os.path.dirname(__file__))

def read_readme():
    readme_path = os.path.join(base_path, "README.md")
    if os.path.exists(readme_path):
        with open(readme_path, "r", encoding="utf-8") as fh:
            return fh.read()

def read_requirements():
    req_path = os.path.join(base_path, "requirements.txt")
    if os.path.exists(req_path):
        with open(req_path, "r", encoding="utf-8-sig") as f:
            return [line.strip() for line in f if line.strip() and not line.startswith("#")]

def get_version():
    try:
        import pkg_resources
        return pkg_resources.get_distribution('StreamingCommunity').version
    
    except Exception:
        version_file_path = os.path.join(os.path.dirname(__file__), "StreamingCommunity", "Upload", "version.py")
        with open(version_file_path, "r", encoding="utf-8") as f:
            version_match = re.search(r"^__version__\s*=\s*['\"]([^'\"]*)['\"]", f.read(), re.M)
        if version_match:
            return version_match.group(1)
        raise RuntimeError("Unable to find version string in StreamingCommunity/Upload/version.py.")

setup(
    name="StreamingCommunity",
    version=get_version(),
    description="Download content from streaming platforms",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    author="Arrowar",
    url="https://github.com/Arrowar/StreamingCommunity",
    packages=find_packages(
        exclude=["tests", "tests.*", "docs", "docs.*", "GUI", "GUI.*", "Test", "Test.*"]
    ),
    install_requires=read_requirements(),
    python_requires='>=3.8',
    entry_points={
        "console_scripts": [
            "streamingcommunity=StreamingCommunity.run:main",
        ],
    },
    include_package_data=False,
    package_data={
        '': ['*.txt', '*.md', '*.json', '*.yaml', '*.yml', '*.cfg'],
        'StreamingCommunity': ['**/*.txt', '**/*.json', '**/*.yaml'],
    },
    keywords="streaming community",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    project_urls={
        "Bug Reports": "https://github.com/Arrowar/StreamingCommunity/issues",
        "Source": "https://github.com/Arrowar/StreamingCommunity",
    }
)