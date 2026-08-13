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
      {/*
        The template's font is delivered through a CSS variable that is only
        defined on this class -- next/font generated both. Without it the page
        silently falls back to Bootstrap's system stack and looks subtly wrong
        rather than broken, which is the hardest kind of bug to notice.
      */}
      <body className="__variable_8a1573">{children}</body>
    </html>
  );
}
