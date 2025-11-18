const questions = [
    { id: 1, text: "What is OHS?", type: "text" },
    { id: 2, text: "List 3 hazards.", type: "text" },
    { id: 3, text: "Select the correct option", type: "mcq", options: ["A", "B", "C"] }
  ];
  
  let currentAnswers = {};
  
  function startAssessment() {
    document.getElementById("assessmentContainer").style.display = "block";
    renderQuestionNav();
    showQuestion(0);
  }
  
  function renderQuestionNav() {
    const nav = document.getElementById("questionNav");
    nav.innerHTML = "";
    questions.forEach((q, index) => {
      const btn = document.createElement("button");
      btn.textContent = `Q${index + 1}`;
      btn.onclick = () => showQuestion(index);
      nav.appendChild(btn);
    });
  }
  
  function showQuestion(index) {
    const area = document.getElementById("questionArea");
    const q = questions[index];
    area.innerHTML = `<p>${q.text}</p>`;
    if (q.type === "text") {
      area.innerHTML += `<textarea id='ans${q.id}'></textarea>`;
    } else if (q.type === "mcq") {
      q.options.forEach(opt => {
        area.innerHTML += `<label><input type='radio' name='ans${q.id}' value='${opt}'> ${opt}</label><br>`;
      });
    }
  }
  
  function submitAssessment() {
    alert("Assessment submitted. Results will be released soon.");
    document.getElementById("assessmentContainer").style.display = "none";
    document.getElementById("appealSection").style.display = "block";
  }
  