"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { API_BASE_URL } from "@/lib/api/config";
import { bookingService } from "@/lib/api/booking.service";
import type { BookingAmendRequest } from "@/lib/api/booking.service";
import { authService } from "@/lib/api/auth.service";
import { cardsService } from "@/lib/api/cards.service";
import { useAuth, useRefreshAuth } from "@/hooks/useAuth";
import type { Booking } from "@/types/api";

type Tab = "overview" | "bookings" | "cards" | "profile";

function money(a: string, c: string) {
  return `${c === "USD" ? "$" : c + " "}${Number(a).toFixed(2)}`;
}
function when(iso: string) {
  return new Date(iso).toLocaleString("en-US", { weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}
function isUpcoming(b: Booking) {
  return b.status !== "cancelled" && b.status !== "completed" && new Date(b.pickup_at) > new Date();
}

function RideCard({ b, onCancel, onAmend, userPhone }: {
  b: Booking;
  onCancel: (ref: string) => void;
  onAmend: (ref: string, changes: BookingAmendRequest) => Promise<void>;
  userPhone: string;
}) {
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");
  const [f, setF] = useState({
    passenger_count: b.passenger_count,
    luggage_count: b.luggage_count,
    flight_number: b.flight_number || "",
    pickup_sign: b.pickup_sign || "",
    notes: b.notes || "",
    phone: userPhone || "",
  });

  const save = async () => {
    setSaving(true); setErr("");
    try {
      await onAmend(b.reference, {
        passenger_count: f.passenger_count,
        luggage_count: f.luggage_count,
        flight_number: f.flight_number.trim(),
        pickup_sign: f.pickup_sign.trim(),
        notes: f.notes.trim(),
        phone: f.phone.trim(),
      });
      setEditing(false);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Could not save your changes.");
    }
    setSaving(false);
  };

  return (
    <div className="mm-ride">
      <div className="mm-ride-top">
        <div>
          <div className="route">{b.pickup_address} → {b.dropoff_address || "Hourly hire"}</div>
          <div className="meta">{when(b.pickup_at)} · {b.vehicle_name} · {money(b.total, b.currency)} · Ref {b.reference}</div>
          <div className="meta">Passengers {b.passenger_count} · Luggage {b.luggage_count}{b.flight_number ? ` · Flight ${b.flight_number}` : ""}</div>
        </div>
        <span className={`mm-badge ${b.status}`}>{b.status_display}</span>
      </div>

      {editing && (
        <div className="row" style={{ marginTop: 14 }}>
          <div className="col-6 mb-15"><label className="text-14 color-grey">Passengers</label><input type="number" min={1} className="form-control" value={f.passenger_count} onChange={(e) => setF({ ...f, passenger_count: Math.max(1, Number(e.target.value)) })} /></div>
          <div className="col-6 mb-15"><label className="text-14 color-grey">Luggage</label><input type="number" min={0} className="form-control" value={f.luggage_count} onChange={(e) => setF({ ...f, luggage_count: Math.max(0, Number(e.target.value)) })} /></div>
          <div className="col-6 mb-15"><label className="text-14 color-grey">Flight number</label><input className="form-control" value={f.flight_number} onChange={(e) => setF({ ...f, flight_number: e.target.value })} /></div>
          <div className="col-6 mb-15"><label className="text-14 color-grey">Contact phone</label><input type="tel" className="form-control" value={f.phone} onChange={(e) => setF({ ...f, phone: e.target.value })} /></div>
          <div className="col-12 mb-15"><label className="text-14 color-grey">Name on pickup sign</label><input className="form-control" value={f.pickup_sign} onChange={(e) => setF({ ...f, pickup_sign: e.target.value })} /></div>
          <div className="col-12 mb-15"><label className="text-14 color-grey">Notes for the driver</label><textarea className="form-control" rows={2} value={f.notes} onChange={(e) => setF({ ...f, notes: e.target.value })} /></div>
          {err && <div className="col-12"><p className="text-14" style={{ color: "#c0392b" }}>{err}</p></div>}
          <div className="col-12" style={{ display: "flex", gap: 8 }}>
            <button className="btn btn-primary btn-sm hover-up" onClick={save} disabled={saving}>{saving ? "Saving…" : "Save changes"}</button>
            <button className="btn btn-border btn-sm hover-up" onClick={() => setEditing(false)}>Cancel</button>
          </div>
        </div>
      )}

      <div className="mm-ride-actions">
        <a className="btn btn-border btn-sm hover-up" href={`${API_BASE_URL}/bookings/${b.reference}/receipt/`} target="_blank" rel="noopener noreferrer">Receipt PDF</a>
        {b.is_amendable && !editing && (
          <button className="btn btn-border btn-sm hover-up" onClick={() => setEditing(true)}>Edit details</button>
        )}
        {isUpcoming(b) && (
          <button className="btn btn-border btn-sm hover-up" style={{ color: "#c0392b" }} onClick={() => onCancel(b.reference)}>Cancel</button>
        )}
      </div>
      {!b.is_amendable && isUpcoming(b) && (
        <div className="meta" style={{ marginTop: 6, color: "#9aa1ac" }}>Online changes are closed for this trip — please contact us to make changes.</div>
      )}
    </div>
  );
}

export default function AccountDashboard() {
  const router = useRouter();
  const qc = useQueryClient();
  const { user, isLoading } = useAuth();
  const refreshAuth = useRefreshAuth();
  const [tab, setTab] = useState<Tab>("overview");
  const [pf, setPf] = useState({ first_name: "", last_name: "", phone: "" });
  const [pfMsg, setPfMsg] = useState("");
  const [pfSaving, setPfSaving] = useState(false);

  useEffect(() => {
    if (!isLoading && !user) router.replace("/login?next=/account");
  }, [isLoading, user, router]);

  useEffect(() => {
    if (user) setPf({ first_name: user.first_name || "", last_name: user.last_name || "", phone: user.phone || "" });
  }, [user]);

  const saveProfile = async () => {
    setPfSaving(true);
    setPfMsg("");
    try {
      await authService.updateProfile(pf);
      await refreshAuth();
      setPfMsg("Saved.");
    } catch (e) {
      setPfMsg(e instanceof Error ? e.message : "Could not save.");
    }
    setPfSaving(false);
  };

  const { data: bookings = [], isLoading: loadingBookings } = useQuery({
    queryKey: ["my-bookings"],
    enabled: !!user,
    queryFn: () => bookingService.mine(),
  });

  const { data: cards = [], isLoading: loadingCards } = useQuery({
    queryKey: ["my-cards"],
    enabled: !!user,
    queryFn: () => cardsService.list(),
  });

  const removeCard = async (id: number) => {
    if (!confirm("Remove this card?")) return;
    try {
      await cardsService.remove(id);
      qc.invalidateQueries({ queryKey: ["my-cards"] });
    } catch (e) {
      alert(e instanceof Error ? e.message : "Could not remove the card.");
    }
  };

  const cancel = async (ref: string) => {
    if (!confirm("Cancel this booking?")) return;
    try {
      await bookingService.cancel(ref);
      qc.invalidateQueries({ queryKey: ["my-bookings"] });
    } catch (e) {
      alert(e instanceof Error ? e.message : "Could not cancel.");
    }
  };

  const amend = async (ref: string, changes: BookingAmendRequest) => {
    await bookingService.amend(ref, changes);
    qc.invalidateQueries({ queryKey: ["my-bookings"] });
    await refreshAuth(); // the contact phone may have changed on the account
  };

  const logout = async () => {
    await authService.logout();
    await refreshAuth();
    router.push("/");
  };

  if (isLoading || !user) return null;

  const upcoming = bookings.filter(isUpcoming).sort((a, b) => +new Date(a.pickup_at) - +new Date(b.pickup_at));
  const past = bookings.filter((b) => !isUpcoming(b));
  const initials = (user.first_name?.[0] || user.email[0] || "?").toUpperCase();

  const navBtn = (id: Tab, label: string) => (
    <button className={tab === id ? "on" : ""} onClick={() => setTab(id)}>{label}</button>
  );

  return (
    <section className="section pt-60 pb-80">
      <div className="container">
        <h2 className="heading-36-medium mb-30">My account</h2>
        <div className="mm-acct">
          <aside className="mm-acct-side">
            <div className="mm-acct-user">
              <div className="mm-acct-avatar">{initials}</div>
              <div>
                <div style={{ fontWeight: 700, fontSize: 14 }}>{`${user.first_name} ${user.last_name}`.trim() || "Customer"}</div>
                <div style={{ fontSize: 12, color: "#9aa1ac" }}>{user.email}</div>
              </div>
            </div>
            <div className="mm-acct-nav">
              {navBtn("overview", "Overview")}
              {navBtn("bookings", "My bookings")}
              {navBtn("cards", "Payment cards")}
              {navBtn("profile", "Profile")}
              <button className="signout" onClick={logout}>Sign out</button>
            </div>
          </aside>

          <div>
            {tab === "overview" && (
              <>
                <div className="mm-acct-kpis">
                  <div className="mm-acct-kpi"><div className="v">{upcoming.length}</div><div className="l">Upcoming rides</div></div>
                  <div className="mm-acct-kpi"><div className="v">{bookings.length}</div><div className="l">Total bookings</div></div>
                  <div className="mm-acct-kpi"><div className="v">{past.length}</div><div className="l">Completed / past</div></div>
                </div>
                <h5 className="text-18-medium mb-15">Next ride</h5>
                {loadingBookings && <p className="color-grey">Loading…</p>}
                {!loadingBookings && upcoming.length === 0 && (
                  <p className="text-16 color-grey">No upcoming rides. <Link href="/booking/vehicle">Book one</Link>.</p>
                )}
                {upcoming.slice(0, 1).map((b) => <RideCard key={b.reference} b={b} onCancel={cancel} onAmend={amend} userPhone={user.phone || ""} />)}
              </>
            )}

            {tab === "bookings" && (
              <>
                <h5 className="text-18-medium mb-15">All bookings</h5>
                {loadingBookings && <p className="color-grey">Loading…</p>}
                {!loadingBookings && bookings.length === 0 && (
                  <p className="text-16 color-grey">No bookings yet. <Link href="/booking/vehicle">Book a ride</Link>.</p>
                )}
                {[...upcoming, ...past].map((b) => <RideCard key={b.reference} b={b} onCancel={cancel} onAmend={amend} userPhone={user.phone || ""} />)}
              </>
            )}

            {tab === "cards" && (
              <>
                <h5 className="text-18-medium mb-15">Payment cards</h5>
                {loadingCards && <p className="color-grey">Loading…</p>}
                {!loadingCards && cards.length === 0 && (
                  <p className="text-16 color-grey">
                    No cards saved yet. When you pay for a booking by card, tick &ldquo;save this card&rdquo;
                    and it&rsquo;ll be here for faster booking next time.
                  </p>
                )}
                {cards.map((c) => (
                  <div key={c.id} className="mm-ride" style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                    <div>
                      <b>{c.label}</b>
                      {c.is_default && <span className="text-14 color-grey"> · default</span>}
                      {c.expiry && <div className="text-14 color-grey">Expires {c.expiry}</div>}
                    </div>
                    <button className="btn btn-border btn-sm hover-up" style={{ color: "#c0392b" }} onClick={() => removeCard(c.id)}>
                      Remove
                    </button>
                  </div>
                ))}
              </>
            )}

            {tab === "profile" && (
              <>
                <h5 className="text-18-medium mb-15">Profile</h5>
                <div className="mm-ride">
                  <div className="row">
                    <div className="col-6 mb-20">
                      <label className="text-14 color-grey">First name</label>
                      <input className="form-control" value={pf.first_name} onChange={(e) => setPf({ ...pf, first_name: e.target.value })} />
                    </div>
                    <div className="col-6 mb-20">
                      <label className="text-14 color-grey">Last name</label>
                      <input className="form-control" value={pf.last_name} onChange={(e) => setPf({ ...pf, last_name: e.target.value })} />
                    </div>
                    <div className="col-6 mb-20">
                      <label className="text-14 color-grey">Phone</label>
                      <input className="form-control" type="tel" value={pf.phone} onChange={(e) => setPf({ ...pf, phone: e.target.value })} />
                    </div>
                    <div className="col-6 mb-20">
                      <label className="text-14 color-grey">Email <span className="color-grey">(sign-in, not editable)</span></label>
                      <input className="form-control" value={user.email} readOnly disabled />
                    </div>
                  </div>
                  <div className="d-flex align-items-center" style={{ gap: 14 }}>
                    <button className="btn btn-primary hover-up" onClick={saveProfile} disabled={pfSaving}>
                      {pfSaving ? "Saving…" : "Save changes"}
                    </button>
                    {pfMsg && <span className="text-14" style={{ color: pfMsg === "Saved." ? "#1e7e34" : "#c0392b" }}>{pfMsg}</span>}
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
