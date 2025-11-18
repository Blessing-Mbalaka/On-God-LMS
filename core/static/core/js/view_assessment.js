
  const data = JSON.parse(localStorage.getItem("selectedAssessment"));
  const generated = JSON.parse(localStorage.getItem("generatedPaper")) || [];

  document.getElementById("assessmentId").textContent = data?.id || "N/A";
  document.getElementById("qualification").textContent = data?.qualification || "";
  document.getElementById("paper").textContent = data?.paper || "";
  document.getElementById("saqa").textContent = data?.saqaID || "";

  const questionList = document.getElementById("questionList");
  if (generated.length > 0) {
    generated.forEach((q, i) => {
      const div = document.createElement("div");
      div.className = "question-block";
      div.innerHTML = `
        <h5>Question ${i + 1}</h5>
        <textarea rows="3">${q.text}</textarea>
        <p><strong>Marks:</strong> ${q.marks}</p>
      `;
      questionList.appendChild(div);
    });
  } else {
    questionList.innerHTML = `<p>No questions found for this assessment.</p>`;
  }

  function forwardToModerator() {
    const notes = document.getElementById("moderatorNotes").value;
    const all = JSON.parse(localStorage.getItem("submittedAssessments")) || [];
    const updated = all.map(a => {
      if (a.id === data.id) {
        return { ...a, internal: "Submitted to Moderator", notes };
      }
      return a;
    });
    localStorage.setItem("submittedAssessments", JSON.stringify(updated));
    alert("Assessment forwarded to Moderator.");
    window.location.href = "assessor_dashboard.html";
  }
