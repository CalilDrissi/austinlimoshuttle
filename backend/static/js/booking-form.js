/* Manual booking form: Google Places autocomplete + Stripe card collection.
 * Loaded as an external file so the dashboard CSP can stay free of
 * script-src 'unsafe-inline'. Config comes from data-* attributes on the form.
 */
(function () {
  "use strict";

  /* --- Google Places autocomplete (new API) on the address inputs --- */
  window.__initPlaces = async function () {
    try {
      const { AutocompleteSuggestion, AutocompleteSessionToken } =
        await google.maps.importLibrary("places");
      ["id_pickup_address", "id_dropoff_address"].forEach(function (id) {
        attachAC(id, AutocompleteSuggestion, AutocompleteSessionToken);
      });
    } catch (e) {
      console.warn("Places init failed", e);
    }
  };

  function attachAC(id, AS, Token) {
    const input = document.getElementById(id);
    if (!input) return;
    input.setAttribute("autocomplete", "off");
    const wrap = document.createElement("div");
    wrap.style.position = "relative";
    input.parentNode.insertBefore(wrap, input);
    wrap.appendChild(input);
    const box = document.createElement("div");
    box.style.cssText =
      "position:absolute;left:0;right:0;z-index:1080;background:#fff;border:1px solid #ddd;border-radius:6px;max-height:220px;overflow:auto;display:none;box-shadow:0 6px 18px rgba(0,0,0,.12)";
    wrap.appendChild(box);
    let token = new Token();
    let timer;
    input.addEventListener("input", function () {
      clearTimeout(timer);
      const q = input.value.trim();
      if (q.length < 3) {
        box.style.display = "none";
        return;
      }
      timer = setTimeout(async function () {
        try {
          const { suggestions } = await AS.fetchAutocompleteSuggestions({
            input: q,
            sessionToken: token,
            includedRegionCodes: ["us"],
            locationBias: { center: { lat: 30.2672, lng: -97.7431 }, radius: 50000 },
          });
          box.innerHTML = "";
          (suggestions || []).forEach(function (s) {
            const p = s.placePrediction;
            if (!p) return;
            const d = document.createElement("div");
            d.textContent = p.text.text;
            d.style.cssText = "padding:8px 12px;cursor:pointer;font-size:14px";
            d.onmouseover = function () { d.style.background = "#f4f4f5"; };
            d.onmouseout = function () { d.style.background = "#fff"; };
            d.onmousedown = function (e) {
              e.preventDefault();
              input.value = p.text.text;
              box.style.display = "none";
              token = new Token();
            };
            box.appendChild(d);
          });
          box.style.display = suggestions && suggestions.length ? "block" : "none";
        } catch (e) {
          box.style.display = "none";
        }
      }, 250);
    });
    document.addEventListener("click", function (e) {
      if (!wrap.contains(e.target)) box.style.display = "none";
    });
  }

  /* --- Stripe card collection for the manual booking --- */
  const form = document.getElementById("booking-form");
  if (!form) return;
  const pk = form.dataset.stripePk || "";
  if (!pk || typeof Stripe === "undefined") return;

  const stripe = Stripe(pk);
  const elements = stripe.elements();
  const card = elements.create("card", { hidePostalCode: true });
  let mounted = false;
  let submitting = false;

  function showCard(on) {
    const w = document.getElementById("card-wrap");
    if (!w) return;
    w.style.display = on ? "block" : "none";
    if (on && !mounted) {
      card.mount("#card-element");
      mounted = true;
    }
  }

  document.querySelectorAll('input[name="payment_method"]').forEach(function (r) {
    r.addEventListener("change", function () {
      showCard(this.value === "card" && this.checked);
    });
  });

  card.on("change", function (ev) {
    document.getElementById("card-errors").textContent = ev.error ? ev.error.message : "";
  });

  form.addEventListener("submit", function (e) {
    const sel = document.querySelector('input[name="payment_method"]:checked');
    if (!sel || sel.value !== "card" || submitting) return; // cash -> normal submit
    e.preventDefault();
    const btn = document.getElementById("submit-btn");
    btn.disabled = true;
    btn.textContent = "Charging…";
    stripe.createPaymentMethod({ type: "card", card: card }).then(function (res) {
      if (res.error) {
        document.getElementById("card-errors").textContent = res.error.message;
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-check-lg me-1"></i>Create booking';
        return;
      }
      document.getElementById("stripe_payment_method_id").value = res.paymentMethod.id;
      submitting = true;
      form.submit();
    });
  });
})();

/* --- City-to-city flat-rate fare (manual booking) ---
 * Independent of Stripe. The route tab fills the fare from a prices map; the
 * server recomputes it authoritatively, so this is only live feedback.
 */
(function () {
  "use strict";
  var form = document.getElementById("booking-form");
  if (!form) return;
  var routeSelect = document.getElementById("city_route_select");
  var modeInput = document.getElementById("pricing_mode");
  if (!routeSelect || !modeInput) return; // not the new-booking form, or no routes

  var prices = {};
  try { prices = JSON.parse(form.dataset.routePrices || "{}"); } catch (e) { prices = {}; }
  var vehicleSelect = document.getElementById("id_vehicle");
  var totalInput = document.getElementById("id_total");
  var info = document.getElementById("route-fare-info");

  function recalc() {
    var r = routeSelect.value;
    var v = vehicleSelect ? vehicleSelect.value : "";
    if (!r) { if (info) { info.textContent = ""; info.className = "small fw-semibold mt-2"; } return; }
    var price = prices[r] && prices[r][v];
    if (price != null) {
      if (totalInput) totalInput.value = price;
      if (info) {
        info.textContent = "Flat fare: $" + Number(price).toFixed(2) + " (all-in)";
        info.className = "small fw-semibold mt-2 text-success";
      }
    } else if (info) {
      info.textContent = "No price set for the selected vehicle on this route. Add one under City routes, or use Custom.";
      info.className = "small fw-semibold mt-2 text-danger";
    }
  }

  // Bootstrap tab change -> record which pricing mode is active.
  document.querySelectorAll('[data-bs-toggle="tab"][data-mode]').forEach(function (btn) {
    btn.addEventListener("shown.bs.tab", function (e) {
      modeInput.value = e.target.getAttribute("data-mode");
      if (modeInput.value === "city_route") recalc();
    });
  });
  routeSelect.addEventListener("change", recalc);
  if (vehicleSelect) {
    vehicleSelect.addEventListener("change", function () {
      if (modeInput.value === "city_route") recalc();
    });
  }
  if (modeInput.value === "city_route") recalc(); // after an error re-render
})();
