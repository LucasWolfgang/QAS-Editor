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

from __future__ import annotations
import re
import logging
from xml.etree import ElementTree as et
from typing import TYPE_CHECKING
from .wrappers import B64File, Dataset, FText, Hint, Tags,\
                    SelectOption, Subquestion, Unit, UnitHandling
from .utils import Serializable
from .enums import Format, ResponseFormat, Status, Distribution, Numbering
from .answer import Answer, ClozeItem, NumericalAnswer, DragText, \
                    CrossWord, CalculatedAnswer, DropZone, DragItem
# import markdown
# import latex2mathml
if TYPE_CHECKING:
    from typing import List, Dict
    from .enums import Direction
LOG = logging.getLogger(__name__)


QNAME: Dict[str, _Question] = {}
QTYPE: Dict[str, _Question] = {}


class _Question(Serializable):
    """
    This is an abstract class Question used as a parent for specific
    types of Questions.
    """
    MOODLE = None
    QNAME = None

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls.QNAME is not None:
            QNAME[cls.QNAME] = cls
        if cls.MOODLE is not None:
            QTYPE[cls.MOODLE] = cls

    def __init__(self, name: str, question: FText = None,
                 default_grade: float = 1.0, feedback: FText = None,
                 id_number: int = None, tags: Tags = None) -> None:
        """
        [summary]

        Args:
            name (str): name of the question
            question (FText): text of the question
            default_grade (float): the default mark
            general_feedback (str, optional): general feedback. Defaults to None.
            id_number (int, optional): id number. Defaults to None.
        """
        self.name = name
        self.question = question if question is not None else \
                        FText("questiontext")
        self.default_grade = default_grade
        self.feedback = feedback if feedback is not None else \
                        FText("generalfeedback")
        self.id_number = id_number
        self.tags = Tags() if tags is None else tags
        self.__parent = None

    @property
    def parent(self):
        """_summary_

        Returns:
            Quiz: _description_
        """
        return self.__parent

    @parent.setter
    def parent(self, value):
        if (self.__parent is None and value is not None and\
                self not in value.questions) or (self.__parent is not None and\
                value is None and self in self.__parent.questions):
            raise ValueError("This attribute can't be assigned directly. Use "+
                             "parent's add/rem_question functions instead.")
        self.__parent = value

    @classmethod
    def from_json(cls, data):
        data["question"] = FText.from_json(data["question"])
        data["feedback"] = FText.from_json(data["feedback"])
        return cls(**data)

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict):
        tags["name"] = (str, "name")
        tags["questiontext"] = (FText.from_xml, "question")
        tags["generalfeedback"] = (FText.from_xml, "feedback")
        tags["defaultgrade"] = (float, "default_grade")
        tags["idnumber"] = (int, "id_number")
        tags["tags"] = (Tags.from_xml, "tags")
        return super().from_xml(root, tags, attrs)

    def to_xml(self, root: et.Element, strict: bool) -> et.Element:
        """
        This method converts current object to Moodle XML.
        """
        question = et.SubElement(root, "question", {"type": self.MOODLE})
        name = et.SubElement(question, "name")
        et.SubElement(name, "text").text = self.name
        self.question.to_xml(question, strict)
        if self.feedback:
            self.feedback.to_xml(question, strict)
        et.SubElement(question, "defaultgrade").text = self.default_grade
        # et.SubElement(question, "hidden").text = "0"
        if self.id_number is not None:
            et.SubElement(question, "idnumber").text = self.id_number
        if self.tags:
            self.tags.to_xml(question, strict)
        return question


class _QuestionMT(_Question):

    def __init__(self, penalty: float = 0.5, hints = None,
                 options: list = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.penalty = penalty
        self.hints = [] if hints is None else hints
        self.options = [] if options is None else options

    @classmethod
    def from_json(cls, data: dict):
        for i in range(len(data["hints"])):
            data["hints"][i] = Hint.from_json(data["hints"][i])
        # Defintion of options reading should be done by children
        return cls(**data)

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict):
        tags["hint"] = (Hint.from_xml, "hints", True)
        tags["penalty"] = (float, "penalty")
        # Defintion of options reading should be done by children
        return super().from_xml(root, tags, attrs)

    def to_xml(self, root: et.Element, strict: bool) -> et.Element:
        question = super().to_xml(root, strict)
        for hint in self.hints:
            hint.to_xml(question , strict)
        et.SubElement(question, "penalty").text = str(self.penalty)
        if hasattr(self, "options"):
            for sub in self.options:
                sub.to_xml(question, strict)
        return question


