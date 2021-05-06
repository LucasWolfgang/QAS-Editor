from enum import Enum

class ClozeFormat(Enum):
    SHORTANSWER = "SA"
    SA = "SA"
    MW = "SA"
    SHORTANSWER_C = "SAC"
    SAC = "SAC"
    MWC = "SAC"
    NUMERICAL = "NM"
    NM = "NM"
    MULTICHOICE = "MC"
    MC = "MC"
    MULTICHOICE_V = "MVC"
    MVC = "MVC"
    MULTICHOICE_H = "MCH"
    MCH = "MCH"
    MULTIRESPONSE = "MR"
    MR = "MR"
    MULTIRESPONSE_H = "MRH"
    MRH = "MRH"

    @classmethod
    def get(cls, value: str) -> "Distribution":
        for i in cls:
            if i.value == value:
                return i
        return None

# ----------------------------------------------------------------------------------------

class Distribution(Enum):
    UNI = "uniform"
    LOG = "loguniform"

    @classmethod
    def get(cls, value: str) -> "Distribution":
        for i in cls:
            if i.value == value:
                return i
        return None

# ----------------------------------------------------------------------------------------

class Format(Enum):
    HTML = "html"
    AUTO = "moodle_auto_format"
    PLAIN = "plain_text"
    MD = "markdown"

    @classmethod
    def get(cls, value: str) -> "Format":
        for i in cls:
            if i.value == value:
                return i
        return None

# ----------------------------------------------------------------------------------------

class Grading(Enum):
    IGNORE = "0"        # Ignore
    RESPONSE = "1"      # Fraction of reponse grade
    QUESTION = "2"      # Fraction of question grade

    @classmethod
    def get(cls, value: str) -> "Grading":
        for i in cls:
            if i.value == value:
                return i
        return None

# ----------------------------------------------------------------------------------------

class Numbering(Enum):
    NONE = "none"
    ALF_LR = "abc"
    ALF_UR = "ABCD"
    NUMERIC = "123"
    ROM_LR = "iii"
    ROM_UR = "IIII"

    @classmethod
    def get(cls, value: str) -> "Numbering":
        for i in cls:
            if i.value == value:
                return i
        return None

# ----------------------------------------------------------------------------------------

class ShapeType(Enum):
    CIRCLE = "circle"
    RECT = "rectangle"
    POLY = "polygon"

    @classmethod
    def get(cls, value: str) -> "Status":
        for i in cls:
            if i.value == value:
                return i
        return None

# ----------------------------------------------------------------------------------------

class ShowUnits(Enum):
    TEXT = "0"          # Text input
    MC = "1"            # Multiple choice
    DROP_DOWN = "2"     # Drop-down
    NONE = "3"          # Not visible

    @classmethod
    def get(cls, value: str) -> "ShowUnits":
        for i in cls:
            if i.value == value:
                return i
        return None

# ----------------------------------------------------------------------------------------

class Status(Enum):
    PRV = "private"
    SHR = "shared"

    @classmethod
    def get(cls, value: str) -> "Status":
        for i in cls:
            if i.value == value:
                return i
        return None

# ----------------------------------------------------------------------------------------

class ResponseFormat(Enum):
    HTML = "editor"
    WFILE = "editorfilepicker"
    PLAIN = "plain"
    MONO = "monospaced"
    ATCH = "noinline"

    @classmethod
    def get(cls, value: str) -> "Status":
        for i in cls:
            if i.value == value:
                return i
        return None

# ----------------------------------------------------------------------------------------

class ToleranceFormat(Enum):
    DEC = "1"           # Decimals
    SIG = "2"           # Significant Figures

    @classmethod
    def get(cls, value: str) -> "ToleranceFormat":
        for i in cls:
            if i.value == value:
                return i
        return None
        
# ----------------------------------------------------------------------------------------

class ToleranceType(Enum):
    REL = "1"           # Relative
    NOM = "2"           # Nominal
    GEO = "3"           # Geometric

    @classmethod
    def get(cls, value: str) -> "ToleranceType":
        for i in cls:
            if i.value == value:
                return i
        return None
