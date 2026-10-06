"use client";

import { useState } from "react";
import Link from "next/link";
import { enquiryService } from "@/lib/api/enquiry.service";

export default function ContactPage() {
  const [form, setForm] = useState({ name: "", email: "", phone: "", subject: "", message: "" });
  const [status, setStatus] = useState<"idle" | "sending" | "sent" | "error">("idle");
  const [error, setError] = useState("");

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!form.name.trim() || !form.email.includes("@") || form.message.trim().length < 10) {
      setError("Please enter your name, a valid email, and a message of at least 10 characters.");
      return;
    }
    setStatus("sending");
    try {
      await enquiryService.submit({
        name: form.name.trim(),
        email: form.email.trim(),
        phone: form.phone.trim() || undefined,
        subject: form.subject.trim() || undefined,
        message: form.message.trim(),
      });
      setStatus("sent");
      setForm({ name: "", email: "", phone: "", subject: "", message: "" });
    } catch (err) {
      setStatus("error");
      setError(err instanceof Error ? err.message : "Could not send your message. Please try again.");
    }
  };

  return (
    <>
      <div className="section pt-60 pb-60 bg-primary">
        <div className="container-sub">
          <h1 className="heading-44-medium color-white mb-5 wow fadeInDown">Contact Us</h1>
          <div className="box-breadcrumb wow fadeInUp">
            <ul>
              <li> <Link href="/">Home</Link></li>
              <li> <Link href="/services">Contact</Link></li>
            </ul>
          </div>
        </div>
      </div>
      <div className="section pt-60 pb-60">
        <div className="container-sub">
          <div className="row">
            <div className="col-lg-3 col-sm-6 mb-30">
              <div className="cardContact wow fadeInRight">
                <div className="cardImage mb-30"><img src="/assets/imgs/page/contact/new-york.png" alt="luxride" /></div>
                <div className="cardInfo">
                  <h6 className="heading-20-medium mb-10">New York Office</h6>
                  <p className="text-16 mb-20">PO Box 16122 Collins Street West Victoria 8007 Australia</p>
                  <p className="text-16 mb-20">+32 2 512 08 15</p>
                  <p className="text-16">newyork@luxride.com</p>
                </div>
              </div>
            </div>
            <div className="col-lg-3 col-sm-6 mb-30">
              <div className="cardContact wow fadeInRight">
                <div className="cardImage mb-30"><img src="/assets/imgs/page/contact/istabul.png" alt="luxride" /></div>
                <div className="cardInfo">
                  <h6 className="heading-20-medium mb-10">Istanbul Office</h6>
                  <p className="text-16 mb-20">PO Box 16122 Collins Street West Victoria 8007 Australia</p>
                  <p className="text-16 mb-20">+32 2 512 08 15</p>
                  <p className="text-16">istanbul@luxride.com</p>
                </div>
              </div>
            </div>
            <div className="col-lg-3 col-sm-6 mb-30">
              <div className="cardContact wow fadeInRight">
                <div className="cardImage mb-30"><img src="/assets/imgs/page/contact/paris.png" alt="luxride" /></div>
                <div className="cardInfo">
                  <h6 className="heading-20-medium mb-10">Paris Office</h6>
                  <p className="text-16 mb-20">PO Box 16122 Collins Street West Victoria 8007 Australia</p>
                  <p className="text-16 mb-20">+32 2 512 08 15</p>
                  <p className="text-16">paris@luxride.com</p>
                </div>
              </div>
            </div>
            <div className="col-lg-3 col-sm-6 mb-30">
              <div className="cardContact wow fadeInRight">
                <div className="cardImage mb-30"><img src="/assets/imgs/page/contact/london.png" alt="luxride" /></div>
                <div className="cardInfo">
                  <h6 className="heading-20-medium mb-10">London Office</h6>
                  <p className="text-16 mb-20">PO Box 16122 Collins Street West Victoria 8007 Australia</p>
                  <p className="text-16 mb-20">+32 2 512 08 15</p>
                  <p className="text-16">london@luxride.com</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div className="section wow fadeInDown">
        <iframe
          className="map-contact"
          src="https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3001155.6943615586!2d-78.01286281141591!3d42.728782799636924!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x4ccc4bf0f123a5a9%3A0xddcfc6c1de189567!2zVGnhu4N1IGJhbmcgTmV3IFlvcmssIEhvYSBL4buz!5e0!3m2!1svi!2s!4v1677510404076!5m2!1svi!2s"
          style={{ border: 0 }}
          allowFullScreen
          loading="lazy"
          referrerPolicy="no-referrer-when-downgrade"
        ></iframe>
      </div>
      <section className="section mt-120 mb-120">
        <div className="container-sub">
          <div className="mw-770">
            <h2 className="heading-44-medium mb-60 text-center wow fadeInDown">Leave us your info</h2>
            <div className="form-contact form-comment wow fadeInUp">
              {status === "sent" ? (
                <div className="box-info-book-border" style={{ textAlign: "center", padding: "36px 24px" }}>
                  <h5 className="heading-20-medium mb-10">Thanks — we&rsquo;ve got your message.</h5>
                  <p className="text-16 color-grey mb-20">Our team will get back to you shortly.</p>
                  <button className="btn btn-primary hover-up" onClick={() => setStatus("idle")}>Send another</button>
                </div>
              ) : (
              <form onSubmit={submit} noValidate>
                <div className="row">
                  <div className="col-lg-6 col-md-6">
                    <div className="form-group">
                      <label className="form-label" htmlFor="fullname">Full Name <span style={{ color: "#c0392b" }}>*</span></label>
                      <input className="form-control" id="fullname" type="text" value={form.name} onChange={set("name")} />
                    </div>
                  </div>
                  <div className="col-lg-6 col-md-6">
                    <div className="form-group">
                      <label className="form-label" htmlFor="email">Email <span style={{ color: "#c0392b" }}>*</span></label>
                      <input className="form-control" id="email" type="email" value={form.email} onChange={set("email")} />
                    </div>
                  </div>
                  <div className="col-lg-6 col-md-6">
                    <div className="form-group">
                      <label className="form-label" htmlFor="phone">Phone</label>
                      <input className="form-control" id="phone" type="tel" value={form.phone} onChange={set("phone")} />
                    </div>
                  </div>
                  <div className="col-lg-6 col-md-6">
                    <div className="form-group">
                      <label className="form-label" htmlFor="subject">Subject</label>
                      <input className="form-control" id="subject" type="text" value={form.subject} onChange={set("subject")} />
                    </div>
                  </div>
                  <div className="col-lg-12">
                    <div className="form-group">
                      <label className="form-label" htmlFor="message">Message <span style={{ color: "#c0392b" }}>*</span></label>
                      <textarea className="form-control" id="message" rows={5} value={form.message} onChange={set("message")}></textarea>
                    </div>
                  </div>
                  {error && (
                    <div className="col-lg-12"><p className="text-14" style={{ color: "#c0392b" }}>{error}</p></div>
                  )}
                  <div className="col-lg-12">
                    <button className="btn btn-primary" type="submit" disabled={status === "sending"}>
                      {status === "sending" ? "Sending…" : "Get In Touch"}
                      <svg className="icon-16 ml-5" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 19.5l15-15m0 0H8.25m11.25 0v11.25" />
                      </svg>
                    </button>
                  </div>
                </div>
              </form>
              )}
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
