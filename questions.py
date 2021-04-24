from typing import List
from xml.etree import ElementTree as et
from utils import CombinedFeedback, Dataset, FText, SelectOption, Subquestion, Unit, Hint, \
                  Tags, UnitHandling, DropZone, DragItem, get_txt
from qas_enums import Status, Distribution, Numbering
from answer import Answer, NumericalAnswer, CalculatedAnswer, Choice
from urllib.request import urlopen
import base64
import re
import os
# import markdown
# import latex2mathml

class Question():
    """
    This is an abstract class Question used as a parent for specific types of Questions.
    """
    _type=None

    def __init__(self, name: str, question_text: FText, default_grade: float=1.0, 
                feedback: FText=None, id_number: int=None, shuffle: bool=False,
                penalty: float=0.5, tags: Tags=None, solution: str=None,
                use_latex: bool=True) -> None:
        """
        [summary]

        Args:
            name (str): name of the question
            question_text (str): text of the question
            default_grade (float): the default mark
            general_feedback (str, optional): general feedback. Defaults to None.
            id_number (int, optional): id number. Defaults to None.
            shuffle (bool, optional): shuffle answers. Defaults to False.
        """
        self.name = name
        self.question_text = question_text
        self.default_grade = default_grade
        self.general_feedback = feedback
        self.id_number = id_number
        self.shuffle = shuffle
        self.penalty = penalty
        self.solution = solution
        self.tags = tags
        self.use_latex = use_latex
        self.hints: List[Hint] = []

    def __repr__(self):
        """ 
        Change string representation.
        """
        return f"Type: {self.__class__.__name__}, name: \'{self.name}\'."

    @classmethod
    def from_xml(cls, root: et.Element, *args) -> "Question":
        data = {x.tag: x for x in root}
        # try:
        name = data['name'][0].text
        # except Exception:
        #     print(data)
        question = FText.from_xml(data['questiontext'])
        grade = get_txt(data, "defaultgrade", 1.0)
        feedback = FText.from_xml(data.get('generalfeedback'))
        id_number = get_txt(data, "idnumber", None)
        shuffle = bool(get_txt(data, "idnumber", 0))
        penalty = float(get_txt(data, "penalty", 0))
        tags = Tags.from_xml(data.get("Tags"))
        question = cls(*args, name, question, grade, feedback, id_number, shuffle, penalty, tags)
        for h in root.findall("hint"):
            question.hints.append(Hint.from_xml(h))
        return question

    def to_xml(self) -> et.Element:
        """
        This method converts current object to Moodle XML.
        """
        question = et.Element("question")
        question.set("type", self._type)
        name = et.SubElement(question, "name")
        et.SubElement(name, "text").text = str(self.name)
        self.question_text.to_xml(question, "questiontext")
        et.SubElement(question, "defaultgrade").text = str(self.default_grade)
        self.general_feedback.to_xml(question, "generalfeedback")
        et.SubElement(question, "hidden").text = "0"
        et.SubElement(question, "idnumber").text = self.id_number
        et.SubElement(question, "shuffleanswers").text = self.shuffle
        et.SubElement(question, "penalty").text = str(self.penalty)
        for h in self.hints:
            question.append(h.to_xml())
        return question

# ----------------------------------------------------------------------------------------

class DescriptionQuestion(Question):
    _type = "description"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

# ----------------------------------------------------------------------------------------

