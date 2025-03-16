const withPWA = require("next-pwa")({
  dest: "public",
  register: true,
  skipWaiting: true,
});

const nextConfig = {
  reactStrictMode: true,
  images: {
    unoptimized: true, // Required when using next/image with static exports
  },
  env: {
    BACKEND_API: "http://192.168.219.28:8000",
    REPLAY_API: "http://192.168.219.28:5001",
  },
};

module.exports = withPWA(nextConfig);
