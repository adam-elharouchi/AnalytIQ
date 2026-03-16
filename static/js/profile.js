// Profile Management JavaScript
// API_BASE_URL should be defined in api-helper.js
if (typeof window.API_BASE_URL === 'undefined') {
  window.API_BASE_URL = '/api';
}

document.addEventListener('DOMContentLoaded', function () {
  loadProfileData();
  setupEventListeners();
});

// Load user profile data
async function loadProfileData() {
  try {
    const currentUser = JSON.parse(localStorage.getItem('currentUser') || '{}');

    if (!currentUser.id) {
      console.error('No user logged in');
      return;
    }

    // Load profile picture IMMEDIATELY from localStorage (instant, no delay)
    const profilePictureEl = document.getElementById('profilePicture');
    const defaultAvatar = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgZmlsbD0iIzMzNDE1NSIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LXNpemU9IjQwIiBmaWxsPSIjOTRhM2I4IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBkeT0iLjNlbSI+8J+RpTwvdGV4dD48L3N2Zz4=';
    if (profilePictureEl) {
      profilePictureEl.src = currentUser.profilePicture || defaultAvatar;
    }

    try {
      // Fetch profile from API (update in background)
      const response = await authFetch(`${window.API_BASE_URL}/users/profile`);
      const profileData = await response.json();

      if (response.ok) {
        // Load personal information
        if (profileData.fullName || profileData.name) {
          document.getElementById('fullName').value = profileData.fullName || profileData.name;
        }

        if (profileData.email) {
          document.getElementById('email').value = profileData.email;
        }

        if (profileData.bio) {
          document.getElementById('bio').value = profileData.bio;
        }

        // Update profile picture from API (if different from localStorage)
        if (profilePictureEl && profileData.profilePicture) {
          if (profileData.profilePicture !== currentUser.profilePicture) {
            profilePictureEl.src = profileData.profilePicture;
            // Update localStorage with API value
            currentUser.profilePicture = profileData.profilePicture;
            localStorage.setItem('currentUser', JSON.stringify(currentUser));
          }
        } else if (profilePictureEl && !profileData.profilePicture) {
          // Use default if API doesn't have a picture
          profilePictureEl.src = defaultAvatar;
        }

        // Load settings
        const settingsResponse = await authFetch(`${window.API_BASE_URL}/users/settings`);
        const settings = await settingsResponse.json();

        if (settingsResponse.ok) {
          if (settings.emailNotifications !== undefined) {
            const emailToggle = document.getElementById('emailNotifications');
            if (emailToggle) {
              emailToggle.checked = settings.emailNotifications;
            }
          }
        }
      }
    } catch (apiError) {
      console.error('Error fetching from API:', apiError);
    }
  } catch (e) {
    console.error('Error loading profile data:', e);
  }
}

// Setup event listeners
function setupEventListeners() {
  // Profile picture upload
  const profilePictureInput = document.getElementById('profilePictureInput');
  profilePictureInput.addEventListener('change', handleProfilePictureUpload);

  // Personal information form
  const personalInfoForm = document.getElementById('personalInfoForm');
  personalInfoForm.addEventListener('submit', handlePersonalInfoSubmit);

  // Password form
  const passwordForm = document.getElementById('passwordForm');
  passwordForm.addEventListener('submit', handlePasswordChange);

  // Email notifications toggle - auto-save on change
  const emailNotificationsToggle = document.getElementById('emailNotifications');
  if (emailNotificationsToggle) {
    emailNotificationsToggle.addEventListener('change', async function () {
      await saveSettings();
    });
  }
}

// Handle profile picture upload
async function handleProfilePictureUpload(event) {
  const file = event.target.files[0];
  if (!file) return;

  // Validate file type
  if (!file.type.startsWith('image/')) {
    alert('Please select an image file');
    return;
  }

  // Validate file size (max 5MB)
  if (file.size > 5 * 1024 * 1024) {
    alert('Image size must be less than 5MB');
    return;
  }

  const reader = new FileReader();
  reader.onload = async function (e) {
    const imageData = e.target.result;
    document.getElementById('profilePicture').src = imageData;

    const currentUser = JSON.parse(localStorage.getItem('currentUser') || '{}');
    if (!currentUser.id) {
      alert('Please log in to update your profile picture');
      return;
    }

    try {
      // Update via API
      const response = await authFetch(`${window.API_BASE_URL}/users/profile`, {
        method: 'PUT',
        body: JSON.stringify({
          profilePicture: imageData
        })
      });

      if (response.ok) {
        // Also update localStorage for session
        currentUser.profilePicture = imageData;
        localStorage.setItem('currentUser', JSON.stringify(currentUser));

        // Update navigation profile picture if function exists
        if (typeof updateNavProfilePicture === 'function') {
          updateNavProfilePicture();
        }

        window.dispatchEvent(new CustomEvent('profilePictureUpdated'));
        showNotification('Profile picture updated successfully!', 'success');
      } else {
        throw new Error('Failed to update profile picture');
      }
    } catch (error) {
      console.error('Error updating profile picture:', error);
      showNotification('Failed to update profile picture', 'error');
    }
  };
  reader.readAsDataURL(file);
}

