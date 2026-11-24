from setuptools import setup, find_packages

setup(
    name="scrapalyser",
    version="0.1.2",
    author="alex34500",
    description="Pre-scraping intelligence tool — scan a website before scraping it",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/alex34500/scrapalyser",
    packages=find_packages(),
    install_requires=[
        "curl_cffi>=0.7.0",
        "beautifulsoup4>=4.12.0",
        # Used automatically when curl_cffi is blocked
        "playwright>=1.44.0",
    ],
    extras_require={
        # Kept so that `pip install scrapalyser[playwright]` still works
        "playwright": [],
    },
    python_requires=">=3.9",
    license="MIT",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
