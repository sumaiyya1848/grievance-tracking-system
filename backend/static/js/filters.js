const searchBox = document.getElementById("searchBox");
const statusFilter = document.getElementById("statusFilter");
const priorityFilter = document.getElementById("priorityFilter");
const overdueOnly = document.getElementById("overdueOnly");
const rows = document.querySelectorAll("#grievanceTable tbody tr");
const emptyMsg = document.getElementById("emptyMsg");

function applyFilters() {
  const text = searchBox.value.trim().toLowerCase();
  let visible = 0;
  rows.forEach(function (row) {
    const matchText = row.textContent.toLowerCase().includes(text);
    const matchStatus = !statusFilter.value || row.dataset.status === statusFilter.value;
    const matchPriority = !priorityFilter.value || row.dataset.priority === priorityFilter.value;
    const matchOverdue = !overdueOnly.checked || row.dataset.overdue === "yes";
    const show = matchText && matchStatus && matchPriority && matchOverdue;
    row.hidden = !show;
    if (show) visible++;
  });
  emptyMsg.hidden = visible !== 0 || rows.length === 0;
}

[searchBox, statusFilter, priorityFilter, overdueOnly].forEach(function (el) {
  el.addEventListener("input", applyFilters);
  el.addEventListener("change", applyFilters);
});