import type { Meta, StoryObj } from "@storybook/react";

const ICONS = [
  "icon-date", "icon-time", "icon-from", "icon-to", "icon-search",
  "icon-account", "icon-facebook", "icon-twitter", "icon-instagram", "icon-linkedin",
  "icon-passengers", "icon-luggage", "icon-checkmark",
  "icon-arrow-right", "icon-arrow-left",
];

function IconGallery() {
  return (
    <div style={{ padding: 32, fontFamily: "DM Sans, sans-serif" }}>
      <h1 style={{ marginBottom: 8 }}>Icons</h1>
      <p style={{ color: "#6b7280", marginBottom: 40 }}>
        Icon font: <strong>uicons-regular-rounded</strong> — from the licensed HTML template.
        Use as <code>{`<span className="item-icon icon-date" />`}</code>.
      </p>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 16 }}>
        {ICONS.map((icon) => (
          <div
            key={icon}
            style={{
              display: "flex", flexDirection: "column", alignItems: "center",
              width: 100, padding: "16px 8px", border: "1px solid #e5e7eb", borderRadius: 8,
            }}
          >
            <span className={`item-icon ${icon}`} style={{ fontSize: 28, display: "block", marginBottom: 8 }} />
            <code style={{ fontSize: 10, color: "#6b7280", textAlign: "center", wordBreak: "break-all" }}>{icon}</code>
          </div>
        ))}
      </div>
    </div>
  );
}

const meta: Meta = {
  title: "Style Guide/Icons",
  component: IconGallery,
  parameters: { layout: "fullscreen" },
  tags: ["autodocs"],
};
export default meta;

export const Gallery: StoryObj = {};
