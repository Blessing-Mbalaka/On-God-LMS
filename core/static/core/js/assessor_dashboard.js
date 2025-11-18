document.addEventListener('DOMContentLoaded', () => {
  const input = document.getElementById('searchInput');
  const rows  = document.querySelectorAll('.assessment-table tbody tr');

  input.addEventListener('input', () => {
    const term = input.value.trim().toLowerCase();
    rows.forEach(tr => {
      const text = tr.textContent.toLowerCase();
      tr.style.display = term === '' || text.includes(term)
                       ? ''
                       : 'none';
    });
  });
});
