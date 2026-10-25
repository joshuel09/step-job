import { getTranslations, setRequestLocale } from "next-intl/server";

import { PageHeading } from "@/components/profile/page-heading";
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
    <main className="page">
      <PageHeading
        title={t("title")}
        subtitle={t("explanation")}
        back={{ href: `/${locale}/profile`, label: t("back") }}
      />

      <ProposalReview proposals={proposals} experiences={experiences} />
    </main>
  );
}
