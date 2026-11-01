import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  async redirects() {
    return [{ source: '/findings', destination: '/', permanent: false }];
  },
  async rewrites() {
    const apiOrigin = process.env.CLAIMGUARD_API_ORIGIN ?? 'http://127.0.0.1:4001';
    return [
      {
        source: '/api/:path*',
        destination: `${apiOrigin}/:path*`,
      },
    ];
  },
};

export default nextConfig;
