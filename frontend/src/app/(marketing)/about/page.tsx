"use client";

import Link from "next/link";
import { Swiper, SwiperSlide } from "swiper/react";
import { Pagination } from "swiper/modules";
import "swiper/css/pagination";

const TESTIMONIALS = [
  {
    name: "Jonathan Miller",
    role: "Web Developer",
    quote:
      "I really can recommend this theme, because it’s coded very well and  it’s really easy to build your own website!",
  },
  {
    name: "Jonathan Miller",
    role: "Web Developer",
    quote:
      "I really can recommend this theme, because it’s coded very well and  it’s really easy to build your own website!",
  },
  {
    name: "Jonathan Miller",
    role: "Web Developer",
    quote:
      "I really can recommend this theme, because it’s coded very well and  it’s really easy to build your own website!",
  },
  {
    name: "Jonathan Miller",
    role: "Web Developer",
    quote:
      "I really can recommend this theme, because it’s coded very well and  it’s really easy to build your own website!",
  },
];

export default function AboutPage() {
  return (
    <>
      <section className="section bg-primary banner-about">
        <div className="container-sub">
          <div className="row">
            <div className="col-lg-5 col-md-12">
              <div className="padding-box">
                <h2 className="heading-44-medium color-white mb-5 wow fadeInDown">About Us</h2>
                <div className="box-breadcrumb wow fadeInLeft">
                  <ul>
                    <li> <Link href="/">Home</Link></li>
                    <li> <Link href="/services">About</Link></li>
                  </ul>
                </div>
                <div className="mt-60 wow fadeInUp">
                  <h2 className="heading-44-medium mb-30 color-white title-fleet">We reimagine the way the world moves for the better</h2>
                  <div className="content-single">
                    <p className="color-white">We offer luxury chauffeur driven airport transfers and pickups to London. Exceptional Safe, Meet and Greet. One hour of complimentary wait time and flight tracking. </p>
                    <ul className="list-ticks list-ticks-small">
                      <li className="text-16 mb-20 color-white">100% Luxurious Fleet</li>
                      <li className="text-16 mb-20 color-white">A Safe &amp; Secure Journey</li>
                      <li className="text-16 mb-20 color-white">Comfortable And Enjoyable</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div className="box-banner-right wow fadeInRight"></div>
      </section>

      <section className="section pt-120">
        <div className="container-sub">
          <div className="text-center">
            <h2 className="heading-44-medium wow fadeInRight">How It Works</h2>
          </div>
          <div className="box-list-how mt-90">
            <ul>
              <li className="has-arrow wow fadeInUp">
                <div className="cardWork">
                  <div className="cardImage"> <img src="/assets/imgs/page/homepage2/route.svg" alt="luxride" /></div>
                  <div className="cardTitle">
                    <h5 className="text-20-medium color-text">Create Your Route</h5>
                  </div>
                  <div className="cardDesc">
                    <p className="color-text text-16">Enter your pickup &amp; dropoff locations or the number of hours you wish to book a car and driver for</p>
                  </div>
                </div>
              </li>
              <li className="has-arrow wow fadeInUp">
                <div className="cardWork">
                  <div className="cardImage"> <img src="/assets/imgs/page/homepage2/vehicle.svg" alt="luxride" /></div>
                  <div className="cardTitle">
                    <h5 className="text-20-medium color-text">Create Your Route</h5>
                  </div>
                  <div className="cardDesc">
                    <p className="color-text text-16">Enter your pickup &amp; dropoff locations or the number of hours you wish to book a car and driver for</p>
                  </div>
                </div>
              </li>
              <li className="wow fadeInUp">
                <div className="cardWork">
                  <div className="cardImage"> <img src="/assets/imgs/page/homepage2/like.svg" alt="luxride" /></div>
                  <div className="cardTitle">
                    <h5 className="text-20-medium color-text">Create Your Route</h5>
                  </div>
                  <div className="cardDesc">
                    <p className="color-text text-16">Enter your pickup &amp; dropoff locations or the number of hours you wish to book a car and driver for</p>
                  </div>
                </div>
              </li>
            </ul>
          </div>
        </div>
      </section>

      <section className="section mt-90 bg-4 bg-your-trip">
        <div className="container-sub">
          <div className="box-the-trip">
            <h3 className="heading-44-medium mb-60 wow fadeInDown">Make Your Trip Your Way With Us</h3>
            <ul className="list-the-trip wow fadeInUp">
              <li>
                <div className="cardImage"> <img src="/assets/imgs/page/about/icon1.png" alt="luxride" /></div>
                <div className="cardInfo">
                  <h6 className="text-20-medium color-text">Safety First</h6>
                  <p className="text-16 color-text">Both you and your shipments will travel with professional drivers. Always with the highest quality standards.</p>
                </div>
              </li>
              <li>
                <div className="cardImage"> <img src="/assets/imgs/page/about/icon2.png" alt="luxride" /></div>
                <div className="cardInfo">
                  <h6 className="text-20-medium color-text">Prices With No Surprises</h6>
                  <p className="text-16 color-text">Both you and your shipments will travel with professional drivers. Always with the highest quality standards.</p>
                </div>
              </li>
              <li>
                <div className="cardImage"> <img src="/assets/imgs/page/about/icon3.png" alt="luxride" /></div>
                <div className="cardInfo">
                  <h6 className="text-20-medium color-text">Private Travel Solutions</h6>
                  <p className="text-16 color-text">Both you and your shipments will travel with professional drivers. Always with the highest quality standards.</p>
                </div>
              </li>
            </ul>
          </div>
        </div>
        <div className="box-the-trip-right wow fadeInRight"> </div>
      </section>

      <section className="section pt-65 pb-35 border-bottom">
        <div className="container-sub">
          <div className="row align-items-center">
            <div className="col-xl-3 col-lg-4 mb-30">
              <h3 className="color-primary wow fadeInDown">The partners who sell<br className="d-none d-lg-block" />our products</h3>
            </div>
            <div className="col-xl-9 col-lg-8 mb-30">
              <ul className="list-logos d-flex align-item-center wow fadeInRight">
                <li><img src="/assets/imgs/slider/logo/air.svg" alt="luxride" /></li>
                <li><img src="/assets/imgs/slider/logo/eb.svg" alt="luxride" /></li>
                <li><img src="/assets/imgs/slider/logo/nba.svg" alt="luxride" /></li>
                <li><img src="/assets/imgs/slider/logo/nla.svg" alt="luxride" /></li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      <section className="section pt-120">
        <div className="container-sub">
          <div className="row align-items-center">
            <div className="col-lg-5 mb-30">
              <div className="box-image-showcase wow fadeInLeft"><img src="/assets/imgs/page/homepage2/showcase.png" alt="luxride" />
                <div className="box-btn-play-video"><a className="btn btn-white" href="#"> <img className="align-middle mr-10" src="/assets/imgs/page/homepage2/play.svg" alt="luxride" />Play Video</a></div>
              </div>
            </div>
            <div className="col-lg-7 mb-30">
              <div className="box-region-right">
                <h2 className="heading-44-medium color-text mb-30 wow fadeInRight">Showcase some impressive numbers.</h2>
                <p className="text-16 color-text mb-30 wow fadeInDown">Lorem ipsum dolor sit amet, consectetur adipiscing elit. Suspendisse varius enim in eros elementum tristique.</p>
                <div className="row align-items-center">
                  <div className="col-sm-4 col-6 mb-30">
                    <div className="box-number-info wow fadeInRight"><span className="text-20-medium text-number">285</span><span className="text-14 text-number-info">Vehicles </span></div>
                  </div>
                  <div className="col-sm-4 col-6 mb-30">
                    <div className="box-number-info wow fadeInRight"><span className="text-20-medium text-number">97</span><span className="text-14 text-number-info">Awards</span></div>
                  </div>
                  <div className="col-sm-4 col-12 mb-30">
                    <div className="box-number-info wow fadeInRight"><span className="text-20-medium text-number">13K</span><span className="text-14 text-number-info">Happy Customer </span></div>
                  </div>
                </div><a className="btn btn-secondary wow fadeInDown">Learn More
                  <svg className="icon-16 ml-5" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 19.5l15-15m0 0H8.25m11.25 0v11.25"></path>
                  </svg></a>
              </div>
            </div>
          </div>
        </div>
      </section>

      <div className="mt-90"></div>

      <section className="section pt-130 pb-130 bg-primary box-testimonials">
        <div className="container-sub">
          <div className="row">
            <div className="col-lg-5 col-md-6 mb-30">
              <div className="box-swiper">
                <Swiper
                  className="swiper-container swiper-group-testimonials pb-50"
                  modules={[Pagination]}
                  pagination={{ el: ".swiper-pagination-testimonials" }}
                >
                  {TESTIMONIALS.map((t, i) => (
                    <SwiperSlide key={i}>
                      <div className="cardQuote wow fadeInRight">
                        <div className="box-quote">
                          <div className="icon-quote"> </div>
                          <div className="info-quote">
                            <h5 className="color-white text-18-medium">{t.name}</h5>
                            <p className="color-white text-14">{t.role}</p>
                          </div>
                        </div>
                        <div className="content-quote">
                          {" "}{t.quote}</div>
                      </div>
                    </SwiperSlide>
                  ))}
                  <div className="box-pagination-testimonials mt-40 wow fadeInRight"> <span className="firstNumber"></span><span className="lastNumber"></span>
                    <div className="swiper-pagination swiper-pagination-testimonials"></div>
                  </div>
                </Swiper>
              </div>
            </div>
            <div className="col-lg-7 col-md-6 mb-30 text-lg-end text-center d-none d-md-block">
              <div className="box-video wow fadeInRight"> <a className="btn btn-play popup-youtube hover-up" href="https://www.youtube.com/watch?v=sVPYIRF9RCQ"></a><img src="/assets/imgs/page/homepage1/img-video.png" alt="luxride" /></div>
            </div>
          </div>
        </div>
      </section>

      <section className="section pt-120 pb-120">
        <div className="container-sub">
          <div className="row align-items-center">
            <div className="col-lg-6 mb-30">
              <div className="box-image-showcase wow fadeInLeft">
                <div className="box-image-top text-center text-lg-start"><img src="/assets/imgs/page/homepage3/img1.png" alt="luxride" /></div>
                <div className="box-image-bottom text-end text-sm-center text-lg-end"><img src="/assets/imgs/page/homepage3/img3.png" alt="luxride" /><img src="/assets/imgs/page/homepage3/img2.png" alt="luxride" /></div>
              </div>
            </div>
            <div className="col-lg-6 mb-30">
              <div className="box-region-right wow fadeInRight">
                <h2 className="heading-44-medium color-text mb-30">Reliability, <br className="d-none d-lg-block" />worldwide</h2>
                <p className="text-16 color-text mb-20">Aliquam erat volutpat. Integer malesuada turpis id fringilla suscipit. </p>
                <ul className="list-ticks">
                  <li>Affordable</li>
                  <li>Punctual</li>
                  <li>Professional</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="section mt-50 bg-download-3 bg-secondary">
        <div className="container-sub">
          <h2 className="heading-44-medium color-white mb-20 wow fadeInDown">Download the app</h2>
          <p className="color-white text-16 mb-60 wow fadeInUp">Have a personal driver at your fingertips no matter where you <br className="d-none d-md-block" />are with our easy-to-use smartphone app.</p>
          <div className="box-button-download"> <a className="btn btn-download mr-15 hover-up wow fadeInRight" href="#">
              <div className="inner-download">
                <div className="icon-download"> <img src="/assets/imgs/template/icons/apple-icon.svg" alt="luxride" /></div>
                <div className="info-download"> <span className="text-download-top">Download on the</span><span className="text-14-medium">Apple Store</span></div>
              </div></a><a className="btn btn-download hover-up wow fadeInRight" href="#">
              <div className="inner-download">
                <div className="icon-download"> <img src="/assets/imgs/template/icons/google-icon.svg" alt="luxride" /></div>
                <div className="info-download"> <span className="text-download-top">Download on the</span><span className="text-14-medium">Apple Store</span></div>
              </div></a></div>
        </div>
      </section>
    </>
  );
}