class _QuestionMTCS(_QuestionMT):
    """Represents classes that have both Multiple tries attributes and
    Combinated Feedbacks parameters. There are no classes that don't present
    all the 4 first attributes. Shuffle was added here too because it is
    also used by all the classes that uses the other 2 groups, except
    <code>QRandomMatching</code>. For now, this is the more efficient way to
    handle this. TODO: track future updates to shuffle attribute.
    """

    def __init__(self, if_correct: FText = None, if_incomplete: FText = None,
                 if_incorrect: FText = None, shuffle = False, show_num = False,
                 **kwargs) -> None:
        super().__init__(**kwargs)
        self.if_correct = FText("correctfeedback") \
                          if if_correct is None else if_correct
        self.if_incomplete = FText("partiallycorrectfeedback") \
                             if if_incomplete is None else if_incomplete
        self.if_incorrect = FText("incorrectfeedback") \
                            if if_incorrect is None else if_incorrect
        self.show_num = show_num
        self.shuffle = shuffle

    @classmethod
    def from_json(cls, data: dict):
        data["if_correct"] = FText.from_json(data["if_correct"])
        data["if_incomplete"] = FText.from_json(data["if_incomplete"])
        data["if_incorrect"] = FText.from_json(data["if_incorrect"])
        return super().from_json(data)

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict):
        tags["correctfeedback"] = (FText.from_xml, "if_correct")
        tags["partiallycorrectfeedback"] = (FText.from_xml, "if_incomplete")
        tags["incorrectfeedback"] = (FText.from_xml, "if_incorrect")
        tags["shownumcorrect"] = (bool, "show_num")
        tags["shuffleanswers"] = (bool, "shuffle")
        return super().from_xml(root, tags, attrs)

    def to_xml(self, root: et.Element, strict: bool) -> et.Element:
        question = super().to_xml(root, strict)
        self.if_correct.to_xml(question, strict)
        self.if_incomplete.to_xml(question, strict)
        self.if_incorrect.to_xml(question, strict)
        if self.show_num:
            et.SubElement(question, "shownumcorrect")
        if hasattr(self, "shuffle") and self.shuffle:
            et.SubElement(question, "shuffleanswers")
        return question


class QCalculated(_QuestionMT):
    """Represents a "Calculated"q question, in which a numberical result should
    be provided.
    """
    MOODLE = "calculated"
    QNAME = "Calculated"

    def __init__(self, synchronize: int = 0, single: bool = False,
                 uhandling: UnitHandling = None, units: List[Unit] = None,
                 datasets: List[Dataset] = None, **kwargs):
        """[summary]

        Args:
            synchronize (int): [description]
            single (bool, optional): [description]. Defaults to False.
            unit_handling (UnitHandling, optional): [description]. Defaults to None.
            units (List[Unit], optional): [description]. Defaults to None.
            datasets (List[Dataset], optional): [description]. Defaults to None.
        """
        super().__init__(**kwargs)
        self.synchronize = synchronize
        self.single = single
        self.unit_handling = UnitHandling() if uhandling is None else uhandling
        self.units = [] if units is None else units
        self.datasets = [] if datasets is None else datasets

    @classmethod
    def from_json(cls, data) -> "QCalculated":
        data["unit_handling"] = UnitHandling.from_json(data["unit_handling"])
        for i in range(len(data["units"])):
            data["units"][i] = Unit.from_json(data["units"][i])
        for i in range(len(data["datasets"])):
            data["datasets"][i] = Dataset.from_json(data["datasets"][i])
        for i in range(len(data["options"])):
            data["options"][i] = CalculatedAnswer.from_json(data["options"][i])
        return super().from_json(data)

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict):
        tags["synchronize"] = (bool, "synchronize")
        tags["single"] = (bool, "single")
        tags["unit_handling"] = (UnitHandling.from_xml, "uhandling")
        tags["units"] = (Unit.from_xml, "units", True)
        tags["dataset_definitions"] = (Dataset.from_xml_list, "datasets")
        tags["answer"] = (CalculatedAnswer.from_xml, "options", True)
        return super().from_xml(root, tags, attrs)

    def to_xml(self, root: et.Element, strict: bool) -> et.Element:
        question = super().to_xml(root, strict)
        if self.synchronize:
            et.SubElement(question, "synchronize")
        if self.single:
            et.SubElement(question, "single")
        self.unit_handling.to_xml(question, strict)
        if self.units:
            units = et.SubElement(question, "units")
            for unit in self.units:
                unit.to_xml(units, strict)
        if self.datasets:
            dataset_definitions = et.SubElement(question, "dataset_definitions")
            for dataset in self.datasets:
                dataset.to_xml(dataset_definitions, strict)
        return question


