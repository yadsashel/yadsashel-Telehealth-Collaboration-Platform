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

//messages
document.addEventListener("DOMContentLoaded", () => {
  const socket = io();

  const currentUserId = document.getElementById("current-user-id").value;
  const contactId = document.getElementById("contact-id").value;

  const messageInput = document.getElementById("messageInput");
  const sendButton = document.getElementById("sendButton");
  const messagesContainer = document.getElementById("messagesContainer");

  // Join own room so server can send you messages
  socket.emit('join_room', { user_id: currentUserId });

  // Append message to chat area
  function appendMessage(data) {
    const isMe = data.sender_id == currentUserId;
    const div = document.createElement("div");
    div.className = `msg-bubble ${isMe ? 'right' : 'left'}`;
    div.innerHTML = `<p>${data.content}</p><span class="msg-time">${data.timestamp}</span>`;
    messagesContainer.appendChild(div);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  // Send message via socket
  sendButton.addEventListener('click', (e) => {
    e.preventDefault();
    const message = messageInput.value.trim();
    if (!message) return;

    socket.emit('send_message', {
      sender_id: currentUserId,
      receiver_id: contactId,
      content: message
    });

    appendMessage({ sender_id: currentUserId, content: message, timestamp: new Date().toLocaleTimeString() });
    messageInput.value = '';
  });

  messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      sendButton.click();
    }
  });

  // Listen for incoming messages
  socket.on('receive_message', (data) => {
    // Only show messages from your current chat contact
    if (data.sender_id == contactId && data.receiver_id == currentUserId) {
      appendMessage(data);
    }
  });
});
