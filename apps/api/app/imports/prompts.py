"""The extraction prompt.

**Constitution gate G13**: changes to AI prompts or output schemas must state how
Principle IV remains satisfied. The answer, for any change to this file, is the
same and does not depend on the wording below:

    Principle IV is enforced by `app/imports/evidence.py`, not by this prompt.
    Every field a model returns is discarded unless its quoted passage is found
    in the source text. Weakening, rewording or entirely removing the
    instructions here cannot cause a fabricated value to reach a user; it can
    only make the model less useful.

That is deliberate. A prompt is a request, and a request can be ignored. The
instructions below exist to make the model's output *better*, not to make it
*safe* — safety is the verifier's job, and a review of any change to this file
should check that the verifier is still the thing standing between a model and a
user's resume.
"""

EXTRACTION_SYSTEM_PROMPT = """\
You extract career information from documents. You are reading someone's resume \
so that they can review what you found and decide what to keep.

Rules:

1. Report only what the document states. Do not infer a job title from \
responsibilities, do not complete a partial date, do not describe duties a role \
"usually" involves, and do not tidy an awkward phrase into a better one.

2. For every field you fill, quote the passage of the document the value came \
from, copied exactly. If you cannot quote a passage that supports a value, omit \
that field. An omitted field is a correct answer; an invented one is not.

3. Leave fields out rather than guessing. A document that does not name an \
employer produces an entry without an employer.

4. Record the language each entry was written in. Do not translate anything.

5. Preserve the precision the document uses. A date given as a year stays a \
year; do not expand it to a month or a day.

6. If the same role is described more than once, report it once.

Everything you return is checked against the document before a person sees it. \
A value whose quote is not found in the source is discarded.
"""


def build_extraction_input(text: str) -> str:
    """Wrap the source so the model can tell document from instruction."""
    return (
        "Extract the career information from the document below.\n\n"
        "--- BEGIN DOCUMENT ---\n"
        f"{text}\n"
        "--- END DOCUMENT ---\n"
    )
