// Shared helpers
function setError(input, errorEl, message) {
  errorEl.textContent = message;
  input.classList.toggle("invalid", Boolean(message));
}