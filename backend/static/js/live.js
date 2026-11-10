(function () {
  var path = window.location.pathname;
  var livePages = ["/", "/grievances", "/reminders"];
  var isDetail = /^\/grievances\/\d+$/.test(path);
  if (livePages.indexOf(path) === -1 && !isDetail) return;

  var INTERVAL = 5000;
  var lastVersion = null;

  function busy() {
    var fields = document.querySelectorAll(
      "input[type=text], input[type=search], input[type=date], textarea"
    );
    for (var i = 0; i < fields.length; i++) {
      if (fields[i].value) return true;
    }
    var active = document.activeElement;
    if (active && /^(INPUT|TEXTAREA|SELECT)$/.test(active.tagName)) return true;

    var status = document.getElementById("statusFilter");
    var priority = document.getElementById("priorityFilter");
    var overdue = document.getElementById("overdueOnly");
    if (status && status.value) return true;
    if (priority && priority.value) return true;
    if (overdue && overdue.checked) return true;
    return false;
  }

  function check() {
    if (document.hidden) return;
    fetch("/api/changes", { cache: "no-store", credentials: "same-origin" })
      .then(function (res) { return res.ok ? res.json() : null; })
      .then(function (data) {
        if (!data) return;
        if (lastVersion === null) {
          lastVersion = data.version;
          return;
        }
        if (data.version !== lastVersion && !busy()) {
          window.location.reload();
        }
      })
      .catch(function () {});
  }

  setInterval(check, INTERVAL);
  check();
})();