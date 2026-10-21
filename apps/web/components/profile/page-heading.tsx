import Link from "next/link";

/**
 * The top of every page under /profile: the way back, the title and what the
 * page is for. One component so the six pages cannot drift apart (#125).
 */
export function PageHeading({
  title,
  subtitle,
  back,
}: {
  title: string;
  subtitle?: string;
  back?: { href: string; label: string };
}) {
  return (
    <header className="flex flex-col gap-2">
      {back && (
        <Link href={back.href} className="back-link">
          <span aria-hidden>←</span>
          {back.label}
        </Link>
      )}
      <h1 className="page-title">{title}</h1>
      {subtitle && <p className="explain max-w-2xl">{subtitle}</p>}
    </header>
  );
}
