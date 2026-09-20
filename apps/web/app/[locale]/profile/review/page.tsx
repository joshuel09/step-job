import { getTranslations, setRequestLocale } from "next-intl/server";
import Link from "next/link";

import { ProposalReview } from "@/components/profile/proposal-review";
import { api, type ProposedEntry, type WorkExperience } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function ReviewPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("profile.review");

  let proposals: ProposedEntry[] = [];
  let experiences: WorkExperience[] = [];
  try {
    [proposals, experiences] = await Promise.all([
      api.listProposals(),
      api.getProfile().then((p) => p.experiences ?? []),
    ]);
  } catch {
    // No profile yet is a normal starting state.
  }

  return (
    <main className="mx-auto flex max-w-3xl flex-col gap-6 p-6">
      <header>
        <Link href={`/${locale}/profile`} className="text-sm underline opacity-70">
          {t("back")}
        </Link>
        <h1 className="mt-2 text-2xl font-semibold">{t("title")}</h1>
        <p className="mt-1 text-sm opacity-70">{t("explanation")}</p>
      </header>

      <ProposalReview proposals={proposals} experiences={experiences} />
    </main>
  );
}
