from setuptools import setup, find_packages

setup(
    name="china_auto_sales_scraper",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "openai>=1.0.0",
        "python-dotenv",
        "tenacity",
        "termcolor",
        "tiktoken",
        "langsmith",
        "instructor",
        "pydantic",
        "aiohttp",
        "firecrawl"
    ],
    python_requires=">=3.8",
    author="Your Name",
    author_email="your.email@example.com",
    description="A scraper for Chinese auto sales data",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
) 