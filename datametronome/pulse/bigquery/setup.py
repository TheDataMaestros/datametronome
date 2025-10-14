"""
Setup configuration for metronome-pulse-bigquery
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="metronome-pulse-bigquery",
    version="0.1.0",
    author="DataMetronome Team",
    author_email="team@datametronome.dev",
    description="BigQuery DataPulse connector for the DataMetronome ecosystem",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/datametronome/datametronome",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Database",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.9",
    install_requires=[
        "metronome-pulse-core>=0.1.0",
        "google-cloud-bigquery>=3.0.0",
        "google-auth>=2.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "mypy>=1.0.0",
        ],
    },
)