class QCalculatedSimple(QCalculated):
    """Same as QCalculated. Implemented only for compatibility with the moodle
    XML format.
    """
    MOODLE = "calculatedsimple"
    QNAME = "Simplified Calculated"


class QCalculatedMultichoice(_QuestionMTCS):
    """Represents a "Calculated" question with multiple choices, behaving like
    a multichoice question where the answers are calculated using equations and
    datasets.
    """
    MOODLE = "calculatedmulti"
    QNAME = "Calculated Multichoice"

    def __init__(self, synchronize: int = 0, single: bool = False,
                 numbering: Numbering = Numbering.ALF_LR,
                 datasets: List[Dataset] = None, **kwargs):
        super().__init__(**kwargs)
        self.synchronize = synchronize
        self.single = single
        self.numbering = numbering
        self.datasets = datasets if datasets is not None else []

    def add_dataset(self, status: Status, name: str, dist: Distribution,
                    minim: float, maxim: float, dec: int) -> None:
        """_summary_

        Args:
            status (Status): _description_
            name (str): _description_
            dist (Distribution): _description_
            minim (float): _description_
            maxim (float): _description_
            dec (int): _description_
        """
        self.datasets.append(Dataset(status, name, "calculated", dist, minim, maxim, dec))

    @classmethod
    def from_json(cls, data: dict) -> QCalculatedMultichoice:
        data["numbering"] = Numbering(data["numbering"])
        for i in range(len(data["datasets"])):
            data["datasets"][i] = Dataset.from_json(data["datasets"][i])
        for i in range(len(data["options"])):
            data["options"][i] = CalculatedAnswer.from_json(data["options"][i])
        return super().from_json(data)

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict):
        tags["synchronize"] = (bool, "synchronize")
        tags["single"] = (bool, "single")
        tags["answernumbering"] = (Numbering, "numbering")
        tags["dataset_definitions"] = (Dataset.from_xml_list, "datasets")
        tags["answer"] = (CalculatedAnswer.from_xml, "options", True)
        return super().from_xml(root, tags, attrs)

    def to_xml(self, root: et.Element, strict: bool) -> et.Element:
        question = super().to_xml(root, strict)
        if self.synchronize:
            et.SubElement(question, "synchronize")
        if self.single:
            et.SubElement(question, "single")
        et.SubElement(question, "answernumbering").text = self.numbering.value
        dataset_definitions = et.SubElement(question, "dataset_definitions")
        for dataset in self.datasets:
            dataset.to_xml(dataset_definitions, strict)
        return question


class QCloze(_QuestionMT):
    """This is a very simples class that hold cloze data. All data is compressed
    inside the question text, so no further implementation is necessary.
    """
    MOODLE = "cloze"
    QNAME = "Cloze"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._update_text()

    @classmethod
    def from_cloze(cls, buffer):
        """_summary_

        Args:
            buffer (MOODLE_): _description_

        Returns:
            QCloze: _description_
        """
        data = buffer.read()
        name, text = data.split("\n", 1)
        ftext = FText("questiontext", text, Format.HTML, None)
        return cls(name=name, question=ftext)

    def _update_text(self):
        pattern = re.compile(r"(?!\\)\{(\d+)?(?:\:(.*?)\:)(.*?(?!\\)\})")
        for match in pattern.finditer(self.question.text):
            item = ClozeItem.from_cloze(match)
            self.options.append(item)


class QDescription(_Question):
    """Represents a simple description. This is not a question. It has the same
    extructure as Question class and was add for compatiblity with the moodle
    XML format.
    """
    MOODLE = "description"
    QNAME = "Description"

    @classmethod
    def from_gift(cls, header: list, answer: list):
        formatting = Format(header[2][1:-1])
        if formatting is None:
            formatting = Format.MD
        return cls(name=header[1], question=FText("questiontext", header[3],
                                                  formatting, None))


class QDragAndDropText(_QuestionMTCS):
    """
    This class represents a drag and drop text onto image question.
    It inherits from abstract class Question.
    """
    MOODLE = "ddwtos"
    QNAME = "Drag and Drop Text"

    @classmethod
    def from_json(cls, data):
        for i in range(len(data["options"])):
            data["options"][i] = DragText.from_json(data["options"][i])
        return super().from_json(data)

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict):
        tags["dragbox"] = (DragText.from_xml, "options", True)
        return super().from_xml(root, tags, attrs)


