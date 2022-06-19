<div align="center">
  <img src="https://badge.fury.io/gh/LucasWolfgang%2FQAS-editor.svg">
  <img src="https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/LucasWolfgang/344598a4a0f7b92a7889d998e33417c4/raw/pylint_3.7.json">
  <img src="https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/LucasWolfgang/344598a4a0f7b92a7889d998e33417c4/raw/pytest_3.7.json">
  <img src="https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/LucasWolfgang/344598a4a0f7b92a7889d998e33417c4/raw/flake8_3.7.json">
</div>

<div align="center">
:exclamation: There is NO stable release so far. The frontend (UI) changes daily, and the backend, montly. :exclamation:
</div><br/>

# QAS-Editor
Question and Answer Sheet Editor is both a python API and a UI utility to automate/help with tasks related to the creation, deletion, update, organization and convertion of question databases.
 
The structure of the class is based on the Moodle XML. The initial source code was forked from [moodle-questions](https://github.com/gethvi/moodle-questions) and has some inspiration from [moodlexport](https://github.com/Guillaume-Garrigos/moodlexport) and [markdown2moodle](https://github.com/brunomnsilva/markdown2moodle)

The GUI uses code from [Megasolid Idiom](https://www.mfitzp.com/examples/megasolid-idiom-rich-text-editor/), [pyqt-collapsible-widget](https://github.com/By0ute/pyqt-collapsible-widget) and [Creating A Tag Bar In PySide](https://robonobodojo.wordpress.com/2018/09/11/creating-a-tag-bar-in-pyside/).

## Requirements
- Requires at least Python 3. If using all dependencies, at least Python 3.6.
- Use the setup.py to install the package using:

    ```python setup.py install```  
    or   
    ```python -m pip install .```  

## Features
  - Hierarchical structures to more easily use and extend module.
 <center>
 
 |  Type                  | Class |  GUI  | Test | Type             | Class |  GUI  | Test |
 | ---------------------- | :---: | :---: | :--: | ---------------- | :---: | :---: | :--: |
 | Calculated             |  :o:  |  :x:  |  :x: | Matching         |  :o:  |  :x:  |  :x: |
 | Calculated multichoice |  :o:  |  :x:  |  :x: | Cloze (Gap Fill) |  :o:  |  :o:  |  :x: |
 | Calculated simple      |  :o:  |  :x:  |  :x: | Multiple choice  |  :o:  |  :o:  |  :x: |
 | Drag and drop text     |  :o:  |  :x:  |  :x: | Short Answer     |  :o:  |  :x:  |  :x: |
 | Drag and drop markers  |  :o:  |  :x:  |  :x: | Numerical        |  :o:  |  :x:  |  :x: |
 | Drag and drop image    |  :o:  |  :x:  |  :x: | Random matching  |  :o:  |  :x:  |  :x: |
 | Description            |  :o:  |  :o:  |  :x: | Missing word     |  :o:  |  :x:  |  :x: |
 | Essay                  |  :o:  |  :x:  |  :x: | True/False       |  :o:  |  :x:  |  :x: | 
 </center><br/

 - A GUI to create, delete, modify and organize questions
 <center>
  
 ![QAS editor GUI](https://user-images.githubusercontent.com/39681420/170771346-1e1d532b-6745-4125-b647-d704d645e5c4.png)
 </center><br/>

 - Many different import and export formats
 <center>
  
 |  Type      | Import | Export | Test | Type              | Import | Export | Test |
 | ---------- | :----: | :----: | :--: | ----------------- | :----: | :----: | :--: |
 | Aiken      |   :o:  |   :o:  |  :o: | Markdown (MCQ)    |   :o:  |   :x:  |  :x: |
 | Anki       |   :x:  |   :x:  |  :x: | Moodle            |   :o:  |   :o:  |  :o: |
 | BlackBoard |   :x:  |   :x:  |  :x: | PDF               |   :x:  |   :x:  |  :x: |
 | Canvas LMS |   :x:  |   :x:  |  :x: | Quizlet           |   :x:  |   :x:  |  :x: |
 | Cloze      |   :o:  |   :x:  |  :x: | Tex (AMQ)         |   :x:  |   :x:  |  :x: |
 | GIFT       |   :o:  |   :x:  |  :x: | Tex (moodlexport) |   :o:  |   :x:  |  :x: |
 | HDF5       |   :x:  |   :x:  |  :x: | Tex (MCexam)      |   :x:  |   :x:  |  :x: |
 | QAS (json) |   :o:  |   :o:  |  :o: | Tex (alterqcm)    |   :x:  |   :x:  |  :x: |
 | Kahoot     |   :x:  |   :o:  |  :x: |
</center ><br/>

## Contributing
This one is a really large project, and I would appreciate if you could contribute to it. Currently the reporistory can be improved by:
 * updating documentation (in-code and wiki);
 * adding examples;
 * adding new parsers;
 * improving parsers performance;
 * adding UI functionalities;
 * adding pytests;
 * improving code quality (flake8 and pylint).

To contribute to this repo just do the usual. Fork, modify and send a PR.
No need to create a separate branch, unless you want to deliver your updates in chunks.
Always make sure all tests are passing before submitting the PR.
It does not need to be fully documented, nor fully pass pylint and flake8, but this would make me pretty happy :).

Here are some points to consider before submitting a PR:
 * This python module is a desktop API/utility. Try your best to keep eveything local. If the only way to import/export the database is connecting to a website or other external service, you may still submit the PR, but it is very likely that it will be not accepted.
 * This module strives to be as pure python and light as possible. Only submit PRs that add new packages/modules to be intalled by the end user if the work needed to implement the code would be herculean, or the module/package can be reused in multiple other parts of the code improving readability and performance.
 * The scope of this repo is only of converting and modifying question databases (creating, deleting, modifying and reorganizing questions).

  Thank you,\
  Wolfgang\
  :blush:
