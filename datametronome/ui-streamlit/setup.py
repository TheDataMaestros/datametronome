from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="datametronome-ui-streamlit",
    version="0.1.0",
    author="DataMetronome Team",
    author_email="team@datametronome.dev",
    description="Default Streamlit user interface for DataMetronome",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/datametronome/datametronome",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Data Engineers",
        "Intended Audience :: Data Scientists",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Database",
        "Topic :: Scientific/Engineering :: Information Analysis",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.9",
    install_requires=[
        "streamlit>=1.28.0",
        "httpx>=0.25.0",
        "pandas>=2.0.0",
        "plotly>=5.17.0",
        "streamlit-ace>=0.1.1",
        "streamlit-option-menu>=0.3.6",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "flake8>=6.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "datametronome-ui=datametronome_ui_streamlit.main:main",
        ],
    },
)
