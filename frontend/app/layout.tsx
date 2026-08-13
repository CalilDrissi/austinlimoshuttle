import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "Austin Limo Shuttle",
    template: "%s | Austin Limo Shuttle",
  },
  description:
    "Airport transfers, weddings and executive travel across Austin, Texas.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      {/*
        The template stylesheet is loaded from /public rather than imported.
        It is a 418 KB compiled bundle that we deliberately keep byte-identical
        so it can be swapped or replaced wholesale later; running it through the
        bundler would mean editing a vendored artefact.
      */}
      <head>
        <link rel="stylesheet" href="/styles/luxride.css" />
        <link rel="stylesheet" href="/styles/luxride-extra.css" />
      </head>
      <body>{children}</body>
    </html>
  );
}
