from setuptools import setup, find_packages

setup(
    name="showonce",
    version="1.0.0",
    author="Venkata Sai",
    author_email="venkata@example.com",
    description="AI-powered automation tool that learns workflows from screenshots",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/venkata2894/ShowOnce",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "python-dotenv>=1.0.0",
        "pydantic>=2.0.0",
        "click>=8.1.0",
        "Pillow>=10.0.0",
        "imagehash>=4.3.0",
        "anthropic>=0.18.0",
        "playwright>=1.40.0",
        "pyautogui>=0.9.54",
        "mss>=9.0.0",
        "pynput>=1.7.6",
        "rich>=13.0.0",
        "tqdm>=4.66.0",
        "streamlit>=1.29.0",
    ],
    entry_points={
        "console_scripts": [
            "showonce=showonce.cli:cli",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Testing",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.10",
)
