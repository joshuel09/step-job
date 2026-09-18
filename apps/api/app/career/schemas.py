"""Request and response models, matching contracts/openapi.yaml."""

import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict

from app.career.models import (
    EmploymentType,
    LanguageProficiency,
    Locale,
    SkillLevel,
    WorkingArrangement,
)


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class IdentityIn(BaseModel):
    full_name_latin: str
    full_name_japanese: str | None = None
    furigana: str | None = None
    email: str | None = None
    phone: str | None = None


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
    employer_name: str
    job_title: str
    employment_type: EmploymentType | None = None
    started_on: date
    ended_on: date | None = None
    description: str = ""
    source_language: Locale = Locale.en


class WorkExperiencePatch(BaseModel):
    employer_name: str | None = None
    job_title: str | None = None
    employment_type: EmploymentType | None = None
    started_on: date | None = None
    ended_on: date | None = None
    description: str | None = None
    source_language: Locale | None = None


class WorkExperienceOut(ORMModel):
    id: uuid.UUID
    employer_name: str
    job_title: str
    employment_type: EmploymentType | None = None
    started_on: date
    ended_on: date | None = None
    description: str = ""
    source_language: Locale


class EducationIn(BaseModel):
    institution: str
    qualification: str | None = None
    field_of_study: str | None = None
    started_on: date | None = None
    ended_on: date | None = None
    source_language: Locale = Locale.en


class EducationOut(EducationIn, ORMModel):
    id: uuid.UUID


class CertificationIn(BaseModel):
    name: str
    issuer: str | None = None
    issued_on: date | None = None
    expires_on: date | None = None
    source_language: Locale = Locale.en


class CertificationOut(CertificationIn, ORMModel):
    id: uuid.UUID


class SkillIn(BaseModel):
    name: str
    level: SkillLevel | None = None


class SkillOut(SkillIn, ORMModel):
    id: uuid.UUID


class LanguageIn(BaseModel):
    language: str
    proficiency: LanguageProficiency
    qualification: str | None = None


class LanguageOut(LanguageIn, ORMModel):
    id: uuid.UUID


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
