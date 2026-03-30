import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  transpilePackages: ["@celestia/shared-types"],
  experimental: {
    serverActions: {
      bodySizeLimit: "10mb",
    },
  },
};

export default nextConfig;
