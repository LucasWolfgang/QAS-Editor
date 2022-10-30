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
import json
import logging
from typing import TYPE_CHECKING
from enum import Enum
from ..enums import EmbeddedFormat, Direction, Distribution, Grading, RespFormat,\
                    ShapeType, Synchronise, TolType, TolFormat, Status,\
                    ShowUnits, TextFormat, Numbering
from ..utils import File, Dataset, FText, Hint, Serializable, TList, Unit, MediaType, FileAddr
from ..answer import ACalculated, ANumerical, Answer, EmbeddedItem, DragItem,\
                     ACrossWord, DropZone, SelectOption, DragGroup, DragImage,\
                     Subquestion
from ..question import _Question, QCalculatedMC, QCrossWord, QEmbedded,\
                        QTrueFalse, QCalculated, QCalculatedSimple, QEssay,\
                        QDaDImage, QDaDMarker, QMissingWord, QDescription,\
                        QMatching, QDaDText, QMultichoice, QRandomMatching,\
                        QNumerical,  QShortAnswer
if TYPE_CHECKING:
    from ..category import Category


_LOG = logging.getLogger(__name__)

def _from_json(data: dict, cls):
    # all_cls = list(cls.__mro__[:-1]) # Removed Object class
    # all_cls.pop(Serializable) # Pop Serializable class if it exists
    # all_args = [_cls.__init__.__code__.co_varnames for _cls in all_cls]
    if isinstance(data, dict):
        # for key in list(data):
        #     if key not in all_args:
        #         data.pop(key)
        #         _LOG.debug("Removed argument %s for %s __init__.", key, cls)
        item = cls(**data)
        return item
    return None


def _from_file(data: dict):
    if data is None:
        return None
    data["ftype"] = FileAddr(data.pop("_type"))
    data.pop("_media", None)
    data.pop("_type", None)
    if data["metadata"]:
        data.update(data.pop("metadata"))
    return _from_json(data, File)


def _from_dataset(data: dict):
    if data is None:
        return None
    data["status"] = Status(data["status"])
    data["distribution"] = Distribution(data["distribution"])
    tmp = {}  # Convertion of keys from string to int
    for key in data["items"]:
        tmp[int(key)] = data["items"][key]
    data["items"] = tmp
    return _from_json(data, Dataset)


def _from_ftext(data: dict):
    if data is None:
        return None
    data["formatting"] = TextFormat(data["formatting"])
    data["text"] = data.pop("_text", "")
    for index in range(len(data["bfile"])):
        data["bfile"][index] = _from_file(data["bfile"][index])
    return _from_json(data, FText)


def _from_hint(data: dict):
    if data is None:
        return None
    data["formatting"] = TextFormat(data["formatting"])
    return _from_json(data, Hint)


def _from_tags(data: list):
    if data is None:
        return None
    return TList(str, data)


def _from_unit(data: dict):
    if data is None:
        return None
    return _from_json(data, Unit)


# -----------------------------------------------------------------------------


def _from_answer(data: dict, cls=None):
    if data is None:
        return None
    data["formatting"] = TextFormat(data["formatting"])
    data["feedback"] = _from_ftext(data.pop("_feedback"))
    return _from_json(data, cls if cls else Answer)


def _from_anumerical(data: dict, cls=None):
    if data is None:
        return None
    return _from_answer(data, cls if cls else ANumerical)


def _from_acalculated(data: dict):
    if data is None:
        return None
    data["ttype"] = TolType(data["ttype"])
    data["aformat"] = TolFormat(data["aformat"])
    return _from_anumerical(data, ACalculated)


def _from_clozeitem(data: dict):
    if data is None:
        return None
    data["cformat"] = EmbeddedFormat(data["cformat"])
    for i in range(len(data["opts"])):
        data["opts"][i] = _from_answer(data["opts"][i])
    return _from_json(data, EmbeddedItem)


def _from_dragitem(data: dict):
    if data is None:
        return None
    return DragItem(**data)


