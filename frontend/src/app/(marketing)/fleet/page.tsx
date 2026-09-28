import Link from "next/link";

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
    title: "SUV Class",
    desc: "Mercedes-Benz V-Class, Chevrolet Suburban, Cadillac Escalade, Toyota Alphard or similar",
    img: "/assets/imgs/page/fleet/suv-class.png",
  },
  {
    title: "Luxury Class",
    desc: "Mercedes-Benz V-Class, Chevrolet Suburban, Cadillac Escalade, Toyota Alphard or similar",
    img: "/assets/imgs/page/homepage1/e-class.png",
  },
  {
    title: "Electric Class",
    desc: "Mercedes-Benz V-Class, Chevrolet Suburban, Cadillac Escalade, Toyota Alphard or similar",
    img: "/assets/imgs/page/homepage1/v-class.png",
  },
];

export default function FleetPage() {
  return (
    <>
      <div className="section pt-60 pb-60 bg-primary">
        <div className="container-sub">
          <h1 className="heading-44-medium color-white mb-5 wow fadeInDown">Our Fleet</h1>
          <div className="box-breadcrumb wow fadeInUp">
            <ul>
              <li> <Link href="/">Home</Link></li>
              <li> <Link href="/fleet">Our Fleet</Link></li>
            </ul>
          </div>
        </div>
      </div>
      <section className="section pt-60 bg-white latest-new-white">
        <div className="container-sub">
          <div className="row align-items-center">
            <div className="col-lg-6 col-md-6 col-sm-6 text-center text-sm-start mb-30">
              <h2 className="heading-24-medium wow fadeInLeft">Choose Your Fleet</h2>
            </div>
            <div className="col-lg-6 col-md-6 col-sm-6 text-center text-sm-end mb-30 wow fadeInDown">
              <div className="dropdown dropdown-menu-box">
                <a className="dropdown-toggle" id="dropdownMenuButton1" href="#" data-bs-toggle="dropdown" aria-expanded="false">Vehicle Type</a>
                <ul className="dropdown-menu" aria-labelledby="dropdownMenuButton1">
                  <li><a className="dropdown-item" href="#">Hatchback</a></li>
                  <li><a className="dropdown-item" href="#">Sedan</a></li>
                  <li> <a className="dropdown-item" href="#">SUV</a></li>
                  <li> <a className="dropdown-item" href="#">Crossover</a></li>
                  <li> <a className="dropdown-item" href="#">Sports Car</a></li>
                  <li> <a className="dropdown-item" href="#">Minivan</a></li>
                </ul>
              </div>
              <div className="dropdown dropdown-menu-box">
                <a className="dropdown-toggle" id="dropdownMenuButton2" href="#" data-bs-toggle="dropdown" aria-expanded="false">Vehicle Make</a>
                <ul className="dropdown-menu" aria-labelledby="dropdownMenuButton2">
                  <li><a className="dropdown-item" href="#">Mercedes-Benz</a></li>
                  <li><a className="dropdown-item" href="#">Audi</a></li>
                  <li> <a className="dropdown-item" href="#">Hyundai</a></li>
                  <li> <a className="dropdown-item" href="#">Honda</a></li>
                  <li> <a className="dropdown-item" href="#">Nissan</a></li>
                  <li> <a className="dropdown-item" href="#">Toyota</a></li>
                  <li> <a className="dropdown-item" href="#">Volkswagen</a></li>
                  <li> <a className="dropdown-item" href="#">Subaru</a></li>
                  <li> <a className="dropdown-item" href="#">Lamborghini</a></li>
                  <li> <a className="dropdown-item" href="#">Lincoln</a></li>
                  <li> <a className="dropdown-item" href="#">Bentley</a></li>
                  <li> <a className="dropdown-item" href="#">Chevrolet</a></li>
                  <li> <a className="dropdown-item" href="#">Ford</a></li>
                  <li> <a className="dropdown-item" href="#">Volvo</a></li>
                  <li> <a className="dropdown-item" href="#">GMC</a></li>
                </ul>
              </div>
            </div>
          </div>
          <div className="row mt-30">
            {FLEET.map((car, i) => (
              <div className="col-lg-4 mb-30" key={i}>
                <div className="cardFleet wow fadeInDown">
                  <div className="cardInfo">
                    <Link href="/fleet">
                      <h3 className="text-20-medium color-text mb-10">{car.title}</h3>
                    </Link>
                    <p className="text-14 color-text mb-30">{car.desc}</p>
                  </div>
                  <div className="cardImage mb-30">
                    <Link href="/fleet"><img src={car.img} alt="Luxride" /></Link>
                  </div>
                  <div className="cardInfoBottom">
                    <div className="passenger"><span className="icon-circle icon-passenger"></span><span className="text-14">Passengers<span>4</span></span></div>
                    <div className="luggage"><span className="icon-circle icon-luggage"></span><span className="text-14">Luggage<span>2</span></span></div>
                  </div>
                </div>
              </div>
            ))}
          </div>
          <div className="text-center mt-40 mb-120">
            <nav className="box-pagination">
              <ul className="pagination">
                <li className="page-item"><a className="page-link page-prev" href="#">
                    <svg fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
                    </svg></a></li>
                <li className="page-item"><a className="page-link" href="#">1</a></li>
                <li className="page-item"><a className="page-link active" href="#">2</a></li>
                <li className="page-item"><a className="page-link" href="#">3</a></li>
                <li className="page-item"><a className="page-link" href="#">...</a></li>
                <li className="page-item"><a className="page-link" href="#">10</a></li>
                <li className="page-item"><a className="page-link page-next" href="#">
                    <svg fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
                    </svg></a></li>
              </ul>
            </nav>
          </div>
        </div>
      </section>
    </>
  );
}
