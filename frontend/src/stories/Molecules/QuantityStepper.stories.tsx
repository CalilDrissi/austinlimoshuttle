import type { Meta, StoryObj } from "@storybook/react";
import { useState } from "react";

function QuantityStepper({ label, min = 0, max = 20, initial = 1 }: {
  label: string; min?: number; max?: number; initial?: number;
}) {
  const [qty, setQty] = useState(initial);
  return (
    <div className="extra-quantity d-flex align-items-center" style={{ gap: 12 }}>
      <span className="text-14-medium color-text" style={{ minWidth: 100 }}>{label}</span>
      <button className="btn btn-quantity minus" onClick={() => setQty((q) => Math.max(min, q - 1))}>−</button>
      <span className="text-16-medium color-text" style={{ width: 32, textAlign: "center" }}>{qty}</span>
      <button className="btn btn-quantity plus" onClick={() => setQty((q) => Math.min(max, q + 1))}>+</button>
    </div>
  );
}

const meta: Meta<typeof QuantityStepper> = {
  title: "Molecules/QuantityStepper",
  component: QuantityStepper,
  parameters: { layout: "centered" },
  tags: ["autodocs"],
};
export default meta;
type Story = StoryObj<typeof QuantityStepper>;

export const Passengers: Story = { args: { label: "Passengers", min: 1, max: 10, initial: 2 } };
export const Luggage: Story = { args: { label: "Luggage", min: 0, max: 10, initial: 1 } };
