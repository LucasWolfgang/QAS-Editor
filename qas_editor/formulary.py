from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .wrappers import FText
import json


class Formulary:
    """Represents test formularies, which can contain equations, tables and other data 
    that is not question specific and is usually added as an appendix in the last page
    of a test to be used by the student as reference
    """

    def __init__(self) -> None:
        self.items = []

    def to_pdf(self):
        pass

    def to_json(self, file_path: str):
        with open(file_path, "w") as ofile:
            json.dump(self.items, ofile)

    @classmethod
    def from_json(cls):
        pass


class Equation:
    """Represents an equation in a formulary
    """

    def __init__(self, name: str, text: FText) -> None:
        self.__name = name
        self.__text = text

    def data(self):
        return self.__name, self.__text

class Table:
    """Represents a table in a formulary
    """

    def __init__(self, name: str, text: FText) -> None:
        self.__name = name
        self.__text = text

    def data(self):
        return self.__name, self.__text

class Rule:
    """Represents a theory, law or other set of sentences that describe a given phenomenum.
    """

    def __init__(self, name: str, text: FText, proof: FText) -> None:
        self.__name = name
        self.__text = text
        self.__proof = proof

    def data(self):
        return self.__name, self.__text, self.__proof