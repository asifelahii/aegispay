(function () {
  "use strict";

  const payload = document.getElementById("experiment-chart-data");
  const svg = document.getElementById("friction-chart");
  if (!payload || !svg) return;

  const data = JSON.parse(payload.textContent);
  const width = 760;
  const height = 290;
  const pad = { top: 20, right: 28, bottom: 42, left: 72 };
  const values = data.legacy.concat(data.canonical);
  const min = Math.min.apply(null, values);
  const max = Math.max.apply(null, values);
  const x = (index) => pad.left + (index * (width - pad.left - pad.right)) / (data.labels.length - 1);
  const y = (value) => pad.top + ((max - value) * (height - pad.top - pad.bottom)) / (max - min);
  const lines = svg.querySelector(".chart-lines");
  const labels = svg.querySelector(".chart-labels");
  const grid = svg.querySelector(".chart-grid-lines");
  const ns = "http://www.w3.org/2000/svg";

  [min, (min + max) / 2, max].forEach((value) => {
    const line = document.createElementNS(ns, "line");
    line.setAttribute("x1", pad.left);
    line.setAttribute("x2", width - pad.right);
    line.setAttribute("y1", y(value));
    line.setAttribute("y2", y(value));
    line.setAttribute("class", "chart-grid-line");
    grid.appendChild(line);
    const text = document.createElementNS(ns, "text");
    text.setAttribute("x", pad.left - 10);
    text.setAttribute("y", y(value) + 4);
    text.setAttribute("text-anchor", "end");
    text.textContent = Math.round(value).toLocaleString();
    labels.appendChild(text);
  });

  data.labels.forEach((label, index) => {
    const text = document.createElementNS(ns, "text");
    text.setAttribute("x", x(index));
    text.setAttribute("y", height - 14);
    text.setAttribute("text-anchor", "middle");
    text.textContent = label;
    labels.appendChild(text);
  });

  [
    { values: data.legacy, className: "chart-line chart-line-legacy", label: "Legacy" },
    { values: data.canonical, className: "chart-line chart-line-canonical", label: "Canonical" },
  ].forEach((series) => {
    const path = document.createElementNS(ns, "path");
    path.setAttribute("class", series.className);
    path.setAttribute("d", series.values.map((value, index) => `${index ? "L" : "M"} ${x(index)} ${y(value)}`).join(" "));
    path.setAttribute("aria-label", series.label);
    lines.appendChild(path);
    series.values.forEach((value, index) => {
      const circle = document.createElementNS(ns, "circle");
      circle.setAttribute("class", series.className);
      circle.setAttribute("cx", x(index));
      circle.setAttribute("cy", y(value));
      circle.setAttribute("r", "4");
      circle.setAttribute("aria-hidden", "true");
      lines.appendChild(circle);
    });
  });
})();