class CalculatedQuestion(Question):
    _type = "calculated"

    def __init__(self, synchronize: int, single: bool=False, 
                unit_handling: UnitHandling=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.synchronize = synchronize
        self.single = single
        self.unit_handling = unit_handling
        self.units: List[Unit] = []
        self.datasets: List[Dataset] = []
        self.answers: List[CalculatedAnswer] = []

    def add_answer(self, fraction: float, text: str, **kwargs) -> None:
        self.answers.append(CalculatedAnswer(fraction=fraction, text=text, **kwargs))

    def add_dataset(self, status: Status, name: str, dist: Distribution, minim: float,
                    maxim: float, dec: int ) -> None:
        self.datasets.append(Dataset(status, name, dist, minim, maxim, dec))

    def add_unit(self, name: str, multiplier: float) -> None:
        self.units.append(Unit(name, multiplier))

    @classmethod
    def from_xml(cls, root: et.Element) -> "CalculatedQuestion":
        data = {x.tag: x for x in root}
        #print(data)
        synchronize = get_txt(data, "synchronize")
        single = get_txt(data, "single")
        unit_handling = UnitHandling.from_xml(data)
        question: "CalculatedQuestion" = super().from_xml(root, synchronize, single, 
                                                        unit_handling)
        for u in root.findall("units"):
            question.units.append(Unit.from_xml(u))
        for ds in root.findall("dataset_definition"):
            question.datasets.append(Dataset.from_xml(ds))
        for ans in root.findall(""):
            question.answers.append(Answer.from_xml(ans))
        return question

    def to_xml(self) -> et.Element:
        question = super().to_xml()
        et.SubElement(question, "synchronize").text = self.synchronize
        et.SubElement(question, "single").text = self.single
        for answer in self.answers:
            question.append(answer.to_xml())
        self.unit_handling.to_xml(question)
        units = et.SubElement(question, "units")
        for unit in self.units:
            units.append(unit.to_xml())
        dataset_definitions = et.SubElement(question, "dataset_definitions")
        for dataset in self.datasets:
            dataset_definitions.append(dataset.to_xml())
        return question

# ----------------------------------------------------------------------------------------

class CalculatedSimpleQuestion(CalculatedQuestion):
    _type = "calculatedsimple"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

# ----------------------------------------------------------------------------------------

class CalculatedMultichoiceQuestion(Question):
    _type = "calculatedmulti"

    def __init__(self, synchronize: int, single: bool=False, 
                answer_numbering: Numbering=Numbering.ALF_LR, 
                combined_feedback: CombinedFeedback=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.synchronize = synchronize
        self.single = single
        self.answer_numbering = answer_numbering
        self.combined_feedback = combined_feedback
        self.datasets: List[Dataset] = []
        self.answers: List[CalculatedAnswer] = []

    def add_answer(self, fraction: float, text: str, **kwargs) -> None:
        self.answers.append(CalculatedAnswer(fraction=fraction, text=text, **kwargs))

    def add_dataset(self, status: Status, name: str, dist: Distribution, minim: float,
                    maxim: float, dec: int ) -> None:
        self.datasets.append(Dataset(status, name, "calculated", dist, minim, maxim, dec))

    def add_unit(self, name: str, multiplier: float) -> None:
        self.units.append(Unit(name, multiplier))

    @classmethod
    def from_xml(cls, root: et.Element) -> "Question":
        data = {x.tag: x for x in root}
        synchronize = data["synchronize"]
        single = data["single"]
        answer_numbering = data["answernumbering"]
        combined_feedback = CombinedFeedback.from_xml(root)
        question: "CalculatedMultichoiceQuestion" = super().from_xml(root, synchronize, single, 
                                                        answer_numbering, combined_feedback)
        for dataset in data["dataset_definitions"]:
            question.datasets.append(Dataset.from_xml(dataset))
        for answer in root.findall("answer"):
            question.answers.append(CalculatedAnswer.from_xml(answer))
        return question

    def to_xml(self) -> et.Element:
        question = super().to_xml()
        et.SubElement(question, "synchronize").text = self.synchronize
        et.SubElement(question, "single").text = self.single
        et.SubElement(question, "answernumbering").text = self.answer_numbering
        question.append(self.combined_feedback.to_xml())
        for answer in self.answers:
            question.append(answer.to_xml()) 
        dataset_definitions = et.SubElement(question, "dataset_definitions")
        for dataset in self.datasets:
            dataset_definitions.append(dataset.to_xml())
        return question

# ----------------------------------------------------------------------------------------

class ClozeQuestion(Question):
    """This is a very simples class that hold cloze data. All data is compressed inside
    the question text, so no further implementation is necessary.
    """
    _type = "cloze"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
    @classmethod
    def from_xml(cls, root: et.Element) -> "ClozeQuestion":
        return super().from_xml(root)

    def to_xml(self) -> et.Element:
        return super().to_xml()

    @staticmethod
    def from_cloze() -> "ClozeQuestion":
        super().from_xml()
        # TODO
        pass

# ----------------------------------------------------------------------------------------

class DragAndDropIntoTextQuestion(Question):
    """
    This class represents a drag and drop text onto image question. 
    It inherits from abstract class Question.
    """
    _type = "ddwtos"

    def __init__(self, combined_feedback: CombinedFeedback, *args, **kwargs):
        """
        Currently not implemented.
        """
        super().__init__(*args, **kwargs)
        self.combined_feedback = combined_feedback
        self._choices: List[Choice] = []

    def add_choice(self, text: str, group: int=1, unlimited: bool=False) -> None:
        """
        Adds new Choice with assigned DropZones.

        Args:
            text (str): text of the drag text
            group (int, optional): group. Defaults to 1.
            unlimited (bool, optional): if item is allowed to be used again. Defaults to False.
        """
        self._choices.append(Choice(text=text, group=group, unlimited=unlimited))

    @classmethod
    def from_xml(cls, root: et.Element) -> "DragAndDropIntoTextQuestion":      
        feedback = CombinedFeedback.from_xml(root)
        question: "DragAndDropIntoTextQuestion" = super().from_xml(root, feedback)
        for c in root.findall("dragbox"):
            question._choices.append(Choice.from_xml(c))
        return question

    def to_xml(self) -> et.Element:
        question = super().to_xml()
        self.combined_feedback.to_xml(question)
        for choice in self._choices:
            question.append(choice.to_xml())
        return question

# ----------------------------------------------------------------------------------------

class DragAndDropOntoImageQuestion(Question):
    """
    This class represents a drag and drop onto image question. 
    It inherits from abstract class Question.
    """
    _type = "ddimageortext"

    def __init__(self, background: str, combined_feedback: CombinedFeedback=None, 
                image: str=None, *args, **kwargs):
        """Creates an drag and drop onto image type of question.

        Args:
            background (str): Filepath to the background image.
        """
        super().__init__(*args, **kwargs)
        self.background = background
        if image:
            self.image = image
        else:
            try:
                with urlopen(background) as response:
                    self.image = str(base64.b64encode(response.read()), "utf-8")
            except Exception:
                with open(background, "rb") as f:
                    self.image = str(base64.b64encode(f.read()), "utf-8")
        self.combined_feedback = combined_feedback
        self._dragitems: List[DragItem] = []
        self._dropzones: List[DropZone] = []

    def add_dragimage(self, text: str, group: int, file: str, unlimited: bool=False) -> None:
        """Adds new DragItem with assigned DropZones.

        Args:
            file (str): path to image to be used as a drag image;
            text (str, optional): text of the drag text.
            group (int, optional): group.
            unlimited (bool, optional): if item is allowed to be used again. Defaults to False.
        """
        dragimage = DragItem(len(self._dragitems) + 1, text, unlimited, group, file=file)
        self._dragitems.append(dragimage)

    def add_dragtext(self, text: str, group: str, unlimited: bool=False) -> None:
        """Adds new DragText with assigned DropZones.

        Args:
            text (str): text of the drag text. 
            group (str): group.
            unlimited (bool, optional): if item is allowed to be used again. Defaults to False.
        """
        dragitem = DragItem(len(self._dragitems) + 1, text, unlimited, group)
        self._dragitems.append(dragitem)

    def add_dropzone(self, x: int, y: int, text: str, choice: int) -> None:
        """[summary]

        Args:
            x (int): [description]
            y (int): [description]
            text (str): [description]
            choice (int): [description]
        """
        self._dropzones.append(DropZone(x, y, text, choice, len(self._dropzones) + 1))

    @classmethod
    def from_xml(cls, root: et.Element) -> "Question":
        data = {x.tag: x for x in root}
        background = data.get("file").get("path", "") + data.get("file").get("name")
        image = data.get("file").text
        combined_feedback = CombinedFeedback.from_xml(root)
        question = super().from_xml(root, background, combined_feedback, image)
        return question

    def to_xml(self):
        question = super().to_xml()
        for dragitem in self._dragitems:
            question.append(dragitem.to_xml())
        for dropzone in self._dropzones:
            question.append(dropzone.to_xml())
        if self.background:
            et.SubElement(question, "file", {
                    "name": os.path.basename( self.background), 
                    "encoding": "base64"})
        return question

# ----------------------------------------------------------------------------------------

class DragAndDropMarkersQuestion(Question):
    _type = "ddmarker"

    def __init__(self, background: str, combined_feedback: CombinedFeedback=None, 
                image: str=None, *args, **kwargs):
        """Creates an drag and drop onto image type of question.

        Args:
            background (str): Filepath to the background image.
        """
        super().__init__(*args, **kwargs)
        self.background = background
        if image:
            self.image = image
        else:
            try:
                with urlopen(background) as response:
                    self.image = str(base64.b64encode(response.read()), "utf-8")
            except Exception:
                with open(background, "rb") as f:
                    self.image = str(base64.b64encode(f.read()), "utf-8")
        self.combined_feedback = combined_feedback
        self._dragitems: List[DragItem] = []

    def add_dragmarker(self, text: str, no_of_drags: str, unlimited: bool=False):
        """[summary]

        Args:
            text (str): [description]
            no_of_drags (str): [description]
            unlimited (bool, optional): [description]. Defaults to False.
        """
        dragitem = DragItem(len(self._dragitems) + 1, text, unlimited, no_of_drags=no_of_drags)
        self._dragitems.append(dragitem)

    @classmethod
    def from_xml(cls, root: et.Element) -> "Question":
        data = {x.tag: x for x in root}
        background = data.get("file").get("path", "") + data.get("file").get("name")
        image = data.get("file").text
        combined_feedback = CombinedFeedback.from_xml(root)
        question = super().from_xml(root, background, combined_feedback, image)
        return question

    def to_xml(self):
        question = super().to_xml()
        self.combined_feedback.to_xml(question)
        for dragitem in self._dragitems:
            question.append(dragitem.to_xml())
        if self.background:
            et.SubElement(question, "file", {
                    "name": os.path.basename( self.background), 
                    "encoding": "base64"})
        return question

# ----------------------------------------------------------------------------------------

class EssayQuestion(Question):
    _type = "essay"

    def __init__(self, response_format: str="editor", response_required: bool=True, 
                responsefield_lines: int=10, attachments: int=1, 
                attachments_required: bool=False, maxbytes: int=None, 
                filetypes_list: str=None, grader_info: FText=None, 
                response_template: FText=None, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.response_format = response_format
        self.response_required = response_required
        self.responsefield_lines = responsefield_lines
        self.attachments = attachments
        self.attachments_required = attachments_required
        self.maxbytes = maxbytes
        self.filetypes_list = filetypes_list
        self.grader_info = grader_info
        self.response_template = response_template

    @classmethod
    def from_xml(cls, root: et.Element) -> "Question":
        data = {x.tag: x for x in root}
        format = data["responseformat"].text
        required = data["responserequired"].text
        lines = data["responsefieldlines"].text
        attachments = data["attachments"].text
        attachments_required = data["attachmentsrequired"].text
        maxbytes = get_txt(data, "maxbytes", None)
        filetypes_list = get_txt(data, "filetypeslist", None)
        grader_info = FText.from_xml(data.get("graderinfo"))
        response_template = FText.from_xml(data.get("responsetemplate"))
        question = super().from_xml(root, format, required, lines, attachments, 
                                attachments_required, maxbytes, filetypes_list, 
                                grader_info, response_template)
        return question

    def to_xml(self) -> et.Element:
        question = super().to_xml()
        et.SubElement(question, "responseformat").text = self.response_format
        et.SubElement(question, "responserequired").text = self.response_required
        et.SubElement(question, "responsefieldlines").text = self.responsefield_lines
        et.SubElement(question, "attachments").text = self.attachments
        et.SubElement(question, "attachmentsrequired").text = self.attachments_required
        if self.maxbytes:
            et.SubElement(question, "maxbytes").text = self.maxbytes
        if self.filetypes_list:
            et.SubElement(question, "filetypeslist").text = self.filetypes_list
        if self.grader_info:
            self.grader_info.to_xml(question, "graderinfo")
        if self.response_template:
            self.response_template.to_xml(question, "responsetemplate")
        return question

# ----------------------------------------------------------------------------------------

class MatchingQuestion(Question):
    IMPLEMENTED = False
    _type = "matching"

    def __init__(self, combined_feedback: CombinedFeedback=None, 
                *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.combined_feedback = combined_feedback
        self.subquestions: List[Subquestion] = []

    def add_subquestion(self, text: str, answer: str) -> None:
        """[summary]

        Args:
            text (str): [description]
            answer (str): [description]
        """
        if isinstance(text, str) and isinstance(answer, str):
            self.subquestions.append((text, answer))

    @classmethod
    def from_xml(cls, root: et.Element) -> "Question":
        combined_feedback = CombinedFeedback.from_xml(root)
        question: "MatchingQuestion" = super().from_xml(root, combined_feedback)
        for sub in root.findall("subquestion"):
            question.subquestions.append(Subquestion.from_xml(sub))
        return question

    def to_xml(self) -> et.Element:
        question = super().to_xml()
        self.combined_feedback.to_xml(question)
        for sub in self.subquestions:
            question.append(sub.to_xml())
        return question

# ----------------------------------------------------------------------------------------

class RandomShortAnswerMatchingQuestion(Question):
    _type = "randomsamatch"

    def __init__(self, choose: int, subcats: bool, combined_feedback: CombinedFeedback=None, 
                *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.combined_feedback = combined_feedback
        self.choose = choose
        self.subcats = subcats

    @classmethod
    def from_xml(cls, root: et.Element) -> "Question":
        data = {x.tag: x for x in root}
        combined_feedback = CombinedFeedback.from_xml(root)
        choose = data["choose"].text
        subcats = data["subcats"].text
        question = super().from_xml(root, choose, subcats, combined_feedback)
        return question

    def to_xml(self) -> et.Element:
        question = super().to_xml()
        self.combined_feedback.to_xml(question)
        et.SubElement(question, "choose").text = self.choose
        et.SubElement(question, "subcats").text = self.subcats
        return question

# ----------------------------------------------------------------------------------------

class SelectMissingWordsQuestion(Question):
    _type = "gapselect"

    def __init__(self, combined_feedback: CombinedFeedback=None,*args, **kwargs):
        super(self, ).__init__(*args, **kwargs)
        self.combined_feedback = combined_feedback
        self.options: List[SelectOption] = []

    @classmethod
    def from_xml(cls, root: et.Element) -> "Question":
        combined_feedback = CombinedFeedback.from_xml(root)
        question: "SelectMissingWordsQuestion" = super().from_xml(root, combined_feedback)
        for option in root.findall("selectoption"):
            question.options.append(SelectOption.from_xml(option))
        return question

    def to_xml(self) -> et.Element:
        question = super().to_xml()
        self.combined_feedback.to_xml(question)
        for opt in self.options:
            question.append(opt.to_xml())
        return question

# ----------------------------------------------------------------------------------------

class MultipleChoiceQuestion(Question):
    """
    This class represents 'Multiple choice' question.
    """
    _type = "multichoice"

    def __init__(self, answer_numbering: Numbering=Numbering.ALF_LR, 
                combined_feedback: CombinedFeedback=None, *args, **kwargs):
        """
        [summary]

        Args:
            answer_numbering (str, optional): [description]. Defaults to "abc".
        """
        super().__init__(*args, **kwargs)
        self.combined_feedback = combined_feedback
        self.answer_numbering: List[str] = answer_numbering
        self.answers: List[Answer] = []

    @classmethod
    def from_xml(cls, root: et.Element) -> "Question":
        data = {x.tag: x for x in root}
        num = Numbering.get(data["answernumbering"])
        feedback = CombinedFeedback.from_xml(root)
        question: "MultipleChoiceQuestion" = super().from_xml(root, num, feedback)
        for answer in root.findall("answer"):
            question.answers.append(Answer.from_xml(answer))
        return question

    def to_xml(self) -> et.Element:
        """[summary]

        Returns:
            [type]: [description]
        """
        question = super().to_xml()
        self.combined_feedback.to_xml(question)
        et.SubElement(question, "answernumbering").text = self.answer_numbering.value
        for answer in self.answers:
            question.append(answer.to_xml())
        return question

    def add_answer(self, fraction: float, text: str, feedback :str=None) -> None:
        """
        Adds an answer to this question.

        Args:
            fraction (float): Percentage of the grade
            text (str): text of the anwser
            feedback (str, optional): feedback shown when this answer is submitted. Defaults to None.
        """
        self.answers.append(Answer(fraction, text, feedback))

    @staticmethod
    def from_markdown(category: str, lines: list, regex: str, answer_numbering: Numbering,
                        shuffle_answers: bool, penalty: int, 
                        name: str="mkquestion") -> "MultipleChoiceQuestion":
        """[summary]

        Returns:
            [type]: [description]
        """
        data = lines.pop()
        question: Question = None
        while lines:
            match = re.match(regex, lines[-1])
            if match:
                if match[0]:
                    raise ValueError("Category found inside a question")
                elif match[2]:
                    raise ValueError("No answer defined for the question")
                elif match[4]:
                    if not question:
                        question = MultipleChoiceQuestion(answer_numbering, name=name,
                                                question_text=data, category=category,
                                                shuffle=shuffle_answers)
                    data = lines.pop()                       
                    while lines and (match[4] or not match):
                        match = re.match(regex, lines[-1])
                        if not match:
                            data += lines.pop()
                        elif match[4] or match[2]:
                            question.add_answer(100.0 if match[5] else 0.0, data, "")
                            data = lines.pop()
                    return question
            else:
                data += lines.pop()  
        return question

# ----------------------------------------------------------------------------------------

class NumericalQuestion(Question):
    """
    This class represents 'Numerical Question' moodle question type.
    Units are currently not implemented, only numerical answer, which
    are specified as text and absolute tolerance value are implemented
    """
    _type = "numerical"

    def __init__(self, unit_handling: UnitHandling=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.unit_handling = unit_handling
        self.units: List[Unit] = []
        self.answers: List[NumericalAnswer] = []

    def add_answer(self, tol: float, fraction: float, text: str, feedback: str=None) -> None:
        self.answers.append(NumericalAnswer(tol, fraction, text, feedback))

    def add_unit(self, name: str, multiplier: float) -> None:
        self.units.append(Unit(name, multiplier))

    @classmethod
    def from_xml(cls, root: et.Element) -> "Question":
        data = {x.tag: x for x in root}
        unit_handling = UnitHandling.from_xml(data)
        question: "NumericalQuestion" = super().from_xml(root, unit_handling)
        for answer in root.findall(""):
            question.answers.append(NumericalAnswer.from_xml(answer))
        return question

    def to_xml(self):
        question = super().to_xml()
        for answer in self.answers:
            question.append(answer.to_xml())
        self.unit_handling.to_xml(question)
        units = et.SubElement(question, "units")
        for unit in self.units:
            units.append(unit.to_xml())
        return question

# ----------------------------------------------------------------------------------------

class ShortAnswerQuestion(Question):
    """
    This class represents 'Short answer' question.
    """
    _type = "shortanswer"

    def __init__(self, use_case: bool, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.use_case = use_case
        self.answers: List[Answer] = []

    def add_answer(self, fraction: float, text: str, feedback: str=None):
        """Adds an answer to this question.

        Args:
            fraction (float): Percentage of the grade
            text (str): text of the anwser
            feedback (str, optional): feedback shown when this answer is submitted. Defaults to None.
        """
        self.answers.append(Answer(fraction, text, feedback))

    @classmethod
    def from_xml(cls, root: et.Element) -> "Question":
        data = {x.tag: x for x in root}
        use_case = data["usecase"]
        question: "ShortAnswerQuestion" = super().from_xml(root, use_case)
        for answer in root.findall("answer"):
            question.answers.append(Answer.from_xml(answer))
        return question

    def to_xml(self):
        question = super().to_xml()
        et.SubElement(question, "usecase").text = self.use_case
        for answer in self.answers:
            question.append(answer.to_xml())
        return question

# ----------------------------------------------------------------------------------------

class TrueFalseQuestion(Question):
    """
    This class represents true/false question.
    """
    _type = "truefalse"

    def __init__(self, correct_answer: bool, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.correct_answer = correct_answer
        self.answer_true = None
        self.answer_false = None

    def set_answer_for_true(self, text: str, feedback: str):
        fraction = 100 if self.correct_answer else 0
        self.answer_true = Answer(fraction, text, feedback)

    def set_answer_for_false(self, text: str, feedback: str):
        fraction = 100 if not self.correct_answer else 0
        self.answer_false = Answer(fraction, text, feedback)

    @classmethod
    def from_xml(cls, root: et.Element) -> "Question":
        question = super().from_xml(root)
        return question

    def to_xml(self) -> et.Element:
        question = super().to_xml()
        question.append(self.answer_true.to_xml())
        question.append(self.answer_false.to_xml())
        return question
