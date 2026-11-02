"""The digest that makes a stale approval detectable (FR-023).

An approved English version describes a particular Japanese sentence. Change
the sentence and the approval still exists, but it no longer describes
anything the profile holds — and a document built from it would say what the
user used to mean. The only thing standing between that and an employer is
a value taken at approval and compared later.

Which is why "stable across processes" is the property that matters most
here. Python's own `hash()` is salted per interpreter: using it would mark
every approval in the database stale on the next restart, and every user
would be asked to re-approve work they had already approved, every deploy.
"""

import subprocess
import sys
import unicodedata

from app.translations.fingerprint import fingerprint, is_stale

JAPANESE = "ビルド時間を四十分から二十分に短縮した"


class TestTheSameTextDigestsTheSame:
    def test_twice_in_a_row(self):
        assert fingerprint(JAPANESE) == fingerprint(JAPANESE)

    def test_in_a_separate_process(self):
        """The property a salted hash would fail, and the one that matters.

        Run in a new interpreter rather than asserted about one, because an
        interpreter-local hash looks perfectly stable from inside itself.
        """
        from pathlib import Path

        # The package root, found from this file rather than from the working
        # directory, so the subprocess can import it wherever pytest was run.
        root = Path(__file__).resolve().parents[2]
        here = fingerprint(JAPANESE)
        elsewhere = subprocess.run(
            [
                sys.executable,
                "-c",
                f"import sys; sys.path.insert(0, {str(root)!r});"
                "from app.translations.fingerprint import fingerprint;"
                f"print(fingerprint({JAPANESE!r}))",
            ],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()

        assert elsewhere == here

    def test_composed_and_decomposed_japanese_are_the_same_text(self):
        """The same character can arrive either way depending on the keyboard
        and the operating system. Two spellings of one character are not a
        change the user made."""
        assert fingerprint(unicodedata.normalize("NFD", "ガラパゴス")) == fingerprint("ガラパゴス")


class TestDifferentTextDiffers:
    def test_a_changed_sentence(self):
        assert fingerprint(JAPANESE) != fingerprint("ビルド時間を三分の一に短縮した")

    def test_a_single_changed_character(self):
        assert fingerprint("二十分") != fingerprint("三十分")

    def test_an_empty_string_is_not_a_sentence(self):
        assert fingerprint("") != fingerprint(JAPANESE)


class TestWhitespaceIsNotNothing:
    """FR-023 on purpose: a user who fixed the spacing changed the text.

    Normalising it away would mean an approval of the old spacing silently
    stood for the new, and the one case where that matters is the one where
    the spacing was the thing being corrected.
    """

    def test_a_trailing_space_is_a_change(self):
        assert fingerprint(JAPANESE) != fingerprint(JAPANESE + " ")

    def test_an_ideographic_space_is_a_change(self):
        assert fingerprint("株式会社サンプル") != fingerprint("株式会社　サンプル")

    def test_a_line_break_is_a_change(self):
        assert fingerprint("一行目二行目") != fingerprint("一行目\n二行目")


class TestStaleness:
    def test_an_unchanged_source_is_not_stale(self):
        assert is_stale(fingerprint(JAPANESE), JAPANESE) is False

    def test_a_changed_source_is_stale(self):
        assert is_stale(fingerprint(JAPANESE), "まったく別の文章") is True

    def test_a_fingerprint_from_nowhere_is_stale(self):
        """A row whose digest was never computed from anything cannot be
        trusted to describe the source, so it reads as stale."""
        assert is_stale("", JAPANESE) is True


class TestTheShapeOfTheValue:
    def test_it_fits_the_column(self):
        """varchar(64), and sha-256 hex is exactly that."""
        assert len(fingerprint(JAPANESE)) == 64

    def test_it_is_hexadecimal(self):
        assert set(fingerprint(JAPANESE)) <= set("0123456789abcdef")
