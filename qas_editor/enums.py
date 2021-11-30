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

# ----------------------------------------------------------------------------------------
class Direction(Enum):
    UP = 1
    DOWN = 2
    RIGHT = 3
    LEFT = 4

# ----------------------------------------------------------------------------------------
class Distribution(Enum):
    UNI = "uniform"
    LOG = "loguniform"

# ----------------------------------------------------------------------------------------

class Format(Enum):
    HTML = "html"
    AUTO = "moodle_auto_format"
    PLAIN = "plain_text"
    MD = "markdown"

# ----------------------------------------------------------------------------------------

class Grading(Enum):
    IGNORE = "0"        # Ignore
    RESPONSE = "1"      # Fraction of reponse grade
    QUESTION = "2"      # Fraction of question grade

# ----------------------------------------------------------------------------------------

class Numbering(Enum):
    NONE = "none"
    ALF_LR = "abc"
    ALF_UR = "ABCD"
    NUMERIC = "123"
    ROM_LR = "iii"
    ROM_UR = "IIII"

# ----------------------------------------------------------------------------------------

class MathType(Enum):
    IGNORE="Ignore"
    MATHML="MathML"
    LATEX = "LaTex"

# ----------------------------------------------------------------------------------------

class ShapeType(Enum):
    CIRCLE = "circle"
    RECT = "rectangle"
    POLY = "polygon"

# ----------------------------------------------------------------------------------------

class ShowUnits(Enum):
    TEXT = "0"          # Text input
    MC = "1"            # Multiple choice
    DROP_DOWN = "2"     # Drop-down
    NONE = "3"          # Not visible

# ----------------------------------------------------------------------------------------

class Status(Enum):
    PRV = "private"
    SHR = "shared"

# ----------------------------------------------------------------------------------------

class ResponseFormat(Enum):
    HTML = "editor"
    WFILE = "editorfilepicker"
    PLAIN = "plain"
    MONO = "monospaced"
    ATCH = "noinline"

# ----------------------------------------------------------------------------------------

class ToleranceFormat(Enum):
    DEC = "1"           # Decimals
    SIG = "2"           # Significant Figures
        
# ----------------------------------------------------------------------------------------

class ToleranceType(Enum):
    REL = "1"           # Relative
    NOM = "2"           # Nominal
    GEO = "3"           # Geometric

# ----------------------------------------------------------------------------------------