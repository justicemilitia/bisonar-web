// Theme Manager
class ThemeManager {
    constructor() {
        this.init();
    }

    init() {
        this.setInitialTheme();
        this.bindEvents();
    }

    setInitialTheme() {
        // localStorage'dan tema bilgisini al veya sistem temasını kullan
        const savedTheme = localStorage.getItem('theme');
        const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        
        const theme = savedTheme || (systemPrefersDark ? 'dark' : 'light');
        this.applyTheme(theme);
    }

    applyTheme(theme) {
        if (theme === 'dark') {
            document.documentElement.classList.add('dark');
        } else {
            document.documentElement.classList.remove('dark');
        }
        localStorage.setItem('theme', theme);
    }

    toggleTheme() {
        const isDark = document.documentElement.classList.contains('dark');
        this.applyTheme(isDark ? 'light' : 'dark');
    }

    bindEvents() {
        // Tema değiştirme butonlarına event listener ekle
        const themeToggles = document.querySelectorAll('[data-theme-toggle]');
        themeToggles.forEach(toggle => {
            toggle.addEventListener('click', () => this.toggleTheme());
        });

        // Sistem teması değişikliklerini dinle
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
            if (!localStorage.getItem('theme')) {
                this.applyTheme(e.matches ? 'dark' : 'light');
            }
        });
    }
}

// Back to Top
// Back to Top - UPDATED FOR HOME PAGE
class BackToTop {
    constructor() {
        this.button = document.getElementById('backToTop');
        this.init();
    }

    init() {
        if (this.button) {
            console.log('✅ Back to Top button found in main.js');
            
            // Sadece scroll visibility için
            window.addEventListener('scroll', () => this.toggleVisibility());
            
            // Click event'ini base.html'deki özel fonksiyon handle edecek
            // Burada sadece fallback olarak
            this.button.addEventListener('click', (e) => {
                e.preventDefault();
                this.scrollToTop();
            });
            
        } else {
            console.log('❌ Back to Top button not found in main.js');
        }
    }

    toggleVisibility() {
        if (this.button) {
            const scrollY = window.pageYOffset || document.documentElement.scrollTop;
            if (scrollY > 300) {
                this.button.classList.remove('hidden');
            } else {
                this.button.classList.add('hidden');
            }
        }
    }

    scrollToTop() {
        console.log('🔄 Fallback scroll from main.js');
        
        // Fallback method
        window.scrollTo({ top: 0, behavior: 'smooth' });
        document.documentElement.scrollTo({ top: 0, behavior: 'smooth' });
    }
}

// Contact Form
class ContactForm {
    constructor() {
        this.form = document.getElementById('contactForm');
        this.init();
    }

    init() {
        if (this.form) {
            this.form.addEventListener('submit', (e) => this.handleSubmit(e));
        }
    }

    async handleSubmit(e) {
        e.preventDefault();
        
        const formData = new FormData(this.form);
        const submitBtn = this.form.querySelector('button[type="submit"]');
        const originalText = submitBtn.textContent;

        try {
            submitBtn.textContent = 'Sending...';
            submitBtn.disabled = true;

            const response = await fetch(this.form.action, {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                this.showMessage('Message sent successfully!', 'success');
                this.form.reset();
            } else {
                throw new Error('Failed to send message');
            }
        } catch (error) {
            this.showMessage('Failed to send message. Please try again.', 'error');
        } finally {
            submitBtn.textContent = originalText;
            submitBtn.disabled = false;
        }
    }

    showMessage(message, type) {
        // Basit bir alert veya daha gelişmiş bir mesaj gösterimi
        alert(`${type}: ${message}`);
    }
}

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

            // Close menu when clicking outside
            document.addEventListener('click', (e) => this.handleClickOutside(e));
        } else {
            console.log('❌ Mobile menu elements not found');
        }
    }

    toggleMenu() {
        console.log('🎯 Toggle menu clicked');
        const isHidden = this.menu.classList.contains('hidden');
        
        if (isHidden) {
            this.menu.classList.remove('hidden');
            this.menu.classList.add('block');
        } else {
            this.menu.classList.add('hidden');
            this.menu.classList.remove('block');
        }
    }

    closeMenu() {
        this.menu.classList.add('hidden');
        this.menu.classList.remove('block');
    }

    handleClickOutside(event) {
        if (!this.menu.contains(event.target) && !this.menuButton.contains(event.target)) {
            this.closeMenu();
        }
    }
}

// Language Manager
class LanguageManager {
    constructor() {
        this.isSwitching = false;
        this.init();
    }

