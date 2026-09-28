import type { Meta, StoryObj } from "@storybook/react";
import Header from "@/components/layout/Header";
import Footer from "@/components/layout/Footer";

function MarketingLayout({ children }: { children?: React.ReactNode }) {
  return (
    <>
      <Header />
      <main className="main">
        {children ?? (
          <section className="section pt-60 pb-60">
            <div className="container">
              <h2 className="heading-36-medium">Page content goes here</h2>
              <p className="text-16 color-grey mt-15">
                This is the shared marketing layout — Header + main + Footer.
              </p>
            </div>
          </section>
        )}
      </main>
      <Footer />
    </>
  );
}

const meta: Meta<typeof MarketingLayout> = {
  title: "Templates/MarketingLayout",
  component: MarketingLayout,
  parameters: { layout: "fullscreen", nextjs: { appDirectory: true } },
  tags: ["autodocs"],
};
export default meta;
type Story = StoryObj<typeof MarketingLayout>;

export const Default: Story = {};
