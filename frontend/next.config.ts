import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  skipTrailingSlashRedirect: true,
  async rewrites() {
    const backend = process.env.INTERNAL_API_URL;
    return [
      { source: "/_allauth/:path*", destination: `${backend}/_allauth/:path*` },
      { source: "/api/:path*", destination: `${backend}/api/:path*` },
    ];
  },
};

export default nextConfig;
