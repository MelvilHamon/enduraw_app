"""Centralised string enums for the metric domain.

All enums subclass ``(str, Enum)`` so their members compare equal to their
string value and serialise cleanly to JSON. They are persisted as ``VARCHAR``
(see :func:`app.models.mixins.str_enum`) — never as native SQL ``ENUM`` types,
which keeps SQLite and PostgreSQL behaviour identical.
"""

from __future__ import annotations

from enum import Enum


class BodyRegion(str, Enum):
    FOOT_FORE = "foot_fore"
    FOOT_MID = "foot_mid"
    FOOT_HEEL = "foot_heel"
    ANKLE = "ankle"
    ACHILLES = "achilles"
    CALF = "calf"
    SHIN = "shin"
    KNEE_ANTERIOR = "knee_anterior"
    KNEE_MEDIAL = "knee_medial"
    KNEE_LATERAL = "knee_lateral"
    KNEE_POSTERIOR = "knee_posterior"
    QUAD = "quad"
    HAMSTRING = "hamstring"
    ADDUCTOR = "adductor"
    IT_BAND = "it_band"
    HIP_FLEXOR = "hip_flexor"
    GLUTE = "glute"
    GROIN = "groin"
    LOWER_BACK = "lower_back"
    UPPER_BACK = "upper_back"
    NECK = "neck"
    SHOULDER = "shoulder"
    OTHER = "other"


class Side(str, Enum):
    LEFT = "left"
    RIGHT = "right"
    CENTER = "center"
    BILATERAL = "bilateral"


class PainType(str, Enum):
    SHARP = "sharp"
    DULL = "dull"
    TENSION = "tension"
    BURNING = "burning"
    STABBING = "stabbing"


class MechanicalPattern(str, Enum):
    UPHILL = "uphill"
    DOWNHILL = "downhill"
    PUSH_OFF = "push_off"
    IMPACT = "impact"
    REST = "rest"
    CONSTANT = "constant"


class Timing(str, Enum):
    DURING = "during"
    AFTER = "after"
    MORNING_STIFFNESS = "morning_stiffness"
    CONSTANT = "constant"


class Affect(str, Enum):
    WEAK = "weak"
    NEUTRAL = "neutral"
    STRONG = "strong"


class MiniTestType(str, Enum):
    JUMP = "jump"
    REACTION = "reaction"


class HrvStatus(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class IllnessSymptom(str, Enum):
    SORE_THROAT = "sore_throat"
    CONGESTION = "congestion"
    FEVER = "fever"
    UNUSUAL_FATIGUE = "unusual_fatigue"
    COUGH = "cough"
    BODY_ACHES = "body_aches"


class FeedbackSource(str, Enum):
    GARMIN_WATCH = "garmin_watch"
    APP_MANUAL = "app_manual"
