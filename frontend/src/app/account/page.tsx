"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { API_BASE_URL } from "@/lib/api/config";
import { bookingService } from "@/lib/api/booking.service";
import { authService } from "@/lib/api/auth.service";
import { useAuth, useRefreshAuth } from "@/hooks/useAuth";
import type { Booking } from "@/types/api";

type Tab = "overview" | "bookings" | "profile";

function money(a: string, c: string) {
  return `${c === "USD" ? "$" : c + " "}${Number(a).toFixed(2)}`;
}
function when(iso: string) {
  return new Date(iso).toLocaleString("en-US", { weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}
function isUpcoming(b: Booking) {
  return b.status !== "cancelled" && b.status !== "completed" && new Date(b.pickup_at) > new Date();
}

function RideCard({ b, onCancel }: { b: Booking; onCancel: (ref: string) => void }) {
  return (
    <div className="mm-ride">
      <div className="mm-ride-top">
        <div>
          <div className="route">{b.pickup_address} → {b.dropoff_address || "Hourly hire"}</div>
          <div className="meta">{when(b.pickup_at)} · {b.vehicle_name} · {money(b.total, b.currency)} · Ref {b.reference}</div>
        </div>
        <span className={`mm-badge ${b.status}`}>{b.status_display}</span>
      </div>
      <div className="mm-ride-actions">
        <a className="btn btn-border btn-sm hover-up" href={`${API_BASE_URL}/bookings/${b.reference}/receipt/`} target="_blank" rel="noopener noreferrer">Receipt PDF</a>
        {isUpcoming(b) && (
          <button className="btn btn-border btn-sm hover-up" style={{ color: "#c0392b" }} onClick={() => onCancel(b.reference)}>Cancel</button>
        )}
      </div>
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

  const cancel = async (ref: string) => {
    if (!confirm("Cancel this booking?")) return;
    try {
      await bookingService.cancel(ref);
      qc.invalidateQueries({ queryKey: ["my-bookings"] });
    } catch (e) {
      alert(e instanceof Error ? e.message : "Could not cancel.");
    }
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
                {upcoming.slice(0, 1).map((b) => <RideCard key={b.reference} b={b} onCancel={cancel} />)}
              </>
            )}

            {tab === "bookings" && (
              <>
                <h5 className="text-18-medium mb-15">All bookings</h5>
                {loadingBookings && <p className="color-grey">Loading…</p>}
                {!loadingBookings && bookings.length === 0 && (
                  <p className="text-16 color-grey">No bookings yet. <Link href="/booking/vehicle">Book a ride</Link>.</p>
                )}
                {[...upcoming, ...past].map((b) => <RideCard key={b.reference} b={b} onCancel={cancel} />)}
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
