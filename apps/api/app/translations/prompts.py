"""The translation prompt.

**Constitution gate G13**: a change to a prompt or an output schema must say
how Principle IV still holds. For extraction the answer is the verifier — a
value whose quote is not in the source is discarded, so the prompt cannot make
a fabrication reach anyone. There is no verifier here, because there is nothing
to verify against: a rendering of 課長 does not appear in the Japanese, and a
check that it did would reject every correct translation.

So the guarantee is a different one, and it is structural rather than textual:

1. **An embellishment cannot become a structured fact.** `TranslationDraft`
   carries a rendering, the source it renders, and the phrases that could go
   more than one way. No summary, no seniority, no headcount, no outcome, so
   nothing downstream can read one as data the profile states. This is worth
   stating precisely rather than generously: it does not stop a model writing
   "Led a team of twelve" inside the rendering itself. Nothing mechanical
   could — that is what the review below is for.

2. **Nothing stores a draft.** The drafting route writes nothing. A draft
   reaches a document only when a person approves it, and what is stored is
   their text, whether they wrote it, edited one, or accepted it unchanged.

3. **No generator can reach a provider.** Document generation reads stored
   approvals and has no code path to `app.ai` at all.

Which means the wording below, like the extraction prompt's, exists to make the
output *better* rather than to make it *safe*. Weakening it produces worse
drafts for a user to correct; it does not let a claim into a resume.
"""

TRANSLATION_SYSTEM_PROMPT = """\
You render text from one language into another for someone's resume. They will \
read what you produce, correct it, and decide whether to use it. You are \
drafting for a person, not writing a document.

Rules:

1. Render what the text says. Do not add a detail the text does not state, do \
not describe what a role "usually" involves, and do not improve a modest \
description into an impressive one.

2. Do not add scope, seniority, team size, duration or an outcome. If the text \
does not say how many people someone led, your rendering does not say either.

3. Do not drop anything the text states. A shorter rendering that leaves out a \
responsibility is as wrong as a longer one that invents a result.

4. Where a phrase could reasonably render more than one way, choose the most \
neutral reading for the draft and report the phrase in `alternatives` with the \
readings it could take and one line on what separates them. Japanese rank \
titles are the common case: 課長 may be "Manager", "Section Chief" or \
"Department Head", and those are three different claims about seniority. \
Return the choice; do not make it.

5. An alternative needs at least two options. One option is not a choice, it \
is a rendering, and it belongs in the draft.

6. Leave proper nouns alone. Do not translate or romanise a company name, a \
university or an awarding body — those come from the profile separately, and a \
guessed English name is a claim the person has to answer for.

7. Keep the register of a resume: plain, specific, past tense for past roles. \
Do not add adjectives the source does not have.

8. Echo the text you were given back in `source_text`, unchanged, so the person \
compares your rendering against what they wrote.
"""


def build_translation_input(text: str, source_language: str, target_language: str) -> str:
    """Wrap the source so the model can tell text from instruction."""
    return (
        f"Render the text below from {source_language} into {target_language}.\n\n"
        "--- BEGIN TEXT ---\n"
        f"{text}\n"
        "--- END TEXT ---\n"
    )
