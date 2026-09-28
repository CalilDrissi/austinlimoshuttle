"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import DayPicker from "@/components/ui/DayPicker";
import TimePicker from "@/components/ui/TimePicker";
import { useBookingStore } from "@/lib/booking/store";
import {
  fetchPlaceSuggestions,
  newSessionToken,
  type PlaceSuggestion,
} from "@/lib/google/places";

const PLANE_ICON = "/assets/imgs/page/homepage1/plane.png";
const PIN_ICON = "/assets/imgs/page/homepage1/building.png";

// Below this length Google predictions are too noisy to be worth a billed call.
const MIN_QUERY = 3;

/**
 * A typeable address field backed by Google Places autocomplete.
 *
 * Free text is always allowed — the backend geocodes whatever is submitted, so
 * the suggestions only save typing. Keystrokes are debounced and grouped under
 * one session token for billing; if Places can't load (missing/blocked key) the
 * field degrades to a plain text input with no dropdown.
 */
function AddressField({ label, value, onChange, placeholder }: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
}) {
  const [open, setOpen] = useState(false);
  const [suggestions, setSuggestions] = useState<PlaceSuggestion[]>([]);
  const [loading, setLoading] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const tokenRef = useRef<unknown>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reqRef = useRef(0); // guards against out-of-order responses

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => {
      document.removeEventListener("mousedown", handler);
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, []);

  const runSearch = (raw: string) => {
    const q = raw.trim();
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (q.length < MIN_QUERY) {
      setSuggestions([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    debounceRef.current = setTimeout(async () => {
      const reqId = ++reqRef.current;
      try {
        if (!tokenRef.current) tokenRef.current = await newSessionToken();
        const results = await fetchPlaceSuggestions(q, tokenRef.current);
        if (reqId === reqRef.current) setSuggestions(results);
      } catch {
        // Missing/blocked key or API error — fall back to plain free text.
        if (reqId === reqRef.current) setSuggestions([]);
      } finally {
        if (reqId === reqRef.current) setLoading(false);
      }
    }, 250);
  };

  const pick = (s: PlaceSuggestion) => {
    onChange(s.full);
    setOpen(false);
    setSuggestions([]);
    tokenRef.current = null; // a selection ends the billing session
  };

  return (
    <div className="search-inputs mm-picker" ref={ref} onClick={() => inputRef.current?.focus()}>
      <label>{label}</label>
      <input
        ref={inputRef}
        className="search-input"
        type="text"
        autoComplete="off"
        placeholder={placeholder}
        value={value}
        onChange={(e) => { onChange(e.target.value); setOpen(true); runSearch(e.target.value); }}
        onFocus={() => { setOpen(true); if (!suggestions.length) runSearch(value); }}
      />
      {open && (value.trim().length >= MIN_QUERY) && (
        <div className="mm-dropdown mm-loc-list">
          {suggestions.length ? (
            suggestions.map((s) => (
              <div
                key={s.id}
                className="mm-loc-item"
                onMouseDown={(e) => { e.preventDefault(); pick(s); }}
              >
                <img src={s.isAirport ? PLANE_ICON : PIN_ICON} alt="" />
                <span className="mm-loc-text">
                  <span className="mm-loc-title">{s.primary}</span>
                  {s.secondary && <span className="mm-loc-sub">{s.secondary}</span>}
                </span>
              </div>
            ))
          ) : (
            <div className="mm-loc-empty">
              {loading ? "Searching…" : "No matches — you can enter any address."}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function BookingSearchWidget() {
  const router = useRouter();
  const setSearch = useBookingStore((s) => s.setSearch);

  const [date, setDate] = useState("");
  const [time, setTime] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [meetGreet, setMeetGreet] = useState(false);
  const [error, setError] = useState("");

  const handleSearch = () => {
    if (!from.trim() || !to.trim() || !date || !time) {
      setError("Please fill in date, time, pickup and drop-off.");
      return;
    }
    setSearch({
      pickupAddress: from.trim(),
      dropoffAddress: to.trim(),
      date,
      time,
      meetGreet,
    });
    router.push("/booking/vehicle");
  };

  return (
    <div className="box-search-ride">
      <div className="search-item search-date">
        <div className="search-icon"><span className="item-icon icon-date" /></div>
        <div className="search-inputs">
          <label>Date</label>
          <DayPicker value={date} onChange={setDate} placeholder="Select date" />
        </div>
      </div>

      <div className="search-item search-time">
        <div className="search-icon"><span className="item-icon icon-time" /></div>
        <div className="search-inputs">
          <label>Time</label>
          <TimePicker value={time} onChange={setTime} />
        </div>
      </div>

      <div className="search-item search-from">
        <div className="search-icon"><span className="item-icon icon-from" /></div>
        <AddressField label="From" value={from} onChange={setFrom} placeholder="Pickup address" />
      </div>

      <div className="search-item search-to">
        <div className="search-icon"><span className="item-icon icon-to" /></div>
        <AddressField label="To" value={to} onChange={setTo} placeholder="Drop-off address" />
      </div>

      <div className="search-item search-meet">
        <label className="mm-check">
          <input type="checkbox" checked={meetGreet} onChange={(e) => setMeetGreet(e.target.checked)} />
          <span className="mm-check-box" />
          <span className="mm-check-label">Meet &amp; Greet</span>
        </label>
      </div>

      <div className="search-item search-button">
        <button className="btn btn-search" type="button" onClick={handleSearch}>
          <Image src="/assets/imgs/template/icons/search.svg" alt="" width={16} height={16} />
          Search
        </button>
      </div>

      {error && <div className="mm-search-error">{error}</div>}
    </div>
  );
}
