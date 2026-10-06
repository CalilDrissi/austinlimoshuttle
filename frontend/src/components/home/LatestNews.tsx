const NEWS = [
  {
    day: "14.",
    date: "Jun, 2022",
    img: "/assets/imgs/page/homepage1/news1.png",
    tag: "Travel",
    title: "3 hidden-gem destinations for your wish list",
  },
  {
    day: "18.",
    date: "Jun, 2022",
    img: "/assets/imgs/page/homepage1/news2.png",
    tag: "Culture",
    title: "Explore the big things happening in Dallas",
  },
  {
    day: "20.",
    date: "Jun, 2022",
    img: "/assets/imgs/page/homepage1/news3.png",
    tag: "News",
    title: "LA’s worst traffic areas and how to avoid them",
  },
];

export default function LatestNews() {
  return (
    <section className="section pt-120 pb-90 bg-primary">
      <div className="container-sub">
        <div className="row align-items-center">
          <div className="col-lg-6 col-7">
            <h2 className="heading-44-medium color-white wow fadeInRight">Latest From News</h2>
          </div>
          <div className="col-lg-6 col-5 text-end">
            <a className="text-16-medium color-white hover-up d-inline-block wow fadeInUp" href="#">
              More News
              <svg
                className="icon-16 color-white"
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
            </a>
          </div>
        </div>
        <div className="row mt-50">
          {NEWS.map((item, i) => (
            <div className="col-lg-4" key={i}>
              <div className="cardNews wow fadeInUp">
                <a href="#">
                  <div className="cardImage">
                    <div className="datePost">
                      <div className="heading-52-medium color-white">{item.day}</div>
                      <p className="text-14 color-white">{item.date}</p>
                    </div>
                    <img src={item.img} alt="luxride" />
                  </div>
                </a>
                <div className="cardInfo">
                  <div className="tags mb-10">
                    <a href="#">{item.tag}</a>
                  </div>
                  <a className="color-white" href="#">
                    <h3 className="text-20-medium color-white mb-20">{item.title}</h3>
                  </a>
                  <a className="cardLink btn btn-arrow-up" href="#">
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
                  </a>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
