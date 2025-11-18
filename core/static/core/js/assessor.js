document.getElementById("uploadForm").addEventListener("submit", function(e) {
    e.preventDefault();
    alert("Assessment tool uploaded successfully!");
  });
  
  function generateFromDatabase() {
    alert("Generated paper from database.");
  }
  





//  { id: "1.1.1", text: "List and explain how all types of maintenance work are identified from notifications / work orders.", marks: 3 },
//       { id: "1.1.1b", text: "Explain the importance of having notification systems to record maintenance requests.", marks: 2 },
//       { id: "1.1.2a", text: "Explain the importance of evaluating notifications.", marks: 5 },
//       { id: "1.1.2b", text: "List 5 key factors to evaluate in the notification to ensure quality work orders.", marks: 5 },
//       { id: "1.1.3a", text: "Identify types of maintenance schedules and describe the review process from CMMS or manual system.", marks: 5 },
//       { id: "1.1.3b", text: "List planning requirements for detailed work orders.", marks: 5 },
//       { id: "1.1.4", text: "List all necessary information that should be on the work order/job card from CMMS or manual system.", marks: 5 },
//       { id: "1.1.5a", text: "Describe different types of equipment failures with practical examples.", marks: 5 },
//       { id: "1.1.5b", text: "List examples of equipment failure modes from notifications or feedback.", marks: 5 },
//       { id: "1.1.5c", text: "Explain how identified equipment failures and root causes are analysed for corrective work.", marks: 10 },
//       { id: "1.1.6", text: "Outline the process of updating work requests from receipt to planning.", marks: 5 },
//       { id: "1.2.1a", text: "Describe Job Scoping, its necessity, and how it is done.", marks: 6 },
//       { id: "1.2.1b", text: "List and describe all resource requirements for Job Scoping.", marks: 14 },
//       { id: "1.2.2", text: "Compile a work order with task list and resources following Job Scoping.", marks: 10 },
//       { id: "1.2.3", text: "Describe reservations and requisitions and their importance in maintenance planning.", marks: 10 },
//       { id: "1.2.4a", text: "Define the work order cycle from open to close.", marks: 5 },
//       { id: "1.2.4b", text: "Give example of work order status codes and updates.", marks: 5 },
//       { id: "1.2.4c", text: "List causes of maintenance backlogs and how to control them.", marks: 5 },
//       { id: "1.3.1a", text: "Describe scheduling, how it’s coordinated, and required items.", marks: 10 },
//       { id: "1.3.1b", text: "Outline how to compile master schedules and what they should include.", marks: 20 },
//       { id: "1.3.2a", text: "Identify key scheduling constraints and root causes from the scenario.", marks: 5 },
//       { id: "1.3.2b", text: "Recommend improvements to avoid reoccurrence of scheduling issues.", marks: 10 },
//       { id: "1.3.3", text: "Define the master schedule implementation approval process and its role players.", marks: 10 }