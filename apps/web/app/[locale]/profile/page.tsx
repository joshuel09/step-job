import { getTranslations, setRequestLocale } from "next-intl/server";
import Link from "next/link";

import { LocaleSwitcher } from "@/components/locale-switcher";
import { ExperienceForm } from "@/components/profile/experience-form";
import { IdentityForm } from "@/components/profile/identity-form";
import { JapanForm } from "@/components/profile/japan-form";
import { PreferenceForm } from "@/components/profile/preference-form";
import {
  CertificationSection,
  EducationSection,
  LanguageSection,
  SkillSection,
} from "@/components/profile/simple-sections";
import { api, type CareerStory, type Profile } from "@/lib/api";

export const dynamic = "force-dynamic";

async function loadProfile(): Promise<Profile | null> {
  try {
    return await api.getProfile();
  } catch {
    // A profile that does not exist yet is a normal starting state, not an error.
    return null;
  }
}

async function loadStories(): Promise<CareerStory[]> {
  try {
    return await api.listStories();
  } catch {
    return [];
  }
}

export default async function ProfilePage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("profile");
  const [profile, stories] = await Promise.all([loadProfile(), loadStories()]);

  return (
    <main className="mx-auto flex max-w-3xl flex-col gap-6 p-6">
      <header className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">{t("title")}</h1>
          <p className="mt-1 text-sm opacity-70">{t("subtitle")}</p>
        </div>
        <div className="flex items-center gap-3">
          <LocaleSwitcher />
          <Link href={`/${locale}/profile/stories`} className="text-sm underline">
            {t("storiesNav")}
          </Link>
          <Link href={`/${locale}/profile/import`} className="text-sm underline">
            {t("importNav")}
          </Link>
          <Link href={`/${locale}/profile/review`} className="text-sm underline">
            {t("reviewNav")}
          </Link>
          <Link href={`/${locale}/profile/settings`} className="text-sm underline">
            {t("settings")}
          </Link>
        </div>
      </header>

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
