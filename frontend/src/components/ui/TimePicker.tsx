"use client";

import { useState, useRef, useEffect } from "react";

const TIMES: string[] = [];
for (let h = 0; h < 24; h++) {
  for (const m of [0, 15, 30, 45]) {
    const hour = h % 12 || 12;
    const ampm = h < 12 ? "AM" : "PM";
    const min = m.toString().padStart(2, "0");
    TIMES.push(`${hour}:${min} ${ampm}`);
  }
}

interface Props {
  value: string;
  onChange: (time: string) => void;
}

export default function TimePicker({ value, onChange }: Props) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

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
        value={value}
        placeholder="Select time"
        onClick={() => setOpen((o) => !o)}
      />
      {open && (
        <div className="mm-dropdown mm-time-list">
          {TIMES.map((t) => (
            <div
              key={t}
              className={`mm-time-item${value === t ? " sel" : ""}`}
              onClick={() => { onChange(t); setOpen(false); }}
            >
              {t}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
