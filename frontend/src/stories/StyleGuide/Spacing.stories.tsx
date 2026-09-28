import type { Meta, StoryObj } from "@storybook/react";

const SPACING = [4, 8, 10, 12, 15, 20, 24, 30, 40, 50, 60, 65, 80, 100];
const BREAKPOINTS = [
  { name: "sm", value: "576px" },
  { name: "md", value: "768px" },
  { name: "lg", value: "992px" },
  { name: "xl", value: "1200px" },
  { name: "xxl", value: "1400px" },
];

function SpacingGuide() {
  return (
    <div style={{ padding: 32, fontFamily: "DM Sans, sans-serif" }}>
      <h1 style={{ marginBottom: 8 }}>Spacing & Breakpoints</h1>
      <p style={{ color: "#6b7280", marginBottom: 40 }}>
        Spacing values used by Bootstrap utility classes (<code>pt-*</code>, <code>pb-*</code>, <code>mb-*</code>, <code>mr-*</code>)
        and custom classes in <code>luxride.css</code>.
      </p>

      <h3 style={{ marginBottom: 16 }}>Spacing Scale (px)</h3>
      <div style={{ marginBottom: 48 }}>
        {SPACING.map((s) => (
          <div key={s} style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 12 }}>
            <code style={{ width: 48, fontFamily: "monospace", fontSize: 13 }}>{s}px</code>
            <div style={{ width: s * 2, height: 24, background: "#0E0E0E", borderRadius: 4 }} />
          </div>
        ))}
      </div>

      <h3 style={{ marginBottom: 16 }}>Bootstrap Breakpoints</h3>
      <table style={{ borderCollapse: "collapse", width: "100%", maxWidth: 600 }}>
        <thead>
          <tr style={{ borderBottom: "2px solid #e5e7eb" }}>
            <th style={{ textAlign: "left", padding: "8px 12px" }}>Name</th>
            <th style={{ textAlign: "left", padding: "8px 12px" }}>Min-width</th>
            <th style={{ textAlign: "left", padding: "8px 12px" }}>Class prefix</th>
          </tr>
        </thead>
        <tbody>
          {BREAKPOINTS.map((bp) => (
            <tr key={bp.name} style={{ borderBottom: "1px solid #f3f4f6" }}>
              <td style={{ padding: "10px 12px", fontWeight: 600 }}>{bp.name}</td>
              <td style={{ padding: "10px 12px", fontFamily: "monospace" }}>{bp.value}</td>
              <td style={{ padding: "10px 12px", fontFamily: "monospace" }}>.d-{bp.name}-*, .col-{bp.name}-*</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const meta: Meta = {
  title: "Style Guide/Spacing",
  component: SpacingGuide,
  parameters: { layout: "fullscreen" },
  tags: ["autodocs"],
};
export default meta;

export const Guide: StoryObj = {};
