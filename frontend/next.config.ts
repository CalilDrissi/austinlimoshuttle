import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [],
  },
  // Type safety is enforced by `tsc --noEmit` in CI/pre-push; don't let lint-only
  // issues (unused import, <img> advisory) block a production build.
  eslint: {
    ignoreDuringBuilds: true,
  },
};

export default nextConfig;
