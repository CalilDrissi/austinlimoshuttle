import type { Meta, StoryObj } from "@storybook/react";

interface BadgeProps {
  label: string;
  color?: "primary" | "success" | "warning" | "error";
}

function Badge({ label, color = "primary" }: BadgeProps) {
  const bg: Record<string, string> = {
    primary: "#0E0E0E",
    success: "#22C55E",
    warning: "#F59E0B",
    error: "#EF4444",
  };
  return (
    <span
      className="text-12"
      style={{
        display: "inline-block", padding: "3px 10px", borderRadius: 20,
        background: bg[color], color: "#fff", fontWeight: 500,
      }}
    >
      {label}
    </span>
  );
}

const meta: Meta<typeof Badge> = {
  title: "Atoms/Badge",
  component: Badge,
  parameters: { layout: "centered" },
  tags: ["autodocs"],
  argTypes: { color: { control: "select", options: ["primary", "success", "warning", "error"] } },
};
export default meta;
type Story = StoryObj<typeof Badge>;

export const Primary: Story = { args: { label: "Business Class", color: "primary" } };
export const Success: Story = { args: { label: "Confirmed", color: "success" } };
export const Warning: Story = { args: { label: "Pending", color: "warning" } };
export const Error: Story = { args: { label: "Cancelled", color: "error" } };
