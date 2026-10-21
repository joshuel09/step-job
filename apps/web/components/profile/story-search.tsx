"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { api, type CareerStory } from "@/lib/api";

/**
 * Finding an accomplishment recorded months ago (SC-006, under a minute).
 *
 * Search runs against all four fields server-side, because the phrase a user
 * remembers is usually in the result rather than in the title they chose.
 */
export function StorySearch({ initial }: { initial: CareerStory[] }) {
  const t = useTranslations("profile.stories");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState(initial);
  const [searching, setSearching] = useState(false);

  useEffect(() => {
    const timer = setTimeout(async () => {
      setSearching(true);
      try {
        setResults(await api.listStories(query || undefined));
      } finally {
        setSearching(false);
      }
    }, 250);
    return () => clearTimeout(timer);
  }, [query]);

  return (
    <div className="flex flex-col gap-4">
      <label className="flex flex-col gap-1">
        <span className="text-sm font-medium">{t("search")}</span>
        <input
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder={t("searchPlaceholder")}
          className="field"
        />
      </label>

      <p className="hint" aria-live="polite">
        {searching ? t("searching") : t("resultCount", { count: results.length })}
      </p>

      {results.length === 0 ? (
        <p className="explain">{query ? t("noMatches") : t("empty")}</p>
      ) : (
        <ul className="flex flex-col gap-3">
          {results.map((story) => (
            <li
              key={story.id}
              className="entry"
            >
              <p className="font-medium">{story.title}</p>
              <p className="hint mt-1">
                <span className="font-medium">{t("challenge")}:</span> {story.challenge}
              </p>
              <p className="hint">
                <span className="font-medium">{t("action")}:</span> {story.action}
              </p>
              <p className="hint">
                <span className="font-medium">{t("result")}:</span> {story.result}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
