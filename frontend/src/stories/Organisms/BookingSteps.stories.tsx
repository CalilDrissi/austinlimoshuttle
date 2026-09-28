import type { Meta, StoryObj } from "@storybook/react";
import BookingSteps from "@/components/booking/BookingSteps";

const meta: Meta<typeof BookingSteps> = {
  title: "Organisms/BookingSteps",
  component: BookingSteps,
  parameters: { layout: "fullscreen", nextjs: { appDirectory: true } },
  tags: ["autodocs"],
};
export default meta;
type Story = StoryObj<typeof BookingSteps>;

export const Step1: Story = { parameters: { nextjs: { navigation: { pathname: "/booking/vehicle" } } } };
export const Step2: Story = { parameters: { nextjs: { navigation: { pathname: "/booking/extra" } } } };
export const Step3: Story = { parameters: { nextjs: { navigation: { pathname: "/booking/passenger" } } } };
export const Step4: Story = { parameters: { nextjs: { navigation: { pathname: "/booking/payment" } } } };
