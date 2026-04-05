import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
    reactStrictMode: true,
    env: {
        API_URL: process.env.API_URL || 'http://localhost:5000',
    },
    images: {
        domains: ['ogiacbcmiboycerigvsd.supabase.co'],
    },
    typescript: {
        // Type errors caught locally; Vercel's bun environment produces false positives
        ignoreBuildErrors: true,
    },
    eslint: {
        // ESLint config-next patch fails in Vercel's bun environment
        ignoreDuringBuilds: true,
    },
}

export default nextConfig
