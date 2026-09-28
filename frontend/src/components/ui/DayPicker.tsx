"use client";

import { useState, useRef, useEffect } from "react";
import { DayPicker as ReactDayPicker } from "react-day-picker";
import "react-day-picker/style.css";

interface Props {
  value: string;
  onChange: (date: string) => void;
  placeholder?: string;
}

export default function DayPicker({ value, onChange, placeholder = "" }: Props) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const selected = value ? new Date(value) : undefined;

  const display = selected
    ? selected.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "2-digit", year: "numeric" })
    : placeholder;

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  return (
    <div ref={ref} className="mm-picker">
      <input
        className="search-input"
        type="text"
        readOnly
        value={display}
        onClick={() => setOpen((o) => !o)}
        placeholder={placeholder}
      />
      {open && (
        <div className="mm-dropdown mm-daypicker">
          <ReactDayPicker
            mode="single"
            selected={selected}
            onSelect={(d) => {
              if (d) { onChange(d.toISOString().split("T")[0]); setOpen(false); }
            }}
            disabled={{ before: new Date() }}
          />
        </div>
      )}
    </div>
  );
}
