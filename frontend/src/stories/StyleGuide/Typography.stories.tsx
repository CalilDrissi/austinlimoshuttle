import type { Meta, StoryObj } from "@storybook/react";

const SCALE = [
  { class: "heading-88-medium", size: "88px", weight: "500", label: "Heading 88 Medium" },
  { class: "heading-64-medium", size: "64px", weight: "500", label: "Heading 64 Medium" },
  { class: "heading-52-medium", size: "52px", weight: "500", label: "Heading 52 Medium" },
  { class: "heading-48-medium", size: "48px", weight: "500", label: "Heading 48 Medium" },
  { class: "heading-40-medium", size: "40px", weight: "500", label: "Heading 40 Medium" },
  { class: "heading-36-medium", size: "36px", weight: "500", label: "Heading 36 Medium" },
  { class: "heading-32-medium", size: "32px", weight: "500", label: "Heading 32 Medium" },
  { class: "heading-24-medium", size: "24px", weight: "500", label: "Heading 24 Medium" },
  { class: "heading-20-medium", size: "20px", weight: "500", label: "Heading 20 Medium" },
  { class: "text-18-medium", size: "18px", weight: "500", label: "Text 18 Medium" },
  { class: "text-16-medium", size: "16px", weight: "500", label: "Text 16 Medium" },
  { class: "text-16", size: "16px", weight: "400", label: "Text 16 Regular" },
  { class: "text-14-medium", size: "14px", weight: "500", label: "Text 14 Medium" },
  { class: "text-14", size: "14px", weight: "400", label: "Text 14 Regular" },
  { class: "text-12", size: "12px", weight: "400", label: "Text 12 Regular" },
];

function TypographyScale() {
  return (
    <div style={{ padding: 32, fontFamily: "DM Sans, sans-serif" }}>
      <h1 style={{ marginBottom: 8 }}>Typography</h1>
      <p style={{ color: "#6b7280", marginBottom: 8 }}>
        Font: <strong>DM Sans</strong> — loaded via <code>next/font/google</code>.
      </p>
      <p style={{ color: "#6b7280", marginBottom: 40 }}>
        All utility classes are defined in <code>luxride.css</code>. Use them directly on HTML elements.
      </p>

      <div style={{ borderBottom: "1px solid #e5e7eb", marginBottom: 32 }}>
        {SCALE.map((item) => (
          <div
            key={item.class}
            style={{ display: "flex", alignItems: "baseline", gap: 24, padding: "16px 0", borderBottom: "1px solid #f3f4f6" }}
          >
            <div style={{ width: 200, flexShrink: 0 }}>
              <code style={{ fontSize: 12, color: "#6b7280" }}>.{item.class}</code>
              <br />
              <span style={{ fontSize: 11, color: "#9ca3af" }}>
                {item.size} / {item.weight}
              </span>
            </div>
            <span className={item.class}>The quick brown fox</span>
          </div>
        ))}
      </div>

      <h3 style={{ marginBottom: 16 }}>Color Utilities</h3>
      <div style={{ display: "flex", gap: 32, flexWrap: "wrap" }}>
        {["color-primary", "color-white", "color-grey", "color-text"].map((cls) => (
          <div key={cls} style={{ background: cls === "color-white" ? "#0E0E0E" : "#fff", padding: "8px 16px", borderRadius: 6 }}>
            <span className={`text-16-medium ${cls}`}>.{cls}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

const meta: Meta = {
  title: "Style Guide/Typography",
  component: TypographyScale,
  parameters: { layout: "fullscreen" },
  tags: ["autodocs"],
};
export default meta;

export const Scale: StoryObj = {};
