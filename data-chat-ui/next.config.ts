import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  output: 'standalone',
  // Configure environment variables for builds that don't have them
  env: {
    NEXT_PUBLIC_SQL_API_URL: process.env.NEXT_PUBLIC_SQL_API_URL || 'https://your-render-backend-url.onrender.com',
  },
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
    // Ensure path aliases are resolved correctly
    config.resolve = config.resolve || {};
    config.resolve.alias = {
      ...(config.resolve.alias || {}),
      '@': require('path').resolve(__dirname, 'src'),
    };
    
    return config;
  }
};

export default nextConfig;
