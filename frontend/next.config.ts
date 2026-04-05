import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
    reactStrictMode: true,
    env: {
        API_URL: process.env.API_URL || 'http://localhost:5000',
    },
    images: {
        domains: ['ogiacbcmiboycerigvsd.supabase.co'],
    },
}

export default nextConfig
