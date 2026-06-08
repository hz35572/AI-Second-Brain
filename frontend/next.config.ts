import type { NextConfig } from "next";

const frontendRoot = __dirname;
const backendApiBase =
  process.env.BACKEND_API_BASE || "http://localhost:9000/api/v1";

const nextConfig = (): NextConfig => ({
  output: "standalone",
  turbopack: {
    root: frontendRoot,
  },
  images: {
    unoptimized: true,
  },
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${backendApiBase}/:path*`,
      },
    ];
  },
});

export default nextConfig;
