// Profile Management JavaScript
document.addEventListener('DOMContentLoaded', function() {
  loadProfileData();
  setupEventListeners();
});

// Load user profile data
function loadProfileData() {
  try {
    const currentUser = JSON.parse(localStorage.getItem('currentUser') || '{}');
    const profileData = JSON.parse(localStorage.getItem('userProfile') || '{}');
    
    // Load personal information
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
    
    // Load profile picture - check currentUser first, then profileData
    const profilePicture = currentUser.profilePicture || profileData.profilePicture;
    if (profilePicture) {
      document.getElementById('profilePicture').src = profilePicture;
    } else {
      // Default avatar
      document.getElementById('profilePicture').src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgZmlsbD0iIzMzNDE1NSIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LXNpemU9IjQwIiBmaWxsPSIjOTRhM2I4IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBkeT0iLjNlbSI+8J+RpTwvdGV4dD48L3N2Zz4=';
    }
    
    // Load settings
    const settings = JSON.parse(localStorage.getItem('userSettings') || '{}');
    if (settings.emailNotifications !== undefined) {
      document.getElementById('emailNotifications').checked = settings.emailNotifications;
    }
    if (settings.darkMode !== undefined) {
      document.getElementById('darkMode').checked = settings.darkMode;
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
}

// Handle profile picture upload
function handleProfilePictureUpload(event) {
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
  reader.onload = function(e) {
    const imageData = e.target.result;
    document.getElementById('profilePicture').src = imageData;
    
    // Save to localStorage
    const profileData = JSON.parse(localStorage.getItem('userProfile') || '{}');
    profileData.profilePicture = imageData;
    localStorage.setItem('userProfile', JSON.stringify(profileData));
    
    // Update current user
    const currentUser = JSON.parse(localStorage.getItem('currentUser') || '{}');
    currentUser.profilePicture = imageData;
    localStorage.setItem('currentUser', JSON.stringify(currentUser));
    
    // Update navigation profile picture if function exists
    if (typeof updateNavProfilePicture === 'function') {
      updateNavProfilePicture();
    }
    
    // Dispatch custom event to update navigation on other pages
    window.dispatchEvent(new CustomEvent('profilePictureUpdated'));
    
    showNotification('Profile picture updated successfully!', 'success');
  };
  reader.readAsDataURL(file);
}

// Handle personal information form submission
function handlePersonalInfoSubmit(event) {
  event.preventDefault();
  
  const fullName = document.getElementById('fullName').value.trim();
  const email = document.getElementById('email').value.trim();
  const bio = document.getElementById('bio').value.trim();
  
  // Validate email
  if (email && !isValidEmail(email)) {
    alert('Please enter a valid email address');
    return;
  }
  
  // Save to localStorage
  const profileData = JSON.parse(localStorage.getItem('userProfile') || '{}');
  profileData.fullName = fullName;
  profileData.email = email;
  profileData.bio = bio;
  localStorage.setItem('userProfile', JSON.stringify(profileData));
  
  // Update current user
  const currentUser = JSON.parse(localStorage.getItem('currentUser') || '{}');
  if (fullName) currentUser.name = fullName;
  if (email) currentUser.email = email;
  localStorage.setItem('currentUser', JSON.stringify(currentUser));
  
  showNotification('Profile information updated successfully!', 'success');
}

// Handle password change
function handlePasswordChange(event) {
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
  
  // Verify current password
  const currentUser = JSON.parse(localStorage.getItem('currentUser') || '{}');
  const users = JSON.parse(localStorage.getItem('users') || '[]');
  const user = users.find(u => u.email === currentUser.email);
  
  if (!user || user.password !== currentPassword) {
    alert('Current password is incorrect');
    return;
  }
  
  // Update password
  user.password = newPassword;
  localStorage.setItem('users', JSON.stringify(users));
  
  // Clear form
  document.getElementById('passwordForm').reset();
  
  showNotification('Password updated successfully!', 'success');
}

// Save settings
function saveSettings() {
  const settings = {
    emailNotifications: document.getElementById('emailNotifications').checked,
    darkMode: document.getElementById('darkMode').checked
  };
  
  localStorage.setItem('userSettings', JSON.stringify(settings));
  showNotification('Settings saved successfully!', 'success');
}

// Delete account
function deleteAccount() {
  if (!confirm('Are you sure you want to delete your account? This action cannot be undone.')) {
    return;
  }
  
  if (!confirm('This will permanently delete all your data. Are you absolutely sure?')) {
    return;
  }
  
  // Remove user from users list
  const currentUser = JSON.parse(localStorage.getItem('currentUser') || '{}');
  const users = JSON.parse(localStorage.getItem('users') || '[]');
  const filteredUsers = users.filter(u => u.email !== currentUser.email);
  localStorage.setItem('users', JSON.stringify(filteredUsers));
  
  // Clear user data
  localStorage.removeItem('currentUser');
  localStorage.removeItem('userProfile');
  localStorage.removeItem('userSettings');
  
  // Redirect to login
  window.location.href = 'login.html';
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

