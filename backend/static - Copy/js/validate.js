const form = document.getElementById("grievanceForm");
const fields = [
  { id: "complainant_name", min: 2, message: "Enter your name." },
  { id: "title", min: 5, message: "Enter a title of at least 5 characters." },
  { id: "description", min: 20, message: "Describe the problem in at least 20 characters." }
];

const description = document.getElementById("description");
const charCount = document.getElementById("charCount");
description.addEventListener("input", function () {
  charCount.textContent = description.value.length;
});

form.addEventListener("submit", function (event) {
  let firstBad = null;
  fields.forEach(function (f) {
    const input = document.getElementById(f.id);
    const error = document.getElementById(f.id + "Error");
    const ok = input.value.trim().length >= f.min;
    setError(input, error, ok ? "" : f.message);
    if (!ok && !firstBad) firstBad = input;
  });
  if (firstBad) {
    event.preventDefault();
    firstBad.focus();
  }
});

fields.forEach(function (f) {
  document.getElementById(f.id).addEventListener("input", function () {
    setError(this, document.getElementById(f.id + "Error"), "");
  });
});