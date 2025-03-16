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
    BACKEND_API: "https://your-flask-app.onrender.com",
    REPLAY_API: "https://your-flask-app.onrender.com",
  },  
};

module.exports = withPWA(nextConfig);
