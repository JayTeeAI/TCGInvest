import { MetadataRoute } from "next"

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: [
          "/auth/callback",
          "/api/",
          "/premium/success",
        ],
      },
    ],
    sitemap: "https://tcginvest.uk/sitemap.xml",
    host: "https://tcginvest.uk",
  }
}
