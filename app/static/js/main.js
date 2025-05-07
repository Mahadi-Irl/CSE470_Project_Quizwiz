// Quiz taking functionality
document.addEventListener('DOMContentLoaded', function() {
    // Handle option selection
    const optionContainers = document.querySelectorAll('.option-container');
    optionContainers.forEach(container => {
        container.addEventListener('click', function() {
            const questionId = this.dataset.questionId;
            const optionId = this.dataset.optionId;
            
            // Remove selected class from other options in the same question
            document.querySelectorAll(`.option-container[data-question-id="${questionId}"]`).forEach(opt => {
                opt.classList.remove('selected');
            });
            
            // Add selected class to clicked option
            this.classList.add('selected');
            
            // Update hidden input
            const input = document.querySelector(`input[name="question_${questionId}"]`);
            if (input) {
                input.value = optionId;
            }
        });
    });

    // Quiz timer functionality
    const timerElement = document.getElementById('quiz-timer');
    if (timerElement) {
        const timeLimit = parseInt(timerElement.dataset.timeLimit);
        let timeLeft = timeLimit * 60; // Convert to seconds

        const timer = setInterval(() => {
            const minutes = Math.floor(timeLeft / 60);
            const seconds = timeLeft % 60;
            
            timerElement.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
            
            if (timeLeft <= 0) {
                clearInterval(timer);
                document.getElementById('quiz-form').submit();
            }
            
            timeLeft--;
        }, 1000);
    }

    // Bookmark functionality
    const bookmarkButtons = document.querySelectorAll('.bookmark-btn');
    bookmarkButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const quizId = this.dataset.quizId;
            
            fetch(`/quiz/${quizId}/bookmark`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            })
            .then(response => response.json())
            .then(data => {
                const icon = this.querySelector('i');
                if (data.status === 'added') {
                    icon.classList.remove('bi-bookmark');
                    icon.classList.add('bi-bookmark-fill');
                } else {
                    icon.classList.remove('bi-bookmark-fill');
                    icon.classList.add('bi-bookmark');
                }
            })
            .catch(error => console.error('Error:', error));
        });
    });

    // Form validation
    const forms = document.querySelectorAll('.needs-validation');
    Array.from(forms).forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });

    // Auto-dismiss alerts
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // Quiz search functionality
    const searchForm = document.getElementById('quiz-search-form');
    if (searchForm) {
        const searchInput = searchForm.querySelector('input[name="search"]');
        const categorySelect = searchForm.querySelector('select[name="category"]');
        
        function performSearch() {
            const searchTerm = searchInput.value.toLowerCase();
            const category = categorySelect.value;
            
            const quizCards = document.querySelectorAll('.quiz-card');
            quizCards.forEach(card => {
                const title = card.querySelector('.card-title').textContent.toLowerCase();
                const quizCategory = card.dataset.category;
                
                const matchesSearch = title.includes(searchTerm);
                const matchesCategory = !category || quizCategory === category;
                
                card.style.display = matchesSearch && matchesCategory ? 'block' : 'none';
            });
        }
        
        searchInput.addEventListener('input', performSearch);
        categorySelect.addEventListener('change', performSearch);
    }
}); 