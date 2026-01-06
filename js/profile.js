// Profile Management JavaScript
// Detect environment and set appropriate API URL
const API_BASE_URL = (() => {
  // If using file:// protocol (opening HTML file directly), use localhost
  if (window.location.protocol === 'file:') {
    console.warn('⚠️ File protocol detected. Please use http://localhost:8080 instead!');
    console.warn('   Start the server with: ./start_all.sh');
    // Use localhost for file:// protocol (fallback)
    return 'http://localhost:5001/api';
  }
  
  // Check if we're running on localhost (development)
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    // If port is 8080, use the proxy server which forwards to Flask
    if (window.location.port === '8080') {
      return '/api'; // Relative URL works with proxy server
    }
    // Direct Flask connection on other ports
    return 'http://localhost:5001/api';
  }
  
  // Production: use relative URL (backend on same domain)
  return '/api';
})();

document.addEventListener('DOMContentLoaded', function() {
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

    try {
      // Fetch profile from API
      const response = await fetch(`${API_BASE_URL}/users/profile?user_id=${currentUser.id}`);
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
        
        // Load profile picture
        if (profileData.profilePicture) {
          document.getElementById('profilePicture').src = profileData.profilePicture;
        } else {
          // Default avatar
          document.getElementById('profilePicture').src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgZmlsbD0iIzMzNDE1NSIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LXNpemU9IjQwIiBmaWxsPSIjOTRhM2I4IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBkeT0iLjNlbSI+8J+RpTwvdGV4dD48L3N2Zz4=';
        }

        // Load settings
        const settingsResponse = await fetch(`${API_BASE_URL}/users/settings?user_id=${currentUser.id}`);
        const settings = await settingsResponse.json();
        
        if (settingsResponse.ok) {
          if (settings.emailNotifications !== undefined) {
            document.getElementById('emailNotifications').checked = settings.emailNotifications;
          }
          if (settings.darkMode !== undefined) {
            document.getElementById('darkMode').checked = settings.darkMode;
          }
        }
      }
    } catch (apiError) {
      console.error('Error fetching from API, using localStorage fallback:', apiError);
      // Fallback to localStorage if API fails
      loadFromLocalStorage();
    }
  } catch (e) {
    console.error('Error loading profile data:', e);
    loadFromLocalStorage();
  }
}

// Fallback: Load from localStorage
function loadFromLocalStorage() {
  try {
    const currentUser = JSON.parse(localStorage.getItem('currentUser') || '{}');
    const profileData = JSON.parse(localStorage.getItem('userProfile') || '{}');
    
    if (currentUser.name) {
      document.getElementById('fullName').value = currentUser.name;
    } else if (profileData.fullName) {
      document.getElementById('fullName').value = profileData.fullName;
    }
    
    if (currentUser.email) {
      document.getElementById('email').value = currentUser.email;
    } else if (profileData.email) {
      document.getElementById('email').value = profileData.email;
    }
    
    if (profileData.bio) {
      document.getElementById('bio').value = profileData.bio;
    }
    
    const profilePicture = currentUser.profilePicture || profileData.profilePicture;
    if (profilePicture) {
      document.getElementById('profilePicture').src = profilePicture;
    } else {
      document.getElementById('profilePicture').src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgZmlsbD0iIzMzNDE1NSIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LXNpemU9IjQwIiBmaWxsPSIjOTRhM2I4IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBkeT0iLjNlbSI+8J+RpTwvdGV4dD48L3N2Zz4=';
    }
    
    const settings = JSON.parse(localStorage.getItem('userSettings') || '{}');
    if (settings.emailNotifications !== undefined) {
      document.getElementById('emailNotifications').checked = settings.emailNotifications;
    }
    if (settings.darkMode !== undefined) {
      document.getElementById('darkMode').checked = settings.darkMode;
    }
  } catch (e) {
    console.error('Error loading from localStorage:', e);
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
  reader.onload = async function(e) {
    const imageData = e.target.result;
    document.getElementById('profilePicture').src = imageData;
    
    const currentUser = JSON.parse(localStorage.getItem('currentUser') || '{}');
    if (!currentUser.id) {
      alert('Please log in to update your profile picture');
      return;
    }

    try {
      // Update via API
      const response = await fetch(`${API_BASE_URL}/users/profile`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          user_id: currentUser.id,
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
      // Fallback to localStorage
      const profileData = JSON.parse(localStorage.getItem('userProfile') || '{}');
      profileData.profilePicture = imageData;
      localStorage.setItem('userProfile', JSON.stringify(profileData));
      currentUser.profilePicture = imageData;
      localStorage.setItem('currentUser', JSON.stringify(currentUser));
      showNotification('Profile picture updated (saved locally)', 'success');
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
    const response = await fetch(`${API_BASE_URL}/users/profile`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        user_id: currentUser.id,
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
    // Fallback to localStorage
    const profileData = JSON.parse(localStorage.getItem('userProfile') || '{}');
    profileData.fullName = fullName;
    profileData.email = email;
    profileData.bio = bio;
    localStorage.setItem('userProfile', JSON.stringify(profileData));
    if (fullName) currentUser.name = fullName;
    if (email) currentUser.email = email;
    localStorage.setItem('currentUser', JSON.stringify(currentUser));
    showNotification('Profile updated (saved locally)', 'success');
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
    const response = await fetch(`${API_BASE_URL}/users/password`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        user_id: currentUser.id,
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
    emailNotifications: document.getElementById('emailNotifications').checked,
    darkMode: document.getElementById('darkMode').checked
  };
  
  const currentUser = JSON.parse(localStorage.getItem('currentUser') || '{}');
  if (!currentUser.id) {
    alert('Please log in to save settings');
    return;
  }

  try {
    // Save via API
    const response = await fetch(`${API_BASE_URL}/users/settings`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        user_id: currentUser.id,
        emailNotifications: settings.emailNotifications,
        darkMode: settings.darkMode
      })
    });

    if (response.ok) {
      // Also save to localStorage for session
      localStorage.setItem('userSettings', JSON.stringify(settings));
      showNotification('Settings saved successfully!', 'success');
    } else {
      throw new Error('Failed to save settings');
    }
  } catch (error) {
    console.error('Error saving settings:', error);
    // Fallback to localStorage
    localStorage.setItem('userSettings', JSON.stringify(settings));
    showNotification('Settings saved (saved locally)', 'success');
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
  if (!currentUser.id) {
    alert('Please log in to delete your account');
    return;
  }

  try {
    // Delete via API
    const response = await fetch(`${API_BASE_URL}/users/delete?user_id=${currentUser.id}`, {
      method: 'DELETE'
    });

    if (response.ok) {
      // Clear local data
      localStorage.removeItem('currentUser');
      localStorage.removeItem('userProfile');
      localStorage.removeItem('userSettings');
      
      // Redirect to login
      window.location.href = 'login.html';
    } else {
      const data = await response.json();
      throw new Error(data.error || 'Failed to delete account');
    }
  } catch (error) {
    alert(error.message || 'Failed to delete account');
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
