"use client";

import Link from "next/link";
import { Swiper, SwiperSlide } from "swiper/react";
import { Navigation } from "swiper/modules";
import "swiper/css/navigation";

const FLEET = [
  {
    title: "Business Class",
    desc: "Mercedes-Benz E-Class, BMW 5 Series, Cadillac XTS or similar",
    img: "/assets/imgs/page/homepage1/e-class.png",
  },
  {
    title: "First Class",
    desc: "Mercedes-Benz EQS, BMW 7 Series, Audi A8 or similar",
    img: "/assets/imgs/page/homepage1/eqs.png",
  },
  {
    title: "Business Van/SUV",
    desc: "Mercedes-Benz V-Class, Chevrolet Suburban, Cadillac Escalade, Toyota Alphard or similar",
    img: "/assets/imgs/page/homepage1/suv.png",
  },
  {
    title: "Limousine",
    desc: "Lincoln Stretch Limousine, Chrysler 300 Limousine or similar",
    img: "/assets/imgs/page/homepage1/v-class.png",
  },
];

export default function OurFleet() {
  return (
    <section className="section pt-120 pb-120 bg-our-fleet">
      <div className="container-sub">
        <div className="row align-items-center">
          <div className="col-lg-6 col-7">
            <h2 className="heading-44-medium title-fleet wow fadeInDown">Our Fleet</h2>
          </div>
          <div className="col-lg-6 col-5 text-end">
            <Link className="text-16-medium color-primary wow fadeInDown" href="/fleet">
              More Fleet
              <svg
                className="icon-16"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                viewBox="0 0 24 24"
                xmlns="http://www.w3.org/2000/svg"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M4.5 19.5l15-15m0 0H8.25m11.25 0v11.25"
                />
              </svg>
            </Link>
          </div>
        </div>
      </div>
      <div className="box-slide-fleet mt-50">
        <div className="box-swiper">
          <Swiper
            className="swiper-container swiper-group-4-fleet pb-0"
            modules={[Navigation]}
            spaceBetween={30}
            navigation={{
              prevEl: ".swiper-button-prev-fleet",
              nextEl: ".swiper-button-next-fleet",
            }}
            breakpoints={{
              0: { slidesPerView: 1 },
              576: { slidesPerView: 2 },
              768: { slidesPerView: 3 },
              1200: { slidesPerView: 3 },
            }}
          >
            {FLEET.map((car, i) => (
              <SwiperSlide key={i}>
                <div className="cardFleet wow fadeInDown">
                  <div className="cardInfo">
                    <Link href="/fleet">
                      <h3 className="text-20-medium color-text mb-10">{car.title}</h3>
                    </Link>
                    <p className="text-14 color-text mb-30">{car.desc}</p>
                  </div>
                  <div className="cardImage mb-30">
                    <Link href="/fleet">
                      <img src={car.img} alt="Luxride" />
                    </Link>
                  </div>
                  <div className="cardInfoBottom">
                    <div className="passenger">
                      <span className="icon-circle icon-passenger"></span>
                      <span className="text-14">
                        Passengers<span>4</span>
                      </span>
                    </div>
                    <div className="luggage">
                      <span className="icon-circle icon-luggage"></span>
                      <span className="text-14">
                        Luggage<span>2</span>
                      </span>
                    </div>
                  </div>
                </div>
              </SwiperSlide>
            ))}
          </Swiper>
          <div className="box-pagination-fleet">
            <div className="swiper-button-prev swiper-button-prev-fleet">
              <svg
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                viewBox="0 0 24 24"
                xmlns="http://www.w3.org/2000/svg"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18"
                />
              </svg>
            </div>
            <div className="swiper-button-next swiper-button-next-fleet">
              <svg
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                viewBox="0 0 24 24"
                xmlns="http://www.w3.org/2000/svg"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3"
                />
              </svg>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
