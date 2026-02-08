// Contact Form Handler
document.addEventListener('DOMContentLoaded', function () {
  // Require authentication
  const authManager = new AuthManager();
  if (!authManager.requireAuth()) {
    return; // Will redirect to login
  }

  const contactForm = document.getElementById('contactForm');
  const statusDiv = document.getElementById('contactMessageStatus');

  // Pre-fill email if user is logged in
  const currentUser = authManager.getCurrentUser();
  if (currentUser && currentUser.email) {
    const emailInput = document.getElementById('contactEmail');
    if (emailInput) {
      emailInput.value = currentUser.email;
    }
  }

  // Pre-fill name if available
  if (currentUser && (currentUser.name || currentUser.fullName)) {
    const nameInput = document.getElementById('contactName');
    if (nameInput) {
      nameInput.value = currentUser.name || currentUser.fullName || '';
    }
  }

  if (contactForm) {
    contactForm.addEventListener('submit', async function (e) {
      e.preventDefault();

      const formData = {
        name: document.getElementById('contactName').value.trim(),
        email: document.getElementById('contactEmail').value.trim(),
        subject: document.getElementById('contactSubject').value,
        message: document.getElementById('contactMessage').value.trim()
      };

      // Validate form
      if (!formData.name || !formData.email || !formData.subject || !formData.message) {
        showStatus('Please fill in all fields', 'error');
        return;
      }

      // Show loading state
      const submitButton = contactForm.querySelector('button[type="submit"]');
      const originalButtonText = submitButton.textContent;
      submitButton.disabled = true;
      submitButton.textContent = 'Sending...';
      showStatus('Sending your message...', 'info');

      try {
        // Send to API endpoint
        const response = await authFetch(`${window.API_BASE_URL}/contact`, {
          method: 'POST',
          body: JSON.stringify({
            name: formData.name,
            email: formData.email,
            subject: formData.subject,
            message: formData.message
          })
        });

        const result = await response.json();

        if (!response.ok) {
          console.error('Contact form error response:', result);
          throw new Error(result.error || `Failed to submit contact form (${response.status})`);
        }

        // Show success message
        showStatus('Thank you for contacting us! We\'ll get back to you soon.', 'success');

        // Reset form
        contactForm.reset();

        // Re-fill email if user is logged in
        if (currentUser && currentUser.email) {
          document.getElementById('contactEmail').value = currentUser.email;
        }
        if (currentUser && (currentUser.name || currentUser.fullName)) {
          document.getElementById('contactName').value = currentUser.name || currentUser.fullName || '';
        }

      } catch (error) {
        console.error('Error submitting contact form:', error);
        showStatus(error.message || 'There was an error sending your message. Please try again.', 'error');
      } finally {
        submitButton.disabled = false;
        submitButton.textContent = originalButtonText;
      }
    });
  }

  function showStatus(message, type) {
    if (!statusDiv) return;

    statusDiv.textContent = message;
    statusDiv.className = 'message-status';
    statusDiv.classList.add(type);
    statusDiv.style.display = 'block';

    // Auto-hide after 5 seconds for success/info, keep error visible
    if (type === 'success' || type === 'info') {
      setTimeout(() => {
        statusDiv.style.display = 'none';
      }, 5000);
    }
  }
});
