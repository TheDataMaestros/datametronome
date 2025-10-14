from setuptools import setup, find_packages

setup(
    name="datametronome-ui-streamlit",
    version="0.1.0",
    description="Streamlit UI for DataMetronome",
    packages=find_packages(),
    install_requires=[
        "streamlit>=1.28.0",
        "plotly>=5.17.0",
        "pandas>=2.0.0",
        "numpy>=1.24.0",
        "httpx>=0.25.0",
    ],
    python_requires=">=3.9",
)
