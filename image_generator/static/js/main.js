document.addEventListener('DOMContentLoaded', () => {
    const modal = document.getElementById('imageModal');
    const modalImage = document.getElementById('modalImage');
    const closeModal = document.querySelector('.close-modal');

    document.querySelectorAll('.preview-btn').forEach(button => {
        button.addEventListener('click', (e) => {
            e.preventDefault();
            const imageUrl = button.getAttribute('data-src');
            modalImage.src = imageUrl;
            modal.style.display = 'flex';
        });
    });

    if (closeModal) {
        closeModal.addEventListener('click', () => {
            modal.style.display = 'none';
        });
    }

    window.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.style.display = 'none';
        }
    });
});
