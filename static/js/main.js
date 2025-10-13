// Language management
class LanguageManager {
    constructor() {
        this.init();
    }

    async switchLanguage(lang) {
        try {
            const response = await fetch(`/set-language/${lang}`);
            const data = await response.json();
            
            if (data.success) {
                location.reload();
            }
        } catch (error) {
            console.error('Language switch failed:', error);
        }
    }

    init() {
        // Language switcher buttons
        const langButtons = document.querySelectorAll('[data-lang]');
        langButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                const lang = button.getAttribute('data-lang');
                this.switchLanguage(lang);
            });
        });
    }
}

// Initialize everything when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new ThemeManager();
    new BackToTop();
    new ContactForm();
    new MobileMenu();
    new LanguageManager();
});

// Mobile Menu Handler
class MobileMenu {
    constructor() {
        this.menuButton = document.getElementById('mobileMenuButton');
        this.menu = document.getElementById('mobileMenu');
        this.init();
    }

    init() {
        if (this.menuButton && this.menu) {
            console.log('✅ Mobile menu elements found');
            this.menuButton.addEventListener('click', () => this.toggleMenu());
            
            // Close menu when clicking on links
            const menuLinks = this.menu.querySelectorAll('a');
            menuLinks.forEach(link => {
                link.addEventListener('click', () => this.closeMenu());
            });
        } else {
            console.log('❌ Mobile menu elements not found');
            console.log('Button:', this.menuButton);
            console.log('Menu:', this.menu);
        }
    }

    toggleMenu() {
        console.log('🎯 Toggle menu clicked');
        this.menu.classList.toggle('hidden');
        this.menu.classList.toggle('block');
    }

    closeMenu() {
        this.menu.classList.add('hidden');
        this.menu.classList.remove('block');
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 DOM loaded - initializing mobile menu');
    new MobileMenu();
    
    // Debug: Log all elements
    console.log('Mobile menu button:', document.getElementById('mobileMenuButton'));
    console.log('Mobile menu:', document.getElementById('mobileMenu'));
});