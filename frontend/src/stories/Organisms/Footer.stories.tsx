import type { Meta, StoryObj } from "@storybook/react";
import Footer from "@/components/layout/Footer";

const meta: Meta<typeof Footer> = {
  title: "Organisms/Footer",
  component: Footer,
  parameters: { layout: "fullscreen", nextjs: { appDirectory: true } },
  tags: ["autodocs"],
};
export default meta;
type Story = StoryObj<typeof Footer>;

export const Default: Story = {};
