import type { Meta, StoryObj } from "@storybook/react";

const COLORS = [
  // Brand
  { name: "Primary / Dark", var: "--color-primary", hex: "#0E0E0E", group: "Brand" },
  { name: "White", var: "--color-white", hex: "#ffffff", group: "Brand" },
  { name: "Grey", var: "--color-grey", hex: "#6B7280", group: "Brand" },
  { name: "Text", var: "--color-text", hex: "#181A1F", group: "Brand" },
  // States
  { name: "Success", hex: "#22C55E", group: "State" },
  { name: "Warning", hex: "#F59E0B", group: "State" },
  { name: "Error", hex: "#EF4444", group: "State" },
  { name: "Info", hex: "#3B82F6", group: "State" },
  // Greys
  { name: "Grey 100", hex: "#F9FAFB", group: "Neutral" },
  { name: "Grey 200", hex: "#F3F4F6", group: "Neutral" },
  { name: "Grey 300", hex: "#E5E7EB", group: "Neutral" },
  { name: "Grey 400", hex: "#D1D5DB", group: "Neutral" },
  { name: "Grey 500", hex: "#9CA3AF", group: "Neutral" },
  { name: "Grey 600", hex: "#6B7280", group: "Neutral" },
  { name: "Grey 700", hex: "#374151", group: "Neutral" },
  { name: "Grey 900", hex: "#111827", group: "Neutral" },
];

const groups = [...new Set(COLORS.map((c) => c.group))];

function ColorSwatch({ name, hex, varName }: { name: string; hex: string; varName?: string }) {
  return (
    <div style={{ width: 140, margin: 12 }}>
      <div
        style={{
          width: 140, height: 80, borderRadius: 8, background: hex,
          border: hex === "#ffffff" ? "1px solid #e5e7eb" : "none",
          boxShadow: "0 1px 3px rgba(0,0,0,.1)",
        }}
      />
      <p style={{ margin: "8px 0 2px", fontWeight: 600, fontSize: 13 }}>{name}</p>
      <p style={{ margin: 0, fontSize: 12, color: "#6b7280", fontFamily: "monospace" }}>{hex}</p>
      {varName && <p style={{ margin: 0, fontSize: 11, color: "#9ca3af", fontFamily: "monospace" }}>{varName}</p>}
    </div>
  );
}

function ColorPalette() {
  return (
    <div style={{ padding: 32, fontFamily: "DM Sans, sans-serif" }}>
      <h1 style={{ marginBottom: 8 }}>Color Palette</h1>
      <p style={{ color: "#6b7280", marginBottom: 40 }}>
        The M&M design system color tokens — extracted from <code>luxride.css</code>.
      </p>
      {groups.map((group) => (
        <div key={group} style={{ marginBottom: 48 }}>
          <h3 style={{ borderBottom: "1px solid #e5e7eb", paddingBottom: 8, marginBottom: 16 }}>{group}</h3>
          <div style={{ display: "flex", flexWrap: "wrap" }}>
            {COLORS.filter((c) => c.group === group).map((c) => (
              <ColorSwatch key={c.hex} name={c.name} hex={c.hex} varName={c.var} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

const meta: Meta = {
  title: "Style Guide/Colors",
  component: ColorPalette,
  parameters: { layout: "fullscreen" },
  tags: ["autodocs"],
};
export default meta;

export const Palette: StoryObj = {};