// Handle personal information form submission
async function handlePersonalInfoSubmit(event) {
  event.preventDefault();

  const fullName = document.getElementById('fullName').value.trim();
  const email = document.getElementById('email').value.trim();
  const bio = document.getElementById('bio').value.trim();

  // Validate email
  if (email && !isValidEmail(email)) {
    alert('Please enter a valid email address');
    return;
  }

  const currentUser = JSON.parse(localStorage.getItem('currentUser') || '{}');
  if (!currentUser.id) {
    alert('Please log in to update your profile');
    return;
  }

  try {
    // Update via API
    const response = await authFetch(`${window.API_BASE_URL}/users/profile`, {
      method: 'PUT',
      body: JSON.stringify({
        fullName: fullName,
        email: email,
        bio: bio
      })
    });

    if (response.ok) {
      // Update localStorage for session
      if (fullName) currentUser.name = fullName;
      if (email) currentUser.email = email;
      localStorage.setItem('currentUser', JSON.stringify(currentUser));

      showNotification('Profile information updated successfully!', 'success');
    } else {
      const data = await response.json();
      throw new Error(data.error || 'Failed to update profile');
    }
  } catch (error) {
    console.error('Error updating profile:', error);
    showNotification('Failed to update profile', 'error');
  }
}

// Handle password change
async function handlePasswordChange(event) {
  event.preventDefault();

  const currentPassword = document.getElementById('currentPassword').value;
  const newPassword = document.getElementById('newPassword').value;
  const confirmPassword = document.getElementById('confirmPassword').value;

  // Validate inputs
  if (!currentPassword || !newPassword || !confirmPassword) {
    alert('Please fill in all password fields');
    return;
  }

  // Validate new password length
  if (newPassword.length < 8) {
    alert('New password must be at least 8 characters long');
    return;
  }
  if (newPassword.length > 72) {
    alert('New password must be at most 72 characters long');
    return;
  }

  // Check if passwords match
  if (newPassword !== confirmPassword) {
    alert('New passwords do not match');
    return;
  }

  const currentUser = JSON.parse(localStorage.getItem('currentUser') || '{}');
  if (!currentUser.id) {
    alert('Please log in to change your password');
    return;
  }

  try {
    // Update password via API
    const response = await authFetch(`${window.API_BASE_URL}/users/password`, {
      method: 'PUT',
      body: JSON.stringify({
        currentPassword: currentPassword,
        newPassword: newPassword
      })
    });

    const data = await response.json();

    if (response.ok) {
      // Clear form
      document.getElementById('passwordForm').reset();
      showNotification('Password updated successfully!', 'success');
    } else {
      throw new Error(data.error || 'Failed to update password');
    }
  } catch (error) {
    alert(error.message || 'Failed to update password');
  }
}

// Save settings
async function saveSettings() {
  const settings = {
    emailNotifications: document.getElementById('emailNotifications').checked
  };

  const currentUser = JSON.parse(localStorage.getItem('currentUser') || '{}');
  if (!currentUser.id) {
    alert('Please log in to save settings');
    return;
  }

  // Save to localStorage first (always works)
  localStorage.setItem('userSettings', JSON.stringify(settings));

  try {
    // Try to save via API (non-blocking)
    const response = await authFetch(`${window.API_BASE_URL}/users/settings`, {
      method: 'PUT',
      body: JSON.stringify({
        emailNotifications: settings.emailNotifications
      })
    });

    if (response.ok) {
      showNotification('Settings saved successfully!', 'success');
    } else {
      // API failed but localStorage saved - settings still work
      showNotification('Settings saved locally', 'success');
    }
  } catch (error) {
    // API failed but localStorage saved - settings still work
    showNotification('Settings saved locally', 'success');
  }
}

// Delete account
async function deleteAccount() {
  if (!confirm('Are you sure you want to delete your account? This action cannot be undone.')) {
    return;
  }

  if (!confirm('This will permanently delete all your data. Are you absolutely sure?')) {
    return;
  }

  const currentUser = JSON.parse(localStorage.getItem('currentUser') || '{}');

  // Get user_id - check both 'id' and 'user_id' fields for compatibility
  const userId = currentUser.user_id || currentUser.id;

  if (!userId) {
    alert('Please log in to delete your account');
    return;
  }

  try {
    // Delete via API - ensure user_id is a string
    const response = await authFetch(`${window.API_BASE_URL}/users/delete`, {
      method: 'DELETE'
    });

    const data = await response.json();

    if (response.ok) {
      // Clear local data
      localStorage.clear();

      // Redirect to login
      window.location.href = '/login';
    } else {
      throw new Error(data.error || 'Failed to delete account');
    }
  } catch (error) {
    console.error('Error deleting account:', error);
    alert(error.message || 'Failed to delete account. Please try again.');
  }
}

// Helper function to validate email
function isValidEmail(email) {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

// Show notification
function showNotification(message, type = 'success') {
  // Remove existing notifications
  const existingNotification = document.querySelector('.notification');
  if (existingNotification) {
    existingNotification.remove();
  }

  // Create notification element
  const notification = document.createElement('div');
  notification.className = `notification notification-${type}`;
  notification.textContent = message;

  // Add to page
  document.body.appendChild(notification);

  // Show notification
  setTimeout(() => {
    notification.classList.add('show');
  }, 10);

  // Hide and remove after 3 seconds
  setTimeout(() => {
    notification.classList.remove('show');
    setTimeout(() => {
      notification.remove();
    }, 300);
  }, 3000);
}
