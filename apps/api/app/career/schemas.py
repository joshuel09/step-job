"""Request and response models, matching contracts/openapi.yaml."""

import uuid
from datetime import date, datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from app.career.models import (
    EmploymentType,
    LanguageProficiency,
    Locale,
    ProposalStatus,
    ProposedEntryType,
    SkillLevel,
    WorkingArrangement,
)


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


def _reject_null[T](value: T) -> T:
    """Refuse an explicit null on a field the entry cannot be without.

    Omitting a field and sending it as null are different requests: the
    first leaves it alone, the second asks to erase it. Patch bodies make
    every field optional so the first is possible, which would let the
    second through to a column that does not accept it — an unexplainable
    500, or a blank where the document expects a fact.

    None only ever reaches here explicitly. Pydantic does not validate
    defaults, so an omitted field is never seen by this.
    """
    if value is None:
        raise ValueError("This cannot be removed. Omit it to leave it unchanged.")
    return value


def _reject_blank[T](value: T) -> T:
    """Refuse a null, and refuse a string with nothing in it.

    A blank is the quieter of the two and the one that reaches paper: the
    request succeeds, the entry keeps its row, and the document prints a
    heading with no employer under it. FR-025 refuses a blank approval for
    the same reason, and a blank fact is no better than a blank rendering.

    Whitespace counts as blank. A name of three spaces is a name the user
    cannot see they have lost.
    """
    if isinstance(value, str) and not value.strip():
        raise ValueError("This cannot be blank.")
    return _reject_null(value)


#: A field the entry cannot be without: never null, never blank. On a patch
#: body it is still optional, because omitting it leaves it alone.
Stated = AfterValidator(_reject_blank)

#: A field that may hold nothing but may not hold null — `description`,
#: which is empty on an entry that has not been described yet.
NotNullable = AfterValidator(_reject_null)


def _supplied_or_absent(value: str | None) -> str | None:
    """An English name the user gave, or nothing — and nothing means null.

    Null is how "not supplied" is recorded (FR-021). An empty string is a
    third state meaning the same thing, which every caller then has to know
    to check for: a generator asking `if employer_name_english` falls back
    to the Japanese, one asking `is not None` prints an empty name.
    """
    if value is not None and not value.strip():
        raise ValueError("This cannot be blank. Leave it out to record no English name.")
    return value


#: An optional English name the user states. Null means not supplied; blank
#: is not a way of saying so.
SuppliedName = AfterValidator(_supplied_or_absent)

#: Bounded to the width of the column behind it. Without this, over-length
#: text reaches a VARCHAR(255) as a database error — a 500, where what the
#: user needed was to be told the value is too long. The bound is on the
#: string rather than on the field, so `Line | None` still accepts null.
#: Stated against the five section schemas only; the rest of feature 001
#: has the same gap and it is not this change's to close.
Line = Annotated[str, Field(max_length=255)]

#: The language column is narrower than the rest.
ShortLine = Annotated[str, Field(max_length=100)]


class IdentityIn(BaseModel):
    full_name_latin: str
    full_name_japanese: str | None = None
    furigana: str | None = None
    email: str | None = None
    phone: str | None = None

    # Added by feature 003 for the 履歴書. Optional: a profile without them is
    # valid, and a document leaves the fields blank rather than inventing them.
    date_of_birth: date | None = None
    address: str | None = None


class IdentityOut(IdentityIn, ORMModel):
    pass


class JapanProfileIn(BaseModel):
    """Disclosure flags default closed; see FR-006."""

    residence_status: str | None = None
    nationality: str | None = None
    visa_type: str | None = None
    visa_expires_on: date | None = None
    work_authorisation: bool | None = None
    japanese_qualification: str | None = None
    disclose_residence_status: bool = False
    disclose_nationality: bool = False
    disclose_visa: bool = False
    disclose_work_authorisation: bool = False
    disclose_japanese_qualification: bool = False