    async switchLanguage(lang) {
        // Çift tıklamayı önle
        if (this.isSwitching) {
            console.log('⏳ Language switch already in progress');
            return;
        }

        this.isSwitching = true;
        
        try {
            console.log(`🔄 Switching language to: ${lang}`);
            console.log(`📍 Current URL: ${window.location.href}`);
            
            // Butonları disable et
            this.disableLanguageButtons(true);
            
            const response = await fetch(`/set-language/${lang}`, {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                },
                credentials: 'same-origin'
            });

            console.log(`📡 Response status: ${response.status}`);

            // Response tipini kontrol et
            const contentType = response.headers.get('content-type') || '';
            console.log(`📡 Content-Type: ${contentType}`);

            if (contentType.includes('application/json')) {
                const data = await response.json();
                console.log('📦 JSON response:', data);

                if (data.success) {
                    console.log('✅ Language changed successfully');
                    
                    // SERVER'DAN GELEN new_path'i KULLAN!
                    if (data.new_path) {
                        console.log(`🔀 Redirecting to server path: ${data.new_path}`);
                        
                        // Base URL'yi al
                        const baseUrl = window.location.origin;
                        const fullUrl = baseUrl + data.new_path;
                        
                        console.log(`🔀 Full redirect URL: ${fullUrl}`);
                        
                        // HEMEN yönlendir
                        window.location.href = fullUrl;
                        return;
                    } else {
                        // Fallback: sayfayı yenile
                        console.log('🔄 No new_path, reloading page');
                        window.location.reload();
                    }
                } else {
                    console.error('❌ Language change failed:', data.error);
                    this.fallbackRedirect(lang);
                }
            } else {
                // JSON değilse, response'u text olarak oku ve logla
                const textResponse = await response.text();
                console.error('❌ Expected JSON but got:', textResponse.substring(0, 200));
                this.fallbackRedirect(lang);
            }

        } catch (error) {
            console.error('❌ Language switch failed:', error);
            this.fallbackRedirect(lang);
        } finally {
            this.isSwitching = false;
            this.disableLanguageButtons(false);
        }
    }

    disableLanguageButtons(disabled) {
        const langButtons = document.querySelectorAll('[data-lang]');
        langButtons.forEach(button => {
            button.disabled = disabled;
            if (disabled) {
                button.classList.add('opacity-50', 'cursor-not-allowed');
            } else {
                button.classList.remove('opacity-50', 'cursor-not-allowed');
            }
        });
    }

    fallbackRedirect(lang) {
        console.log('🔄 Using fallback redirect');
        // Mevcut URL'yi kullanarak yeni URL oluştur
        const currentPath = window.location.pathname;
        let newPath;

        if (currentPath.startsWith('/en/') || currentPath.startsWith('/tr/')) {
            newPath = `/${lang}${currentPath.substring(3)}`;
        } else if (currentPath === '/en' || currentPath === '/tr') {
            newPath = `/${lang}`;
        } else if (currentPath === '/' || currentPath === '') {
            newPath = `/${lang}`;
        } else {
            newPath = `/${lang}${currentPath}`;
        }

        // Query parametrelerini koru
        const search = window.location.search;
        const hash = window.location.hash;
        const newUrl = newPath + search + hash;
        
        console.log(`🔀 Redirecting to: ${newUrl}`);
        window.location.href = newUrl;
    }

    init() {
        // Language switcher buttons
        const langButtons = document.querySelectorAll('[data-lang]');
        console.log(`🎯 Found ${langButtons.length} language buttons`);
        
        langButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                
                const lang = button.getAttribute('data-lang');
                console.log(`🌐 Language button clicked: ${lang}`);
                this.switchLanguage(lang);
            });
        });

        // Fallback linkleri için
        this.updateFallbackLinks();
    }

    updateFallbackLinks() {
        // JavaScript disabled ise çalışacak fallback linkleri
        const currentPath = window.location.pathname;
        const langLinks = document.querySelectorAll('a[data-lang-fallback]');
        
        langLinks.forEach(link => {
            const lang = link.getAttribute('data-lang-fallback');
            let newHref = this.getUrlForLanguage(lang, currentPath);
            link.setAttribute('href', newHref);
        });
    }

    getUrlForLanguage(lang, currentPath) {
        if (currentPath.startsWith('/en/') || currentPath.startsWith('/tr/')) {
            return `/${lang}${currentPath.substring(3)}`;
        } else if (currentPath === '/en' || currentPath === '/tr') {
            return `/${lang}`;
        } else if (currentPath === '/' || currentPath === '') {
            return `/${lang}`;
        } else {
            return `/${lang}${currentPath}`;
        }
    }
}

// Initialize everything when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 DOM loaded - initializing all managers');
    
    // Debug information
    console.log('📍 Current path:', window.location.pathname);
    console.log('📍 Current language from HTML:', document.documentElement.lang);
    
    // Initialize managers
    new ThemeManager();
    new BackToTop();
    new ContactForm();
    new MobileMenu();
    new LanguageManager();

    console.log('✅ All managers initialized successfully');
});