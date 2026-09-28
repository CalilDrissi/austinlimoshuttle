import type { Meta, StoryObj } from "@storybook/react";
import { useState } from "react";

interface InputProps {
  label?: string;
  placeholder?: string;
  type?: string;
  disabled?: boolean;
}

function FormInput({ label, placeholder, type = "text", disabled }: InputProps) {
  const [focused, setFocused] = useState(false);
  const [value, setValue] = useState("");
  return (
    <div className={`form-group${focused || value ? " focused" : ""}`} style={{ minWidth: 280 }}>
      {label && <label className="text-14 color-grey mb-5 d-block">{label}</label>}
      <input
        className="form-control"
        type={type}
        placeholder={placeholder}
        disabled={disabled}
        value={value}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        onChange={(e) => setValue(e.target.value)}
      />
    </div>
  );
}

const meta: Meta<typeof FormInput> = {
  title: "Atoms/Input",
  component: FormInput,
  parameters: { layout: "centered" },
  tags: ["autodocs"],
};
export default meta;
type Story = StoryObj<typeof FormInput>;

export const Default: Story = { args: { label: "Email", placeholder: "you@example.com", type: "email" } };
export const Password: Story = { args: { label: "Password", placeholder: "••••••••", type: "password" } };
export const Disabled: Story = { args: { label: "Disabled", placeholder: "Unavailable", disabled: true } };
export const SearchInput: Story = {
  render: () => (
    <div style={{ background: "#0E0E0E", padding: 24, borderRadius: 12 }}>
      <div className="search-inputs">
        <label className="text-14 color-grey">From</label>
        <input className="search-input" type="text" readOnly placeholder="London Heathrow Airport (LHR)" />
      </div>
    </div>
  ),
};