class JapanProfileOut(JapanProfileIn, ORMModel):
    pass


class WorkExperienceIn(BaseModel):
    employer_name: Annotated[Line, Stated]
    job_title: Annotated[Line, Stated]
    employment_type: EmploymentType | None = None
    started_on: date
    ended_on: date | None = None
    description: str = ""
    source_language: Locale = Locale.en
    # The organisation's own English name, as the user supplies it. Set
    # through this route rather than one of feature 005's own: it is a
    # profile field, and a second way to edit an entry is what Principle I
    # rules out. Absent means they have not given one, never a guess.
    employer_name_english: Annotated[Line | None, SuppliedName] = None


class WorkExperiencePatch(BaseModel):
    """Every field optional, so any one of them can be changed on its own.

    `ended_on` is the only one of these that means something as null — the
    job is ongoing. The rest the entry cannot be without.
    """

    employer_name: Annotated[Line | None, Stated] = None
    employer_name_english: Annotated[Line | None, SuppliedName] = None
    job_title: Annotated[Line | None, Stated] = None
    employment_type: EmploymentType | None = None
    started_on: Annotated[date | None, Stated] = None
    ended_on: date | None = None
    description: Annotated[str | None, NotNullable] = None
    source_language: Annotated[Locale | None, Stated] = None


class WorkExperienceOut(ORMModel):
    id: uuid.UUID
    employer_name: str
    employer_name_english: str | None = None
    job_title: str
    employment_type: EmploymentType | None = None
    started_on: date
    ended_on: date | None = None
    description: str = ""
    source_language: Locale


class EducationIn(BaseModel):
    institution: Annotated[Line, Stated]
    institution_english: Annotated[Line | None, SuppliedName] = None
    qualification: Line | None = None
    field_of_study: Line | None = None
    started_on: date | None = None
    ended_on: date | None = None
    source_language: Locale = Locale.en


class EducationPatch(BaseModel):
    institution: Annotated[Line | None, Stated] = None
    institution_english: Annotated[Line | None, SuppliedName] = None
    qualification: Line | None = None
    field_of_study: Line | None = None
    started_on: date | None = None
    ended_on: date | None = None
    source_language: Annotated[Locale | None, Stated] = None


# The output models below declare their fields rather than inheriting them
# from the input ones, as WorkExperienceOut already did. Inheriting would
# carry the write-time rules onto the read path, and a row that predates a
# rule — or that an import wrote straight through the service — would then
# fail validation on its way out. A blank institution is a thing to fix;
# a 500 on the page that would let the user fix it is not.
class EducationOut(ORMModel):
    id: uuid.UUID
    institution: str
    institution_english: str | None = None
    qualification: str | None = None
    field_of_study: str | None = None
    started_on: date | None = None
    ended_on: date | None = None
    source_language: Locale


class CertificationIn(BaseModel):
    name: Annotated[Line, Stated]
    # A certification is in no translation at all: a name, an issuer and two
    # dates means the first two are proper nouns and the last two are not
    # words. Both English forms are the user's to state (R-002).
    name_english: Annotated[Line | None, SuppliedName] = None
    issuer: Line | None = None
    issuer_english: Annotated[Line | None, SuppliedName] = None
    issued_on: date | None = None
    expires_on: date | None = None
    source_language: Locale = Locale.en


class CertificationPatch(BaseModel):
    name: Annotated[Line | None, Stated] = None
    name_english: Annotated[Line | None, SuppliedName] = None
    issuer: Line | None = None
    issuer_english: Annotated[Line | None, SuppliedName] = None
    issued_on: date | None = None
    expires_on: date | None = None
    source_language: Annotated[Locale | None, Stated] = None


class CertificationOut(ORMModel):
    id: uuid.UUID
    name: str
    name_english: str | None = None
    issuer: str | None = None
    issuer_english: str | None = None
    issued_on: date | None = None
    expires_on: date | None = None
    source_language: Locale


