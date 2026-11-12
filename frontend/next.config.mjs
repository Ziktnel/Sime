/** O Next encaminha /api/* para o backend FastAPI (sem CORS no navegador). */
const backend = process.env.OHMNIA_BACKEND_URL || "http://localhost:8000";
export default {
  reactStrictMode: true,
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${backend}/api/:path*` }];
  },
};
