"""
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
import logging
import zipfile
from typing import TYPE_CHECKING
from xml.etree import ElementTree as et

from ..answer import ACalculated, ANumerical, Answer, DragItem, DragGroup, \
                     DragImage, DropZone, Subquestion, SelectOption
from ..question import QCalculated, QCalculatedMC, QDescription, QDaDImage,\
                       QCalculatedSimple, QCloze, QMissingWord, QTrueFalse,\
                       QDaDMarker, QNumerical, QDaDText, QEssay, QMatching,\
                       QMultichoice, QRandomMatching, QShortAnswer
from ..enums import TextFormat, ShowUnits, Numbering, RespFormat, Synchronise,\
                    ShapeType, Grading, Status, TolFormat, TolType,\
                    Distribution, ShowAnswer
from ..utils import gen_hier, Dataset, Hint, TList, FText, File, Unit, \
                    EXTRAS_FORMULAE, nxt, serialize_fxml
if TYPE_CHECKING:
    from ..category import Category, _Question
    from ..question import _QHasOptions, _QHasUnits
_LOG = logging.getLogger(__name__)


def get_sympy(string: str) -> str:
    """This function suposse that at least once the 
    """
    if EXTRAS_FORMULAE:
        from sympy.parsing.sympy_parser import parse_expr 
    result = []
    _vars = set()
    last = 0
    counter = 0
    stt = [0, False]
    while stt[0] < len(string):
        if string[stt[0]] == "{" and not stt[1]:
            nxt(stt, string)
            if counter == 0:
                result.append(string[last: stt[0]-1])
                last = stt[0]
                if string[stt[0]] == "=" and not stt[1]:
                    last +=1
            counter += 1
        elif string[stt[0]] == "}" and not stt[1]:
            counter -= 1
            if counter == 0:
                expr = string[last: stt[0]]
                if EXTRAS_FORMULAE:
                    expr = expr.replace("{","").replace("}","")
                    expr = expr.replace("pi()","pi")
                    expr = parse_expr(expr)
                    _vars |= expr.free_symbols
                    last = stt[0] + 1
                elif expr.isalpha():
                    _vars |= expr
                result.append(expr)
        nxt(stt, string)
    result.append(string[last:])
    return _vars, result

# -----------------------------------------------------------------------------


def _from_xml(root: et.Element, tags: dict) -> dict:
    if root is None:
        return None
    results = {}
    for obj in root:
        if obj.tag in tags:
            cast_type, name, *_ = tags[obj.tag]
            if not isinstance(cast_type, type):
                tmp = cast_type(obj, {})
            else:
                tmp = obj.text.strip() if obj.text else ""
                if not tmp:
                    text = obj.find("text")
                    if text is not None:
                        tmp = text.text
                if cast_type == bool:
                    tmp = tmp.lower() in ["true", "1", "t", ""]
                elif tmp or cast_type == str:
                    tmp = cast_type(tmp)
            if len(tags[obj.tag]) == 3 and tags[obj.tag][2]:
                if name not in results:
                    results[name] = []
                results[name].append(tmp)
            else:
                results[name] = tmp
                tags.pop(obj.tag)
    for key in tags:
        cast_type, name, *_ = tags[key]
        if cast_type == bool:  # Some tags act like False when missing
            results[name] = False
    return results


def _from_B64File(root: et.Element, *_):
    return File(root.get("name"), root.get("path"), root.text)


def _from_DatasetItems(root: et.Element, *_):
    data = {}
    for item in root:
        number = int(item.find("number").text)
        value = float(item.find("value").text)
        data[number] = value
    return data


def _from_Datasets(root: et.Element, tags: dict):
    data = []
    for obj in root:
        tags["status"] = (Status, "status")
        tags["name"] = (str, "name")
        tags["type"] = (str, "ctype")
        tags["distribution"] = (Distribution, "distribution")
        tags["minimum"] = (str, "minimum")
        tags["maximum"] = (str, "maximum")
        tags["decimals"] = (str, "decimals")
        tags["dataset_items"] = (_from_DatasetItems, "items")
        data.append(Dataset(**_from_xml(obj, tags)))
    return data


def _from_FText(root: et.Element, tags: dict):
    tags["text"] = (str, "text")
    tags["file"] = (_from_B64File, "bfile", True)
    data = _from_xml(root, tags)
    data["formatting"] = TextFormat(root.get("format"))
    return FText(**data)


def _from_Hint(root: et.Element, tags: dict) -> "Hint":
    tags["text"] = (str, "text")
    tags["options"] = (bool, "state_incorrect")
    tags["shownumcorrect"] = (bool, "show_correct")
    tags["clearwrong"] = (bool, "clear_wrong")
    data = _from_xml(root, tags)
    data["formatting"] = TextFormat(root.get("format"))
    return Hint(**data)


def _from_SelectOption(root: et.Element, tags: dict):
    tags["text"] = (str, "text")
    tags["group"] = (str, "group")
    return SelectOption(**_from_xml(root, tags))


def _from_Subquestion(root: et.Element, tags: dict):
    tags["text"] = (str, "text")
    tags["answer"] = (str, "answer")
    data = _from_xml(root, tags)
    data["formatting"] = TextFormat(root.get("format"))
    return Subquestion(**data)


def _from_units(root: et.Element, *_) -> Unit:
    units = []
    for elem in root:
        multiplier = float(elem.find("multiplier").text)
        unit = Unit(elem.find("unit_name").text, multiplier)
        units.append(unit)
    return units


def _from_Tags(root: et.Element, *_) -> TList:
    _tags = TList(str)
    for elem in root:
        _tags.append(elem.find("text").text)
    return _tags


# -----------------------------------------------------------------------------


def _from_Answer(root: et.Element, tags: dict, go_up=False):
    tags["text"] = (str, "text")
    tags["feedback"] = (_from_FText, "feedback")
    data = _from_xml(root, tags)
    data["formatting"] = TextFormat(root.get("format", "plain_text"))
    data["fraction"] = float(root.get("fraction", 0))
    return data if go_up else Answer(**data)


def _from_ANumerical(root: et.Element, tags: dict, go_up=False):
    tags["tolerance"] = (float, "tolerance")
    data = _from_Answer(root, tags, True)
    return data if go_up else ANumerical(**data)


def _from_ACalculated(root: et.Element, tags: dict):
    tags["tolerancetype"] = (TolType, "ttype")
    tags["correctanswerformat"] = (TolFormat, "aformat")
    tags["correctanswerlength"] = (int, "alength")
    return ACalculated(**_from_ANumerical(root, tags, True))


def _from_draggroup(root: et.Element, tags: dict):
    tags["text"] = (str, "text")
    tags["group"] = (str, "group")
    tags["unlimited"] = (bool, "unlimited")
    data = _from_xml(root, tags)
    unlimited = data.pop("unlimited")
    data["no_of_drags"] = -1 if unlimited else 1
    return DragGroup(**data)


def _from_dropzone(root: et.Element, *_):
    data = {a.tag: a for a in root}
    res = {}
    if "coords" in data and "shape" in data:
        res["shape"] = ShapeType(data["shape"].text)
        coords = data["coords"].text.split(";", 1)
        res["coord_x"], res["coord_y"] = map(int, coords[0].split(","))
        res["points"] = coords[1]
    elif "xleft" in data and "ytop" in data:
        res["coord_x"] = int(data["xleft"].text)
        res["coord_y"] = int(data["ytop"].text)
    else:
        raise AttributeError("One or more coordenates are missing")
    res["choice"] = int(data["choice"].text)
    res["number"] = int(data["no"].text)
    res["text"] = data["text"].text if "text" in data else None
    return DropZone(**res)


# -----------------------------------------------------------------------------


def _from_question(root: et.Element, tags: dict):
    tags["name"] = (str, "name")
    tags["questiontext"] = (_from_FText, "question")
    tags["generalfeedback"] = (_from_FText, "remarks")
    tags["defaultgrade"] = (float, "default_grade")
    tags["idnumber"] = (int, "dbid")
    tags["tags"] = (_from_Tags, "tags")
    return _from_xml(root, tags)


def _from_question_mt(root: et.Element, tags: dict):
    tags["hint"] = (_from_Hint, "hints", True)
    tags["max_tries"] = (float, "penalty")
    res = _from_question(root, tags)
    if res.get("max_tries") is None:
        res["max_tries"] = -1
    else:
        res["max_tries"] = int(1/res["max_tries"])
    return res


def _from_question_mtcs(root: et.Element, tags: dict):
    tags["correctfeedback"] = (_from_FText, "if_correct")
    tags["partiallycorrectfeedback"] = (_from_FText, "if_incomplete")
    tags["incorrectfeedback"] = (_from_FText, "if_incorrect")
    tags["shownumcorrect"] = (bool, "show_ans")
    tags["shuffleanswers"] = (bool, "shuffle")
    data = _from_question_mt(root, tags)
    data["feedbacks"] = {}
    data["feedbacks"][0.0] = data.pop("if_correct")
    data["feedbacks"][50.0] = data.pop("if_incomplete")
    data["feedbacks"][100.0] = data.pop("if_incorrect")
    return data


def _from_question_mtuh(root: et.Element, tags: dict):
    tags["unitgradingtype"] = (Grading, "grading_type")
    tags["unitpenalty"] = (str, "unit_penalty")
    tags["unitsleft"] = (bool, "left")
    tags["showunits"] = (ShowUnits, "show_unit")
    return _from_question_mt(root, tags)


def _from_qcalculated(root: et.Element, tags: dict, go_up=False):
    tags["synchronize"] = (Synchronise, "synchronize")
    tags["units"] = (_from_units, "units", False)
    tags["dataset_definitions"] = (_from_Datasets, "datasets")
    tags["answer"] = (_from_ACalculated, "options", True)
    data = _from_question_mtuh(root, tags)
    return data if go_up else QCalculated(**data)


def _from_qcalculatedsimple(root: et.Element, tags: dict):
    return QCalculatedSimple(**_from_qcalculated(root, tags, True))


def _from_qcalcmultichoice(root: et.Element, tags: dict):
    tags["synchronize"] = (Synchronise, "synchronize")
    tags["single"] = (bool, "single")
    tags["answernumbering"] = (Numbering, "numbering")
    tags["dataset_definitions"] = (_from_Datasets, "datasets")
    tags["answer"] = (_from_ACalculated, "options", True)
    return QCalculatedMC(**_from_question_mtcs(root, tags))


def _from_qcloze(root: et.Element, tags: dict):
    data = _from_question_mt(root, tags)
    text, opts = QCloze.get_items(data["question"].text)
    data["question"].text = text
    data["options"] = opts
    return QCloze(**data)


def _from_qdescription(root: et.Element, tags: dict):
    return QDescription(**_from_question(root, tags))


def _from_ddwtos(root: et.Element, tags: dict):
    tags["dragbox"] = (_from_draggroup, "options", True)
    return QDaDText(**_from_question_mtcs(root, tags))


def _from_ddimageortext(root: et.Element, tags: dict):
    def _from_dragimage(root: et.Element, tags: dict):
        tags["no"] = (int, "number")
        tags["text"] = (str, "text")
        tags["infinite"] = (bool, "unlimited")
        tags["draggroup"] = (int, "group")
        tags["file"] = (_from_B64File, "image")
        data = _from_xml(root, tags)
        unlimited = data.pop("unlimited")
        data["no_of_drags"] = -1 if unlimited else 1
        return DragImage(**data)
    tags["file"] = (_from_B64File, "background")
    tags["drag"] = (_from_dragimage, "options", True)
    tags["drop"] = (_from_dropzone, "zones", True)
    return QDaDImage(**_from_question_mtcs(root, tags))


def _from_ddmarker(root: et.Element, tags: dict):
    def _from_dragitem(root: et.Element, tags: dict):
        tags["no"] = (int, "number")
        tags["text"] = (str, "text")
        tags["infinite"] = (bool, "no_of_drags")
        data = _from_xml(root, tags)
        data["no_of_drags"] = -1 if data["no_of_drags"] else 1
        return DragItem(**data)
    tags["file"] = (_from_B64File, "background")
    tags["showmisplaced"] = (bool, "highlight")
    tags["drag"] = (_from_dragitem, "options", True)
    tags["drop"] = (_from_dropzone, "zones", True)
    return QDaDMarker(**_from_question_mtcs(root, tags))


def _from_qessay(root: et.Element, tags: dict):
    tags["responseformat"] = (RespFormat, "rsp_format")
    tags["responserequired"] = (bool, "rsp_required")
    tags["responsefieldlines"] = (int, "lines")
    tags["minwordlimit"] = (int, "min_words")
    tags["minwordlimit"] = (int, "max_words")
    tags["attachments"] = (int, "attachments")
    tags["attachmentsrequired"] = (bool, "atts_required")
    tags["maxbytes"] = (int, "max_bytes")
    tags["filetypeslist"] = (str, "file_types")
    tags["graderinfo"] = (_from_FText, "grader_info")
    tags["responsetemplate"] = (_from_FText, "template")
    return QEssay(**_from_question(root, tags))


def _from_qmatching(root: et.Element, tags: dict):
    tags["subquestion"] = (_from_Subquestion, "options", True)
    return QMatching(**_from_question_mtcs(root, tags))


def _from_QRandomMatching(root: et.Element, tags: dict):
    tags["choose"] = (int, "choose")
    tags["subcats"] = (bool, "subcats")
    return QRandomMatching(**_from_question_mtcs(root, tags))


def _from_QMissingWord(root: et.Element, tags: dict):
    tags["selectoption"] = (_from_SelectOption, "options", True)
    return QMissingWord(**_from_question_mtcs(root, tags))


def _from_QMultichoice(root: et.Element, tags: dict):
    tags["single"] = (bool, "single")
    tags["showstandardinstruction"] = (bool, "show_instr")
    tags["answernumbering"] = (Numbering, "numbering")
    tags["answer"] = (_from_Answer, "options", True)
    return QMultichoice(**_from_question_mtcs(root, tags))


def _from_QNumerical(root: et.Element, tags: dict):
    tags["answer"] = (_from_ANumerical, "options", True)
    tags["units"] = (_from_units, "units", False)
    return QNumerical(**_from_question_mtuh(root, tags))


def _from_QShortAnswer(root: et.Element, tags: dict):
    tags["usecase"] = (str, "use_case")
    tags["answer"] = (_from_Answer, "options", True)
    return QShortAnswer(**_from_question_mt(root, tags))


def _from_QTrueFalse(root: et.Element, tags: dict):
    tags["answer"] = (_from_Answer, "options", True)
    data = _from_question(root, tags)
    opt = data.pop("options")
    if opt[0].text.lower() == "true":
        data["correct"] = opt[0].fraction == 100
        data["true_feedback"] = opt[0].feedback
        data["false_feedback"] = opt[1].feedback
    else:
        data["correct"] = opt[0].fraction == 0
        data["true_feedback"] = opt[1].feedback
        data["false_feedback"] = opt[0].feedback
    return QTrueFalse(**data)


# -----------------------------------------------------------------------------


def _to_b64file(b64file: File) -> et.Element:
    bfile = et.Element("file", {"name": b64file.name, "encoding": "base64"})
    if b64file.path:
        bfile.set("path", b64file.path)
    bfile.text = b64file.source
    return bfile


def _to_dataset(dset) -> et.Element:
    dataset_def = et.Element("dataset_definition")
    status = et.SubElement(dataset_def, "status")
    et.SubElement(status, "text").text = dset.status.value
    name = et.SubElement(dataset_def, "name")
    et.SubElement(name, "text").text = dset.name
    et.SubElement(dataset_def, "type").text = dset.ctype
    distribution = et.SubElement(dataset_def, "distribution")
    et.SubElement(distribution, "text").text = dset.distribution.value
    minimum = et.SubElement(dataset_def, "minimum")
    et.SubElement(minimum, "text").text = dset.minimum
    maximum = et.SubElement(dataset_def, "maximum")
    et.SubElement(maximum, "text").text = dset.maximum
    decimals = et.SubElement(dataset_def, "decimals")
    et.SubElement(decimals, "text").text = dset.decimals
    et.SubElement(dataset_def, "itemcount").text = len(dset.items)
    dataset_items = et.SubElement(dataset_def, "dataset_items")
    for key, val in dset.items.items():
        item = et.Element("dataset_item")
        number = et.Element("number")
        number.text = key
        item.append(number)
        value = et.Element("value")
        value.text = val
        item.append(value)
        dataset_items.append(item)
    et.SubElement(dataset_def, "number_of_items").text = len(dset.items)
    return dataset_def


def _to_ftext(ftext: FText, name: str) -> None:
    elem = et.Element(name, {"format": ftext.formatting.value})
    txt = et.SubElement(elem, "text")
    txt.text = ftext.text
    for bfile in ftext.bfile:
        elem.append(_to_b64file(bfile))
    return elem


def _to_hint(hint: Hint) -> et.Element:
    elem = et.Element("hint", {"format": hint.formatting.value})
    txt = et.SubElement(elem, "text")
    txt.text = hint.text
    if hint.show_correct:
        et.SubElement(elem, "shownumcorrect")
    if hint.state_incorrect:
        et.SubElement(elem, "options")
    if hint.clear_wrong:
        et.SubElement(elem, "clearwrong")
    return elem


def _to_unit(unit: Unit) -> et.Element:
    elem = et.Element("units")
    et.SubElement(elem, "unit_name").text = unit.unit_name
    et.SubElement(elem, "multiplier").text = unit.multiplier
    return elem


def _to_tags(tags: TList) -> et.Element:
    item = et.Element("tags")
    for tag in tags:
        _itag = et.SubElement(item, "tag")
        et.SubElement(_itag, "text").text = tag
    return item


def _to_answer(ans: Answer) -> et.Element:
    answer = et.Element("answer", {"fraction": ans.fraction})
    if ans.formatting:
        answer.set("format", ans.formatting.value)
    et.SubElement(answer, "text").text = ans.text
    if ans.feedback:
        answer.append(_to_ftext(ans.feedback, "feedback"))
    return answer


def _to_anumerical(ans) -> et.Element:
    answer = _to_answer(ans)
    et.SubElement(answer, "tolerance").text = ans.tolerance
    return answer


def _to_acalculated(ans) -> et.Element:
    answer = _to_anumerical(ans)
    et.SubElement(answer, "tolerancetype").text = ans.ttype.value
    et.SubElement(answer, "correctanswerformat").text = ans.aformat.value
    et.SubElement(answer, "correctanswerlength").text = ans.alength
    return answer


def _to_dropzone(drop) -> et.Element:
    dropzone = et.Element("drop")
    if drop.text:
        et.SubElement(dropzone, "text").text = drop.text
    et.SubElement(dropzone, "no").text = str(drop.number)
    et.SubElement(dropzone, "choice").text = str(drop.choice)
    if drop.shape:
        et.SubElement(dropzone, "shape").text = drop.shape.value
    if not drop.points:
        et.SubElement(dropzone, "xleft").text = str(drop.coord_x)
        et.SubElement(dropzone, "ytop").text = str(drop.coord_y)
    else:
        _tmp = et.SubElement(dropzone, "coords")
        _tmp.text = f"{drop.coord_x},{drop.coord_y};{drop.points}"
    return dropzone


def _to_subquestion(sub) -> et.Element:
    subquestion = et.Element("subquestion",
                             {"format": sub.formatting.value})
    text = et.Element("text")
    text.text = sub.text
    subquestion.append(text)
    answer = et.Element("answer")
    subquestion.append(answer)
    text = et.Element("text")
    text.text = sub.answer
    answer.append(text)
    return subquestion


def _to_selectOption(opt) -> et.Element:
    select_option = et.Element("selectoption")
    text = et.Element("text")
    text.text = opt.text
    select_option.append(text)
    group = et.Element("group")
    group.text = str(opt.group)
    select_option.append(group)
    return select_option


def _to_question(question: "_Question") -> et.Element:
    elem = et.Element("question", {"type": question.MOODLE})
    name = et.SubElement(elem, "name")
    et.SubElement(name, "text").text = question.name
    elem.append(_to_ftext(question.question, "questiontext"))
    if question.remarks:
        elem.append(_to_ftext(question.remarks, "generalfeedback"))
    et.SubElement(elem, "defaultgrade").text = question.default_grade
    # et.SubElement(question, "hidden").text = "0"
    if question.dbid is not None:
        et.SubElement(elem, "idnumber").text = question.dbid
    if question.tags:
        elem.append(_to_tags(question.tags))
    return elem


def _to_question_mt(qst: "_QHasOptions", opt_callback) -> et.Element:
    question = _to_question(qst)
    for hint in qst.fail_hints:
        question.append(_to_hint(hint))
    et.SubElement(question, "penalty").text = 1/qst.max_tries
    if opt_callback:  # Workaround for QRandomMatching.
        for sub in qst.options:
            question.append(opt_callback(sub))
    return question


def _to_question_mtcs(qst: "_QHasOptions", opt_callback) -> et.Element:
    question = _to_question_mt(qst, opt_callback)
    question.append(_to_ftext(qst.feedbacks.get(0, ""), "correctfeedback"))
    for key in qst.feedbacks:
        if 0 < key < 100:
            question.append(_to_ftext(qst.feedbacks[key], "partiallycorrectfeedback"))
    question.append(_to_ftext(qst.feedbacks.get(0, ""), "incorrectfeedback"))
    if qst.show_ans != ShowAnswer.NEVER:
        et.SubElement(question, "shownumcorrect")
    if hasattr(qst, "shuffle") and qst.shuffle:    # Workaround for
        et.SubElement(question, "shuffleanswers")   # QRandomMatching
    return question


def _to_question_mtuh(qst: "_QHasUnits", opt_callback) -> et.Element:
    question = _to_question_mt(qst, opt_callback)
    et.SubElement(question, "unitgradingtype").text = qst.grading_type.value
    et.SubElement(question, "unitpenalty").text = qst.unit_penalty
    et.SubElement(question, "showunits").text = qst.show_unit.value
    et.SubElement(question, "unitsleft").text = qst.left
    return question


def _to_qcalculated(qst: QCalculated) -> et.Element:
    question = _to_question_mtuh(qst, _to_acalculated)
    et.SubElement(question, "synchronize").text = qst.synchronize.value
    units = et.SubElement(question, "units")
    for unit in qst.units:
        units.append(_to_unit(unit))
    definitions = et.SubElement(question, "dataset_definitions")
    for dataset in qst.datasets:
        definitions.append(_to_dataset(dataset))
    return question


def _to_qcalcmultichoice(qst: QCalculatedMC) -> et.Element:
    question = _to_question_mtcs(qst, _to_acalculated)
    et.SubElement(question, "synchronize").text = qst.synchronize.value
    if qst.single:
        et.SubElement(question, "single")
    et.SubElement(question, "answernumbering").text = qst.numbering.value
    dataset_definitions = et.SubElement(question, "dataset_definitions")
    for dataset in qst.datasets:
        dataset_definitions.append(_to_dataset(dataset))
    return question


def _to_qcloze(qst: QCloze) -> et.Element:
    tmp = qst.question.text
    qst.question.text = qst.pure_text(False)
    question = _to_question_mt(qst, None)
    qst.question.text = tmp
    return question


def _to_qdescription(qst: QDescription) -> et.Element:
    return _to_question(qst)


def _to_qdad_text(qst: QDaDText) -> et.Element:
    def _to_draggroup(drag: DragGroup) -> et.Element:
        dragbox = et.Element("dragbox")
        et.SubElement(dragbox, "text").text = drag.text
        et.SubElement(dragbox, "group").text = drag.group
        if drag.no_of_drags < 0:   # Same as unlimited
            et.SubElement(dragbox, "infinite")
        return dragbox
    return _to_question_mtcs(qst, _to_draggroup)


def _to_qdad_image(qst: QDaDImage) -> et.Element:
    def _to_dragimage(drag: DragImage) -> et.Element:
        dragitem = et.Element("drag")
        et.SubElement(dragitem, "no").text = drag.number
        et.SubElement(dragitem, "text").text = drag.text
        if drag.group:
            et.SubElement(dragitem, "draggroup").text = drag.group
        if drag.no_of_drags < 0:
            et.SubElement(dragitem, "infinite")
        if drag.image:
            dragitem.append(_to_b64file(drag.image))
        return dragitem
    question = _to_question_mtcs(qst, _to_dragimage)
    if qst.background:
        question.append(_to_b64file(qst.background))
    for dropzone in qst.zones:
        question.append(_to_dropzone(dropzone))
    return question


def _to_qdad_marker(qst: QDaDMarker) -> et.Element:
    def _to_dragmarker(drag: DragItem) -> et.Element:
        dragitem = et.Element("drag")
        et.SubElement(dragitem, "no").text = drag.number
        et.SubElement(dragitem, "text").text = drag.text
        if drag.no_of_drags < 0:
            et.SubElement(dragitem, "infinite")
        else:
            et.SubElement(dragitem, "noofdrags").text = drag.no_of_drags
        return dragitem
    question = _to_question_mtcs(qst, _to_dragmarker)
    if qst.highlight:
        et.SubElement(question, "showmisplaced")
    for dropzone in qst.zones:
        question.append(_to_dropzone(dropzone))
    if qst.background:
        question.append(_to_b64file(qst.background))
    return question


def _to_qessay(qst) -> et.Element:
    question = _to_question(qst)
    et.SubElement(question, "responseformat").text = qst.rsp_format.value
    if qst.rsp_required:
        et.SubElement(question, "responserequired")
    et.SubElement(question, "responsefieldlines").text = qst.lines
    et.SubElement(question, "attachments").text = qst.attachments
    if qst.atts_required:
        et.SubElement(question, "attachmentsrequired")
    if qst.max_bytes:
        et.SubElement(question, "maxbytes").text = qst.max_bytes
    if qst.file_types:
        et.SubElement(question, "filetypeslist").text = qst.file_types
    if qst.grader_info:
        question.append(_to_ftext(qst.grader_info, "graderinfo"))
    if qst.template:
        question.append(_to_ftext(qst.template, "responsetemplate"))
    return question


def _to_qmatching(qst) -> et.Element:
    return _to_question_mtcs(qst, _to_subquestion)


def _to_qrandommatching(qst) -> et.Element:
    question = _to_question_mtcs(qst, None)
    et.SubElement(question, "choose").text = qst.choose
    et.SubElement(question, "subcats").text = qst.subcats
    return question


def _to_qmissingword(qst) -> et.Element:
    return _to_question_mtcs(qst, _to_selectOption)


def _to_qmultichoice(qst) -> et.Element:
    question = _to_question_mtcs(qst, _to_answer)
    et.SubElement(question, "answernumbering").text = qst.numbering.value
    if qst.single:
        et.SubElement(question, "single")
    return question


def _to_qnumerical(qst: QNumerical) -> et.Element:
    question = _to_question_mtuh(qst, _to_anumerical)
    if len(qst.units) > 0:
        units = et.SubElement(question, "units")
        for unit in qst.units:
            units.append(_to_unit(unit))
    return question


def _to_qshortanswer(qst) -> et.Element:
    question = _to_question_mt(qst, _to_answer)
    et.SubElement(question, "usecase").text = qst.use_case
    return question


def _to_qtruefalse(qst: QTrueFalse) -> et.Element:
    item = _to_question(qst)
    ans = et.SubElement(item, "answer", {"fraction": 100 if qst.correct else 0,
                                         "format": TextFormat.AUTO.value})
    et.SubElement(ans, "text").text = "true"
    ans.append(_to_ftext(qst.true_feedback))
    ans = et.SubElement(item, "answer", {"fraction": 0 if qst.correct else 100,
                                         "format": TextFormat.AUTO.value})
    et.SubElement(ans, "text").text = "false"
    ans.append(_to_ftext(qst.false_feedback))
    return item


# -----------------------------------------------------------------------------


_QTYPE = {
    "calculated": (_from_qcalculated, _to_qcalculated),
    "calculatedsimple": (_from_qcalculatedsimple, _to_qcalculated),
    "calculatedmulti": (_from_qcalcmultichoice, _to_qcalcmultichoice),
    "cloze": (_from_qcloze, _to_qcloze),
    "description": (_from_qdescription, _to_qdescription),
    "ddwtos": (_from_ddwtos, _to_qdad_text),
    "ddimageortext": (_from_ddimageortext, _to_qdad_image),
    "ddmarker": (_from_ddmarker, _to_qdad_marker),
    "essay": (_from_qessay, _to_qessay),
    "matching": (_from_qmatching, _to_qmatching),
    "randomsamatch": (_from_QRandomMatching, _to_qrandommatching),
    "gapselect": (_from_QMissingWord, _to_qmissingword),
    "multichoice": (_from_QMultichoice, _to_qmultichoice),
    "numerical": (_from_QNumerical, _to_qnumerical),
    "shortanswer": (_from_QShortAnswer, _to_qshortanswer),
    "truefalse": (_from_QTrueFalse, _to_qtruefalse)
}


def read_moodle(cls, file_path: str, category: str = None) -> "Category":
    """[summary]

    Returns:
        [type]: [description]
    """
    data_root = et.parse(file_path)
    top_quiz: Category = cls(category)
    quiz = top_quiz
    for elem in data_root.getroot():
        if elem.tag != "question":
            continue
        if elem.get("type") == "category":
            quiz = gen_hier(cls, top_quiz, elem[0][0].text)
        elif elem.get("type") not in _QTYPE:
            raise TypeError(f"Type {elem.get('type')} not implemented")
        else:
            question = _QTYPE[elem.get("type")][0](elem, {})
            quiz.add_question(question)
    _LOG.debug("Parsed %s questions from %s.", top_quiz.get_size(True), file_path)
    return top_quiz


def read_moodle_backup(cls, file_path: str) -> "Category":
    """[summary]

    Returns:
        [type]: [description]
    """
    with zipfile.ZipFile(file_path, "r") as ifile:
        data = ifile.extract("questions.xml")
        top_quiz: Category = read_moodle(cls, data)
        data = ifile.extract("moodle_backup.xml")
        top_quiz.metadata["moodle_course"] = file_path

# -----------------------------------------------------------------------------


def write_moodle(self: "Category", file_path: str, pretty=False):
    """Generates XML compatible with Moodle and saves to a file.

    Args:
        file_path (str): filename where the XML will be saved
        pretty (bool): saves XML pretty printed.
    """
    def _txrecursive(cat: "Category", root: et.Element):
        question = et.Element("question")           # Add category on the top
        if cat.get_size() > 0:
            question.set("type", "category")
            category = et.SubElement(question, "category")
            catname = [cat.name]
            tmp = cat.parent
            while tmp:
                catname.append(tmp.name)
                tmp = tmp.parent
            catname.reverse()
            et.SubElement(category, "text").text = "/".join(catname)
            root.append(question)
            for question in cat.questions:          # Add own questions first
                root.append(_QTYPE[question.MOODLE][1](question))
        for name in cat:                            # Then add children data
            _txrecursive(cat[name], root)
    root = et.Element("quiz")
    _txrecursive(self, root)
    with open(file_path, "w") as ofile:
        ofile.write("<?xml version='1.0' encoding='utf-8'?>\n")
        serialize_fxml(ofile.write, root, True, pretty)
