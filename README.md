# QAS-Editor
 Question and Answer Sheet Edior for importing, editing and exporting different extensions.  
 
 The goal of this repository is to create a tool that can be used both for automate and  
 manually edit questions and answers. The extracture of the class is based on the Moodle  
 XML format since this is the most complete file extension imported and exported so far  
 in the tool. The initial sorce code was forked from [moodle-questions](https://github.com/adam-p/markdown-here/wiki/Markdown-Cheatsheet#links) and has some  
 inspiration from [moodlexport](https://github.com/Guillaume-Garrigos/moodlexport).  

 ## Requirements
 - Python3
 - PyQT5 if GUI is used

## Features
  - Hierarchical structures to more easily use and extend module
  - GUI to create and update questions manually
  - Import
    - Moodle XML file
    - Aiken file
    - JSON (internal format)
  - Export
    - Moodle XML file
    - JSON (internal format)

## Next features
  - Import
    - Cloze file
    - LaTex
    - GIFT file
    - Markdown files (as MCQ)
  - Export
    - Aiken file 
    - Cloze file 
    - GIFT file 
    - LaTex 
    - Markdown files (as MCQ)
  - Add LaTEX support using latex2mathml