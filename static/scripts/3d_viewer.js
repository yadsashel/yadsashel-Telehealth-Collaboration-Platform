document.addEventListener('DOMContentLoaded', () => {
  const tabButtons = document.querySelectorAll('[data-tab]');
  const contentSections = document.querySelectorAll('[data-content]');

  tabButtons.forEach(button => {
    button.addEventListener('click', () => {
      const target = button.getAttribute('data-tab');

      // Remove "active" class from all buttons
      tabButtons.forEach(btn => btn.classList.remove('active'));

      // Add "active" class to clicked button
      button.classList.add('active');

      // Hide all viewer sections
      contentSections.forEach(section => {
        section.style.display = 'none';
      });

      // Show the selected viewer section
      const targetSection = document.querySelector(`[data-content="${target}"]`);
      if (targetSection) {
        targetSection.style.display = 'block';
      }
    });
  });
});