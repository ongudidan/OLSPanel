// Initialize Hamburger Menu
function initHamburgerMenu() {
    const hamburger = document.querySelector('.hamburger');
    const navContainer = document.querySelector('.nav-container');

    hamburger.addEventListener('click', () => {
        hamburger.classList.toggle('active');
        navContainer.classList.toggle('active');
    });

    // Close the menu when a nav link is clicked
    const navLinks = document.querySelectorAll('.nav-links a');
    navLinks.forEach(link => {
        link.addEventListener('click', () => {
            hamburger.classList.remove('active');
            navContainer.classList.remove('active');
        });
    });
}

// Initialize Slideshow
function initSlideshow() {
    let slideIndex = 0;
    const slides = document.getElementsByClassName('slide');
    const dots = document.getElementsByClassName('dot');

    // If there are no slides, return early to avoid errors
    if (slides.length === 0 || dots.length === 0) {
        console.log('No slides or dots found for slideshow.');
        return;
    }

    function showSlides() {
        // Hide all slides and remove active dot
        for (let i = 0; i < slides.length; i++) {
            slides[i].style.display = 'none';
            slides[i].classList.remove('fade');
            dots[i].classList.remove('active');
        }

        slideIndex++;
        if (slideIndex > slides.length) {
            slideIndex = 1;
        }

        // Show the current slide and add fade animation
        slides[slideIndex - 1].style.display = 'block';
        slides[slideIndex - 1].classList.add('fade');
        dots[slideIndex - 1].classList.add('active');

        setTimeout(showSlides, 4000); // Change slide every 4 seconds
    }

    // Add click event to dots for manual navigation
    for (let i = 0; i < dots.length; i++) {
        dots[i].addEventListener('click', () => {
            slideIndex = i + 1;
            showSlides();
        });
    }

    showSlides();
}

// Initialize Parallax Effect
function initParallax() {
    const sections = document.querySelectorAll('[data-parallax-speed]');
    sections.forEach(section => {
        const parallaxWrapper = document.createElement('div');
        parallaxWrapper.classList.add('parallax-wrapper');
        section.insertBefore(parallaxWrapper, section.firstChild);
    });

    window.addEventListener('scroll', () => {
        const scrollPosition = window.pageYOffset;
        sections.forEach(section => {
            const parallaxWrapper = section.querySelector('.parallax-wrapper');
            if (parallaxWrapper) {
                const sectionTop = section.getBoundingClientRect().top + window.pageYOffset;
                const speed = section.dataset.parallaxSpeed || 0.5;
                const offset = (scrollPosition - sectionTop) * speed;
                parallaxWrapper.style.transform = `translateY(${offset}px)`;
            }
        });
    });
}

// Initialize Feature Animations with Intersection Observer
function initFeatureAnimations() {
    const elements = document.querySelectorAll(
        '.easy-to-start-section h2, .easy-to-start-section > p, .feature-card, .create-site-btn, .supported-tech p, .tech-icon, ' +
        '.introduction-header h1, .section-subtitle, .introduction-image, .benefit-card, .next-btn, ' +
        '.documentation-header h1, .documentation-image, .platform-card, .code-snippet, .documentation-note, ' +
        '.mission-header h2, .mission-text p, .mission-image, .values-section h2, .value-card, .team-section h2, .team-card, ' +
        '.blog-post, .blog-sidebar, ' +
        '.pricing-card'
    );

    const observer = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                // Ensure the element is visible
                entry.target.style.opacity = '1';
                // Add a class to trigger the animation
                entry.target.classList.add('animate');
                observer.unobserve(entry.target); // Stop observing once animated
            }
        });
    }, { threshold: 0.1 });

    elements.forEach(element => {
        // Ensure initial state matches CSS
        element.style.opacity = '0';
        observer.observe(element);
    });
}

// Initialize Contact Form Submission


// Initialize All Features on Page Load
document.addEventListener('DOMContentLoaded', () => {
    initHamburgerMenu();
    initSlideshow();
    initParallax();
    initFeatureAnimations();
    
});