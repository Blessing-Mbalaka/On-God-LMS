let chartInstance;

// Sum up each metric and write into the cards
function updateCounts(filtered) {
  document.getElementById("toolsGenerated").innerText =
    filtered.reduce((sum, r) => sum + r.toolsGenerated, 0);
  document.getElementById("toolsSubmitted").innerText =
    filtered.reduce((sum, r) => sum + r.toolsSubmitted, 0);
  document.getElementById("questionsAdded").innerText =
    filtered.reduce((sum, r) => sum + r.questionsAdded, 0);
}

// Render or re-render the Chart.js bar chart
function renderChart(filtered) {
  const labels    = filtered.map(d => d.qualification);
  const generated = filtered.map(d => d.toolsGenerated);
  const submitted = filtered.map(d => d.toolsSubmitted);
  const added     = filtered.map(d => d.questionsAdded);

  const ctx = document.getElementById("assessorChart").getContext("2d");
  if (chartInstance) chartInstance.destroy();

  chartInstance = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [
        { label: "Tools Generated", data: generated },
        { label: "Tools Submitted", data: submitted },
        { label: "Questions Added", data: added }
      ]
    },
    options: {
      responsive: true,
      plugins: { legend: { position: "top" } },
      scales: { y: { beginAtZero: true } }
    }
  });
}

// Filter by the dropdown selection and update everything
function filterChart() {
  const sel = document.getElementById("qualificationFilter").value;
  const filtered = sel ? data.filter(d => d.qualification === sel) : data;
  updateCounts(filtered);
  renderChart(filtered);
}

// Build a CSV and trigger download
function exportCSV() {
  const header = "Qualification,Tools Generated,Tools Submitted,Questions Added\n";
  const rows = data
    .map(r => `${r.qualification},${r.toolsGenerated},${r.toolsSubmitted},${r.questionsAdded}`)
    .join("\n");
  const blob = new Blob([header + rows], { type: "text/csv" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "assessor_developer_reports.csv";
  document.body.appendChild(a);
  a.click();
  a.remove();
}

// Wire up events once the page is loaded
document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("qualificationFilter")
          .addEventListener("change", filterChart);

  document.getElementById("exportBtn")
          .addEventListener("click", exportCSV);

  // initial render
  filterChart();
});