class QDragAndDropImage(_QuestionMTCS):
    """This class represents a drag and drop onto image question.
    It inherits from abstract class Question.
    """
    MOODLE = "ddimageortext"
    QNAME = "Drag and Drop Image"

    def __init__(self, background: B64File = None,
                 dropzones: List[DropZone] = None, **kwargs) -> None:
        """Creates an drag and drop onto image type of question.

        Args:
            background (str): Filepath to the background image.
        """
        super().__init__(**kwargs)
        self.background = background
        self._dropzones: List[DropZone] = dropzones if dropzones is not None else []

    def add_dragimage(self, text: str, group: int, file: str,
                      unlimited: bool = False) -> None:
        """Adds new DragItem with assigned DropZones.

        Args:
            file (str): path to image to be used as a drag image;
            text (str, optional): text of the drag text.
            group (int, optional): group.
            unlimited (bool, optional): if item is allowed to be used again.
                Defaults to False.
        """
        dragimage = DragItem(len(self.options) + 1, text, unlimited, group,
                             image=file)
        self.options.append(dragimage)

    def add_dragtext(self, text: str, group: str, unlimited: bool = False) -> None:
        """Adds new DragText with assigned DropZones.

        Args:
            text (str): text of the drag text.
            group (str): group.
            unlimited (bool, optional): if item is allowed to be used again.
                Defaults to False.
        """
        dragitem = DragItem(len(self.options) + 1, text, unlimited, group)
        self.options.append(dragitem)

    def add_dropzone(self, coord_x: int, coord_y: int, text: str, choice: int) -> None:
        """[summary]

        Args:
            x (int): [description]
            y (int): [description]
            text (str): [description]
            choice (int): [description]
        """
        self._dropzones.append(DropZone(coord_x, coord_y, text, choice,
                                        len(self._dropzones) + 1))

    @classmethod
    def from_json(cls, data):
        data["background"] = B64File.from_json(data["background"])
        for i in range(len(data["options"])):
            data["options"][i] = DragItem.from_json(data["options"][i])
        for i in range(len(data["_dropzones"])):
            data["_dropzones"][i] = DropZone.from_json(data["_dropzones"][i])
        return super().from_json(data)

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict):
        tags["file"] = (B64File.from_xml, "background")
        tags["drag"] = (DragItem.from_xml, "options", True)
        tags["drop"] = (DropZone.from_xml, "dropzones", True)
        return super().from_xml(root, tags, attrs)

    def to_xml(self, root: et.Element, strict: bool):
        question = super().to_xml(root, strict)
        if self.background:
            self.background.to_xml(question, strict)
        for dropzone in self._dropzones:
            dropzone.to_xml(question, strict)
        return question


class QDragAndDropMarker(_QuestionMTCS):
    """Represents a Drag and Drop question where the items are markers.
    """
    MOODLE = "ddmarker"
    QNAME = "Drag and Drop Marker"

    def __init__(self, background: B64File = None, dropzones: List[DropZone] = None,
                 highlight_empty: bool = False, **kwargs):
        """Creates an drag and drop onto image type of question.

        Args:
            background (str): Filepath to the background image.
        """
        super().__init__(**kwargs)
        self.background = background
        self.highlight_empty = highlight_empty
        self._dropzones = dropzones if dropzones is not None else []

    def add_option(self, text: str, no_of_drags: str, unlimited: bool = False):
        """[summary]

        Args:
            text (str): [description]
            no_of_drags (str): [description]
            unlimited (bool, optional): [description]. Defaults to False.
        """
        dragitem = DragItem(len(self.options) + 1, text, unlimited,
                            no_of_drags=no_of_drags)
        self.options.append(dragitem)

    @classmethod
    def from_json(cls, data):
        data["background"] = B64File.from_json(data["background"])
        for i in range(len(data["options"])):
            data["options"][i] = DragItem.from_json(data["options"][i])
        for i in range(len(data["_dropzones"])):
            data["_dropzones"][i] = DropZone.from_json(data["_dropzones"][i])
        return super().from_json(data)

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict):
        tags["file"] = (B64File.from_xml, "background")
        tags["showmisplaced"] = (bool, "highlight_empty")
        tags["drag"] = (DragItem.from_xml, "options", True)
        tags["drop"] = (DropZone.from_xml, "dropzones", True)
        return super().from_xml(root, tags, attrs)

    def to_xml(self, root: et.Element, strict: bool):
        question = super().to_xml(root, strict)
        if self.highlight_empty:
            et.SubElement(question, "showmisplaced")
        for dropzone in self._dropzones:
            dropzone.to_xml(question, strict)
        if self.background:
            self.background.to_xml(question, strict)
        return question


