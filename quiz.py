import questions
from xml.etree import ElementTree as et
from typing import List, Dict
from qas_enums import Numbering
import logging
import re

def _escape_cdata(text):
    try:
        if str.startswith(text, "<![CDATA[") and str.endswith(text, "]]>"):
            return text
        if "&" in text:
            text = text.replace("&", "&amp;")
        if "<" in text:
            text = text.replace("<", "&lt;")
        if ">" in text:
            text = text.replace(">", "&gt;")
        return text
    except (TypeError, AttributeError):
        et._raise_serialization_error(text)
et._escape_cdata = _escape_cdata

# ----------------------------------------------------------------------------------------
QTYPES = [m for m in dir(questions) if type(getattr(questions, m)) == type and 
        issubclass(getattr(questions, m), questions.Question)]

class Quiz:
    """
    This class represents Quiz as a set of Questions.
    """

    def __init__(self, category_name: str="$course$", category_info: str="",
                idnumber: int=None, parent: "Quiz"=None):
        self._questions: List[questions.Question] = []
        self.category_name = category_name
        self.category_info = category_info
        self.idnumber = idnumber
        self.children: Dict[str, Quiz] = {}
        self.parent = parent

    def _to_xml_element(self, root: et.Element) -> None:
        """[summary]

        Args:
            root (et.Element): [description]
        """
        question = et.Element("question")               # Add category on the top
        question.set("type", "category")
        category = et.SubElement(question, "category")
        text = et.SubElement(category, "text")
        text.text = str(self.category_name)
        info = et.SubElement(question, "info")
        text = et.SubElement(info, "text")
        text.text = str(self.category_info)
        idnumber = et.SubElement(question, "idnumber")
        if self.idnumber:
            idnumber.text = str(self.category_info)
        root.append(question)        
        for question in self._questions:                # Add own questions first
            root.append(question.to_xml())
        for child in self.children.values():            # Then add children data
            child._to_xml_element(root)

    def add_question(self, question: questions.Question):
        """
        Adds a question to the quiz object.

        :type question: Question
        :param question: the question to add
        """
        if not isinstance(question, questions.Question):
            TypeError(f"Object must be subclass of Question, not {question.__class__.__name__}")
        self._questions.append(question)

    @staticmethod
    def read_aiken(file_path: str) -> "Quiz":
        """[summary]

        Args:
            file_path (str): [description]
        """
        log = logging.getLogger(__name__)
        quiz = Quiz()
        with open(file_path) as infile:
            lines = infile.readlines()
        lines.reverse()
        name = file_path.rsplit("/", 1)[-1][:-4]
        question_cnt = 0
        try:
            while lines:
                line = lines.pop().strip()
                question = questions.MultipleChoiceQuestion(name=f"{name}_{question_cnt}", 
                                                            question_text=line)
                while lines and "ANSWER:" not in line[:7]:
                    line = lines.pop()
                    ans = re.match(r"[A-Z]+\) (.+)", line)
                    if ans:
                        question.add_answer(0.0, ans[1])
                question.answers[ord(line[8].upper())-65].fraction = 100.0
                quiz.add_question(question)
                question_cnt+=1    
        except IndexError:
            log.exception(f"Failed to import Aiken File. {len(quiz._questions)} questions"
                            " imported. Following question does not have options.")
        else:
            log.info(f"Imported Aiken file successfully. {len(quiz._questions)} questions"
                    " imported.")
        return quiz

    @staticmethod
    def read_gift(file_path: str):
        pass

    @staticmethod
    def read_json():
        """
        Generic file. This is the default file format used by the QAS Editor.
        """
        pass

    @staticmethod
    def read_latex():
        pass

    @staticmethod
    def read_markdown(file_path: str, question_mkr :str="\s*\*\s+(.*)", 
                        answer_mkr: str="\s*-\s+(!)(.*)", category_mkr: str="\s*#\s+(.*)", 
                        answer_numbering: Numbering=Numbering.ALF_LR, 
                        shuffle_answers: bool=True, single_answer_penalty_weight: int=0):
        """[summary]

        Args:
            file_path (str): [description]
            question_mkr (str, optional): [description]. Defaults to "\s*\*\s+(.*)".
            answer_mkr (str, optional): [description]. Defaults to "\s*-\s+(!)(.*)".
            category_mkr (str, optional): [description]. Defaults to "\s*#\s+(.*)".
            answer_numbering (Numbering, optional): [description]. Defaults to Numbering.ALF_LOWER.
            shuffle_answers (bool, optional): [description]. Defaults to True.
            single_answer_penalty_weight (int, optional): [description]. Defaults to 0.

        Raises:
            ValueError: [description]
            ValueError: [description]
            ValueError: [description]
        """
        regex_exp = f"({question_mkr})|({category_mkr})|({answer_mkr})"
        with open(file_path) as infile:
            lines = infile.readlines()
        lines.reverse()
        cnt = 0
        category = ""
        top_quiz: Quiz = None
        quiz = top_quiz
        while lines:
            match = re.match(regex_exp, lines[-1])
            if match:
                if match[0]:
                    if not category or not quiz:
                        raise ValueError("No classification defined for this question")
                    quiz.add_question(questions.MultipleChoiceQuestion.from_markdown(
                                        category, lines, regex_exp, 
                                        answer_numbering, shuffle_answers,
                                        single_answer_penalty_weight, name=f"mkquestion_{cnt}"))
                elif match[2]:
                    category = lines.pop()
                    tmp = category.split("/")
                    tmp.reverse()
                    if not top_quiz:
                        top_quiz = Quiz(category_name=tmp[-1])
                    elif top_quiz.category_name != tmp[-1]:
                        raise ValueError("Top classification redefined")
                    quiz = top_quiz
                    while tmp:
                        cur_cat = tmp.pop()
                        tmp_quiz = quiz.children.get(cur_cat, None)
                        if not tmp_quiz:
                            tmp_quiz = Quiz(category_name=cur_cat, parent=quiz)
                        quiz = tmp_quiz
                elif match[4]:
                    raise ValueError("Answer found out of a question block.")

    @staticmethod
    def read_xml(file_path: str) -> "Quiz":
        """[summary]
        """
        top_quiz = Quiz()
        quiz = top_quiz
        data_root = et.parse(file_path)
        for question in data_root.getroot():
            qdict: Dict[str, questions.Question] = {
                getattr(questions, m)._type: getattr(questions, m) for m in QTYPES
            }
            if question.get("type") == "category":
                pass
            elif question.get("type") not in qdict:
                raise TypeError(f"The type {question.get('type')} not implemented")
            else:
                quiz._questions.append(qdict[question.get("type")].from_xml(question))
        return quiz

    def write_xml(self, file_path: str):
        """
        Generates XML compatible with Moodle and saves to a file.

        :type file: str
        :param file: filename where the XML will be saved

        :type pretty: bool
        :param pretty: (not implemented) saves XML pretty printed
        """
        quiz: et.ElementTree = et.ElementTree(et.Element("quiz"))
        root = quiz.getroot()
        self._to_xml_element(root)
        quiz.write(file_path, encoding="utf-8", xml_declaration=True, short_empty_elements=False)

    def write_pdf(self):
        # TODO
        pass
