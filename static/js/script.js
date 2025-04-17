document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const uploadForm = document.getElementById('uploadForm');
    const fileInput = document.querySelector('input[type="file"]');
    const previewImg = document.getElementById('preview');
    const similarContainer = document.getElementById('similarItems');
    const accessoriesContainer = document.getElementById('accessories');
    const resultsSection = document.getElementById('results');
    const submitBtn = uploadForm.querySelector('button');

    // Image Preview Handler
    fileInput.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function(event) {
                previewImg.src = event.target.result;
                previewImg.style.display = 'block';
            };
            reader.readAsDataURL(file);
        }
    });

    // Form Submission Handler
    uploadForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // UI Loading State
        submitBtn.disabled = true;
        submitBtn.innerHTML = `
            <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
            Analyzing...
        `;
        resultsSection.style.opacity = '0.5';
        
        try {
            const formData = new FormData(uploadForm);
            
            // Send to Flask backend
            const response = await fetch('/recommend', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            // Display Results
            displayUploadedImage(data.uploaded_image);
            displayRecommendations(data.similar, similarContainer, 'Similar Items');
            displayRecommendations(data.accessories, accessoriesContainer, 'Recommended Accessories');
            
        } catch (error) {
            console.error('Error:', error);
            showErrorToast('Failed to get recommendations. Please try again.');
        } finally {
            // Reset UI
            submitBtn.disabled = false;
            submitBtn.textContent = 'Get Recommendations';
            resultsSection.style.opacity = '1';
        }
    });

    // Display Uploaded Image
    function displayUploadedImage(imagePath) {
        previewImg.src = imagePath;
        previewImg.style.display = 'block';
        previewImg.alt = "Your uploaded outfit";
    }

    // Display Recommendation Cards
    function displayRecommendations(items, container, sectionTitle) {
        container.innerHTML = '';
        
        if (!items || items.length === 0) {
            container.innerHTML = `
                <div class="col-12 text-center py-4">
                    <p class="text-muted">No ${sectionTitle.toLowerCase()} found</p>
                </div>
            `;
            return;
        }
        
        const header = document.createElement('h3');
        header.className = 'recommendation-header';
        header.textContent = sectionTitle;
        container.appendChild(header);
        
        const cardWrapper = document.createElement('div');
        cardWrapper.className = 'card-wrapper';
        
        items.forEach(item => {
            const card = createRecommendationCard(item);
            cardWrapper.appendChild(card);
        });
        
        container.appendChild(cardWrapper);
    }

    // Create Individual Card
    function createRecommendationCard(item) {
        const card = document.createElement('div');
        card.className = 'recommendation-card';
        
        card.innerHTML = `
            <div class="card-image-container">
                <img src="/static/inventory/${item.file_path}" alt="${item.productDisplayName}" 
                     onerror="this.src='/static/images/placeholder.jpg'">
            </div>
            <div class="card-body">
                <h5 class="card-title">${item.productDisplayName || 'Fashion Item'}</h5>
                <p class="card-price">${item.price || '$XX.XX'}</p>
                <button class="btn-details">View Details</button>
            </div>
        `;
        
        // Add click handler for card interaction
        card.addEventListener('click', function() {
            // Implement card click behavior (e.g., modal popup)
            console.log('Selected item:', item);
        });
        
        return card;
    }

    // Error Notification
    function showErrorToast(message) {
        const toast = document.createElement('div');
        toast.className = 'error-toast';
        toast.textContent = message;
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.classList.add('fade-out');
            setTimeout(() => toast.remove(), 500);
        }, 3000);
    }

    // Initialize tooltips for cards
    function initTooltips() {
        $(document).ready(function(){
            $('[data-toggle="tooltip"]').tooltip(); 
        });
    }
});