class QEssay(_Question):
    """Represents an essay question, in which the answer is written as an essay
    and need to be submitted for review (no automatic correct/answer feedback
    provided).
    """
    MOODLE = "essay"
    QNAME = "Essay"

    def __init__(self, response_format: ResponseFormat = ResponseFormat.HTML,
                 response_required: bool = True, lines: int = 10, attachments: int = 0,
                 attachments_required: bool = False, maxbytes: int = None,
                 filetypes_list: str = None, grader_info: FText = None,
                 response_template: FText = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.response_format = response_format
        self.response_required = response_required
        self.responsefield_lines = lines
        self.attachments = attachments
        self.attachments_required = attachments_required
        self.maxbytes = maxbytes
        self.filetypes_list = filetypes_list
        self.grader_info = grader_info
        self.response_template = response_template

    @classmethod
    def from_gift(cls, header: list, answer: list):
        formatting = Format(header[2][1:-1])
        if formatting is None:
            formatting = Format.MD
        return cls(name=header[1], question=FText("questiontext", header[3],
                                                  formatting, None))

    @classmethod
    def from_json(cls, data):
        data["response_format"] = ResponseFormat(data["response_format"])
        data["grader_info"] = FText.from_json(data["grader_info"])
        data["response_template"] = FText.from_json(data["response_template"])
        return super().from_json(data)

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict):
        tags["responseformat"] = (ResponseFormat, "response_format")
        tags["responserequired"] = (bool, "response_required")
        tags["responsefieldlines"] = (int, "lines")
        tags["attachments"] = (int, "attachments")
        tags["attachmentsrequired"] = (bool, "attachments_required")
        tags["maxbytes"] = (int, "maxbytes")
        tags["filetypeslist"] = (str, "filetypes_list")
        tags["graderinfo"] = (FText.from_xml, "grader_info")
        tags["responsetemplate"] = (FText.from_xml, "response_template")
        return super().from_xml(root, tags, attrs)

    def to_xml(self, root: et.Element, strict: bool) -> et.Element:
        question = super().to_xml(root, strict)
        et.SubElement(question, "responseformat").text = self.response_format.value
        if self.response_required:
            et.SubElement(question, "responserequired")
        et.SubElement(question, "responsefieldlines").text = self.responsefield_lines
        et.SubElement(question, "attachments").text = self.attachments
        if self.attachments_required:
            et.SubElement(question, "attachmentsrequired")
        if self.maxbytes:
            et.SubElement(question, "maxbytes").text = self.maxbytes
        if self.filetypes_list:
            et.SubElement(question, "filetypeslist").text = self.filetypes_list
        if self.grader_info:
            self.grader_info.to_xml(question, strict)
        if self.response_template:
            self.response_template.to_xml(question, strict)
        return question


class QMatching(_QuestionMTCS):
    """Represents a Matching question, in which the goal is to find matchs.
    """
    MOODLE = "matching"
    QNAME = "Matching"

    def add_option(self, text: str, answer: str) -> None:
        """[summary]

        Args:
            text (str): [description]
            answer (str): [description]
        """
        self.options.append(Subquestion(Format.AUTO, text, answer))

    @classmethod
    def from_gift(cls, header: list, answer: list):
        formatting = Format(header[2][1:-1])
        if formatting is None:
            formatting = Format.MD
        qst = cls(name=header[1], question=FText("questiontext", header[3],
                                                 formatting, None))
        for ans in answer:
            if ans[0] == "=":
                rgx = re.match(r"(.*?)(?<!\\)->(.*)", ans[2])
                qst.options.append(Subquestion(formatting, rgx[1].strip(),
                                                    rgx[2].strip()))
            elif ans[0] == "####":
                qst.feedback = FText("generalfeedback", ans[2],
                                             formatting, None)
        return qst

    @classmethod
    def from_json(cls, data):
        for i in range(len(data["options"])):
            data["options"][i] = Subquestion.from_json(data["options"][i])
        return super().from_json(data)

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict):
        tags["subquestion"] = (Subquestion.from_xml, "options", True)
        return super().from_xml(root, tags, attrs)


class QRandomMatching(_QuestionMTCS):
    """Represents a Random match question.
    """
    MOODLE = "randomsamatch"
    QNAME = "Random Matching"

    def __init__(self, choose: int = 0, subcats: bool = False, **kwargs):
        super().__init__(**kwargs)
        delattr(self, "options")
        delattr(self, "shuffle")
        self.choose = choose
        self.subcats = subcats

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict):
        tags["choose"] = (int, "choose")
        tags["subcats"] = (bool, "subcats")
        return super().from_xml(root, tags, attrs)

    def to_xml(self, root: et.Element, strict: bool) -> et.Element:
        question = super().to_xml(root, strict)
        et.SubElement(question, "choose").text = self.choose
        et.SubElement(question, "subcats").text = self.subcats
        return question