class SkillIn(BaseModel):
    name: Annotated[Line, Stated]
    level: SkillLevel | None = None


class SkillPatch(BaseModel):
    name: Annotated[Line | None, Stated] = None
    level: SkillLevel | None = None


class SkillOut(ORMModel):
    id: uuid.UUID
    name: str
    level: SkillLevel | None = None


class LanguageIn(BaseModel):
    language: Annotated[ShortLine, Stated]
    proficiency: LanguageProficiency
    qualification: Line | None = None


class LanguagePatch(BaseModel):
    language: Annotated[ShortLine | None, Stated] = None
    proficiency: Annotated[LanguageProficiency | None, Stated] = None
    qualification: Line | None = None


class LanguageOut(ORMModel):
    id: uuid.UUID
    language: str
    proficiency: LanguageProficiency
    qualification: str | None = None


class CareerPreferenceIn(BaseModel):
    desired_roles: list[str] = []
    desired_locations: list[str] = []
    working_arrangement: WorkingArrangement | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    currency: str | None = None
    source_language: Locale = Locale.en


class CareerPreferenceOut(CareerPreferenceIn, ORMModel):
    pass


class CareerStoryIn(BaseModel):
    work_experience_id: uuid.UUID | None = None
    title: str
    challenge: str
    action: str
    result: str
    source_language: Locale = Locale.en


class CareerStoryPatch(BaseModel):
    work_experience_id: uuid.UUID | None = None
    title: str | None = None
    challenge: str | None = None
    action: str | None = None
    result: str | None = None
    source_language: Locale | None = None


class CareerStoryOut(ORMModel):
    id: uuid.UUID
    work_experience_id: uuid.UUID | None = None
    title: str
    challenge: str
    action: str
    result: str
    source_language: Locale


class WorkExperienceDetail(WorkExperienceOut):
    """A role together with the accomplishments recorded against it."""

    stories: list[CareerStoryOut] = []


class ProposedEntryIn(BaseModel):
    entry_type: ProposedEntryType
    source: str
    payload: dict


class ProposedEntryOut(ORMModel):
    id: uuid.UUID
    entry_type: ProposedEntryType
    source: str
    status: ProposalStatus
    payload: dict
    possible_duplicate_of: uuid.UUID | None = None
    reviewed_at: datetime | None = None

    # Added by feature 002. Evidence is present only while the proposal awaits
    # review; it is cleared when the decision is recorded.
    import_id: uuid.UUID | None = None
    evidence: dict | None = None
    conflicts: list | None = None


class ProposalAccept(BaseModel):
    payload: dict | None = None


class ProposalMerge(BaseModel):
    target_entry_id: uuid.UUID
    payload: dict | None = None


class AcceptedProposal(BaseModel):
    proposal_id: uuid.UUID
    created_entry_id: uuid.UUID
    entry_type: ProposedEntryType


class ProfilePatch(BaseModel):
    interface_locale: Locale


class ProfileOut(ORMModel):
    id: uuid.UUID
    interface_locale: Locale
    identity: IdentityOut | None = None
    japan: JapanProfileOut | None = None
    preferences: CareerPreferenceOut | None = None
    experiences: list[WorkExperienceOut] = []
    education: list[EducationOut] = []
    certifications: list[CertificationOut] = []
    skills: list[SkillOut] = []
    languages: list[LanguageOut] = []


class ReferenceOut(BaseModel):
    kind: str
    count: int


class ReferenceWarning(BaseModel):
    message: str
    references: list[ReferenceOut]


class DeletionReceiptOut(BaseModel):
    erased_immediately: list[str]
    recoverable_until: str


class SnapshotCapture(BaseModel):
    document_ref: str
    entry_ids: list[uuid.UUID]


class SnapshotOut(ORMModel):
    id: uuid.UUID
    document_ref: str
    captured_at: datetime
    captured_entry_ids: list[uuid.UUID]
    payload: dict
