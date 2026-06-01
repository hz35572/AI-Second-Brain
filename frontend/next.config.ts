import type { NextConfig } from "next";
import { PHASE_DEVELOPMENT_SERVER } from "next/constants";

const frontendRoot = __dirname;
const backendApiBase =
  process.env.BACKEND_API_BASE || "http://localhost:8000/api/v1";

const nextConfig = (phase: string): NextConfig => ({
  output: 'export',
  distDir: 'dist',
  turbopack: {
    root: frontendRoot,
  },
  images: {
    unoptimized: true,
  },
  ...(phase === PHASE_DEVELOPMENT_SERVER
    ? {
        async rewrites() {
          return [
            {
              source: "/api/v1/:path*",
              destination: `${backendApiBase}/:path*`,
            },
          ];
        },
      }
    : {}),
});

export default nextConfig;
