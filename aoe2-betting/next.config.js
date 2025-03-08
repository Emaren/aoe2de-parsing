const withPWA = require("next-pwa")({
  dest: "public",
  register: true,
  skipWaiting: true,
});

module.exports = withPWA({
  reactStrictMode: true,
  env: {
    BACKEND_API: "http://192.168.219.28:8000",
    REPLAY_API: "http://192.168.219.28:5001",
  },
});
