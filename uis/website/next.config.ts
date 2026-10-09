import type { NextConfig } from 'next';

const config: NextConfig = {
  devIndicators: false,
  allowedDevOrigins: ['localhost', '127.0.0.1', '*.app.github.dev'],
  experimental: { cpus: 2 },
  async rewrites() {
    const target = process.env.API_PROXY_TARGET || 'http://127.0.0.1:8000';
    return [{ source: '/api/:path*', destination: `${target}/:path*` }];
  },
  webpack(config, { dev }) {
    if (dev) config.watchOptions = { ...config.watchOptions, poll: 300, aggregateTimeout: 200 };
    return config;
  },
};

export default config;