"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useBookingStore, useHydrated } from "@/lib/booking/store";
import { bookingService } from "@/lib/api/booking.service";
import { paymentService } from "@/lib/api/payment.service";
import { ApiRequestError } from "@/lib/api/client";
import OrderSummary from "@/components/booking/OrderSummary";

type Method = "cash" | "card";

function money(amount: string, currency: string) {
  const symbol = currency === "USD" ? "$" : `${currency} `;
  return `${symbol}${Number(amount).toFixed(2)}`;
}

export default function BookingPaymentPage() {
  const router = useRouter();
  const quote = useBookingStore((s) => s.quote);
  const trip = useBookingStore((s) => s.trip);
  const contact = useBookingStore((s) => s.contact);
  const setReference = useBookingStore((s) => s.setReference);

  const [method, setMethod] = useState<Method>("cash");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const hydrated = useHydrated();

  useEffect(() => {
    if (hydrated && !quote) router.replace("/booking/vehicle");
  }, [hydrated, quote, router]);
  if (!hydrated || !quote) return null;

  const confirm = async () => {
    setSubmitting(true);
    setError("");
    try {
      // When booking for someone else, the passenger's name goes on the driver's
      // pickup sign and their phone into the notes (the booker stays the contact).
      const pickupSign = trip.forSomeoneElse && trip.passengerName ? trip.passengerName : trip.pickupSign;
      const notes = [
        trip.notes,
        trip.forSomeoneElse && trip.passengerPhone ? `Passenger phone: ${trip.passengerPhone}` : "",
      ].filter(Boolean).join(" — ");

      // 1. Create the booking from the signed quote token (server recomputes the fare).
      const booking = await bookingService.create({
        quote_token: quote.quote_token,
        passenger_count: trip.passengerCount,
        luggage_count: trip.luggageCount,
        flight_number: trip.flightNumber,
        pickup_sign: pickupSign,
        notes,
        guest_email: contact.email,
        guest_name: contact.name,
      });
      setReference(booking.reference);

      // 2. Settle it.
      if (method === "cash") {
        // Confirmed immediately — the driver collects the fare.
        await paymentService.payCash(booking.reference);
      } else {
        // Card: start a Stripe intent. When Stripe isn't configured the backend
        // returns 503 and the booking stays pending; still proceed.
        try {
          await paymentService.createIntent(booking.reference);
          // TODO: mount Stripe Elements and confirm the card with client_secret.
        } catch (e) {
          if (!(e instanceof ApiRequestError && e.status === 503)) throw e;
        }
      }

      router.push("/booking/confirmation");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong creating your booking.");
      setSubmitting(false);
    }
  };

  const methodBox = (m: Method, title: string, sub: string, disabled = false) => (
    <label
      style={{
        display: "block", border: `1px solid ${method === m ? "#0E0E0E" : "#e5e5e5"}`,
        borderRadius: 10, padding: "12px 16px", marginBottom: 10,
        cursor: disabled ? "not-allowed" : "pointer", opacity: disabled ? 0.55 : 1,
      }}
    >
      <input
        type="radio" name="method" style={{ marginRight: 8 }}
        checked={method === m} disabled={disabled}
        onChange={() => setMethod(m)}
      />
      <b>{title}</b>
      <div className="text-14 color-grey" style={{ marginLeft: 24 }}>{sub}</div>
    </label>
  );

  return (
    <section className="section">
      <div className="container-sub">
        <div className="box-row-tab mt-50">
          <div className="box-tab-left">
            <div className="box-content-detail">
              <h3 className="heading-24-medium color-text mb-20">Review &amp; confirm</h3>

        <div style={{ border: "1px solid #eee", borderRadius: 12, padding: 20, marginBottom: 24 }}>
          <div className="d-flex justify-content-between mb-10">
            <span className="text-16-medium">{quote.vehicle_name}</span>
            <span className="text-16-medium">{money(quote.total, quote.currency)}</span>
          </div>
          {quote.lines.map((l, i) => (
            <div key={i} className="d-flex justify-content-between text-14 color-grey">
              <span>{l.label}</span><span>{money(l.amount, quote.currency)}</span>
            </div>
          ))}
          <hr />
          <div className="d-flex justify-content-between heading-20-medium">
            <span>Total</span><span>{money(quote.total, quote.currency)}</span>
          </div>
        </div>

        <h5 className="text-16-medium mb-10">How would you like to pay?</h5>
        {methodBox("cash", "Cash — pay the driver", "Confirm now, pay in the vehicle. No card needed.")}
        {methodBox("card", "Pay by card", "Card payment is coming soon (Stripe not configured yet).", true)}

              {error && <p className="text-14" style={{ color: "#c0392b" }}>{error}</p>}
              <button className="btn btn-primary hover-up mt-10" onClick={confirm} disabled={submitting}>
                {submitting ? "Confirming…" : method === "cash" ? "Confirm booking (cash)" : "Continue to card"}
              </button>
            </div>
          </div>
          <OrderSummary />
        </div>
      </div>
    </section>
  );
}
