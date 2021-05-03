# QAS-Editor
 Question and Answer Sheet Edior for importing, editing and exporting different extensions.  
 
 The goal of this repository is to create a tool that can be used both for automate and manually edit questions and answers. The extracture of the class is based on the Moodle XML format since this is the most complete file extension imported and exported so far in the tool. The initial sorce code was forked from [moodle-questions](https://github.com/gethvi/moodle-questions) and has some inspiration from [moodlexport](https://github.com/Guillaume-Garrigos/moodlexport) and [markdown2moodle](https://github.com/brunomnsilva/markdown2moodle).  

 So why is necessary one more Moodle import/export tool? Well, I think that is just because the current implementation are just not generic enought and I need something that was basicalle [moodle-questions](https://github.com/gethvi/moodle-questions) but could do all the other flows. 

The GUI uses code from [Megasolid Idiom](https://www.mfitzp.com/examples/megasolid-idiom-rich-text-editor/) (great editor by the way) and [pyqt-collapsible-widget](https://github.com/By0ute/pyqt-collapsible-widget).


## Requirements
 - Python3
 - PyQT5 if GUI is used

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
  - GUI to create and update questions manually
  - Import
    - Moodle XML file
    - Aiken file
    - GIFT file
    - Markdown files 
  - Export
    - Aiken file
    - Moodle XML file
    - JSON

## Next features
  - Import
    - Cloze file
    - LaTex (as MCQ)
    - JSON
  - Export 
    - Cloze file 
    - GIFT file 
    - LaTex (as MCQ) 
    - Markdown files 
  - Complete GUI
