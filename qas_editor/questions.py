from typing import List
from xml.etree import ElementTree as et
from .wrappers import B64File, CombinedFeedback, Dataset, FText, SelectOption, Subquestion, \
                    Unit, Hint, Tags, UnitHandling, DropZone, DragItem
from .utils import get_txt, extract
from .enums import Format, Status, Distribution, Numbering
from .answer import Answer, NumericalAnswer, CalculatedAnswer, Choice
import re
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
                use_latex: bool=True, hints: List[Hint]=None) -> None:
        """
        [summary]

        Args:
            name (str): name of the question
            question_text (FText): text of the question
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
        self.hints: List[Hint] = hints if hints is not None else []

    def __repr__(self):
        """ 
        Change string representation.
        """
        return f"Type: {self.__class__.__name__}, name: \'{self.name}\'."

    @classmethod
    def from_xml(cls, root: et.Element, **kwargs) -> "Question":
        data = {x.tag: x for x in root}
        res = {}
        res["name"] = data['name'][0].text
        res["question_text"] = FText.from_xml(data['questiontext'])
        res["general_feedback"] = FText.from_xml(data.get('generalfeedback'))
        extract(data, "defaultgrade"  , res, "default_grade", float)
        extract(data, "idnumber"      , res, "id_number"    , int)
        extract(data, "shuffleanswers", res, "shuffle"      , bool)
        extract(data, "penalty"       , res, "penaly"       , float)
        res["tags"] = Tags.from_xml(data.get("tags"))
        question = cls(**kwargs, **res)
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
        if self.general_feedback:
            self.general_feedback.to_xml(question, "generalfeedback")
        et.SubElement(question, "defaultgrade").text = str(self.default_grade)
        et.SubElement(question, "penalty").text = str(self.penalty)
        et.SubElement(question, "hidden").text = "0"
        if self.id_number is not None:
            et.SubElement(question, "idnumber").text = str(self.id_number)
        if self.shuffle:
            et.SubElement(question, "shuffleanswers").text = "true"
        for h in self.hints:
            question.append(h.to_xml())
        if self.tags:
            question.append(self.tags.to_xml())
        return question

# ----------------------------------------------------------------------------------------

class QDescription(Question):
    _type = "description"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    @classmethod
    def from_gift(cls, header: list, answer: list) -> "QDescription":
        formatting = Format.get(header[2][1:-1])
        if formatting is None:
            formatting = Format.MD
        return cls(name=header[1], question_text=FText(header[3], formatting))

# ----------------------------------------------------------------------------------------

class QCalculated(Question):
    _type = "calculated"

    def __init__(self, synchronize: int, single: bool=False, unit_handling: UnitHandling=None, 
                units: List[Unit]=None, datasets: List[Dataset]=None, 
                answers: List[CalculatedAnswer]=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.synchronize = synchronize
        self.single = single
        self.unit_handling = unit_handling
        self.units: List[Unit] = units if units is not None else []
        self.datasets: List[Dataset] = datasets if datasets is not None else []
        self.answers: List[CalculatedAnswer] = answers if answers is not None else []

    def add_answer(self, fraction: float, text: str, **kwargs) -> None:
        self.answers.append(CalculatedAnswer(fraction=fraction, text=text, **kwargs))

    def add_dataset(self, status: Status, name: str, dist: Distribution, minim: float,
                    maxim: float, dec: int ) -> None:
        self.datasets.append(Dataset(status, name, dist, minim, maxim, dec))

    def add_unit(self, name: str, multiplier: float) -> None:
        self.units.append(Unit(name, multiplier))

    @classmethod
    def from_xml(cls, root: et.Element) -> "QCalculated":
        data = {x.tag: x for x in root}
        res = {}
        extract(data, "synchronize", res, "synchronize", int)
        extract(data, "single"     , res, "single"     , bool)
        res["unit_handling"] = UnitHandling.from_xml(data)
        question: "QCalculated" = super().from_xml(root, **res)
        for u in root.findall("units"):
            question.units.append(Unit.from_xml(u))
        for ds in data["dataset_definitions"]:
            question.datasets.append(Dataset.from_xml(ds))
        for ans in root.findall("answer"):
            question.answers.append(CalculatedAnswer.from_xml(ans))
        return question

    def to_xml(self) -> et.Element:
        question = super().to_xml()
        et.SubElement(question, "synchronize").text = self.synchronize
        et.SubElement(question, "single").text = self.single
        for answer in self.answers:
            question.append(answer.to_xml())
        self.unit_handling.to_xml(question)
        if self.units:
            units = et.SubElement(question, "units")
            for unit in self.units:
                units.append(unit.to_xml())
        if self.datasets:
            dataset_definitions = et.SubElement(question, "dataset_definitions")
            for dataset in self.datasets:
                dataset_definitions.append(dataset.to_xml())
        return question

# ----------------------------------------------------------------------------------------

class QCalculatedSimple(QCalculated):
    _type = "calculatedsimple"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

# ----------------------------------------------------------------------------------------

class QCalculatedMultichoice(Question):
    _type = "calculatedmulti"

    def __init__(self, synchronize: int, single: bool=False, 
                answer_numbering: Numbering=Numbering.ALF_LR, 
                combined_feedback: CombinedFeedback=None, 
                datasets: List[Dataset]=None, answers: List[CalculatedAnswer]=None,
                *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.synchronize = synchronize
        self.single = single
        self.answer_numbering = answer_numbering
        self.combined_feedback = combined_feedback
        self.datasets: List[Dataset] = datasets if datasets is not None else []
        self.answers: List[CalculatedAnswer] = answers if answers is not None else []

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
        res = {}
        synchronize = data["synchronize"].text
        single = data["single"].text
        answer_numbering = data["answernumbering"].text
        combined_feedback = CombinedFeedback.from_xml(root)
        question: "QCalculatedMultichoice" = super().from_xml(root, synchronize, single, 
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
        self.combined_feedback.to_xml(question)
        for answer in self.answers:
            question.append(answer.to_xml()) 
        dataset_definitions = et.SubElement(question, "dataset_definitions")
        for dataset in self.datasets:
            dataset_definitions.append(dataset.to_xml())
        return question

# ----------------------------------------------------------------------------------------

class QCloze(Question):
    """This is a very simples class that hold cloze data. All data is compressed inside
    the question text, so no further implementation is necessary.
    """
    _type = "cloze"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
    @classmethod
    def from_xml(cls, root: et.Element) -> "QCloze":
        return super().from_xml(root)

    def to_xml(self) -> et.Element:
        return super().to_xml()

    @staticmethod
    def from_cloze() -> "QCloze":
        super().from_xml()
        # TODO
        pass

# ----------------------------------------------------------------------------------------

class QDragAndDropText(Question):
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
    def from_xml(cls, root: et.Element) -> "QDragAndDropText":      
        feedback = CombinedFeedback.from_xml(root)
        question: "QDragAndDropText" = super().from_xml(root, feedback)
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

class QDragAndDropImage(Question):
    """
    This class represents a drag and drop onto image question. 
    It inherits from abstract class Question.
    """
    _type = "ddimageortext"

    def __init__(self, background: B64File, combined_feedback: CombinedFeedback=None, 
                *args, **kwargs) -> None:
        """Creates an drag and drop onto image type of question.

        Args:
            background (str): Filepath to the background image.
        """
        super().__init__(*args, **kwargs)
        self.background = background
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
        combined_feedback = CombinedFeedback.from_xml(root)
        background = B64File.from_xml(data.get("file"))
        question: "QDragAndDropImage" = super().from_xml(root, background, combined_feedback)
        for dragitem in root.findall("drag"):
            question._dragitems.append(DragItem.from_xml(dragitem))
        for dropzone in root.findall("drop"):
            question._dropzones.append(DropZone.from_xml(dropzone))
        return question

    def to_xml(self):
        question = super().to_xml()
        self.combined_feedback.to_xml(question)
        if self.background:
            question.append(self.background.to_xml())
        for dragitem in self._dragitems:
            question.append(dragitem.to_xml())
        for dropzone in self._dropzones:
            question.append(dropzone.to_xml())
        return question

# ----------------------------------------------------------------------------------------

class QDragAndDropMarker(Question):
    _type = "ddmarker"

    def __init__(self, background: B64File, combined_feedback: CombinedFeedback=None, 
                highlight_empty: bool=False, *args, **kwargs):
        """Creates an drag and drop onto image type of question.

        Args:
            background (str): Filepath to the background image.
        """
        super().__init__(*args, **kwargs)
        self.background = background
        self.combined_feedback = combined_feedback
        self.highlight_empty = highlight_empty
        self._dragitems: List[DragItem] = []
        self._dropzones: List[DropZone] = []

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
    def from_xml(cls, root: et.Element) -> "QDragAndDropMarker":
        data = {x.tag: x for x in root}
        background = B64File.from_xml(data.get("file"))
        highlight = "showmisplaced" in data
        combined_feedback = CombinedFeedback.from_xml(root)
        question: "QDragAndDropMarker" = super().from_xml(root, background, combined_feedback, highlight)
        for dragitem in root.findall("drag"):
            question._dragitems.append(DragItem.from_xml(dragitem))
        for dropzone in root.findall("drop"):
            question._dropzones.append(DropZone.from_xml(dropzone))
        return question

    def to_xml(self):
        question = super().to_xml()
        if self.highlight_empty:
            et.SubElement(question, "showmisplaced")
        self.combined_feedback.to_xml(question)
        for dragitem in self._dragitems:
            question.append(dragitem.to_xml())
        for dropzone in self._dropzones:
            question.append(dropzone.to_xml())
        if self.background:
            question.append(self.background.to_xml())
        return question

# ----------------------------------------------------------------------------------------

class QEssay(Question):
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
    def from_gift(cls, header: list, answer: list) -> "QEssay":
        formatting = Format.get(header[2][1:-1])
        if formatting is None:
            formatting = Format.MD
        return cls(name=header[1], question_text=FText(header[3], formatting))

    @classmethod
    def from_xml(cls, root: et.Element) -> "QEssay":
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

class QMatching(Question):
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
    def from_gift(cls, header: list, answer: list) -> "QMatching":
        formatting = Format.get(header[2][1:-1])
        if formatting is None:
            formatting = Format.MD
        qst = cls(name=header[1], question_text=FText(header[3], formatting))
        for a in answer:
            if a[0] == "=":
                g = re.match(r"(.*?)(?<!\\)->(.*)", a[2])
                qst.subquestions.append(Subquestion(formatting, g[1].strip(), g[2].strip()))
            elif a[0] == "####":
                qst.general_feedback = FText(a[2], formatting)
        return qst

    @classmethod
    def from_xml(cls, root: et.Element) -> "QMatching":
        combined_feedback = CombinedFeedback.from_xml(root)
        question: "QMatching" = super().from_xml(root, combined_feedback)
        for sub in root.findall("subquestion"):
            question.subquestions.append(Subquestion.from_xml(sub))
        return question

    def to_xml(self) -> et.Element:
        question = super().to_xml()
        if self.combined_feedback:
            self.combined_feedback.to_xml(question)
        for sub in self.subquestions:
            question.append(sub.to_xml())
        return question

# ----------------------------------------------------------------------------------------

class QRandomMatching(Question):
    _type = "randomsamatch"

    def __init__(self, choose: int, subcats: bool, combined_feedback: CombinedFeedback=None, 
                *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.combined_feedback = combined_feedback
        self.choose = choose
        self.subcats = subcats

    @classmethod
    def from_xml(cls, root: et.Element) -> "QRandomMatching":
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

class QMissingWord(Question):
    _type = "gapselect"

    def __init__(self, combined_feedback: CombinedFeedback=None,*args, **kwargs):
        super().__init__(*args, **kwargs)
        self.combined_feedback = combined_feedback
        self.options: List[SelectOption] = []

    @classmethod
    def from_gift(cls, header: list, answer: list) -> "QMissingWord":
        formatting = Format.get(header[2][1:-1])
        if formatting is None:
            formatting = Format.MD
        qst = cls(name=header[1], question_text=FText(header[3], formatting))
        correct = None
        for i in answer:
            if i[0] == "=":
                correct = SelectOption(i[2], 1)
            else:
                qst.options.append(SelectOption(i[2], 1))
        qst.options.insert(0, correct)
        return qst

    @classmethod
    def from_xml(cls, root: et.Element) -> "QMissingWord":
        combined_feedback = CombinedFeedback.from_xml(root)
        question: "QMissingWord" = super().from_xml(root, combined_feedback)
        for option in root.findall("selectoption"):
            question.options.append(SelectOption.from_xml(option))
        return question

    def to_xml(self) -> et.Element:
        question = super().to_xml()
        if self.combined_feedback:
            self.combined_feedback.to_xml(question)
        for opt in self.options:
            question.append(opt.to_xml())
        return question

# ----------------------------------------------------------------------------------------

class QMultichoice(Question):
    """
    This class represents 'Multiple choice' question.
    """
    _type = "multichoice"

    def __init__(self, single: bool=True, answer_numbering: Numbering=Numbering.ALF_LR, 
                combined_feedback: CombinedFeedback=None, *args, **kwargs):
        """
        [summary]

        Args:
            answer_numbering (str, optional): [description]. Defaults to "abc".
        """
        super().__init__(*args, **kwargs)
        self.single = single
        self.combined_feedback = combined_feedback
        self.answer_numbering: Numbering = answer_numbering
        self.answers: List[Answer] = []

    @classmethod
    def from_gift(cls, header: list, answer: list) -> "QMultichoice":
        formatting = Format.get(header[2][1:-1])
        if formatting is None:
            formatting = Format.MD
        qst = cls(name=header[1], question_text=FText(header[3], formatting))
        prev_answer = None
        for a in answer:
            txt = a[2]
            if a[0] == "~": # Wrong or partially correct answer
                fraction = 0 if not a[1] else float(a[1][1:-1])
                prev_answer = Answer(fraction, txt, formatting=formatting)
                qst.answers.append(prev_answer)
            elif a[0] == "=": # Correct answer
                prev_answer = Answer(100, txt, formatting=formatting)
                qst.answers.append(prev_answer)
            elif a[0] == "#": # Answer feedback
                prev_answer.feedback = FText(a[2], formatting)
        return qst

    @classmethod
    def from_xml(cls, root: et.Element) -> "QMultichoice":
        data = {x.tag: x for x in root}
        num = Numbering.get(data["answernumbering"].text)
        feedback = CombinedFeedback.from_xml(root)
        single = bool(get_txt(data, "single", True))
        question: "QMultichoice" = super().from_xml(root, single, num, feedback)
        for answer in root.findall("answer"):
            question.answers.append(Answer.from_xml(answer))
        return question

    def to_xml(self) -> et.Element:
        """[summary]

        Returns:
            [type]: [description]
        """
        question = super().to_xml()
        if self.combined_feedback:
            self.combined_feedback.to_xml(question)
        et.SubElement(question, "answernumbering").text = self.answer_numbering.value
        et.SubElement(question, "single").text = str(self.single).lower()
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
    def from_markdown(lines: list, answer_mkr: str, question_mkr: str, 
                        answer_numbering: Numbering, shuffle_answers: bool, penalty: float, 
                        name: str="mkquestion") -> "QMultichoice":
        """[summary]

        Returns:
            [type]: [description]
        """
        data = ""
        match = re.match(answer_mkr, lines[-1])
        while lines and match is None:        
            data += lines.pop().strip()
            match = re.match(answer_mkr, lines[-1])
        question: Question = QMultichoice(answer_numbering, name=name, 
                                        question_text=FText(data, Format.MD), 
                                        shuffle=shuffle_answers, penalty=penalty)
        regex_exp = f"({question_mkr})|({answer_mkr})"
        while lines:
            match = re.match(regex_exp, lines.pop())
            if match and match[3]: 
                question.add_answer(100.0 if match[4] is not None else 0.0, match[5], "")
            else:
                break
        return question

# ----------------------------------------------------------------------------------------

class QNumerical(Question):
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
    def from_xml(cls, root: et.Element) -> "QNumerical":
        data = {x.tag: x for x in root}
        unit_handling = UnitHandling.from_xml(data)
        question: "QNumerical" = super().from_xml(root, unit_handling)
        for answer in root.findall("answer"):
            question.answers.append(NumericalAnswer.from_xml(answer))
        return question

    @classmethod
    def from_gift(cls, header:list, answer:list) -> "QNumerical":
        def _extract(data: str) -> tuple:
            g = re.match(r"(.+?)(:|(?:\.\.))(.+)", data)
            if g[2] == "..":
                txt = (float(g[1]) + float(g[3]))/2
                tol = txt - float(g[1])
                txt = str(txt)
            else:
                txt = g[1]
                tol = float(g[3])
            return txt, tol
        formatting = Format.get(header[2][1:-1])
        if formatting is None:
            formatting = Format.MD
        qst = cls(name=header[1], question_text=FText(header[3], formatting))
        if len(answer) == 1:
            txt, tol = _extract(answer[0][2])
            qst.answers.append(NumericalAnswer(tol, 100, txt))
        elif len(answer) > 1:
            for ans in answer[1:]:
                if ans[0] == "=":
                    txt, tol = _extract(ans[2])
                    fraction = float(ans[1][1:-1]) if ans[0] == "=" else 0
                    a = NumericalAnswer(tol, fraction, txt)
                    qst.answers.append(a)
                elif ans[0] == "~":
                    a = NumericalAnswer(0, 0, "")
                elif ans[0] == "#":
                    a.feedback = FText(ans[2], formatting)
        return qst

    def to_xml(self):
        question = super().to_xml()
        for answer in self.answers:
            question.append(answer.to_xml())
        if self.unit_handling:
            self.unit_handling.to_xml(question)
        if len(self.units) > 0:
            units = et.SubElement(question, "units")
            for unit in self.units:
                units.append(unit.to_xml())
        return question

# ----------------------------------------------------------------------------------------

class QShortAnswer(Question):
    """
    This class represents 'Short answer' question.
    """
    _type = "shortanswer"

    def __init__(self, use_case: bool, *args, **kwargs) -> None:
        """[summary]

        Args:
            use_case (bool): [description]
        """
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
    def from_gift(cls, header: list, answer: list) -> "QShortAnswer":
        formatting = Format.get(header[2][1:-1])
        if formatting is None:
            formatting = Format.MD
        qst = cls(False, name=header[1], question_text=FText(header[3], formatting))
        for a in answer:
            fraction = 100 if not a[1] else float(a[1][1:-1])
            qst.answers.append(Answer(fraction, a[2], formatting=formatting))
        return qst

    @classmethod
    def from_xml(cls, root: et.Element) -> "Question":
        data = {x.tag: x for x in root}
        use_case = data["usecase"].text
        question: "QShortAnswer" = super().from_xml(root, use_case)
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

class QTrueFalse(Question):
    """
    This class represents true/false question.
    """
    _type = "truefalse"

    def __init__(self, correct_answer: bool, true_ans: Answer, false_ans: Answer, 
                *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.__answer_true = true_ans
        self.__answer_false = false_ans
        self.correct_answer = correct_answer

    def set_feedbacks(self, correct: FText, incorrect: FText):
        self.__answer_true.feedback = correct if self.correct_answer else incorrect
        self.__answer_false.feedback = correct if not self.correct_answer else incorrect

    @property
    def correct_answer(self) -> bool:
        return self.__correct_answer

    @correct_answer.setter
    def correct_answer(self, value: bool) -> None:
        self.__answer_true.fraction = 100 if value else 0
        self.__answer_false.fraction = 100 if not value else 0
        self.__correct_answer = value

    @classmethod
    def from_gift(cls, header: list, answer: list) -> "QTrueFalse":
        correct = answer.pop(0)[0].lower() in ["true", "t"]
        true_ans = Answer(0, "true")
        false_ans = Answer(0, "false")
        formatting = Format.get(header[2][1:-1])
        if formatting is None:
            formatting = Format.MD
        qst = cls(correct, true_ans, false_ans, name=header[1], 
                question_text=FText(header[3], formatting))
        for ans in answer:
            if ans[0] == "####":
                qst.general_feedback = FText(ans[2], Format.get(header[2][1:-1]))
            elif false_ans.feedback is None:
                false_ans.feedback = FText(ans[2], Format.get(header[2][1:-1]))
            else:
                true_ans = FText(ans[2], Format.get(header[2][1:-1]))
        return qst

    @classmethod
    def from_xml(cls, root: et.Element) -> "Question":
        answer_true = None
        answer_false = None
        correct = False
        for answer in root.findall("answer"):
            tmp = Answer.from_xml(answer)
            if tmp.text.lower() == "true":
                answer_true = tmp
                correct = True if answer_true.fraction == 100 else False
            elif tmp.text.lower() == "false":
                answer_false = tmp
        question = super().from_xml(root, correct, answer_true, answer_false)
        return question

    def to_xml(self) -> et.Element:
        question = super().to_xml()
        question.append(self.__answer_true.to_xml())
        question.append(self.__answer_false.to_xml())
        return question