def _from_draggroup(data: dict):
    if data is None:
        return None
    return DragGroup(**data)


def _from_dragimage(data: dict):
    if data is None:
        return None
    data["image"] = _from_file(data["image"])
    return DragImage(**data)


def _from_dropzone(data: dict):
    if data is None:
        return None
    if data["shape"] is not None:
        data["shape"] = ShapeType(data["shape"])
    return _from_json(data, DropZone)


def _from_acrossword(data: dict):
    if data is None:
        return None
    data["direction"] = Direction(data["direction"])
    return _from_json(data, ACrossWord)


def _from_subquestion(data: dict):
    if data is None:
        return None
    data["formatting"] = TextFormat(data["formatting"])
    return _from_json(data, Subquestion)


def _from_selectoption(data: dict):
    return _from_json(data, SelectOption)


# -----------------------------------------------------------------------------


def _from_question(data: dict, cls):
    data["question"] = _from_ftext(data.pop("_question"))
    data["remarks"] = _from_ftext(data.pop("_remarks"))
    data["tags"] = _from_tags(data.pop("_tags", None))
    for key in data["_feedbacks"]:
        data["_feedbacks"][key] = _from_ftext(data["_feedbacks"][key])
    data["feedbacks"] = data.pop("_feedbacks")
    data["free_hints"] = data.pop("_free_hints", None)
    return _from_json(data, cls)


def _from_question_mt(data: dict, cls, opt_callback):
    for i in range(len(data["_fail_hints"])):
        data["_fail_hints"][i] = _from_hint(data["_fail_hints"][i])
    data["hints"] = data.pop("_fail_hints")
    if opt_callback is not None:
        for i in range(len(data["_options"])):
            data["_options"][i] = opt_callback(data["_options"][i])
        data["options"] = data.pop("_options")
    return _from_question(data, cls)


def _from_question_mtuh(data: dict, cls, opt_callback):
    data["grading_type"] = Grading(data["grading_type"])
    data["show_unit"] = ShowUnits(data["show_unit"])
    return _from_question_mt(data, cls, opt_callback)


def _from_qcalculated(data: dict, cls=None):
    data["synchronize"] = Synchronise(data["synchronize"])
    for i in range(len(data["units"])):
        data["units"][i] = _from_unit(data["units"][i])
    for i in range(len(data["datasets"])):
        data["datasets"][i] = _from_dataset(data["datasets"][i])
    return _from_question_mtuh(data, cls if cls else QCalculated,
                               _from_acalculated)


def _from_qcalculatedsimple(data: dict):
    return _from_qcalculated(data, QCalculatedSimple)


def _from_qcalculatedmc(data: dict):
    data["numbering"] = Numbering(data["numbering"])
    data["synchronize"] = Synchronise(data["synchronize"])
    for i in range(len(data["datasets"])):
        data["datasets"][i] = _from_dataset(data["datasets"][i])
    return _from_question_mt(data, QCalculatedMC, _from_acalculated)


def _from_qcloze(data: dict):
    return _from_question_mt(data, QEmbedded, _from_clozeitem)


def _from_qdescription(data: dict):
    return _from_question(data, QDescription)


def _from_qdraganddroptext(data: dict):
    return _from_question_mt(data, QDaDText, _from_draggroup)


def _from_qdraganddropimage(data: dict, cls=None, callback=None):
    data["background"] = _from_file(data["background"])
    for i in range(len(data["_zones"])):
        data["_zones"][i] = _from_dropzone(data["_zones"][i])
    data["zones"] = data.pop("_zones")
    return _from_question_mt(data, cls if cls else QDaDImage,
                               callback if callback else _from_dragimage)


def _from_qdraganddropmarker(data: dict):
    return _from_qdraganddropimage(data, QDaDMarker, _from_dragitem)


def _from_qessay(data: dict):
    data["rsp_format"] = RespFormat(data["rsp_format"])
    data["grader_info"] = _from_ftext(data["grader_info"])
    data["template"] = _from_ftext(data["template"])
    return _from_question(data, QEssay)


