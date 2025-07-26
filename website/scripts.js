// Main JavaScript for the Doctrine of Frequency website
// This file can be used for interactive elements, animations, or data loading.

document.addEventListener('DOMContentLoaded', () => {
    console.log("Doctrine of Frequency website scripts loaded.");

    // Example: Add a simple hover effect to CTA tiles if not handled by Tailwind
    const ctaTiles = document.querySelectorAll('.law-preview-tile'); // Assuming a class for these tiles
    ctaTiles.forEach(tile => {
        tile.addEventListener('mouseenter', () => {
            // Add hover class or direct style changes
            tile.style.transform = 'scale(1.05)';
        });
        tile.addEventListener('mouseleave', () => {
            // Remove hover class or revert style changes
            tile.style.transform = 'scale(1)';
        });
    });

    // Future: Implement custom cursor logic, dynamic content loading, etc.
});
