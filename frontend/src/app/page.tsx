import Header from "@/components/layout/Header";
import Footer from "@/components/layout/Footer";
import HeroSection from "@/components/home/HeroSection";
import PartnersStrip from "@/components/home/PartnersStrip";
import OurFleet from "@/components/home/OurFleet";
import HowItWorks from "@/components/home/HowItWorks";
import TripYourWay from "@/components/home/TripYourWay";
import Showcase from "@/components/home/Showcase";
import OurService from "@/components/home/OurService";
import Testimonials from "@/components/home/Testimonials";
import Region from "@/components/home/Region";
import LatestNews from "@/components/home/LatestNews";
import Faqs from "@/components/home/Faqs";

export default function HomePage() {
  return (
    <>
      <Header />
      <main className="main">
        <HeroSection />
        <PartnersStrip />
        <OurFleet />
        <HowItWorks />
        <TripYourWay />
        <Showcase />
        <OurService />
        <Testimonials />
        <Region />
        <LatestNews />
        <Faqs />
      </main>
      <Footer />
    </>
  );
}
