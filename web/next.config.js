/** @type {import('next').NextConfig} */
const isDev = process.env.NODE_ENV !== 'production';

const nextConfig = {
  // In dev we run `next dev` and proxy /api → backend.
  // In prod we statically export and FastAPI serves /api itself.
  output: isDev ? undefined : 'export',
  basePath: '/app',
  assetPrefix: isDev ? undefined : '/app',
  images: { unoptimized: true },
  // trailingSlash matters for static export so directory pages resolve. In dev we skip
  // it because it causes Next.js to redirect /api/* before our rewrites can match.
  trailingSlash: !isDev,
  reactStrictMode: true,
  ...(isDev
    ? {
        async rewrites() {
          const target = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';
          return [
            // basePath: false escapes the /app prefix so /api/* hits FastAPI as-is.
            { source: '/api/:path*', destination: target + '/api/:path*', basePath: false },
          ];
        },
      }
    : {}),
};

module.exports = nextConfig;