def _from_qmatching(data: dict):
    return _from_question_mt(data, QMatching, _from_subquestion)


def _from_qrandommatching(data: dict):
    return _from_question_mt(data, QRandomMatching, None)


def _from_qmissingword(data: dict):
    return _from_question_mt(data, QMissingWord, _from_selectoption)


def _from_qcrossword(data: dict):
    for i in range(len(data["words"])):
        data["words"][i] = _from_acrossword(data["words"][i])
    return _from_question(data, QCrossWord)


def _from_qmultichoice(data: dict):
    data["numbering"] = Numbering(data["numbering"])
    return _from_question_mt(data, QMultichoice, _from_answer)


def _from_qnumerical(data: dict):
    for i in range(len(data["units"])):
        data["units"][i] = _from_unit(data["units"][i])
    return _from_question_mtuh(data, QNumerical, _from_anumerical)


def _from_qshortanswer(data: dict):
    return _from_question_mt(data, QShortAnswer, _from_answer)


def _from_qtruefalse(data: dict):
    data["true_feedback"] = _from_ftext(data.pop("_true_feedback"))
    data["false_feedback"] = _from_ftext(data.pop("_false_feedback"))
    return _from_question(data, QTrueFalse)


# -----------------------------------------------------------------------------


_QTYPE = {
    "QCalculated": _from_qcalculated,
    "QCalculatedSimple": _from_qcalculatedsimple,
    "QCalculatedMC": _from_qcalculatedmc,
    "QEmbedded": _from_qcloze,
    "QDescription": _from_qdescription,
    "QDaDText": _from_qdraganddroptext,
    "QDaDImage": _from_qdraganddropimage,
    "QDaDMarker": _from_qdraganddropmarker,
    "QEssay": _from_qessay,
    "QMatching": _from_qmatching,
    "QRandomMatching": _from_qrandommatching,
    "QMissingWord": _from_qmissingword,
    "QMultichoice": _from_qmultichoice,
    "QNumerical": _from_qnumerical,
    "QShortAnswer": _from_qshortanswer,
    "QTrueFalse": _from_qtruefalse
}


def read_json(cls, file_path) -> "Category":
    """
    Generic file. This is the default file format used by the QAS Editor.
    """
    def _rjrecursive(_dt: dict):
        quiz = cls(_dt["_Category__name"])
        for qst in _dt["_Category__questions"]:
            quiz.add_question(_QTYPE[qst.pop("__clsname__")](qst))
        for i in _dt["_Category__categories"]:
            quiz.add_subcat(_rjrecursive(_dt["_Category__categories"][i]))
        return quiz
    with open(file_path, "rb") as infile:
        data = json.load(infile)
    return _rjrecursive(data)


# -----------------------------------------------------------------------------


def write_json(self, file_path: str, pretty=False) -> None:
    """[summary]

    Args:
        file_path (str): [description]
        pretty (bool, optional): [description]. Defaults to False.
    """
    def _tjrecursive(data):
        for num, i in enumerate(data):
            res = val = data[i] if isinstance(data, dict) else i
            if isinstance(val, (list, dict)):
                res = _tjrecursive(val.copy())
            elif isinstance(val, Enum):  # For the enums
                res = val.value
            elif hasattr(val, "__dict__"):  # for the objects
                tmp = val.__dict__.copy()
                if isinstance(val, _Question):
                    tmp["__clsname__"] = val.__class__.__name__
                if "_Question__parent" in tmp:
                    del tmp["_Question__parent"]
                elif "_Category__parent" in tmp:
                    del tmp["_Category__parent"]
                res = _tjrecursive(tmp)
            if res != val:
                if isinstance(data, dict):
                    data[i] = res
                else:
                    data[num] = res
        return data
    tmp = self.__dict__.copy()
    del tmp["_Category__parent"]
    with open(file_path, "w", encoding="utf-8") as ofile:
        json.dump(_tjrecursive(tmp), ofile, indent=4 if pretty else None)
