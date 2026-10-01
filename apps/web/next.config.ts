import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  async redirects() {
    return [{ source: '/findings', destination: '/', permanent: false }];
  },
};

export default nextConfig;
