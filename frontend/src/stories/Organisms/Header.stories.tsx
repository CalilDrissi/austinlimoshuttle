import type { Meta, StoryObj } from "@storybook/react";
import Header from "@/components/layout/Header";

const meta: Meta<typeof Header> = {
  title: "Organisms/Header",
  component: Header,
  parameters: { layout: "fullscreen", nextjs: { appDirectory: true } },
  tags: ["autodocs"],
};
export default meta;
type Story = StoryObj<typeof Header>;

export const Default: Story = {};
