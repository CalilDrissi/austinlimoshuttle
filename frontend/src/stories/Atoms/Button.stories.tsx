import type { Meta, StoryObj } from "@storybook/react";

interface ButtonProps {
  label: string;
  variant?: "primary" | "default" | "white" | "search";
  href?: string;
  onClick?: () => void;
}

function Button({ label, variant = "primary", onClick }: ButtonProps) {
  const classMap: Record<string, string> = {
    primary: "btn btn-primary hover-up",
    default: "btn btn-default hover-up",
    white: "btn btn-white hover-up",
    search: "btn btn-search",
  };
  return (
    <button className={classMap[variant]} onClick={onClick} type="button">
      {label}
    </button>
  );
}

const meta: Meta<typeof Button> = {
  title: "Atoms/Button",
  component: Button,
  parameters: { layout: "centered" },
  tags: ["autodocs"],
  argTypes: {
    variant: { control: "select", options: ["primary", "default", "white", "search"] },
  },
};
export default meta;
type Story = StoryObj<typeof Button>;

export const Primary: Story = { args: { label: "Book Now", variant: "primary" } };
export const Default: Story = { args: { label: "Log In", variant: "default" } };
export const White: Story = {
  args: { label: "Sign Up", variant: "white" },
  parameters: { backgrounds: { default: "dark" } },
};
export const Search: Story = { args: { label: "Search", variant: "search" } };
export const AllVariants: Story = {
  render: () => (
    <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center", padding: 16, background: "#0E0E0E" }}>
      <Button label="Book Now" variant="primary" />
      <Button label="Log In" variant="default" />
      <Button label="Sign Up" variant="white" />
      <Button label="Search" variant="search" />
    </div>
  ),
};
