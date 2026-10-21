import { getTranslations, setRequestLocale } from "next-intl/server";

import { PageHeading } from "@/components/profile/page-heading";
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
    <main className="page">
      <PageHeading title={t("title")} back={{ href: `/${locale}/profile`, label: t("back") }} />

      <StorySearch initial={stories} />
      <StoryForm existing={stories} experiences={experiences} />
    </main>
  );
}
