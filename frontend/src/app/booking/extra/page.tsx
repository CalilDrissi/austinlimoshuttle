"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useBookingStore, useHydrated } from "@/lib/booking/store";
import OrderSummary from "@/components/booking/OrderSummary";

export default function BookingExtraPage() {
  const router = useRouter();
  const quote = useBookingStore((s) => s.quote);
  const trip = useBookingStore((s) => s.trip);
  const setTrip = useBookingStore((s) => s.setTrip);
  const hydrated = useHydrated();

  useEffect(() => {
    if (hydrated && !quote) router.replace("/booking/vehicle");
  }, [hydrated, quote, router]);
  if (!hydrated || !quote) return null;

  const next = () => router.push("/booking/passenger");

  return (
    <section className="section">
      <div className="container-sub">
        <div className="box-row-tab mt-50">
          <div className="box-tab-left">
            <div className="box-content-detail">
              <h3 className="heading-24-medium color-text mb-30">Trip details</h3>

        <div className="row">
          <div className="col-6 mb-20">
            <label className="text-14 color-grey">Passengers</label>
            <input type="number" min={1} className="form-control" value={trip.passengerCount}
              onChange={(e) => setTrip({ passengerCount: Math.max(1, Number(e.target.value)) })} />
          </div>
          <div className="col-6 mb-20">
            <label className="text-14 color-grey">Luggage</label>
            <input type="number" min={0} className="form-control" value={trip.luggageCount}
              onChange={(e) => setTrip({ luggageCount: Math.max(0, Number(e.target.value)) })} />
          </div>
          <div className="col-6 mb-20">
            <label className="text-14 color-grey">Flight number (optional)</label>
            <input type="text" className="form-control" value={trip.flightNumber ?? ""}
              onChange={(e) => setTrip({ flightNumber: e.target.value })} />
          </div>
          <div className="col-6 mb-20">
            <label className="text-14 color-grey">Name on pickup sign (optional)</label>
            <input type="text" className="form-control" value={trip.pickupSign ?? ""}
              onChange={(e) => setTrip({ pickupSign: e.target.value })} />
          </div>
          <div className="col-12 mb-20">
            <label className="text-14 color-grey">Notes for the driver (optional)</label>
            <textarea className="form-control" rows={3} value={trip.notes ?? ""}
              onChange={(e) => setTrip({ notes: e.target.value })} />
          </div>
        </div>

              <button className="btn btn-primary hover-up mt-10" onClick={next}>Continue</button>
            </div>
          </div>
          <OrderSummary />
        </div>
      </div>
    </section>
  );
}
