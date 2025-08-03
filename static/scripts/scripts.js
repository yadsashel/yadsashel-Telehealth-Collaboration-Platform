document.addEventListener("DOMContentLoaded", function () {
  // === Navbar for main pages ===
  const mobileMenu = document.getElementById('mobile-menu');
  const navMenu = document.querySelector('.nav-menu');

  if (mobileMenu && navMenu) {
    mobileMenu.addEventListener('click', function () {
      navMenu.classList.toggle('active');
    });
  }

  // === Navbar for dashboards ===
  const sidebarToggle = document.getElementById('sidebarToggle');
  const sidebar = document.querySelector('.sidebar');
  if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener('click', () => {
      sidebar.classList.toggle('sidebar-hidden');
    });
  }

  // === Counter Animation ===
  function animateCounters() {
    const doctorsCounter = document.getElementById('doctorsCounter');
    const patientsCounter = document.getElementById('patientsCounter');
    const satisfactionCounter = document.getElementById('satisfactionCounter');

    if (!doctorsCounter || !patientsCounter || !satisfactionCounter) return;

    const doctorsTarget = 400;
    const patientsTarget = 50000;
    const satisfactionTarget = 98;

    let doctorsCurrent = 0;
    let patientsCurrent = 0;
    let satisfactionCurrent = 0;

    const doctorsIncrement = doctorsTarget / 50;
    const patientsIncrement = patientsTarget / 50;
    const satisfactionIncrement = satisfactionTarget / 50;

    const interval = setInterval(() => {
      doctorsCurrent = Math.min(doctorsCurrent + doctorsIncrement, doctorsTarget);
      patientsCurrent = Math.min(patientsCurrent + patientsIncrement, patientsTarget);
      satisfactionCurrent = Math.min(satisfactionCurrent + satisfactionIncrement, satisfactionTarget);

      doctorsCounter.innerText = Math.round(doctorsCurrent) + '+';
      patientsCounter.innerText = Math.round(patientsCurrent) + '+';
      satisfactionCounter.innerText = Math.round(satisfactionCurrent) + '%';

      if (
        doctorsCurrent >= doctorsTarget &&
        patientsCurrent >= patientsTarget &&
        satisfactionCurrent >= satisfactionTarget
      ) {
        clearInterval(interval);
      }
    }, 50);
  }

  // === Observer to trigger counter animation ===
  const heroStats = document.querySelector('.hero-stats');
  if (heroStats) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          animateCounters();
          observer.disconnect();
        }
      });
    }, { threshold: 0.1 });

    observer.observe(heroStats);
  }

  // === AI Assistant Logic ===
  const askBtn = document.getElementById("askBtn");
  const promptInput = document.getElementById("userPrompt");
  const responseBox = document.getElementById("aiResponse");

  if (askBtn && promptInput && responseBox) {
    askBtn.addEventListener("click", async function () {
      const prompt = promptInput.value.trim();
      if (!prompt) {
        responseBox.textContent = "Please enter a question.";
        return;
      }

      responseBox.textContent = "Thinking...";

      try {
        const res = await fetch("/api/ask", {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({ prompt: prompt })
        });

        const data = await res.json();
        console.log(data);
        responseBox.innerHTML = formatResponse(data.response || "Sorry, no response received.");
      } catch (err) {
        console.error("Error:", err);
        responseBox.textContent = "There was an error connecting to the AI.";
      }
    });
  }

  function formatResponse(text) {
  if (!text) return "";

  // Convert numbered list
  const numbered = text.match(/^(\d+\.\s)/gm);
  if (numbered && numbered.length > 1) {
    const lines = text.split('\n').filter(Boolean);
    return '<ol>' + lines.map(line => `<li>${line.replace(/^\d+\.\s/, '')}</li>`).join('') + '</ol>';
  }

  // Convert bullets (if you use * or - or • in future answers)
  if (text.includes("•") || text.includes("- ")) {
    const bullets = text.split('\n').map(line => line.trim()).filter(Boolean);
    return '<ul>' + bullets.map(line => `<li>${line.replace(/^[-•*]\s*/, '')}</li>`).join('') + '</ul>';
  }

  // Otherwise, just return with line breaks
  return text.replace(/\n/g, '<br>');
}

});

// === Appointment Booking Modal ===
function toggleModal() {
  const modal = document.getElementById('appointmentModal');
  const bookBtn = document.getElementById('bookAppointmentBtn');
    modal.classList.toggle('show');  
    document.body.classList.toggle('modal-open');
      if (bookBtn) {
        bookBtn.addEventListener('click', () => toggleModal(true));
}
}

document.addEventListener('keydown', function (e) {
  if (e.key === 'Escape') {
    toggleModal(false);
  }
});

