
    function exportArchive() {
  // Gather all rows
  const rows = Array.from(document.querySelectorAll('table tbody tr'))
    .map(tr => Array.from(tr.cells).map(td => td.textContent.trim()));

  // Build CSV
  let csv = rows.map(r => r.join(',')).join('\n');

  // Download
  const blob = new Blob([csv], { type: 'text/csv' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = 'assessment_archive.csv';
  document.body.appendChild(link);
  link.click();
  link.remove();
}
