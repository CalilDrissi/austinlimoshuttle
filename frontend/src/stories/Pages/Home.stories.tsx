import type { Meta, StoryObj } from "@storybook/react";
import HeroSection from "@/components/home/HeroSection";
import Header from "@/components/layout/Header";
import Footer from "@/components/layout/Footer";

function HomePage() {
  return (
    <>
      <Header />
      <main className="main">
        <HeroSection />
      </main>
      <Footer />
    </>
  );
}

const meta: Meta<typeof HomePage> = {
  title: "Pages/Home",
  component: HomePage,
  parameters: { layout: "fullscreen", nextjs: { appDirectory: true } },
};
export default meta;
type Story = StoryObj<typeof HomePage>;

export const Default: Story = {};
