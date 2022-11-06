from setuptools import setup

setup(
   name="QAS Editor",
   version="0.0.5",
   description="Question and Answer Sheet editor",
   author="Lucas Wolfgang",
   author_email="lucawolfcs@hotmail.com",
   url="https://github.com/LucasWolfgang/QAS-Editor",
   packages=["qas_editor"],
   classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GPL-3.0 license",
        "Operating System :: OS Independent",
        'Development Status :: 3 - Alpha',
        "Topic :: Education",
        "Topic :: Software Development :: Libraries"
    ],
    python_requires=">=3.7",
    install_requires=[],
    extras_require={
        "formulae" : ["sympy", "matplotlib"],
        # For users that need to work with formulae and graphs. Includes:
        #   cycler, fonttools, kiwisolver, numpy, packaging, pillow, pyparsing,
        #   mpmath, python-dateutil
        "gui": ["PyQt5 >= 5.15.0"],
        # For users that need to use the GUI. Includes:
        #   PyQt5-Qt5, PyQt5-sip
        "docx": ["odfpy"],
        # For users that need convert ODF files. Includes:
        #   TODO
        "test": ["pytest", "pytest-qt"]
        # For users that want to run tests.
    },
    zip_safe=False,     # TODO Need to update the resource management
    platforms='any'
)