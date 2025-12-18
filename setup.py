"""ShowOnce - AI-powered workflow automation from screenshots."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="showonce",
    version="0.1.0",
    author="Venkata Sai",
    author_email="your.email@example.com",
    description="AI-powered tool that learns automation workflows from screenshots",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/showonce",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Testing",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.10",
    install_requires=[
        "python-dotenv>=1.0.0",
        "pydantic>=2.0.0",
        "click>=8.1.0",
        "Pillow>=10.0.0",
        "anthropic>=0.18.0",
        "playwright>=1.40.0",
        "mss>=9.0.0",
        "pynput>=1.7.6",
        "rich>=13.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "black>=23.0.0",
            "flake8>=6.1.0",
        ],
        "ui": [
            "streamlit>=1.29.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "showonce=showonce.cli:main",
        ],
    },
    keywords="automation, AI, screenshots, workflow, playwright, claude",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/showonce/issues",
        "Source": "https://github.com/yourusername/showonce",
        "Documentation": "https://github.com/yourusername/showonce/docs",
    },
)