class QMissingWord(_QuestionMTCS):
    """ Represents a "Missing Word" question.
    """
    MOODLE = "gapselect"
    QNAME = "Missing Word"

    @classmethod
    def from_json(cls, data):
        for i in range(len(data["options"])):
            data["options"][i] = SelectOption.from_json(data["options"][i])
        return super().from_json(data)

    @classmethod
    def from_gift(cls, header: list, answer: list):
        formatting = Format(header[2][1:-1])
        if formatting is None:
            formatting = Format.MD
        qst = cls(name=header[1], question=FText("questiontext", header[3],
                                                 formatting, None))
        correct = None
        for i in answer:
            if i[0] == "=":
                correct = SelectOption(i[2], 1)
            else:
                qst.options.append(SelectOption(i[2], 1))
        qst.options.insert(0, correct)
        return qst

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict):
        tags["selectoption"] = (SelectOption.from_xml, "options", True)
        return super().from_xml(root, tags, attrs)


class QMultichoice(_QuestionMTCS):
    """This class represents 'Multiple choice' question.
    """
    MOODLE = "multichoice"
    QNAME = "Multichoice"

    def __init__(self, single: bool = True, show_instruction: bool = False,
                 answer_numbering: Numbering = Numbering.ALF_LR, **kwargs):
        super().__init__(**kwargs)
        self.single = single
        self.show_instruction = show_instruction
        self.answer_numbering = answer_numbering

    @classmethod
    def from_json(cls, data):
        data["answer_numbering"] = Numbering(data["answer_numbering"])
        for i in range(len(data["options"])):
            data["options"][i] = Answer.from_json(data["options"][i])
        return super().from_json(data)

    @classmethod
    def from_aiken(cls, buffer, name):
        """_summary_

        Args:
            buffer (LineBuffer): _description_
            name (str): _description_

        Returns:
            QMultichoice: _description_
        """
        header = buffer.read(True)
        answers = []
        while buffer.read() and "ANSWER:" not in buffer.read()[:7]:
            ans = re.match(r"[A-Z]+\) (.+)", buffer.read(True))
            if ans:
                answers.append(Answer(0.0, ans[1], None, Format.PLAIN))
        try:
            answers[ord(buffer.read(True)[8].upper())-65].fraction = 100.0
        except IndexError:
            LOG.exception(f"Failed to set correct answer in question {name}.")
        return cls(name=name, options=answers,
                   question=FText("questiontext", header, Format.PLAIN, None))

    @classmethod
    def from_gift(cls, header: list, answer: list):
        formatting = Format(header[2][1:-1])
        if formatting is None:
            formatting = Format.MD
        qst = cls(name=header[1], question=FText("questiontext", header[3],
                                                 formatting, None))
        prev_answer = None
        for ans in answer:
            txt = ans[2]
            if ans[0] == "~": # Wrong or partially correct answer
                fraction = 0 if not ans[1] else float(ans[1][1:-1])
                prev_answer = Answer(fraction, txt, None, formatting)
                qst.options.append(prev_answer)
            elif ans[0] == "=": # Correct answer
                prev_answer = Answer(100, txt, None, formatting)
                qst.options.append(prev_answer)
            elif ans[0] == "#": # Answer feedback
                prev_answer.feedback = FText("feedback", ans[2],
                                             formatting, None)
        return qst

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict):
        tags["single"] = (bool, "single")
        tags["showstandardinstruction"] = (bool, "show_instruction")
        tags["answernumbering"] = (Numbering, "answer_numbering")
        tags["answer"] = (Answer.from_xml, "options", True)
        return super().from_xml(root, tags, attrs)

    @staticmethod
    def from_markdown(lines: list, answer_mkr: str, question_mkr: str,
                      name: str = "mkquestion"):
        """[summary]

        Returns:
            [type]: [description]
        """
        data = ""
        match = re.match(answer_mkr, lines[-1])
        while lines and match is None:
            data += lines.pop().strip()
            match = re.match(answer_mkr, lines[-1])
        question = QMultichoice(name=name, question=FText("questiontext", data,
                                                          Format.MD, None))
        regex_exp = f"({question_mkr})|({answer_mkr})"
        while lines:
            match = re.match(regex_exp, lines.pop())
            if match and match[3]:
                ans = Answer(100.0 if match[4] is not None else 0.0, match[5],
                             None, Format.HTML)
                question.options.append(ans)
            else:
                break
        return question

    def to_xml(self, root: et.Element, strict: bool) -> et.Element:
        question = super().to_xml(root, strict)
        et.SubElement(question, "answernumbering").text = self.answer_numbering.value
        if self.single:
            et.SubElement(question, "single")
        return question


