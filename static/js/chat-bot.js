
// CHATBOT JAVASCRIPT - FLASK API ÜZERİNDEN
let sessionId = '';
let userId = 'web_user_' + Date.now();

// Cookie fonksiyonları
function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return null;
}

function setCookie(name, value, days = 30) {
    const date = new Date();
    date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
    const expires = `expires=${date.toUTCString()}`;
    document.cookie = `${name}=${value}; ${expires}; path=/; SameSite=Lax`;
}

function generateSessionId() {
    return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}

// Session ID'yi başlat
function initializeSession() {
    // Mevcut session ID'yi kontrol et
    sessionId = getCookie('bisonar_session_id');
    if (!sessionId) {
        sessionId = generateSessionId();
        setCookie('bisonar_session_id', sessionId);
        console.log('🆕 Yeni oturum başlatıldı:', sessionId);
    } else {
        console.log('📚 Mevcut oturum devam ediyor:', sessionId);
    }
}

// Sayfa yüklendiğinde session'ı başlat
document.addEventListener('DOMContentLoaded', function() {
    initializeSession();
    const chatbotInput = document.getElementById('chatbotInput');
    if (chatbotInput) {
        chatbotInput.focus();
    }
});

function toggleChatbot() {
    const container = document.getElementById('chatbotContainer');
    container.classList.toggle('open');
    
    // Chatbot açıldığında input'a focus
    if (container.classList.contains('open')) {
        setTimeout(() => {
            const chatbotInput = document.getElementById('chatbotInput');
            if (chatbotInput) {
                chatbotInput.focus();
            }
        }, 300);
    }
}

async function sendChatbotMessage() {
    const input = document.getElementById('chatbotInput');
    const message = input.value.trim();
    
    if (!message) return;
    
    addChatbotMessage('Siz', message, 'user');
    input.value = '';
    
    // Loading state
    input.disabled = true;
    document.querySelector('.send-button').disabled = true;
    document.querySelector('.send-button').textContent = '...';
    
    // Clear quick replies
    document.getElementById('chatbotQuickReplies').innerHTML = '';
    
    try {
        // ✅ FLASK API'ye istek yap (CORS hatası olmaz)
        const response = await fetch('/api/chatbot', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                sessionId: sessionId,
                userId: userId
            })
        });
        
        if (response.ok) {
            const data = await response.json();
            console.log('✅ Flask API Başarılı:', data);
            
            let aiResponse = "Cevap alınamadı";
            let quickReplies = ['n8n Otomasyonu', 'AI İş Akışları', 'Danışmanlık', 'Fiyat Bilgisi'];
            
            if (typeof data === 'object') {
                if (data.response) {
                    aiResponse = data.response;
                } 
                else if (Array.isArray(data) && data.length > 0 && data[0].response) {
                    aiResponse = data[0].response;
                    if (data[0].quickReplies) {
                        quickReplies = data[0].quickReplies;
                    }
                }
                else if (data.message) {
                    aiResponse = data.message;
                } else if (data.text) {
                    aiResponse = data.text;
                }
                
                if (data.quickReplies && Array.isArray(data.quickReplies)) {
                    quickReplies = data.quickReplies;
                } else if (Array.isArray(data) && data[0] && data[0].quickReplies) {
                    quickReplies = data[0].quickReplies;
                }
            }
            
            console.log('📝 AI Response:', aiResponse);
            console.log('🔘 Quick Replies:', quickReplies);
            
            addChatbotMessage('AI Asistan', aiResponse, 'bot');
            showChatbotQuickReplies(quickReplies);
            
        } else {
            throw new Error(`API hatası: ${response.status}`);
        }
        
    } catch (error) {
        console.error('API hatası:', error);
        
        // ✅ FALLBACK DEMO MODU
        addChatbotMessage('AI Asistan', '🤖 ' + getDemoResponse(message), 'bot');
        showChatbotQuickReplies(['n8n Otomasyonu', 'AI İş Akışları', 'Danışmanlık', 'Fiyat Bilgisi']);
        
    } finally {
        input.disabled = false;
        document.querySelector('.send-button').disabled = false;
        document.querySelector('.send-button').textContent = 'Gönder';
        input.focus();
    }
}

// Local demo yanıtları (fallback için)
function getDemoResponse(message) {
    const lowerMessage = message.toLowerCase();
    if (lowerMessage.includes('n8n')) return '🚀 n8n otomasyon hizmetlerimizle iş süreçlerinizi otomatikleştirin!';
    if (lowerMessage.includes('ai')) return '🤖 AI iş akışları ile verimliliğinizi artırın!';
    if (lowerMessage.includes('danışmanlık')) return '💼 Danışmanlık hizmetlerimizle size özel çözümler sunuyoruz!';
    return 'Size nasıl yardımcı olabilirim? n8n otomasyonu, AI iş akışları veya danışmanlık hakkında bilgi alabilirsiniz.';
}

function sendQuickReply(message) {
    document.getElementById('chatbotInput').value = message;
    sendChatbotMessage();
}

function addChatbotMessage(sender, text, type) {
    const messagesContainer = document.getElementById('chatbotMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${type}-message`;
    messageDiv.innerHTML = `<strong>${sender}:</strong> ${text}`;
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function showChatbotQuickReplies(replies) {
    const quickRepliesContainer = document.getElementById('chatbotQuickReplies');
    quickRepliesContainer.innerHTML = '';
    
    if (replies && Array.isArray(replies)) {
        replies.forEach(reply => {
            const button = document.createElement('button');
            button.className = 'quick-reply-btn';
            button.textContent = reply;
            button.onclick = () => sendQuickReply(reply);
            quickRepliesContainer.appendChild(button);
        });
    }
}

function handleChatbotKeyPress(e) {
    if (e.key === 'Enter') {
        sendChatbotMessage();
    }
}
