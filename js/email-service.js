// Email Service - Simulates sending emails (for demo purposes)
// In a production environment, this would connect to an actual email service API

class EmailService {
  constructor() {
    this.sentEmails = JSON.parse(localStorage.getItem('sentEmails') || '[]');
  }

  // Send welcome email to new user
  async sendWelcomeEmail(userEmail, userName) {
    const emailData = {
      to: userEmail,
      subject: 'Welcome to AnalytIQ! 🎉',
      template: 'welcome',
      sentAt: new Date().toISOString(),
      userName: userName
    };

    // Generate email content
    const emailContent = this.generateWelcomeEmail(userName);

    // In a real application, this would make an API call to send the email
    // For demo purposes, we'll simulate it and store it locally
    try {
      // Simulate API delay
      await this.simulateEmailSend();
      
      // Store email record
      this.sentEmails.push({
        ...emailData,
        content: emailContent,
        status: 'sent'
      });
      localStorage.setItem('sentEmails', JSON.stringify(this.sentEmails));

      // Log to console for demo purposes
      console.log('📧 Welcome Email Sent:', {
        to: userEmail,
        subject: emailData.subject,
        content: emailContent
      });

      return {
        success: true,
        message: 'Welcome email sent successfully!',
        emailData: emailData
      };
    } catch (error) {
      console.error('Error sending welcome email:', error);
      return {
        success: false,
        message: 'Failed to send welcome email',
        error: error.message
      };
    }
  }

  // Generate welcome email content
  generateWelcomeEmail(userName) {
    return `
<!DOCTYPE html>
<html>
<head>
  <style>
    body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
    .container { max-width: 600px; margin: 0 auto; padding: 20px; }
    .header { background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
    .content { background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }
    .button { display: inline-block; padding: 12px 30px; background: #10b981; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }
    .footer { text-align: center; color: #6b7280; font-size: 12px; margin-top: 20px; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>Welcome to AnalytIQ! 🎉</h1>
    </div>
    <div class="content">
      <h2>Hello ${userName || 'there'}!</h2>
      <p>We're thrilled to have you join the AnalytIQ community! You've taken the first step towards mastering data analytics.</p>
      
      <h3>What's Next?</h3>
      <ul>
        <li><strong>Explore Modules:</strong> Start with our structured learning paths from beginner to advanced</li>
        <li><strong>Practice Your Skills:</strong> Try hands-on exercises and coding challenges</li>
        <li><strong>Use Code:</strong> Get AI-powered help with your data analysis projects</li>
        <li><strong>Access Resources:</strong> Browse our library of articles, videos, and datasets</li>
      </ul>
      
      <p style="text-align: center;">
        <a href="#" class="button">Get Started Now</a>
      </p>
      
      <p>If you have any questions or need help, don't hesitate to reach out. We're here to support your learning journey!</p>
      
      <p>Happy learning!<br>
      <strong>The AnalytIQ Team</strong></p>
    </div>
    <div class="footer">
      <p>This email was sent to you because you created an account on AnalytIQ.</p>
      <p>© ${new Date().getFullYear()} AnalytIQ. All rights reserved.</p>
    </div>
  </div>
</body>
</html>
    `.trim();
  }

  // Simulate email sending delay
  simulateEmailSend() {
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve();
      }, 500); // Simulate 500ms API call
    });
  }

  // Get sent emails (for admin/debugging purposes)
  getSentEmails() {
    return this.sentEmails;
  }

  // Clear email history
  clearEmailHistory() {
    this.sentEmails = [];
    localStorage.removeItem('sentEmails');
  }
}

// Global email service instance
const emailService = new EmailService();