class QNumerical(_QuestionMT):
    """
    This class represents 'Numerical Question' moodle question type.
    Units are currently not implemented, only numerical answer, which
    are specified as text and absolute tolerance value are implemented
    """
    MOODLE = "numerical"
    QNAME = "Numerical"

    def __init__(self, uhandling: UnitHandling = None,
                 units: List[Unit] = None,  **kwargs):
        super().__init__(**kwargs)
        self.unit_handling = UnitHandling() if uhandling is None else \
                             uhandling
        self.units = units if units is not None else []

    def add_option(self, text: str, tol: float, fraction: float,
                   feedback: str = None) -> None:
        """_summary_

        Args:
            tol (float): _description_
            fraction (float): _description_
            text (str): _description_
            feedback (str, optional): _description_. Defaults to None.
        """
        self.options.append(NumericalAnswer(tol, fraction=fraction, text=text,
                                            formatting=feedback))

    @classmethod
    def from_json(cls, data):
        data["unit_handling"] = UnitHandling.from_json(data["unit_handling"])
        for i in range(len(data["units"])):
            data["units"][i] = Unit.from_json(data["units"][i])
        for i in range(len(data["options"])):
            data["options"][i] = NumericalAnswer.from_json(data["options"][i])
        return super().from_json(data)

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict):
        tags["unit_handling"] = (UnitHandling.from_xml, "uhandling")
        tags["answer"] = (NumericalAnswer.from_xml, "options", True)
        tags["units"] = (Unit.from_xml, "units", True)
        return super().from_xml(root, tags, attrs)

    @classmethod
    def from_gift(cls, header: list, answer: list):
        def _extract(data: str) -> tuple:
            rgx = re.match(r"(.+?)(:|(?:\.\.))(.+)", data)
            if rgx[2] == "..": # Converts min/max to value +- tol
                txt = (float(rgx[1]) + float(rgx[3]))/2
                tol = txt - float(rgx[1])
                txt = str(txt)
            else:
                txt = rgx[1]
                tol = float(rgx[3])
            return txt, tol
        formatting = Format(header[2][1:-1])
        if formatting is None:
            formatting = Format.MD
        qst = cls(name=header[1], question=FText("questiontext", header[3],
                                                      formatting, None))
        if len(answer) == 1:
            txt, tol = _extract(answer[0][2])
            qst.options.append(NumericalAnswer(tol, fraction=100, text=txt,
                                               formatting=Format.AUTO))
        elif len(answer) > 1:
            for ans in answer[1:]:
                if ans[0] == "=":   # Happens first, thus nans is always defined
                    txt, tol = _extract(ans[2])
                    fraction = float(ans[1][1:-1]) if ans[0] == "=" else 0
                    nans = NumericalAnswer(tol, fraction=fraction, text=txt,
                                           formatting=Format.AUTO)
                    qst.options.append(nans)
                elif ans[0] == "~":
                    nans = NumericalAnswer(0, fraction=0, text="",
                                           formatting=Format.AUTO)
                elif ans[0] == "#":
                    nans.feedback = FText("feedback", ans[2], formatting, None)
        return qst

    def to_xml(self, root: et.Element, strict: bool) -> et.Element:
        question = super().to_xml(root, strict)
        self.unit_handling.to_xml(question, strict)
        if len(self.units) > 0:
            units = et.SubElement(question, "units")
            for unit in self.units:
                unit.to_xml(units, strict)
        return question


class QShortAnswer(_QuestionMT):
    """
    This class represents 'Short answer' question.
    """
    MOODLE = "shortanswer"
    QNAME = "Short Answer"

    def __init__(self, use_case: bool = False, **kwargs) -> None:
        super().__init__(**kwargs)
        self.use_case = use_case

    @classmethod
    def from_json(cls, data):
        for i in range(len(data["options"])):
            data["options"][i] = Answer.from_json(data["options"][i])
        return super().from_json(data)

    @classmethod
    def from_gift(cls, header: list, answer: list):
        formatting = Format(header[2][1:-1])
        if formatting is None:
            formatting = Format.MD
        qst = cls(name=header[1], question=FText("questiontext", header[3], formatting, None))
        for ans in answer:
            fraction = 100 if not ans[1] else float(ans[1][1:-1])
            qst.options.append(Answer(fraction, ans[2], formatting, Format.AUTO))
        return qst

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict):
        tags["usecase"] = (str, "use_case")
        tags["answer"] = (Answer.from_xml, "options", True)
        return super().from_xml(root, tags, attrs)

    def to_xml(self, root: et.Element, strict: bool) -> et.Element:
        question = super().to_xml(root, strict)
        et.SubElement(question, "usecase").text = self.use_case
        return question


