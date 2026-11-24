from setuptools import setup, find_packages

setup(
    name="scrapalyser",
    version="0.2.0",
    author="alex34500",
    description="Pre-scraping intelligence tool — scan a website before scraping it",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/codesme34/scrapalyser",
    project_urls={
        "Source": "https://github.com/codesme34/scrapalyser",
        "Changelog": "https://github.com/codesme34/scrapalyser/blob/main/CHANGELOG.md",
        "Issues": "https://github.com/codesme34/scrapalyser/issues",
    },
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
        "dev": ["pytest>=7.0"],
    },
    entry_points={
        "console_scripts": ["scrapalyser=scrapalyser.cli:main"],
    },
    python_requires=">=3.9",
    license="MIT",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
