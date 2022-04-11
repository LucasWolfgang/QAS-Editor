![Pylint](https://github.com/LucasWolfgang/QAS-Editor/actions/workflows/regression.yml/pylint.svg)
![Pylint](https://github.com/LucasWolfgang/QAS-Editor/actions/workflows/regression.yml/badge.svg)

# QAS-Editor
 Question and Answer Sheet Editor for importing, editing and exporting different extensions.  
 
 The goal of this repository is to create a tool that can be used both for automate and manually edit questions and answers. The extracture of the class is based on the Moodle XML format since this is the most complete file extension imported and exported so far in the tool. The initial sorce code was forked from [moodle-questions](https://github.com/gethvi/moodle-questions) and has some inspiration from [moodlexport](https://github.com/Guillaume-Garrigos/moodlexport) and [markdown2moodle](https://github.com/brunomnsilva/markdown2moodle).  

 So why is necessary one more Moodle import/export tool? Well, I think that is just because the current implementation are just not generic enought and I need something that was basicalle [moodle-questions](https://github.com/gethvi/moodle-questions) but could do all the other flows. 

The GUI uses code from [Megasolid Idiom](https://www.mfitzp.com/examples/megasolid-idiom-rich-text-editor/) (great editor by the way), [pyqt-collapsible-widget](https://github.com/By0ute/pyqt-collapsible-widget) (very organized) and [Creating A Tag Bar In PySide](https://robonobodojo.wordpress.com/2018/09/11/creating-a-tag-bar-in-pyside/) (great idea). All these coded were modified a lot, but even so, thank a lot for those who coded them.


## Requirements
 - Requires at least Python 3. If using all dependencies, at least Python 3.6.
 - Use the requirements.txt file to get all the required dependencies installed to be able to fully use the library. 

    ```python -pip install -r requirements.txt```
  
  - <i>PyQt</i> is only necessary to use the GUI, of course.
  - <i>PyPDF2</i> and <i>Pillow</i> may be replaced by <i>PikePDF</i> in the future.

## Features
  - Hierarchical structures to more easily use and extend module. All moodle objects implemented:
 <center>

 |  Type                   |  Available         | Type             |  Available         |
 | ----------------------- |  :---------------: | ---------------- |  :---------------: |
 | Calculated              | :heavy_check_mark: | Matching         | :heavy_check_mark: |
 | Calculated multi-choice | :heavy_check_mark: | Cloze (Gap Fill) | :heavy_check_mark: |
 | Calculated simple       | :heavy_check_mark: | Multiple choice  | :heavy_check_mark: |
 | Drag and drop text      | :heavy_check_mark: | Short Answer     | :heavy_check_mark: |
 | Drag and drop markers   | :heavy_check_mark: | Numerical        | :heavy_check_mark: |
 | Drag and drop image     | :heavy_check_mark: | Random matching  | :heavy_check_mark: |
 | Description             | :heavy_check_mark: | Missing word     | :heavy_check_mark: |
 | Essay                   | :heavy_check_mark: | True/False       | :heavy_check_mark: | 
 </center>

 <sup><sup>1</sup> Original table from [moodle-questions](https://github.com/gethvi/moodle-questions)</sup>
  - Import
    - Aiken file
    - Cloze file
    - GIFT file
    - JSON
    - Markdown files 
    - Moodle XML file
  - Export
    - Aiken file
    - Moodle XML file
    - JSON
  - GUI to create and update questions manually
<img src="https://user-images.githubusercontent.com/39681420/154966147-ed3b0661-5709-4942-97b5-dcdc33c88f29.png" alt="drawing" width="600" height="420"/>

## Next features
  - Import
    - LaTex (as MCQ)
  - Export 
    - Cloze file 
    - GIFT file 
    - LaTex (as MCQ) 
    - Markdown files 
  - Complete GUI

# Open to ideas
  - Have any format that you want to see the tool able to import or export?
  - Have any suggestions for the GUI?
  Just create an issue! One day I will definently work on it (if it is a good idea, of course).
  
  Thank you,\
  Wolfgang\
  :blush:
