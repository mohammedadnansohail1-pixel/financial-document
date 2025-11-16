"""
Setup script for Financial Report Intelligence System
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="financial-report-intelligence",
    version="1.0.0",
    author="Your Organization",
    author_email="contact@example.com",
    description="Production-level Financial Report Intelligence with RefRAG",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-org/financial-report-intelligence",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Financial and Insurance Industry",
        "Topic :: Office/Business :: Financial :: Investment",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "pytest-asyncio>=0.21.1",
            "pytest-cov>=4.1.0",
            "black>=23.11.0",
            "flake8>=6.1.0",
            "mypy>=1.7.1",
            "pylint>=3.0.3",
        ],
        "gpu": [
            "torch==2.1.1+cu118",
            "faiss-gpu>=1.7.2",
        ],
    },
    entry_points={
        "console_scripts": [
            "finrag-server=api.server:main",
            "finrag-cli=utils.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.yaml", "*.yml", "*.json"],
    },
    zip_safe=False,
    keywords=[
        "financial-analysis",
        "rag",
        "retrieval-augmented-generation",
        "sec-filings",
        "earnings-analysis",
        "investment-research",
        "knowledge-graph",
        "temporal-analysis",
        "compliance",
        "nlp",
        "machine-learning",
    ],
    project_urls={
        "Bug Reports": "https://github.com/your-org/financial-report-intelligence/issues",
        "Documentation": "https://docs.finrag.example.com",
        "Source": "https://github.com/your-org/financial-report-intelligence",
    },
)
