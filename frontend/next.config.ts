import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  turbopack: {
    root: __dirname,
  },
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "cf.furunavi.jp" },
      { protocol: "https", hostname: "www.satofull.jp" },
      { protocol: "https", hostname: "thumbnail.image.rakuten.co.jp" },
      { protocol: "https", hostname: "*.rakuten.co.jp" },
    ],
  },
};

export default nextConfig;
