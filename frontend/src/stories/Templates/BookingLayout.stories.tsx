import type { Meta, StoryObj } from "@storybook/react";
import Header from "@/components/layout/Header";
import Footer from "@/components/layout/Footer";
import BookingSteps from "@/components/booking/BookingSteps";

function BookingLayout() {
  return (
    <>
      <Header />
      <main className="main">
        <BookingSteps />
        <section className="section pt-40 pb-60">
          <div className="container">
            <p className="text-16 color-grey">Step content rendered here.</p>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}

const meta: Meta<typeof BookingLayout> = {
  title: "Templates/BookingLayout",
  component: BookingLayout,
  parameters: {
    layout: "fullscreen",
    nextjs: { appDirectory: true, navigation: { pathname: "/booking/vehicle" } },
  },
  tags: ["autodocs"],
};
export default meta;
type Story = StoryObj<typeof BookingLayout>;

export const VehicleStep: Story = {};
export const PassengerStep: Story = {
  parameters: { nextjs: { navigation: { pathname: "/booking/passenger" } } },
};
