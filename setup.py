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
    ],
    python_requires=">=3.7",
    install_requires=[
        "PyQt5 >= 5.15.0"
    ],
    extras_require={
        #"PyPDF2 >= 1.26.0",
        #"Pillow >= 9.0.0",
        #"python-docx"
    }
)
