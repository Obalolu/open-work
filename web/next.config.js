/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  async rewrites() {
    const apiBase = process.env.API_INTERNAL_URL || "http://api:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${apiBase}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
