"use client";

import { Swiper, SwiperSlide } from "swiper/react";
import { Pagination } from "swiper/modules";
import "swiper/css/pagination";

const QUOTES = [0, 1, 2, 3];

export default function Testimonials() {
  return (
    <section className="section pt-130 pb-130 bg-primary box-testimonials">
      <div className="container-sub">
        <div className="row">
          <div className="col-lg-5 col-md-6 mb-30">
            <div className="box-swiper">
              <Swiper
                className="swiper-container swiper-group-testimonials pb-50"
                modules={[Pagination]}
                loop
                pagination={{
                  el: ".swiper-pagination-testimonials",
                  clickable: true,
                }}
              >
                {QUOTES.map((i) => (
                  <SwiperSlide key={i}>
                    <div className="cardQuote wow fadeInRight">
                      <div className="box-quote">
                        <div className="icon-quote"> </div>
                        <div className="info-quote">
                          <h5 className="color-white text-18-medium">Jonathan Miller</h5>
                          <p className="color-white text-14">Web Developer</p>
                        </div>
                      </div>
                      <div className="content-quote">
                        I really can recommend this theme, because it{"’"}s coded very well and it
                        {"’"}s really easy to build your own website!
                      </div>
                    </div>
                  </SwiperSlide>
                ))}
              </Swiper>
              <div className="box-pagination-testimonials mt-40 wow fadeInRight">
                <span className="firstNumber">02</span>
                <span className="lastNumber">04</span>
                <div className="swiper-pagination swiper-pagination-testimonials"></div>
              </div>
            </div>
          </div>
          <div className="col-lg-7 col-md-6 mb-30 text-lg-end text-center d-none d-md-block">
            <div className="box-video wow fadeInRight">
              <a
                className="btn btn-play popup-youtube hover-up"
                href="https://www.youtube.com/watch?v=sVPYIRF9RCQ"
              ></a>
              <img src="/assets/imgs/page/homepage1/img-video.png" alt="luxride" />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
