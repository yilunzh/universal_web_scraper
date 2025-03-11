import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  output: 'standalone',
  // Configure domain rewrites if needed
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: process.env.NEXT_PUBLIC_SQL_API_URL + '/:path*' // Proxy API requests
      }
    ];
  }
};

export default nextConfig;
