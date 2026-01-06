// Run this script in your browser console to export users data to CSV
// Copy and paste this into the browser console

(function() {
    try {
        const usersStr = localStorage.getItem('users');
        const currentUserStr = localStorage.getItem('currentUser');
        const profileStr = localStorage.getItem('userProfile');
        const settingsStr = localStorage.getItem('userSettings');

        const users = usersStr ? JSON.parse(usersStr) : [];
        const currentUser = currentUserStr ? JSON.parse(currentUserStr) : null;
        const profile = profileStr ? JSON.parse(profileStr) : {};
        const settings = settingsStr ? JSON.parse(settingsStr) : {};

        if (users.length === 0) {
            console.log('No users found in localStorage');
            return;
        }

        // Create CSV header
        const headers = ['id', 'name', 'email', 'password_hash', 'fullName', 'bio', 'profilePicture', 'emailNotifications', 'darkMode'];
        let csv = headers.join(',') + '\n';

        // Helper function to escape CSV values
        const escapeCSV = (value) => {
            if (value === null || value === undefined) return '';
            const str = String(value);
            if (str.includes(',') || str.includes('"') || str.includes('\n')) {
                return '"' + str.replace(/"/g, '""') + '"';
            }
            return str;
        };

        // Add user data
        users.forEach(user => {
            const isCurrentUser = currentUser && user.email === currentUser.email;
            const userProfile = isCurrentUser ? profile : {};
            const userSettings = isCurrentUser ? settings : {};

            const row = [
                escapeCSV(user.id || ''),
                escapeCSV(user.name || ''),
                escapeCSV(user.email || ''),
                escapeCSV(user.password || ''),
                escapeCSV(userProfile.fullName || user.name || ''),
                escapeCSV(userProfile.bio || ''),
                escapeCSV(userProfile.profilePicture || currentUser?.profilePicture || ''),
                escapeCSV(userSettings.emailNotifications || false),
                escapeCSV(userSettings.darkMode || false)
            ];
            csv += row.join(',') + '\n';
        });

        console.log('=== CSV DATA (Copy and save as .csv file) ===');
        console.log(csv);
        console.log('=== END OF CSV DATA ===');
        
        // Try to copy to clipboard
        if (navigator.clipboard) {
            navigator.clipboard.writeText(csv).then(() => {
                console.log('\n✓ Copied to clipboard!');
                console.log('Save it as users_export.csv');
            }).catch(() => {
                console.log('\n(Clipboard copy failed, but data is above)');
            });
        }
        
        return csv;
    } catch (error) {
        console.error('Error exporting data:', error);
    }
})();
