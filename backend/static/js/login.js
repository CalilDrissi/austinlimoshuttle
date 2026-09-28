/*
 * Password reveal on the staff sign-in page.
 *
 * A separate file rather than an inline <script> because the Content-Security-
 * Policy in config/middleware.py sets script-src 'self'. An inline block is
 * blocked by the browser with no server-side error: the page renders perfectly
 * and the button simply does nothing, which is exactly how this shipped the
 * first time.
 */
(function () {
  "use strict";

  var button = document.getElementById("togglePw");
  var input = document.getElementById("id_password");
  var icon = document.getElementById("togglePwIcon");
  if (!button || !input || !icon) return;

  button.addEventListener("click", function () {
    var reveal = input.type === "password";
    input.type = reveal ? "text" : "password";
    icon.className = reveal ? "bi bi-eye-slash" : "bi bi-eye";
    button.setAttribute("aria-pressed", String(reveal));
    button.setAttribute("aria-label", reveal ? "Hide password" : "Show password");
    input.focus();
  });
})();
