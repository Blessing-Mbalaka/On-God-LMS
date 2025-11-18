// generate_tool.js

const questions = [
  // Maintenance Planner
  {
    id: 1, qualification: "Maintenance Planner", elo: "ELO 1",
    text: "List and explain how all types of maintenance work are identified from notifications / work orders.", marks: 3
  },
  {
    id: 2, qualification: "Maintenance Planner", elo: "ELO 1",
    text: "Explain the importance of having notification systems to record maintenance requests.", marks: 2
  },
  {
    id: 3, qualification: "Maintenance Planner", elo: "ELO 1",
    text: "Explain the importance of evaluating notifications.", marks: 5
  },

  // Quality Controller
  {
    id: 101, qualification: "Quality Controller", elo: "ELO 1",
    text: "Define quality and explain why it is important in manufacturing.", marks: 5
  },
  {
    id: 102, qualification: "Quality Controller", elo: "ELO 2",
    text: "List five common quality tools used in process control.", marks: 5
  },
  {
    id: 103, qualification: "Quality Controller", elo: "ELO 2",
    text: "Explain how a control chart is used to monitor production.", marks: 10
  },
  {
    id: 104, qualification: "Quality Controller", elo: "ELO 3",
    text: "Discuss the role of audits in a quality management system.", marks: 10
  },
  {
    id: 105, qualification: "Quality Controller", elo: "ELO 4",
    text: "Describe corrective and preventive actions and provide examples of each.", marks: 10
  }
];

let selected = [];

function renderQuestions() {
  const list = document.getElementById("questionList");
  list.innerHTML = "";
  const qualifications = [...new Set(questions.map(q => q.qualification))];

  qualifications.forEach(qName => {
    const folder = document.createElement("details");
    folder.classList.add("question-folder");
    const summary = document.createElement("summary");
    summary.textContent = `📁 ${qName}`;
    folder.appendChild(summary);

    const elos = [...new Set(questions.filter(q => q.qualification === qName).map(q => q.elo))];

    elos.forEach(elo => {
      const eloDiv = document.createElement("div");
      eloDiv.innerHTML = `<h4>${elo}</h4>`;
      const qList = document.createElement("ul");

      questions.filter(q => q.qualification === qName && q.elo === elo).forEach(q => {
        const li = document.createElement("li");
        li.innerHTML = `
          <div style='display: flex; justify-content: space-between; align-items: center;'>
            <span>${q.text} (${q.marks} marks)</span>
            <button onclick='addToSelection(${q.id})' style='margin-left: 10px;'>Add</button>
          </div>
        `;
        qList.appendChild(li);
      });

      eloDiv.appendChild(qList);
      folder.appendChild(eloDiv);
    });

    list.appendChild(folder);
  });
}

function addToSelection(id) {
  const q = questions.find(q => q.id === id);
  if (!selected.includes(q)) {
    selected.push(q);
    renderSelected();
    showToast("Question added to paper!");
  }
}

function renderSelected() {
  const list = document.getElementById("selectedList");
  list.innerHTML = "";

  selected.forEach((q, index) => {
    const li = document.createElement("li");
    li.innerHTML = `
      <div style="display: flex; flex-direction: column; gap: 6px; margin-bottom: 15px;">
        <input type="text" value="${q.text}" onchange="updateSelectedText(${index}, this.value)" 
               style="padding: 5px; width: 100%; border: 1px solid #ccc; border-radius: 4px;" />

        <input type="number" value="${q.marks}" onchange="updateSelectedMarks(${index}, this.value)" 
               style="width: 100px; padding: 5px; border: 1px solid #ccc; border-radius: 4px;" />

        <div style="display: flex; gap: 10px;">
          <button onclick="removeFromSelection(${index})" 
                  style="background-color: #dc3545; color: white; border: none; border-radius: 4px; padding: 5px 10px;">
            Remove
          </button>
          <button onclick="addToFinal(${index})" 
                  style="background-color: #0d6efd; color: white; border: none; border-radius: 4px; padding: 5px 10px;">
            Add to Final
          </button>
        </div>
      </div>
    `;
    list.appendChild(li);
  });
}

function applyFilters() {
  const keyword = document.getElementById("keywordFilter").value.toLowerCase();
  const qualification = document.getElementById("qualificationFilter").value.toLowerCase();
  const list = document.getElementById("questionList");
  list.innerHTML = "";

  const filtered = questions.filter(q =>
    q.text.toLowerCase().includes(keyword) &&
    (qualification === "" || q.qualification.toLowerCase().includes(qualification))
  );

  const qNames = [...new Set(filtered.map(q => q.qualification))];
  qNames.forEach(qName => {
    const folder = document.createElement("details");
    folder.classList.add("question-folder");
    const summary = document.createElement("summary");
    summary.textContent = `📁 ${qName}`;
    folder.appendChild(summary);

    const elos = [...new Set(filtered.filter(q => q.qualification === qName).map(q => q.elo))];
    elos.forEach(elo => {
      const eloDiv = document.createElement("div");
      eloDiv.innerHTML = `<h4>${elo}</h4>`;
      const qList = document.createElement("ul");

      filtered.filter(q => q.qualification === qName && q.elo === elo).forEach(q => {
        const li = document.createElement("li");
        li.innerHTML = `
          <div style='display: flex; justify-content: space-between; align-items: center;'>
            <span>${q.text} (${q.marks} marks)</span>
            <button onclick='addToSelection(${q.id})' style='margin-left: 10px;'>Add</button>
          </div>
        `;
        qList.appendChild(li);
      });

      eloDiv.appendChild(qList);
      folder.appendChild(eloDiv);
    });

    list.appendChild(folder);
  });
}

