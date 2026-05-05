/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  basePath: '/app',
  assetPrefix: '/app',
  images: { unoptimized: true },
  trailingSlash: true,
  reactStrictMode: true,
};

module.exports = nextConfig;
