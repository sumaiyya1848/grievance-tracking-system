const chart = document.getElementById("categoryChart");

fetch("/api/stats")
  .then(function (res) { return res.json(); })
  .then(function (data) {
    const entries = Object.entries(data.by_priority || {});
    if (entries.length === 0) {
      chart.innerHTML = '<p class="empty">No grievances yet, so there is nothing to chart.</p>';
      return;
    }
    const max = Math.max.apply(null, entries.map(function (e) { return e[1]; }));
    chart.innerHTML = "";
    entries.forEach(function (entry) {
      const row = document.createElement("div");
      row.className = "bar-row";
      const label = document.createElement("span");
      label.textContent = entry[0];
      const track = document.createElement("div");
      track.className = "bar-track";
      const fill = document.createElement("div");
      fill.className = "bar-fill";
      fill.style.width = (entry[1] / max * 100) + "%";
      track.appendChild(fill);
      const count = document.createElement("span");
      count.textContent = entry[1];
      row.append(label, track, count);
      chart.appendChild(row);
    });
  })
  .catch(function () {
    chart.innerHTML = '<p class="empty">Could not load the chart. Refresh the page to try again.</p>';
  });