function previewPaper() {
  const previewContent = selected.map(q => `${q.text} (${q.marks} marks)`).join("\n\n");
  const container = document.getElementById("finalPreview");
  container.textContent = previewContent || "No questions selected yet.";
}


function exportPaper() {
  const qualification = prompt("Enter Qualification (e.g. Maintenance Planner):");
  const paper = prompt("Enter Paper Number (e.g. 1A):");
  const saqaID = prompt("Enter SAQA ID (e.g. 123456):");

  if (!qualification || !paper || !saqaID) {
    showToast("Please provide all required details.");
    return;
  }

  const generatedAssessment = {
    id: `EISA-${Date.now().toString().slice(-4)}`,
    qualification,
    paper,
    saqaID,
    internal: "Pending",
    external: "Not Yet Sent",
    qcto: "Not Yet Sent",
    comment: "Generated from databank",
    file: `Generated-${paper}.pdf`,
    memo: "Not uploaded"
  };

  const existing = JSON.parse(localStorage.getItem("submittedAssessments")) || [];
  existing.push(generatedAssessment);
  localStorage.setItem("submittedAssessments", JSON.stringify(existing));

  showToast("Assessment generated and added!");
  setTimeout(() => {
    window.location.href = "assessor_dashboard.html";
  }, 1500);
}


function showToast(message) {
  const toast = document.createElement("div");
  toast.textContent = message;
  toast.style.position = "fixed";
  toast.style.bottom = "20px";
  toast.style.right = "20px";
  toast.style.background = "#552a74";
  toast.style.color = "white";
  toast.style.padding = "10px 20px";
  toast.style.borderRadius = "8px";
  toast.style.boxShadow = "0 2px 6px rgba(0,0,0,0.2)";
  toast.style.zIndex = 9999;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 3000);
}

window.onload = renderQuestions;

document.getElementById("demoForm")
  .addEventListener("submit", async function (e) {
    e.preventDefault();

    const form = e.target;
    const fd = new FormData(form);
    const preview = document.getElementById("previewContainer");
    preview.innerHTML = "<em>Loading...</em>";

    try {
      const resp = await fetch(form.dataset.url, {
        method: "POST",
        headers: {
          "X-CSRFToken": form.querySelector("[name=csrfmiddlewaretoken]").value
        },
        body: fd
      });

      let data;
      try {
        data = await resp.json();
      } catch (jsonErr) {
        const fallback = await resp.text();
        return alert("❌ Could not parse server response:\n" + fallback);
      }

      if (!resp.ok) {
        return alert("❌ Error from server:\n" + (data.error || "Unknown error"));
      }

      const { questions, total } = data;

      if (!questions || questions.length === 0) {
        preview.innerHTML = "<em>No questions were generated.</em>";
        return;
      }

      let content = "";
      questions.forEach((q, i) => {
        content += `Q${i + 1}: ${q.text}\nMarks: ${q.marks}\nCase Study: ${q.case_study}\n\n`;
      });

      preview.textContent = content;
      showToast(`✅ Paper generated: ${questions.length} questions (${total} marks)`);

    } catch (err) {
      console.error(err);
      preview.innerHTML = "<em>Failed to load questions.</em>";
      alert("❌ A network or server error occurred.");
    }
  });

document.getElementById("submitPaperForm")
  .addEventListener("submit", async function (e) {
    e.preventDefault();

    const previewDiv = document.getElementById("previewContainer");
    const qualification = document.getElementById("qualification").value;

    // Set hidden fields before sending
    document.getElementById("finalQualification").value = qualification;
    document.getElementById("finalPaperContent").value = previewDiv.innerText;

    const fd = new FormData(e.target);
    const resp = await fetch(e.target.dataset.url, {
      method: "POST",
      headers: {
        "X-CSRFToken": fd.get("csrfmiddlewaretoken")
      },
      body: fd
    });

    if (!resp.ok) {
      const msg = await resp.text();
      return alert("❌ Failed to forward paper:\n" + msg);
    }

    showToast("✅ Paper forwarded to Moderator.");
  });


    function submitToModerator() {
      // TODO: hook up to your moderation endpoint
      alert("Assessment forwarded to Moderator.");
    }

    