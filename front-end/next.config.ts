import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination:
          process.env.INTERNAL_API_URL
            ? `${process.env.INTERNAL_API_URL}/api/v1/:path*`
            : "http://backend:8000/api/v1/:path*",
      },
    ];
  },
};

export default nextConfig;
