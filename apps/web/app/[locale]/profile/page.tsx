import Link from "next/link";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { ExperienceForm } from "@/components/profile/experience-form";
import { IdentityForm } from "@/components/profile/identity-form";
import { JapanForm } from "@/components/profile/japan-form";
import { PageHeading } from "@/components/profile/page-heading";
import { PreferenceForm } from "@/components/profile/preference-form";
import {
  CertificationSection,
  EducationSection,
  LanguageSection,
  SkillSection,
} from "@/components/profile/simple-sections";
import { api, type CareerStory, type Profile } from "@/lib/api";

export const dynamic = "force-dynamic";

/** Load the profile when present; a missing profile is an expected first-use state. */
async function loadProfile(): Promise<Profile | null> {
  try {
    return await api.getProfile();
  } catch {
    // A profile that does not exist yet is a normal starting state, not an error.
    return null;
  }
}

/** Load recorded achievement stories; the page remains usable if that list is unavailable. */
async function loadStories(): Promise<CareerStory[]> {
  try {
    return await api.listStories();
  } catch {
    return [];
  }
}

/** Render the user's recorded career profile and its editing sections. */
export default async function ProfilePage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("profile");
  const [profile, stories] = await Promise.all([loadProfile(), loadStories()]);

  return (
    <main className="page">
      <PageHeading title={t("title")} subtitle={t("subtitle")} />

      <Link href={`/${locale}/profile/documents/shokumu-keirekisho`} className="link self-start">
        {t("shokumuNav")}
      </Link>

      <IdentityForm initial={profile?.identity} />
      <ExperienceForm existing={profile?.experiences ?? []} stories={stories} />
      <EducationSection entries={(profile?.education ?? []) as Record<string, unknown>[]} />
      <CertificationSection
        entries={(profile?.certifications ?? []) as Record<string, unknown>[]}
      />
      <SkillSection entries={(profile?.skills ?? []) as Record<string, unknown>[]} />
      <LanguageSection entries={(profile?.languages ?? []) as Record<string, unknown>[]} />
      <PreferenceForm initial={profile?.preferences} />
      <JapanForm initial={profile?.japan} />
    </main>
  );
}
