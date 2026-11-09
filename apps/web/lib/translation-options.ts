/** Locate a full reading without treating it as part of a longer word. */
function occurrences(text: string, option: string): { start: number; end: number }[] {
  if (!option) return [];
  const matches: { start: number; end: number }[] = [];
  const word = /[\p{L}\p{N}]/u;
  let start = text.indexOf(option);
  while (start !== -1) {
    const end = start + option.length;
    const joinedBefore = start > 0 && word.test(text[start - 1]!) && word.test(option[0]!);
    const joinedAfter =
      end < text.length && word.test(text[end]!) && word.test(option[option.length - 1]!);
    if (!joinedBefore && !joinedAfter) matches.push({ start, end });
    start = text.indexOf(option, start + 1);
  }
  return matches;
}

/** Whether selected wording is present as a full reading, not a word fragment. */
export function containsTranslationOption(text: string, option: string): boolean {
  return occurrences(text, option).length > 0;
}

/** Replace one identifiable reading only; ambiguous edits remain the user's. */
export function applyTranslationOption(
  text: string,
  options: readonly string[],
  chosen: string,
): string {
  const matches = [...new Set(options)].flatMap((option) => occurrences(text, option));
  // An option such as "Chief" nested within "Section Chief" is one match.
  const distinct = matches.filter(
    (match) =>
      !matches.some(
        (other) =>
          other !== match &&
          other.start <= match.start &&
          other.end >= match.end &&
          (other.start < match.start || other.end > match.end),
      ),
  );
  if (distinct.length !== 1) return text;
  const match = distinct[0]!;
  return text.slice(0, match.start) + chosen + text.slice(match.end);
}
