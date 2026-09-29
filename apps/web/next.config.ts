import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  transpilePackages: ["@claimguard/shared-types"],
};

export default nextConfig;
