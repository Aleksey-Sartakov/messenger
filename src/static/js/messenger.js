const userList = document.getElementById('userList');
const chatArea = document.getElementById('chatArea');
const chatTitle = document.getElementById('chatTitle');
const chatMessages = document.getElementById('chatMessages');
const messageInput = document.getElementById('messageInput');
const sendButton = document.getElementById('sendButton');
const logoutBtn = document.getElementById('logoutBtn');
const userItems = document.querySelectorAll('.user-item');

let selectedUserId = null;
let selectedUserName = null;
let websocketConnectionWithSelectedUser = null;
let messagePollingInterval = null;


function createMessageElement(message, userName) {
    const messageContainer = document.createElement('div');
    let messageType;
    let senderName;

    if (message.recipient_id == selectedUserId) {
        messageType = 'sent';
        senderName = 'Вы';
    } else {
        messageType = 'received';
        senderName = userName;
    }
    messageContainer.className = `message-container ${messageType}`;

    const messageInfo = document.createElement('div');
    messageInfo.className = 'message-info';
    let localDate = new Date(message.created_at.slice(0, 23) + 'Z');
    messageInfo.textContent = `${senderName} • ${localDate.toLocaleString()}`;

    const messageElement = document.createElement('div');
    messageElement.className = 'message';
    messageElement.textContent = message.text_content;

    messageContainer.appendChild(messageInfo);
    messageContainer.appendChild(messageElement);
    chatMessages.appendChild(messageContainer);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

async function loadMessages(userId, userName) {
    try {
        const response = await fetch(`/messenger/messages/${userId}`);
        const messages = await response.json();
        console.log(messages);

        for (let message of messages) {
            createMessageElement(message, userName)
        };

    } catch (error) {
        console.error('Ошибка загрузки сообщений:', error);
    }
}

function sendMessage() {
    const message = messageInput.value.trim();
    if (message && selectedUserId) {
        let payload = {'recipient_id': selectedUserId, 'text_content': message};
        try {
            websocketConnectionWithSelectedUser.send(JSON.stringify(payload));
            messageInput.value = '';

        } catch (error) {
            console.error('Ошибка при отправке сообщения:', error);  // Ловим ошибки
        }
    }
}


function connectWebSocketWithSelectedUser() {
    if (websocketConnectionWithSelectedUser) websocketConnectionWithSelectedUser.close();

    websocketConnectionWithSelectedUser = new WebSocket(`ws://${window.location.host}/messenger/ws?recipient_id=${selectedUserId}&current_user_id=${currentUserId}`);

    websocketConnectionWithSelectedUser.onopen = () => console.log('WebSocket соединение с выбранным пользователем установлено');

    websocketConnectionWithSelectedUser.onmessage = (event) => {
        let incomingMessage = JSON.parse(event.data);
        createMessageElement(incomingMessage, selectedUserName);
    };

    websocketConnectionWithSelectedUser.onclose = () => console.log('WebSocket соединение с пользователем закрыто');
}

function connectGlobalWebSocket() {
    let globalWebsocketId = 0;
    let globalWebsocket = new WebSocket(`ws://${window.location.host}/messenger/ws?recipient_id=${globalWebsocketId}&current_user_id=${currentUserId}`);

    globalWebsocket.onopen = () => console.log('Глобальное WebSocket соединение установлено');

    globalWebsocket.onmessage = (event) => {
        console.log("-");
    };

    globalWebsocket.onclose = () => console.log('Глобальное WebSocket соединение закрыто');
}


async function selectUser(userId, userName) {
    selectedUserId = userId;
    selectedUserName = userName;
    chatTitle.textContent = `Чат с ${userName}`;

    document.querySelectorAll('.user-item').forEach(item => item.classList.remove('active'));
    document.querySelector(`.user-item[data-user-id="${userId}"]`).classList.add('active');

    chatMessages.innerHTML = '';
    chatArea.classList.remove('hidden');

    await loadMessages(selectedUserId, selectedUserName);
    connectWebSocketWithSelectedUser();
}


userItems.forEach(item => {
    item.addEventListener('click', async () => {
        let userName = item.textContent.trim();
        let userId = item.getAttribute('data-user-id');

        await selectUser(userId, userName);
    });
});

sendButton.addEventListener('click', sendMessage);
messageInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
});

logoutBtn.addEventListener('click', async () => {
    const response = await fetch('/auth/logout', {
        method: 'POST',
        credentials: 'include'
    });
    if (response.ok) {
        window.location.href = '/auth';
    } else {
        console.error('Ошибка при выходе');
    }
});

connectGlobalWebSocket();