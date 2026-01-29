// Home page code animation
document.addEventListener('DOMContentLoaded', function () {
    const codeElement = document.getElementById('codeAnimation');
    if (!codeElement) return;

    // Code to animate
    const code = `# Import the necessary libraries
from sklearn.datasets import load_wine
import pandas as pd

# Load the wine dataset from scikit-learn
wine = load_wine()

# Create a DataFrame from the dataset's data and feature names
df_wine = pd.DataFrame(data=wine.data, columns=wine.feature_names)

# Add the target column (the wine cultivar) to the DataFrame
df_wine['target'] = wine.target

# Display the first 5 rows of the DataFrame
print(df_wine.head())`;

    let currentCharIndex = 0;
    let isDeleting = false;
    let typingSpeed = 30;
    let deletingSpeed = 15;
    let pauseTime = 2000;

    function typeCode() {
        const codeLine = codeElement.querySelector('.code-line');
        if (!codeLine) return;

        // Escape HTML helper
        const escapeHtml = (text) => {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        };

        if (!isDeleting && currentCharIndex < code.length) {
            // Typing
            const currentText = code.substring(0, currentCharIndex + 1);
            codeLine.innerHTML = escapeHtml(currentText) + '<span class="cursor">|</span>';
            currentCharIndex++;
            setTimeout(typeCode, typingSpeed);
        } else if (isDeleting && currentCharIndex > 0) {
            // Deleting
            const currentText = code.substring(0, currentCharIndex - 1);
            codeLine.innerHTML = escapeHtml(currentText) + '<span class="cursor">|</span>';
            currentCharIndex--;
            setTimeout(typeCode, deletingSpeed);
        } else if (!isDeleting && currentCharIndex === code.length) {
            // Pause at end - remove cursor
            const currentText = code.substring(0, currentCharIndex);
            codeLine.innerHTML = escapeHtml(currentText);
            isDeleting = true;
            setTimeout(typeCode, pauseTime);
        } else if (isDeleting && currentCharIndex === 0) {
            // Restart
            isDeleting = false;
            codeLine.innerHTML = '<span class="cursor">|</span>';
            setTimeout(typeCode, 500);
        }
    }

    // Start animation
    typeCode();
});
