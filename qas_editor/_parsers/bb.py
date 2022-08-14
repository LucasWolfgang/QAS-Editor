""""
Question and Answer Sheet Editor <https://github.com/LucasWolfgang/QAS-Editor>
Copyright (C) 2022  Lucas Wolfgang

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
import re
import os
import uuid
import sympy
import random
from zipfile import ZipFile, ZIP_DEFLATED
from xml.etree import ElementTree as etree
from typing import TYPE_CHECKING

from qas_editor.enums import ShuffleType
from ..question import QMultichoice, QShortAnswer, QTrueFalse, QNumerical,\
                       QMultichoice, QCloze
from ..utils import serialize_fxml, render_latex
if TYPE_CHECKING:
    from typing import Dict
    from ..category import Category
    from ..utils import FText
    from ..question import _Question, _QHasOptions


__doc__= """BlackBoard uses a modified version of QTI Content Package v1.2.
            See https://www.imsglobal.org/content/packaging/index.html.
            https://www.imsglobal.org/question/qtiv1p2/imsqti_res_bestv1p2.html
            https://www.imsglobal.org/question/qtiv1p2/imsqti_asi_outv1p2.html
            """

def roundSF(val, sf):
    return float('{:.{p}g}'.format(val, p=sf))

def regexSF(val, sf):
    #This is not really functional. It will match floats but not with rounding restrictions!
    #Match the start of the string and any initial whitespace
    regex="^[ ]*" 

    #Match the sign of the variable
    if val < 0:
        regex = regex +'-' #negative is required
    else:
        regex = regex +'\+?' #plus is optional

    #Round the figure to the required S.F.
    val = str(roundSF(abs(val), sf))
    
    didx=val.find('.')
    if didx == -1:
        didx = len(val)
    
    if val[0]=='0':
        regex += re.search('(0\.[0]*[0-9]{0,'+str(sf)+'})', val).group(0) + "[0-9]*[ ]*"
    elif didx>=sf:
        regex += val[:sf]+"[0-9]{"+str(didx-sf)+'}(.|($|[ ]+))'
    else:
        regex += val[:sf+1].replace('.', r'\.')
    return regex

class Pool:

    def __init__(self, package: "Package", cat: "Category", instructions=""):
        """Initialises a question pool
        """
        self.pkg = package
        self.cat = cat
        self.pool_name = cat.name
        self.questestinterop = etree.Element("questestinterop")
        assessment = etree.SubElement(self.questestinterop, 'assessment', {'title':self.pool_name})

        self.metadata(assessment, 'Assessment', 'Pool', weight=0)
        
        rubric = etree.SubElement(assessment, 'rubric', {'view':'All'})
        flow_mat = etree.SubElement(rubric, 'flow_mat', {'class':'Block'})
        self.material(flow_mat, instructions)

        presentation_material = etree.SubElement(assessment, 'presentation_material')
        flow_mat = etree.SubElement(presentation_material, 'flow_mat', {'class':'Block'})
        self.material(flow_mat, cat.info)

        self.section = etree.SubElement(assessment, 'section')
        
        self.metadata(self.section, 'Section', 'Pool', weight=0)

    def material(self, node, text):
        material = etree.SubElement(node, 'material')
        mat_extension = etree.SubElement(material, 'mat_extension')
        etree.SubElement(mat_extension, 'mat_formattedtext',
                         {'type':'HTML'}).text = text

    def metadata(self, node: etree.Element, name: str, typename='Pool',
                 qtype='Multiple Choice', scoremax=0, weight=0,
                 sectiontype='Subsection', instructor_notes='',
                 partialcredit='false', negpoints='N', ntype='none'):
        md = etree.SubElement(node, name.lower()+'metadata')
        for key, val in [
                ('bbmd_asi_object_id', '_'+str(self.pkg.bbid())+'_1'),
                ('bbmd_asitype', name),
                ('bbmd_assessmenttype', typename),
                ('bbmd_sectiontype', sectiontype),
                ('bbmd_questiontype', qtype),
                ('bbmd_is_from_cartridge', 'false'),
                ('bbmd_is_disabled', 'false'),
                ('bbmd_negative_points_ind', negpoints),
                ('bbmd_canvas_fullcrdt_ind', 'false'),
                ('bbmd_all_fullcredit_ind', 'false'),
                ('bbmd_numbertype', ntype),
                ('bbmd_partialcredit', partialcredit),
                ('bbmd_orientationtype', 'vertical'),
                ('bbmd_is_extracredit', 'false'),
                ('qmd_absolutescore_max', str(scoremax)),
                ('qmd_weighting', str(weight)),
                ('qmd_instructornotes', instructor_notes),
        ]:
            etree.SubElement(md, key).text = val

    def close(self):
        self.pkg.embed_resource(self.pool_name, "assessment/x-bb-qti-pool",
                                '<?xml version="1.0" encoding="UTF-8"?>\n' + 
                                etree.tostring(self.questestinterop, 
                                               pretty_print=False).decode('utf-8'))
              
    def _question(self, qst: _Question, qtype: str, partialcredit='false',
                  negpoints='N', ntype='none'):
        if 0.0 in qst.feedbacks:
            ifdbk = qst.feedbacks[0.0].get_string(self.embed_file)
        else:
            ifdbk = ""
        if 100.0 in qst.feedbacks:
            cfdbk = qst.feedbacks[100.0].get_string(self.embed_file)
        else:
            cfdbk = ""
        item = etree.SubElement(self.section, 'item', title = qst.name, 
                                maxattempts=qst.max_tries)
        self.metadata(item, 'Item', 'Pool',  qtype, qst.default_grade, 1,
                      'Subsection', qst.notes, partialcredit, negpoints, ntype)
        presentation = etree.SubElement(item, 'presentation')
        block = etree.SubElement(presentation, 'flow', {'class':'Block'})
        qblock = etree.SubElement(block, 'flow', {'class':'QUESTION_BLOCK'})
        ftblock = etree.SubElement(qblock, 'flow', {'class':'FORMATTED_TEXT_BLOCK'})
        self.material(ftblock, qst.question.get_string(self.pkg.embed_file))
        rblock = etree.SubElement(block, 'flow', {'class':'RESPONSE_BLOCK'})
        resp_proc = etree.SubElement(item, 'resprocessing',
                                         scoremodel='SumOfScores')
        fdbk = etree.SubElement(item, 'itemfeedback', ident='correct', view='All')
        self.flow_mat2(fdbk, cfdbk) 
        fdbk = etree.SubElement(item, 'itemfeedback', ident='incorrect', view='All')
        self.flow_mat2(fdbk, ifdbk)
        return item, block, rblock, resp_proc

    def _hasoptions(self, qst: _QHasOptions, qtype: str):
        item, _, flow2, resprocessing = self._question(qst, qtype)
        resp = etree.SubElement(flow2, 'response_lid', ident='response', rtiming='No')
        render_choice = etree.SubElement(resp, 'render_choice', 
                                         minnumber='0', maxnumber='0')
        if qst.shuffle != ShuffleType.NEVER:
            render_choice.attrib["shuffle"] = 'Yes' 
        else:
            render_choice.attrib["shuffle"] = 'No'                        
        flow_label = etree.SubElement(render_choice, 'flow_label', {'class':'Block'})
        non_zero = 0
        for opt in qst.options:
            luuid = uuid.uuid4().hex
            label = etree.SubElement(flow_label, 'response_label',
                                     ident=luuid, shuffle='Yes', 
                                     rarea='Ellipse', rrange='Exact')
            flow_mat = etree.SubElement(label, 'flow_mat', {'class':'Block'})
            material = etree.SubElement(flow_mat, 'material')
            etree.SubElement(material, 'mattext', {'charset':'us-ascii',
                             'texttype':'text/plain'}).text = opt.text.text
            respcondition = etree.SubElement(resprocessing, 'respcondition')
            conditionvar = etree.SubElement(respcondition, 'conditionvar')
            etree.SubElement(conditionvar, 'varequal', {'respident':luuid, 'case':'No'})
            etree.SubElement(respcondition, 'setvar', variablename='SCORE',
                             action='Set').text = opt.fraction
            if opt.fraction != 0:
                non_zero += 1
            etree.SubElement(respcondition, 'displayfeedback', linkrefid=luuid,
                             feedbacktype='Response')
            itemfeedback = etree.SubElement(item, 'itemfeedback', ident=luuid,
                                            view='All')
            solution = etree.SubElement(itemfeedback, 'solution', view='All',
                                        feedbackstyle='Complete')
            solutionmaterial = etree.SubElement(solution, 'solutionmaterial')
            self.flow_mat2(solutionmaterial, '')
        if non_zero == 1:
            resp.attrib["rcardinality"] = "Single"
        elif qst.ordered:
            resp.attrib["rcardinality"] = "Ordered"
        else:
            resp.attrib["rcardinality"] = "Multiple"
        return item, flow2, resprocessing
        
    def addNumQ(self, qst: QNumerical):
        """Numeric
        Done
        """
        errlow = float(qst.options[0].text) - qst.options[0].tolerance
        errhigh = float(qst.options[0].text) + qst.options[0].tolerance
        _, _, flow2, resprocessing = self._question(qst, 'Numeric')
        response_num = etree.SubElement(flow2, 'response_num', ident='response',
                                        rcardinality='Single', rtiming='No')
        etree.SubElement(response_num, 'render_fib', charset='us-ascii',
                         encoding='UTF_8', rows='0', columns='0', maxchars='0',
                         prompt='Box', fibtype='Decimal', minnumber='0',
                         maxnumber='0')
        respcondition = etree.SubElement(resprocessing, 'respcondition', {'title':uuid.uuid4().hex})
        conditionvar = etree.SubElement(respcondition, 'conditionvar')
        etree.SubElement(conditionvar, 'vargte', {'respident':'response'}).text = errlow
        etree.SubElement(conditionvar, 'varlte', {'respident':'response'}).text = errhigh
        etree.SubElement(conditionvar, 'varequal', {'respident':'response', 'case':'No'}).text = qst.options[0].text
        etree.SubElement(respcondition, 'displayfeedback', {'linkrefid':'correct', 'feedbacktype':'Response'})
        respcondition = etree.SubElement(resprocessing, 'respcondition', {'title':'incorrect'})
        conditionvar = etree.SubElement(respcondition, 'conditionvar')
        etree.SubElement(conditionvar, 'other')
        etree.SubElement(respcondition, 'setvar', {'variablename':'SCORE', 'action':'Set'}).text = '0'
        etree.SubElement(respcondition, 'displayfeedback', {'linkrefid':'incorrect', 'feedbacktype':'Response'})
 
    def addMCQ_multchoice(self, qst:QMultichoice):
        """Multiple Choice
        Done
        """
        self._hasoptions(qst, 'Multiple Choice')

    def addSRQ(self, qst: QShortAnswer, rows=3, maxchars=0):
        """Short Response
        Done
        """
        item, _, flow2, resprocessing = self._question(qst, "Short Response")
        
        response_str = etree.SubElement(flow2, 'response_str', ident='response', 
                                        cardinality='Single', rtiming='No')
        etree.SubElement(response_str, 'render_fib', charset='us-ascii',
                         encoding='UTF_8', rows='{:d}'.format(rows),
                         columns='127', maxchars='{:d}'.format(maxchars), 
                         prompt='Box', fibtype='String', minnumber='0', 
                         maxnumber='0')
        outcomes = etree.SubElement(resprocessing, 'outcomes', {})
        etree.SubElement(outcomes, 'decvar', varname='SCORE',
                         vartype='Decimal', defaultval='0', minvalue='0')
        
        respcondition = etree.SubElement(resprocessing, 'respcondition', 
                                         title='correct')
        conditionvar = etree.SubElement(respcondition, 'conditionvar')
        etree.SubElement(respcondition, 'setvar', variablename='SCORE',
                        action='Set').text = 'SCORE.max'
        etree.SubElement(respcondition, 'displayfeedback', linkrefid='correct',
                         feedbacktype='Response')
        respcondition = etree.SubElement(resprocessing, 'respcondition',
                                         title='incorrect')
        conditionvar = etree.SubElement(respcondition, 'conditionvar')
        etree.SubElement(conditionvar, 'other')
        etree.SubElement(respcondition, 'setvar', variablename='SCORE',
                         action='Set').text = '0'
        etree.SubElement(respcondition, 'displayfeedback', linkrefid='incorrect',
                         feedbacktype='Response')
        for opt in qst.options:
            itemfeedback = etree.SubElement(item, 'itemfeedback', ident='solution',
                                            view='All')
            solution = etree.SubElement(itemfeedback, 'solution', view='All',
                                        feedbackstyle='Complete')
            solutionmaterial = etree.SubElement(solution, 'solutionmaterial')
            flow = etree.SubElement(solutionmaterial, 'flow_mat', {'class':'Block'})
            self.material(flow, opt.get_string(self.pkg.embed_file))
            
    def addTFQ_truefalse(self, qst: QTrueFalse):
        """True/False
            Done
        """
        _, _, flow2, resprocessing = self._question(qst, "True/False")

        resp = etree.SubElement(flow2, 'response_lid', ident='response',
                                rcardinality='Single', rtiming='No')
        render_choice = etree.SubElement(resp, 'render_choice', shuffle='No',
                                         minnumber='0', maxnumber='0')
        flow_label = etree.SubElement(render_choice, 'flow_label', {'class':'Block'})
        for response in ['true','false']:
            label = etree.SubElement(flow_label, 'response_label',
                                     ident=response, shuffle='Yes', 
                                     rarea='Ellipse', rrange='Exact')
            flow_mat = etree.SubElement(label, 'flow_mat', {'class':'Block'})
            material = etree.SubElement(flow_mat, 'material')
            etree.SubElement(material, 'mattext', charset='us-ascii',
                             texttype='text/plain').text = response
        
        outcomes = etree.SubElement(resprocessing, 'outcomes', {})
        etree.SubElement(outcomes, 'decvar', varname='SCORE', 
                         vartype='Decimal', defaultval='0', minvalue='0')
        
        respcondition = etree.SubElement(resprocessing, 'respcondition',
                                         title='correct')
        conditionvar = etree.SubElement(respcondition, 'conditionvar')
        etree.SubElement(conditionvar, 'varequal', respident='response',
                         case='No').text = 'true' if qst.correct else 'false'
        etree.SubElement(respcondition, 'setvar', variablename='SCORE',
                         action='Set').text = 'SCORE.max'
        etree.SubElement(respcondition, 'displayfeedback', linkrefid='correct',
                         feedbacktype='Response')

        respcondition = etree.SubElement(resprocessing, 'respcondition',
                                        title='incorrect')
        conditionvar = etree.SubElement(respcondition, 'conditionvar')
        etree.SubElement(conditionvar, 'other')
        etree.SubElement(respcondition, 'setvar', variablename='SCORE',
                         action='Set').text = '0'
        etree.SubElement(respcondition, 'displayfeedback', linkrefid='incorrect',
                         feedbacktype='Response')

    def addOQ_ordering(self, qst: QMultichoice):
        """Ordering. Done
        Args:
            qst (QMultichoice): _description_
        """
        _, _, flow2, resprocessing = self._question(qst, "Ordering")
        outcomes = etree.SubElement(resprocessing, 'outcomes')
        etree.SubElement(outcomes, 'decvar', varname='SCORE', vartype='Decimal',
                         defaultval='0', minvalue='0')

        response_lid = etree.SubElement(flow2, 'response_lid', ident='response',
                                        rcardinality='Ordered', rtiming='No')
        render_choice = etree.SubElement(response_lid, 'render_choice', shuffle='No',
                                         minnumber='0', maxnumber='0')

        respcondition = etree.SubElement(resprocessing, 'respcondition', title='correct')
        setvar = etree.SubElement(respcondition, 'setvar', variablename='SCORE',
                                  action='Set')
        setvar.text = 'SCORE.max'
        etree.SubElement(respcondition, 'displayfeedback', {'linkrefid':'correct', 'feedbacktype':'Response'})
        conditionvar = etree.SubElement(respcondition, 'conditionvar')
        and_ = etree.SubElement(conditionvar, 'and')
        for opt in qst.options:
            luuid = uuid.uuid4().hex
            flow_label = etree.SubElement(render_choice, 'flow_label', {'class':'Block'})
            response_label = etree.SubElement(flow_label, 'response_label',
                                              ident=luuid, rarea='Ellipse',
                                              rrange='Exact')
            bb_answer_text = self.pkg.process_string(opt.text)
            etree.SubElement(and_, 'varequal', respident='response', case='No').text = luuid
            self.flow_mat1(response_label, bb_answer_text)
        respcondition = etree.SubElement(resprocessing, 'respcondition', title='incorrect')
        conditionvar = etree.SubElement(respcondition, 'conditionvar')
        etree.SubElement(conditionvar, 'other')
        setvar = etree.SubElement(respcondition, 'setvar', variablename='SCORE', action='Set')
        setvar.text = '0'
        etree.SubElement(respcondition, 'displayfeedback', linkrefid='incorrect',
                         feedbacktype='Response')

    def addFITBQ_cloze(self, qst: QCloze):
        """Fill in the blank questions
        Done
        """
        _, _, flow2, resprocessing = self._question(qst, "Fill in the Blank Plus", "true")
        outcomes = etree.SubElement(resprocessing, 'outcomes', {})
        etree.SubElement(outcomes, 'decvar', {'varname':'SCORE', 'vartype':'Decimal', 'defaultval':'0', 'minvalue':'0'})
        
        respcondition = etree.SubElement(resprocessing, 'respcondition', {'title':'correct'})
        conditionvar = etree.SubElement(respcondition, 'conditionvar')
        and_tag = etree.SubElement(conditionvar, 'and')
        for opt in qst.options:
            luuid = uuid.uuid4().hex
            response_str = etree.SubElement(flow2, 'response_str', ident=luuid,
                                            rcardinality='Single', rtiming='No')
            etree.SubElement(response_str, 'render_choice', charset='us-ascii',
            columns="0", encoding='UTF_8', fibtype='String', maxchars='0',
            maxnumber='0', minnumber='0', prompt='Box', rows='0')
            or_tag = etree.SubElement(and_tag, 'or')
            for regex in opt.opts:
                etree.SubElement(or_tag, 'varsubset', respident=luuid,
                                 setmatch='Matches').text = regex.text
        etree.SubElement(respcondition, 'setvar', variablename='SCORE',
                         action='Set').text = 'SCORE.max'
        etree.SubElement(respcondition, 'displayfeedback', linkrefid='correct',
                         feedbacktype='Response')

        respcondition = etree.SubElement(resprocessing, 'respcondition',
                                         title='incorrect')
        conditionvar = etree.SubElement(respcondition, 'conditionvar')
        etree.SubElement(conditionvar, 'other')
        etree.SubElement(respcondition, 'setvar', variablename='SCORE',
                         action='Set').text = '0'
        etree.SubElement(respcondition, 'displayfeedback', linkrefid='incorrect', 
                         feedbacktype='Response')

    def flow_mat2(self, node, text):
        flow = etree.SubElement(node, 'flow_mat', {'class':'Block'})
        self.flow_mat1(flow, text)

    def flow_mat1(self, node, text):
        flow = etree.SubElement(node, 'flow_mat', {'class':'FORMATTED_TEXT_BLOCK'})
        self.material(flow, text)

       
class Package:

    def __init__(self, courseID="IMPORT"):
        """Initialises a Blackboard package
        """
        self.courseID = courseID
        self.embedded_files: Dict[str, tuple] = {}
        self.zf = ZipFile(self.courseID+'.zip', mode='w', compression=ZIP_DEFLATED)
        self.next_xid = 1000000
        self.equation_counter = 0
        self.resource_counter = 0
        self.embedded_paths = {}
        #Create the manifest file
        self.xmlNS = "http://www.w3.org/XML/1998/namespace"
        self.bbNS = 'http://www.blackboard.com/content-packaging/'
        self.manifest = etree.Element("manifest", {'identifier':'man00001'}, nsmap={'bb':self.bbNS})
        self.resources = etree.SubElement(self.manifest, 'resources')

        self.idcntr = 3191882
        self.latex_kwargs = dict()
        self.latex_cache = {}
        
    def bbid(self):
        self.idcntr += 1
        return self.idcntr

    def create_unique_filename(self, base, ext):
        count = 0
        while True:
            fname = base+'_'+str(count)+ext
            if not os.path.isfile(fname):
                return fname
            count += 1
    
    def close(self):
        #Write additional data to implement the course name
        parentContext = etree.Element("parentContextInfo")
        etree.SubElement(parentContext, "parentContextId").text = self.courseID
        self.embed_resource(self.courseID, "resource/x-mhhe-course-cx", '<?xml version="1.0" encoding="utf-8"?>\n'+etree.tostring(parentContext, pretty_print=False).decode('utf-8'))

        #Finally, write the manifest file
        self.zf.writestr('imsmanifest.xml', '<?xml version="1.0" encoding="utf-8"?>\n'+etree.tostring(self.manifest, pretty_print=False).decode('utf-8'))
        self.zf.writestr('.bb-package-info', open(os.path.join(os.path.dirname(__file__), '.bb-package-info')).read())
        self.zf.close()

    def createPool(self, pool_name, *args, **kwargs):
        return Pool(pool_name, self, *args, **kwargs)

    def embed_resource(self, title, type, content):
        self.resource_counter += 1
        name = 'res'+format(self.resource_counter, '05')
        resource = etree.SubElement(self.resources, 'resource', {'identifier':name, 'type':type})
        resource.attrib[etree.QName(self.xmlNS, 'base')] = name
        resource.attrib[etree.QName(self.bbNS, 'file')] = name+'.dat'
        resource.attrib[etree.QName(self.bbNS, 'title')] = title
        self.zf.writestr(name+'.dat', content)
        return name
        
    def embed_file_data(self, name: str, content):
        """Embeds a file (given a name and content) to the quiz and returns the
        unique id of the file, and the path to the file in the zip
        """                

        #First, we need to process the path of the file, and embed xid
        #descriptors for each directory/subdirectory
        
        #Split the name into filename and path
        path, filename = os.path.split(name)

        #Simplify the path (remove any ./ items and simplify ../ items to come at the start)
        if (path != ""):
            path = os.path.relpath(path)
        
        #Split the path up into its components
        def rec_split(s):
            rest, tail = os.path.split(s)
            if rest in ('', os.path.sep):
                return [tail]
            return rec_split(s) + [tail]

        path = rec_split(path)
        root, ext = os.path.splitext(filename)

        def processDirectories(path, embedded_paths, i=0):
            #Keep processing until the whole path is processed
            if i >= len(path):
                return path

            #Slice any useless entries from the path
            if i==0 and (path[0] == ".." or path[0] == '/' or path[0] == ''):
                path = path[1:]
                return processDirectories(path, embedded_paths, i)

            #Check if the path is already processed
            if path[i] in embedded_paths:
                new_e_paths = embedded_paths[path[i]][1]
                path[i] = embedded_paths[path[i]][0]
            else:
                #Path not processed, add it
                descriptor_node = etree.Element("lom") #attrib = {'xmlns':, 'xmlns:xsi':'http://www.w3.org/2001/XMLSchema-instance', 'xsi:schemaLocation':'http://www.imsglobal.org/xsd/imsmd_rootv1p2p1 imsmd_rootv1p2p1.xsd'}
                relation = etree.SubElement(descriptor_node, 'relation')
                resource = etree.SubElement(relation, 'resource')

                self.next_xid += 1
                transformed_path = path[i]+'__xid-'+str(self.next_xid)+'_1'
                etree.SubElement(resource, 'identifier').text = str(self.next_xid)+'_1' + '#' + '/courses/'+self.courseID+'/' + os.path.join(*(path[:i+1]))
                embedded_paths[path[i]] = [transformed_path, {}]
                new_e_paths = embedded_paths[path[i]][1]

                path[i] = transformed_path
                
                self.zf.writestr(os.path.join('csfiles/home_dir', *(path[:i+1]))+'.xml', '<?xml version="1.0" encoding="UTF-8"?>\n'+etree.tostring(descriptor_node, pretty_print=False).decode('utf-8'))

            return processDirectories(path, new_e_paths, i+1)

        processDirectories(path, self.embedded_paths)
        
        #Finally, assign a xid to the file itself
        self.next_xid += 1
        filename = root + '__xid-'+str(self.next_xid)+'_1' + ext

        #Merge the path pieces and filename
        path = path + [filename]
        path = os.path.join(*path)
        filepath = os.path.join('csfiles/home_dir/', path)
        self.zf.writestr(filepath, content)
        
        descriptor_node = etree.Element("lom") #attrib = {'xmlns':, 'xmlns:xsi':'http://www.w3.org/2001/XMLSchema-instance', 'xsi:schemaLocation':'http://www.imsglobal.org/xsd/imsmd_rootv1p2p1 imsmd_rootv1p2p1.xsd'}
        relation = etree.SubElement(descriptor_node, 'relation')
        resource = etree.SubElement(relation, 'resource')
        etree.SubElement(resource, 'identifier').text = str(self.next_xid) + '#' + '/courses/'+self.courseID+'/'+path
        self.zf.writestr(filepath+'.xml', '<?xml version="1.0" encoding="UTF-8"?>\n'+etree.tostring(descriptor_node, pretty_print=False).decode('utf-8'))
        return str(self.next_xid)+'_1', filepath

    def embed_file(self, filename, file_data=None):
        """Embeds a file, and returns an img tag for use in blackboard, and an
        equivalent for html.
        """
        #Grab the file data
        if file_data == None:
            with open(filename, mode='rb') as file:
                file_data = file.read()
            
        #Check if this file has already been embedded
        if filename not in self.embedded_files:
            xid, path = self.embed_file_data(filename, file_data)
            self.embedded_files[filename] = (xid, path)
            return xid, path
            
        #Hmm something already exists with that name, check the data
        xid, path = self.embedded_files[filename]
        fz = self.zf.open(path)
        if file_data == fz.read():
            #It is the same file! return the existing link
            return xid, path
        fz.close()
        
        #Try generating a new filename, checking if that already exists in the store too
        count=-1
        fbase, ext = os.path.splitext(filename)
        while True:
            count += 1 
            fname = fbase + '_'+str(count)+ext
            if fname in self.embedded_files:
                xid, path = self.embedded_files[fname]
                fz = self.zf.open(path)
                if file_data == fz.read():
                    return xid, path
                else:
                    continue
            break
        #OK we have a new unique name, fname. Use this to embed the file
        xid, path = self.embed_file_data(fname, file_data)
        self.embedded_files[fname] = (xid, path)
        return xid, path

    def process_string(self, text: FText):
        """Scan a string for LaTeX equations, image tags, etc, and process them.
        """
        return text.get_string(self.embed_file)


# ----------------------------------------------------------------------------


def read_blackboard(self, file_path: str) -> None:
    """_summary_

    Args:
        file_path (str): _description_
    """
    raise NotImplementedError("Blackboard not implemented")


# -----------------------------------------------------------------------------


def _txrecursive(cat: Category, path: str):
    for question in cat.questions:
        pass
    for name in cat:
        _txrecursive(cat[name])


def write_blackboard(self: Category, file_path: str, courseID) -> None:
    """_summary_

    Args:
        file_path (str): _description_
    """
    pck = Package()

    