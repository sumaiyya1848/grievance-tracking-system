const followupForm = document.getElementById("followupForm");
const noteInput = document.getElementById("note");
const remindInput = document.getElementById("remind_at");
const followupError = document.getElementById("followupError");

remindInput.min = new Date().toISOString().split("T")[0];

followupForm.addEventListener("submit", function (event) {
  let message = "";
  if (noteInput.value.trim().length < 3) {
    message = "Enter a follow-up note of at least 3 characters.";
  } else if (!remindInput.value) {
    message = "Choose the date you want to be reminded.";
  }
  followupError.textContent = message;
  if (message) event.preventDefault();
});