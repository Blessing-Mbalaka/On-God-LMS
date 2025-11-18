// assessor_upload.js
function confirmUpload() {
    const eisa = document.getElementById("eisaTool").value;
    const memo = document.getElementById("memoFile").value;
    const exam = document.getElementById("examPaper").value;
  
    if (!eisa && !memo && !exam) {
      alert("Please select at least one file to upload.");
      return;
    }
  
    alert("Files submitted successfully for processing.");
  }

  window.onload = function () {
    const generated = localStorage.getItem("generatedPaper");
    if (generated) {
      alert("You have a generated paper ready for upload.");
      // You can display the questions here or simulate a file attached
      console.log("Generated Questions:", JSON.parse(generated));
      // Optional: populate a preview box or mock file label
    }
  };
  