import type { Meta, StoryObj } from "@storybook/react";
import BookingSearchWidget from "@/components/booking/BookingSearchWidget";

const meta: Meta<typeof BookingSearchWidget> = {
  title: "Organisms/BookingSearchWidget",
  component: BookingSearchWidget,
  parameters: {
    layout: "fullscreen",
    nextjs: { appDirectory: true },
    backgrounds: { default: "dark" },
  },
  tags: ["autodocs"],
};
export default meta;
type Story = StoryObj<typeof BookingSearchWidget>;

export const Default: Story = {
  render: () => (
    <div style={{ background: "#0E0E0E", minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <BookingSearchWidget />
    </div>
  ),
};
