import { getTranslations, setRequestLocale } from "next-intl/server";
import Link from "next/link";

import { StoryForm } from "@/components/profile/story-form";
import { StorySearch } from "@/components/profile/story-search";
import { api, type CareerStory, type WorkExperience } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function StoriesPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("profile.stories");

  let stories: CareerStory[] = [];
  let experiences: WorkExperience[] = [];
  try {
    [stories, experiences] = await Promise.all([
      api.listStories(),
      api.getProfile().then((p) => p.experiences ?? []),
    ]);
  } catch {
    // No profile yet is a normal starting state, not an error.
  }

  return (
    <main className="mx-auto flex max-w-3xl flex-col gap-6 p-6">
      <header>
        <Link href={`/${locale}/profile`} className="text-sm underline opacity-70">
          {t("back")}
        </Link>
        <h1 className="mt-2 text-2xl font-semibold">{t("title")}</h1>
      </header>

      <StorySearch initial={stories} />
      <StoryForm existing={stories} experiences={experiences} />
    </main>
  );
}
