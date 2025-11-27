/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    domains: ['localhost'],
  },
  env: {
    MCP_API_URL: process.env.MCP_API_URL || 'http://localhost:7801',
    MCP_TOKEN: process.env.MCP_TOKEN || '',
  },
}

module.exports = nextConfig
