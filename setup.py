"""
Setup configuration for ChatVault - OpenAI-compatible chat proxy with usage tracking.
"""

from setuptools import setup, find_packages

# Read README if it exists
try:
    with open("README.md", "r", encoding="utf-8") as fh:
        long_description = fh.read()
except FileNotFoundError:
    long_description = "ChatVault - OpenAI-compatible chat proxy with usage tracking and secure key management"

# Read requirements
def read_requirements(filename):
    with open(filename, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]

install_requires = read_requirements("requirements.txt")

setup(
    name="chatvault",
    version="1.0.0",
    author="ChatVault Team",
    author_email="",
    description="OpenAI-compatible chat proxy with usage tracking and secure key management",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-org/chatvault",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Security",
    ],
    python_requires=">=3.8",
    install_requires=install_requires + [
        "click>=8.0.0",
        "PyYAML>=6.0",
        "setuptools>=65.0",
        "wheel>=0.37.0",
    ],
    extras_require={
        "dev": read_requirements("requirements-dev.txt") if "requirements-dev.txt" else [],
        "test": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "chatvault=chatvault.cli:main",
            "cv-tester=chatvault.cv_tester:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)