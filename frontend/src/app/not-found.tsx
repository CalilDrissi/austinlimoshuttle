import Link from "next/link";
export default function NotFound() {
  return (
    <section className="section pt-60 pb-60">
      <div className="container text-center">
        <h2 className="heading-52-medium color-primary mb-20">404</h2>
        <p className="text-16 color-grey mb-30">Page not found.</p>
        <Link className="btn btn-primary hover-up" href="/">Back to Home</Link>
      </div>
    </section>
  );
}