class QTrueFalse(_Question):
    """
    This class represents true/false question.
    """
    MOODLE = "truefalse"
    QNAME = "True or False"

    def __init__(self, options: list, **kwargs) -> None:
        super().__init__(**kwargs)
        if options is not None:
            if len(options) != 2:
                raise ValueError()
            for answer in options:
                if answer.text.lower() == "true":
                    self.__true = answer
                    self.__correct = answer.fraction == 100
                elif answer.text.lower() == "false":
                    self.__false = answer
        else:
            self.__true = Answer(100, "true", FText("feedback"), Format.AUTO)
            self.__false = Answer(0, "false", FText("feedback"), Format.AUTO)
            self.__correct = True

    def set_feedbacks(self, correct: FText, incorrect: FText):
        """_summary_

        Args:
            correct (FText): _description_
            incorrect (FText): _description_
        """
        self.__true.feedback = correct if self.correct_answer else incorrect
        self.__false.feedback = correct if not self.correct_answer else incorrect

    @property
    def correct_answer(self) -> bool:
        """_summary_

        Returns:
            bool: _description_
        """
        return self.__correct

    @correct_answer.setter
    def correct_answer(self, value: bool) -> None:
        """_summary_

        Args:
            value (bool): _description_
        """
        self.__true.fraction = 100 if value else 0
        self.__false.fraction = 100 if not value else 0
        self.__correct = value

    @classmethod
    def from_json(cls, data):
        data["options"] = [Answer.from_json(data["_QTrueFalse__true"]),
                           Answer.from_json(data["_QTrueFalse__false"])]
        return super().from_json(data)

    @classmethod
    def from_gift(cls, header: list, answer: list):
        correct = answer.pop(0)[0].lower() in ["true", "t"]
        true_ans = Answer(100 if correct else 0, "true", None, Format.AUTO)
        false_ans = Answer(0 if correct else 100, "false", None, Format.AUTO)
        formatting = Format(header[2][1:-1])
        if formatting is None:
            formatting = Format.MD
        qst = cls(options=[true_ans, false_ans], name=header[1],
                  question=FText("questiontext", header[3], formatting, None))
        for ans in answer:
            if ans[0] == "####":
                qst.feedback = FText("generalfeedback", ans[2],
                                     Format(header[2][1:-1]))
            elif false_ans.feedback is None:
                false_ans.feedback = FText("feedback", ans[2],
                                           Format(header[2][1:-1]))
            else:
                true_ans = FText("feedback", ans[2], Format(header[2][1:-1]))
        return qst

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict):
        tags["answer"] = (Answer.from_xml, "options", True)
        return super().from_xml(root, tags, attrs)

    def to_xml(self, root: et.Element, strict: bool) -> et.Element:
        question = super().to_xml(root, strict)
        self.__true.to_xml(question, strict)
        self.__false.to_xml(question, strict)
        return question


class QFreeDrawing(_Question):
    """Represents a question where the use is free to make any drawing. The
    result is submited for review (there is no automatic correct/wrong feedback).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class QLineDrawing(_Question):
    """Represents a question where the user should draw line either to complete
    an image or to draw a new one. The result is submited for review (there is
    no automatic correct/wrong feedback).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class QCrossWord(_Question):
    """Represents a Crossword question.
    """

    def __init__(self, x_grid: int = 0, y_grid: int = 0,
                 words: List[CrossWord] = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.x_grid = x_grid
        self.y_grid = y_grid
        self.words = words if words else []      # The class only checks grid

    def add_word(self, word: str, coord_x: int, coord_y: int,
                 direction: Direction, clue: str) -> None:
        """_summary_

        Args:
            word (str): _description_
            coord_x (int): _description_
            coord_y (int): _description_
            direction (Direction): _description_
            clue (str): _description_

        Raises:
            ValueError: _description_
        """
        if coord_x < 0 or coord_x > self.x_grid+len(word) or \
                coord_y < 0 or coord_y > self.y_grid+len(word):
            raise ValueError("New word does not fit in the current grid")
        self.words.append(CrossWord(word, coord_x, coord_y, direction, clue))

    def get_solution(self) -> bool:
        """
        Iterate over the object list to verify if it is valid.
        """
        solution: Dict[int, Dict[int, str]] = {}
        for word in self.words:
            if word.coord_x not in solution:
                solution[word.x] = {}
            if word.coord_y not in solution:
                solution[word.coord_x][word.coord_y] = {}

    @classmethod
    def from_json(cls, data):
        for i in range(len(data["words"])):
            data["words"][i] = CrossWord.from_json(data["words"][i])
        return super().from_json(data)
