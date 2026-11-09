import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin("./i18n.ts");

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  distDir: process.env.PROFILE_BROWSER_TEST === "1" ? ".next-profile-tests" : ".next",
};

export default withNextIntl(nextConfig);
