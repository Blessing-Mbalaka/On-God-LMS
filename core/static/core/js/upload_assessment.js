document.addEventListener("DOMContentLoaded", () => {
  const form       = document.getElementById("uploadForm");
  const fileInput  = document.getElementById("fileInput");
  const memoInput  = document.getElementById("memoFile");
  const submitBtn  = form.querySelector("button[type=submit]");

  // Show selected file names in the label (you'll need to add <span id="fileNameDisplay"> and #memoNameDisplay in your HTML)
  fileInput.addEventListener("change", () => {
    const name = fileInput.files[0]?.name || "No file chosen";
    document.getElementById("fileNameDisplay").textContent = name;
  });
  memoInput.addEventListener("change", () => {
    const name = memoInput.files[0]?.name || "No file chosen";
    document.getElementById("memoNameDisplay").textContent = name;
  });

  // Disable the submit button after click to prevent double-submits
  form.addEventListener("submit", () => {
    submitBtn.disabled = true;
    submitBtn.textContent = "Uploading…";
  });
});
