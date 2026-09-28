"use client";

import { Swiper, SwiperSlide } from "swiper/react";
import { Navigation, Pagination, Autoplay } from "swiper/modules";
import "swiper/css/navigation";
import "swiper/css/pagination";
import BookingSearchWidget from "@/components/booking/BookingSearchWidget";

const SLIDES = [
  { bg: "/assets/imgs/page/homepage1/banner.png" },
  { bg: "/assets/imgs/page/homepage1/banner2.png" },
  { bg: "/assets/imgs/page/homepage1/banner3.png" },
  { bg: "/assets/imgs/page/homepage1/banner4.png" },
  { bg: "/assets/imgs/page/homepage1/banner5.png" },
];

export default function HeroSection() {
  return (
    <section className="section banner-home1">
      <div className="box-swiper">
        <Swiper
          className="swiper-container swiper-banner-1 pb-0"
          modules={[Navigation, Pagination, Autoplay]}
          loop
          autoplay={{ delay: 5000, disableOnInteraction: false }}
          navigation={{
            prevEl: ".swiper-button-prev-banner",
            nextEl: ".swiper-button-next-banner",
          }}
          pagination={{ el: ".swiper-pagination-banner", type: "fraction" }}
        >
          {SLIDES.map((slide, i) => (
            <SwiperSlide key={i}>
              <div className="box-cover-image" style={{ backgroundImage: `url(${slide.bg})` }} />
              <div className="box-banner-info">
                <p className="text-16 color-white">Where Would You Like To Go?</p>
                <h2 className="heading-52-medium color-white">
                  Your Personal <br className="d-none d-lg-block" />
                  Chauffeur Services
                </h2>
              </div>
            </SwiperSlide>
          ))}
        </Swiper>

        <div className="box-pagination-button">
          <div className="swiper-button-prev swiper-button-prev-banner" />
          <div className="swiper-button-next swiper-button-next-banner" />
          <div className="swiper-pagination swiper-pagination-banner swiper-pagination-fraction" />
        </div>
      </div>

      <BookingSearchWidget />
    </section>
  );
}
