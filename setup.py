import re

from setuptools import find_packages, setup

with open("src/parrottools/__version__.py", encoding="utf8") as f:
    data = f.read()
    version = re.search(r'__version__ = "(.*?)"', data).group(1)  # type: ignore
    title = re.search(r'__title__ = "(.*?)"', data).group(1)  # type: ignore

setup(
    name=title,
    description="Collection of common utilities.",
    url="https://github.com/parrot-com/parrottools",
    project_urls={"Source Code": "https://github.com/parrot-com/parrottools"},
    author="Parrot",
    maintainer="Parrot",
    keywords=["observability", "logging"],
    version=version,
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.7",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
    install_requires=["structlog~=21.1.0", "sentry-sdk~=0.19.5"],
    extras_require={
        "tests": ["pytest>=6.2.1"],
        "dev": ["pytest>=6.2.1", "pre-commit>=2.9.3"],
    },
    include_package_data=True,
)
