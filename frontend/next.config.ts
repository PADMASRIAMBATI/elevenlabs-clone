/** @type {import('next').NextConfig} */
const nextConfig = {
  // Add this line to enable the standalone output mode
  output: 'standalone',

  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*',
      },
    ];
  },
};

module.exports = nextConfig;