//cancel appointment button
function cancelAppointment(button) {
    const appointmentId = button.getAttribute('data-id');
    if (!appointmentId) {
      alert("Error: Appointment ID not found.");
      return;
    }

    const confirmed = confirm("Are you sure you want to cancel this appointment?");
    if (!confirmed) return;

    fetch(`/cancel_appointment/${appointmentId}`, {
      method: "DELETE",
      headers: {
        "Content-Type": "application/json"
      }
    })
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        alert("Appointment canceled successfully.");
        button.closest('.appointment-entry').remove(); // remove from UI
      } else {
        alert("Error: " + data.message);
      }
    })
    .catch(error => {
      console.error("Error:", error);
      alert("Something went wrong.");
    });
  }

//past appointments
function showTab(event, tabId) {
  // Remove "active" class from all tab buttons
  const tabs = document.querySelectorAll('.tab');
  tabs.forEach(tab => tab.classList.remove('active'));

  // Add "active" class to the clicked tab button
  event.currentTarget.classList.add('active');

  // Hide all tab contents
  const contents = document.querySelectorAll('.tab-content');
  contents.forEach(content => content.classList.remove('active'));

  // Show the selected tab content
  const selectedTab = document.getElementById(tabId);
  if (selectedTab) {
    selectedTab.classList.add('active');
  }
}

const chatBox = document.getElementById("chatBox");
const chatInput = document.getElementById("chatInput");
const model = document.getElementById("bodyModel");
const popup = document.getElementById("hotspotPopup");
let conversation = [];

function sendMessage() {
  const text = chatInput.value.trim();
  if (!text) return;

  conversation.push({ role: "user", content: text });
  appendMessage("user", text);
  chatInput.value = "";

  fetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages: conversation }),
  })
    .then((res) => res.json())
    .then((data) => {
      if (data.reply) {
        appendMessage("ai", data.reply);
        if (data.action === "highlight" && data.target) {
          zoomToTarget(data.target, data.message);
        } else if (data.diagnosis && data.target) {
          zoomToTarget(data.target, data.diagnosis);
        }
      }
    })
    .catch((err) => {
      console.error("Error:", err);
      appendMessage("ai", "⚠️ An error occurred while contacting the server.");
    });
}

function appendMessage(sender, text) {
  const msg = document.createElement("div");
  msg.className = `chat-message ${sender}`;
  msg.innerText = text;
  chatBox.appendChild(msg);
  chatBox.scrollTop = chatBox.scrollHeight;
}

function zoomToTarget(target, explanation) {
  // Clear old hotspots and popup
  model.querySelectorAll("button.Hotspot").forEach((el) => el.remove());
  popup.style.display = "none";

  const targets = {
    head: { target: "0 1.65 0", orbit: "0deg 55deg 0.45m", pos: "0 1.65 0" },
    heart: { target: "0 1.3 0.05", orbit: "0deg 45deg 0.5m", pos: "0 1.3 0" },
    lungs: { target: "0 1.4 0.05", orbit: "0deg 45deg 0.5m", pos: "0 1.4 0" },
    stomach: { target: "0 1.05 0", orbit: "0deg 50deg 0.45m", pos: "0 1.05 0" },
    intestines: { target: "0 0.9 0", orbit: "0deg 50deg 0.45m", pos: "0 0.9 0" },
    "right hand": { target: "0.3 1.0 0", orbit: "30deg 30deg 0.5m", pos: "0.3 1.0 0" },
    "left hand": { target: "-0.3 1.0 0", orbit: "-30deg 30deg 0.5m", pos: "-0.3 1.0 0" },
    legs: { target: "0 0.45 0", orbit: "0deg 75deg 0.5m", pos: "0 0.45 0" },
    back: { target: "0 1.3 -0.3", orbit: "180deg 40deg 0.5m", pos: "0 1.3 -0.3" },
  };

  const def = targets[target.toLowerCase()] || targets.heart;

  // Zoom model-viewer camera
  model.cameraTarget = def.target;
  model.cameraOrbit = def.orbit;
  model.jumpCameraToGoal();

  // Show hotspot with popup after zoom animation (~800ms)
  setTimeout(() => {
    const hotspot = document.createElement("button");
    hotspot.className = "Hotspot";
    hotspot.slot = "hotspot-1";
    hotspot.setAttribute("data-position", def.pos);
    hotspot.setAttribute("data-normal", "0 1 0");
    model.appendChild(hotspot);

    hotspot.onclick = (e) => {
      const rect = hotspot.getBoundingClientRect();
      popup.style.left = `${rect.left + 25}px`;
      popup.style.top = `${rect.top - 40}px`;
      popup.innerText = explanation || "Affected area";
      popup.style.display = "block";
      e.stopPropagation();
    };

    document.onclick = () => {
      popup.style.display = "none";
    };
  }, 800);
}

// Support Enter key to send message
chatInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    sendMessage();
    e.preventDefault();
  }
});

// Expose globally for button onclick
window.sendMessage = sendMessage;