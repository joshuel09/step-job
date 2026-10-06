"""Disclosure filtering — gate G5.

One case per flag, in both directions. A single case that happens to pass does
not show the other flags are wired, and the failure this guards against is
publishing someone's immigration status.

The policy is written out here rather than read from the module, so a change to
the module's table has to be made twice to pass: once in the code and once
where a reviewer reads it as policy (data-model.md, "Disclosure filtering").

The model is the real one, unsaved. Its flags are `None` until a row is written,
which is exactly the state a filter that tested for "not False" would get wrong.
"""

from datetime import date

import pytest
from app.career.models import JapanProfile
from app.rirekisho.disclosure import GOVERNED_BY, disclosed_fields

# Flag, and every field it governs.
POLICY = {
    "disclose_residence_status": ("residence_status",),
    "disclose_nationality": ("nationality",),
    "disclose_visa": ("visa_type", "visa_expires_on"),
    "disclose_work_authorisation": ("work_authorisation",),
    "disclose_japanese_qualification": ("japanese_qualification",),
}

# A value in every field, each one distinct, so a leak names its source.
VALUES = {
    "residence_status": "永住者",
    "nationality": "Philippines",
    "visa_type": "技術・人文知識・国際業務",
    "visa_expires_on": date(2028, 3, 31),
    "work_authorisation": True,
    "japanese_qualification": "JLPT N2",
}

ALL_FIELDS = set(VALUES)


def _profile(**flags: bool) -> JapanProfile:
    """Every field filled; only the flags given are set."""
    return JapanProfile(**VALUES, **flags)


class TestOneFlagAtATime:
    @pytest.mark.parametrize("flag", POLICY)
    def test_a_disclosed_flag_lets_its_fields_through(self, flag):
        assert disclosed_fields(_profile(**{flag: True})) == {
            field: VALUES[field] for field in POLICY[flag]
        }

    @pytest.mark.parametrize("flag", POLICY)
    def test_every_other_flag_disclosed_still_withholds_this_one(self, flag):
        others = {f: True for f in POLICY if f != flag}
        shown = disclosed_fields(_profile(**others, **{flag: False}))

        assert set(shown).isdisjoint(POLICY[flag])
        assert set(shown) == ALL_FIELDS - set(POLICY[flag])


class TestTheDefaultIsWithheld:
    def test_flags_never_set_withhold_everything(self):
        """An unsaved record: every flag is None, not False."""
        profile = _profile()
        assert all(getattr(profile, flag) is None for flag in POLICY)
        assert disclosed_fields(profile) == {}

    def test_flags_set_false_withhold_everything(self):
        assert disclosed_fields(_profile(**{flag: False for flag in POLICY})) == {}

    def test_no_japan_profile_discloses_nothing(self):
        assert disclosed_fields(None) == {}

    @pytest.mark.parametrize("truthy", ["true", 1, "yes"])
    def test_only_an_explicit_true_discloses(self, truthy):
        """A stray truthy value is not an opt-in."""
        profile = _profile()
        for flag in POLICY:
            setattr(profile, flag, truthy)
        assert disclosed_fields(profile) == {}


class TestEverythingDisclosed:
    def test_every_field_appears(self):
        assert disclosed_fields(_profile(**{flag: True for flag in POLICY})) == VALUES

    def test_withdrawing_a_disclosure_removes_the_field(self):
        """FR-021: the same profile, opted in and then out."""
        profile = _profile(disclose_nationality=True)
        assert "nationality" in disclosed_fields(profile)

        profile.disclose_nationality = False
        assert "nationality" not in disclosed_fields(profile)


class TestNothingIsInvented:
    @pytest.mark.parametrize("flag", POLICY)
    def test_a_disclosed_field_with_no_value_is_left_out(self, flag):
        """FR-013: there is nothing the user chose to show."""
        profile = JapanProfile(**{flag: True})
        assert disclosed_fields(profile) == {}

    def test_blank_text_counts_as_no_value(self):
        profile = JapanProfile(nationality="  ", disclose_nationality=True)
        assert disclosed_fields(profile) == {}

    def test_false_is_a_value_not_an_absence(self):
        """A user may choose to state that they lack work authorisation."""
        profile = JapanProfile(work_authorisation=False, disclose_work_authorisation=True)
        assert disclosed_fields(profile) == {"work_authorisation": False}

    def test_a_visa_disclosure_with_only_an_expiry_shows_only_the_expiry(self):
        profile = JapanProfile(visa_expires_on=date(2028, 3, 31), disclose_visa=True)
        assert disclosed_fields(profile) == {"visa_expires_on": date(2028, 3, 31)}


class TestTheAllowlistCoversTheModel:
    """A new Japan-specific column must not slip past the filter unnoticed."""

    BOOKKEEPING = {"id", "created_at", "updated_at", "profile_id"}

    def _columns(self) -> set[str]:
        return {c.name for c in JapanProfile.__table__.columns} - self.BOOKKEEPING

    def test_the_policy_here_matches_the_module(self):
        assert GOVERNED_BY == {field: flag for flag, fields in POLICY.items() for field in fields}

    def test_every_flag_on_the_model_governs_something(self):
        flags = {c for c in self._columns() if c.startswith("disclose_")}
        assert flags == set(POLICY)

    def test_every_field_on_the_model_has_a_flag(self):
        """Fails when a field is added without deciding who may see it."""
        fields = {c for c in self._columns() if not c.startswith("disclose_")}
        assert fields == set(GOVERNED_BY)

    def test_a_field_the_allowlist_does_not_name_never_appears(self):
        """Even on an object carrying it, with every flag set."""
        profile = _profile(**{flag: True for flag in POLICY})
        profile.religion = "should never appear"  # type: ignore[attr-defined]
        assert "religion" not in disclosed_fields(profile)


def test_the_order_is_stable():
    """So a document lists the same fields in the same order every time."""
    shown = disclosed_fields(_profile(**{flag: True for flag in POLICY}))
    assert list(shown) == list(GOVERNED_BY)
