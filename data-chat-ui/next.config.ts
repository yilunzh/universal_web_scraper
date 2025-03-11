import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  output: 'standalone',
  // Configure domain rewrites if needed
  async rewrites() {
    // Only apply rewrites if the API URL is defined
    const apiUrl = process.env.NEXT_PUBLIC_SQL_API_URL;
    
    if (!apiUrl) {
      console.warn('NEXT_PUBLIC_SQL_API_URL is not defined, skipping API rewrites');
      return [];
    }
    
    return [
      {
        source: '/api/:path*',
        destination: `${apiUrl}/:path*` // Proxy API requests with proper string interpolation
      }
    ];
  },
  // Explicitly define webpack configuration to ensure path aliases work
  webpack: (config) => {
    // Add your webpack config here if needed
    return config;
  }
};

export default nextConfig;
