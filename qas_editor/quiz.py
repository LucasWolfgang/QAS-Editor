from qas_editor.wrappers import FText
import re
import logging
import json
from xml.etree import ElementTree as et
from typing import List, Dict, Iterator
from .enums import Format, Numbering
from . import questions

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

    def __init__(self, category_name: str="$course$", category_info: str=None,
                idnumber: int=None, parent: "Quiz"=None):
        self.questions: List[questions.Question] = []
        self.category_name = category_name
        self.category_info = category_info
        self.idnumber = idnumber
        self.children: Dict[str, Quiz] = {}
        self.parent = parent

    def __iter__(self) -> Iterator[str]:
        return  self.children.__iter__()

    @staticmethod
    def __gen_hier(top: "Quiz", category: str) -> tuple:
        cat_list = category.strip().split("/")
        cat_list.reverse()
        if top is None:
            top = Quiz(category_name=cat_list[-1])
        elif top.category_name != cat_list[-1]:
            raise ValueError(f"Top classification '{cat_list[-1]}' is different from the "+
                            f"previously defined '{top.category_name}'")
        cat_path = cat_list.pop()
        quiz = top
        while cat_list:
            cat_cur = cat_list.pop()
            cat_path += "/" + cat_cur
            if cat_cur not in quiz.children:
                quiz.children[cat_cur] = Quiz(category_name=cat_path)
            quiz = quiz.children[cat_cur]  
        return top, quiz

    def _indent(self, elem: et.Element, level: int=0):
        """[summary]

        Args:
            elem (et.Element): [description]
            level (int, optional): [description]. Defaults to 0.
        """
        i = "\n" + level * "  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for elem in elem:
                self._indent(elem, level + 1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i

    def _to_aiken(self) -> str:
        data = ""
        for question in self.questions:
            if isinstance(question, questions.QMultichoice):
                data += f"{question.question_text.text}\n"
                correct = "ANSWER: None\n\n"
                for num, ans in enumerate(question.answers):
                    data += f"{chr(num+65)}) {ans.text}\n"
                    if ans.fraction == 100:
                        correct = f"ANSWER: {chr(num+65)}\n\n"
                data += correct
        for child in self.children:
            data += self.children[child]._to_aiken()
        return data

    def _to_xml_element(self, root: et.Element) -> None:
        """[summary]

        Args:
            root (et.Element): [description]
        """
        question = et.Element("question")                   # Add category on the top
        if len(self.questions) > 0:
            question.set("type", "category")
            category = et.SubElement(question, "category")
            text = et.SubElement(category, "text")
            text.text = str(self.category_name)
            root.append(question)        
            for question in self.questions:                # Add own questions first
                root.append(question.to_xml())
        for child in self.children.values():                # Then add children data
            child._to_xml_element(root)

    def _to_json(self, data: dict):
        """[summary]

        Args:
            data (dict): [description]

        Returns:
            [type]: [description]
        """
        for i in data:
            if isinstance(data[i], list):
                data[i] = [self._to_json(k.__dict__.copy()) if "__dict__" in dir(k) 
                            else k for k in data[i]]
            elif isinstance(data[i], dict):
                data[i] = self._to_json(data[i])
            elif "__dict__" in dir(data[i]):
                data[i] = self._to_json(data[i].__dict__.copy())
            elif "value" in dir(data[i]):
                data[i] = data[i].value
        return data

    def add_question(self, question: questions.Question):
        """
        Adds a question to the quiz object.

        :type question: Question
        :param question: the question to add
        """
        if not isinstance(question, questions.Question):
            TypeError(f"Object must be subclass of Question, not {question.__class__.__name__}")
        self.questions.append(question)
        question.parent = self

    def get_hier(self, root:dict) -> None:
        """[summary]

        Args:
            root (dict): [description]
        """
        root[self.category_name] = {"__questions__" : self.questions}
        for child in self.children.values():
            child.get_hier(root[self.category_name])

    @classmethod
    def read_aiken(cls, file_path: str, category: str="$course$") -> "Quiz":
        """[summary]

        Args:
            file_path (str): [description]
        """
        log = logging.getLogger(__name__)
        quiz = cls(category)
        with open(file_path) as infile:
            lines = infile.readlines()
        lines.reverse()
        name = file_path.rsplit("/", 1)[-1][:-4]
        question_cnt = 0
        try:
            while lines:
                line = lines.pop().strip()
                question = questions.QMultichoice(name=f"{name}_{question_cnt}", 
                                                question_text=FText(line, Format.PLAIN))
                while lines and "ANSWER:" not in line[:7]:
                    line = lines.pop()
                    ans = re.match(r"[A-Z]+\) (.+)", line)
                    if ans:
                        question.add_answer(0.0, ans[1])
                question.answers[ord(line[8].upper())-65].fraction = 100.0
                quiz.add_question(question)
                question_cnt+=1    
        except IndexError:
            log.exception(f"Failed to import Aiken File. {len(quiz.questions)} questions"
                            " imported. Following question does not have options.")
        return quiz

    @classmethod
    def read_cloze(cls, file_path: str, category: str="$course$") -> "Quiz":
        top_quiz: Quiz = Quiz(category_name=category)
        with open(file_path, "r") as ifile:
            data = "\n" + ifile.read()
        data = re.sub("\n(?!::)", "", data) + "\n" # Remove \n's inside a question
        for q in re.findall(r"(?:\:\:(.+?)\:\:)(.+?)\n", data): # Get the questions
            top_quiz.add_question(questions.QCloze.from_cloze(*q))
        return top_quiz

    @classmethod
    def read_gift(cls, file_path: str) -> "Quiz":
        top_quiz: Quiz = None
        quiz = top_quiz
        with open(file_path, "r") as ifile:
            data = "\n" + ifile.read()
        data = re.sub(r"\n//.*?(?=\n)", "", data)           # Remove comments
        data = re.sub("(?<!\})\n(?!::)", "", data) + "\n"   # Remove \n's inside a question
        tmp = re.findall(r"(?:\$CATEGORY:\s*(.+))|(?:\:\:(.+?)\:\:(\[.+?\])?(.+?)(?:(\{.*?)(?<!\\)\}(.*?))?)\n", 
                        data)
        for i in tmp:
            if i[0]:
                top_quiz, quiz = Quiz.__gen_hier(top_quiz, i[0])
            if not i[0]:
                question = None
                ans = re.findall(r"((?<!\\)(?:=|~|TRUE|FALSE|T|F|####|#))(%[\d\.]+%)?((?:(?<=\\)[=~#]|[^~=#])*)", i[4])           
                if not i[4]:
                    question = questions.QDescription.from_gift(i, ans)
                elif not ans:
                    question = questions.QEssay.from_gift(i, ans)
                elif ans[0][0] == "#":
                    question = questions.QNumerical.from_gift(i, ans)
                elif i[5]:  
                    question = questions.QMissingWord.from_gift(i, ans)  
                elif ans[0][0] in ["TRUE", "FALSE", "T", "F"]:               
                    question = questions.QTrueFalse.from_gift(i, ans)
                elif all([a[0] in ["=", "#", "####"] for a in ans]):
                    if re.match(r"(.*?)(?<!\\)->(.*)", ans[0][2]):
                        question = questions.QMatching.from_gift(i, ans)
                    else:
                        question = questions.QShortAnswer.from_gift(i, ans)
                else:
                    question = questions.QMultichoice.from_gift(i, ans)
                quiz.add_question(question)
        return top_quiz

    @staticmethod
    def read_json():
        """
        Generic file. This is the default file format used by the QAS Editor.
        """
        pass

    @staticmethod
    def read_latex():
        # TODO
        pass

    @staticmethod
    def read_markdown(file_path: str, question_mkr :str="\s*\*\s+(.*)", 
                        answer_mkr: str="\s*-\s+(!)?(.*)", category_mkr: str="\s*#\s+(.*)", 
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
        regex_exp = f"({category_mkr})|({question_mkr})|({answer_mkr})"
        with open(file_path) as infile:
            lines = infile.readlines()
        lines.append("\n") # Make sure that the document has 2 newlines in the end
        lines.append("\n")
        lines.reverse()
        cnt = 0
        top_quiz: Quiz = None
        quiz = top_quiz
        while lines:
            match = re.match(regex_exp, lines[-1])
            if match:
                if match[1]:
                    top_quiz, quiz = Quiz.__gen_hier(top_quiz, match[2])
                    lines.pop()
                elif match[3]:
                    if quiz is None:
                        raise ValueError("No classification defined for this question")
                    quiz.add_question(questions.QMultichoice.from_markdown( lines, 
                                    answer_mkr, question_mkr, answer_numbering, shuffle_answers,
                                    single_answer_penalty_weight, name=f"mkquestion_{cnt}"))
                elif match[5]:
                    raise ValueError(f"Answer found out of a question block: {match[5]}.")
            else:
                lines.pop()
        return top_quiz

    @classmethod
    def read_xml(cls, file_path: str) -> "Quiz":
        """[summary]

        Raises:
            TypeError: [description]

        Returns:
            [type]: [description]
        """
        data_root = et.parse(file_path)
        mcat = data_root.getroot()[0]
        top_quiz: Quiz = None
        quiz = top_quiz
        for question in data_root.getroot():
            qdict: Dict[str, questions.Question] = {
                getattr(questions, m)._type: getattr(questions, m) for m in QTYPES
            }
            if question.get("type") == "category":
                top_quiz, quiz = Quiz.__gen_hier(top_quiz, question[0][0].text)         
            elif question.get("type") not in qdict:
                raise TypeError(f"The type {question.get('type')} not implemented")
            else:
                if top_quiz is None and quiz is None:
                    top_quiz: Quiz = Quiz(category_name="$course$")
                    quiz = top_quiz
                quiz.questions.append(qdict[question.get("type")].from_xml(question))
        return top_quiz

    def write_aiken(self, file_path: str) -> None:
        data = self._to_aiken()
        with open(file_path, "w") as ofile:
            ofile.write(data)

    def write_json(self, file_path: str, pretty_print: bool=False) -> None:
        """[summary]

        Args:
            file_path (str): [description]
            pretty_print (bool, optional): [description]. Defaults to False.
        """
        with open(file_path, "w") as ofile:
            if pretty_print:
                json.dump(self._to_json(self.__dict__.copy()), ofile, indent=4)
            else:
                json.dump(self._to_json(self.__dict__.copy()), ofile)

    def write_xml(self, file_path: str, pretty_print: bool=False):
        """Generates XML compatible with Moodle and saves to a file.

        Args:
            file_path (str): filename where the XML will be saved
            pretty_print (bool, optional): (not implemented) saves XML pretty printed. Defaults to False.
        """
        quiz: et.ElementTree = et.ElementTree(et.Element("quiz"))
        root = quiz.getroot()
        self._to_xml_element(root)
        if pretty_print:
            self._indent(root)
        quiz.write(file_path, encoding="utf-8", xml_declaration=True, short_empty_elements=False)

    def write_pdf(self):
        # TODO
        pass
