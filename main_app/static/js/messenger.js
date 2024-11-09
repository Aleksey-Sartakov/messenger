const userList = document.getElementById('userList');
const chatArea = document.getElementById('chatArea');
const chatTitle = document.getElementById('chatTitle');
const chatMessages = document.getElementById('chatMessages');
const messageInput = document.getElementById('messageInput');
const sendButton = document.getElementById('sendButton');
const logoutBtn = document.getElementById('logoutBtn');
const userItems = document.querySelectorAll('.user-item');
const loadMore = document.getElementById('loadMore');

let selectedUserId = null;
let selectedUserName = null;
let websocketConnectionWithSelectedUser = null;
let messagePollingInterval = null;
let messagesLimit = 20;
let countUploadedMessages = 0;
let isLoadingMessages = false;
let hasMoreMessages = true;


function createMessageElement(message, userName) {
    let messageContainer = document.createElement('div');
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

    let messageInfo = document.createElement('div');
    messageInfo.className = 'message-info';
    let localDate = new Date(message.created_at.slice(0, 23) + 'Z');
    messageInfo.textContent = `${senderName} • ${localDate.toLocaleString()}`;

    let messageElement = document.createElement('div');
    messageElement.className = 'message';
    messageElement.textContent = message.text_content;

    messageContainer.appendChild(messageInfo);
    messageContainer.appendChild(messageElement);

    return messageContainer;
}

async function loadMessages(userId, userName, limit, offset) {
    try {
        let response = await fetch(`/messenger/messages/${userId}?limit=${limit}&offset=${offset}`);
        let messages = await response.json();

		if (messages) {
			countUploadedMessages += messages.length;
        	return messages;
		}

		return null;

    } catch (error) {
        console.error('Ошибка загрузки сообщений:', error);

        return null
    }
}

function sendMessage() {
    let message = messageInput.value.trim();
    if (message && selectedUserId) {
        let payload = {'recipient_id': selectedUserId, 'text_content': message};
        try {
            websocketConnectionWithSelectedUser.send(JSON.stringify(payload));
            messageInput.value = '';

        } catch (error) {
            console.error('Ошибка при отправке сообщения:', error);
        }
    }
}


function connectWebSocketWithSelectedUser() {
    if (websocketConnectionWithSelectedUser) websocketConnectionWithSelectedUser.close();

    websocketConnectionWithSelectedUser = new WebSocket(`ws://${window.location.host}/messenger/ws?recipient_id=${selectedUserId}&current_user_id=${currentUserId}`);

    websocketConnectionWithSelectedUser.onopen = () => console.log('WebSocket соединение с выбранным пользователем установлено');

    websocketConnectionWithSelectedUser.onmessage = (event) => {
        let incomingMessage = JSON.parse(event.data);
        countUploadedMessages += 1;

        chatMessages.appendChild(createMessageElement(incomingMessage, selectedUserName));
        chatMessages.scrollTop = chatMessages.scrollHeight;
    };

    websocketConnectionWithSelectedUser.onclose = () => console.log('WebSocket соединение с пользователем закрыто');
}

function connectSessionWebSocket() {
    let sessionWebsocketId = 0;
    let sessionWebsocket = new WebSocket(`ws://${window.location.host}/messenger/ws?session_marker=True&recipient_id=${sessionWebsocketId}&current_user_id=${currentUserId}`);

    sessionWebsocket.onopen = () => console.log('WebSocket соединение для отслеживания состояния сессии установлено');

    sessionWebsocket.onmessage = (event) => {
        // pass
    };

    sessionWebsocket.onclose = () => console.log('WebSocket соединение для отслеживания состояния сессии закрыто');
}


async function handleScroll() {
	if (chatMessages.scrollTop === 0 && !isLoadingMessages && hasMoreMessages) {
		isLoadingMessages = true;
		const oldScrollHeight = chatMessages.scrollHeight;

		let messages = await loadMessages(selectedUserId, selectedUserName, messagesLimit, countUploadedMessages);

		if (messages) {
			const fragment = document.createDocumentFragment();
			for (let message of messages) {
				fragment.appendChild(createMessageElement(message, selectedUserName))
			};

			chatMessages.insertBefore(fragment, chatMessages.firstChild);
			chatMessages.scrollTop = chatMessages.scrollHeight - oldScrollHeight;
		} else {
			hasMoreMessages = false;
			removeScrollHandler();
		}

		isLoadingMessages = false;
	}
}

function attachScrollHandler() {
	chatMessages.addEventListener('scroll', handleScroll);
}

function removeScrollHandler() {
	chatMessages.removeEventListener('scroll', handleScroll);
}


async function selectUser(userId, userName) {
    removeScrollHandler();

    selectedUserId = userId;
    selectedUserName = userName;
    countUploadedMessages = 0;

    chatTitle.textContent = `Чат с ${selectedUserName}`;
    document.querySelectorAll('.user-item').forEach(item => item.classList.remove('active'));
    document.querySelector(`.user-item[data-user-id="${selectedUserId}"]`).classList.add('active');

    chatMessages.innerHTML = '';
    chatArea.classList.remove('hidden');

    let messages = await loadMessages(selectedUserId, selectedUserName, messagesLimit, countUploadedMessages);

    for (let message of messages) {
		chatMessages.appendChild(createMessageElement(message, selectedUserName));
	}
	chatMessages.scrollTop = chatMessages.scrollHeight;

	attachScrollHandler();

    connectWebSocketWithSelectedUser();
}


function addUsersToList(users) {
	users.forEach(user => {
		if (user.id != currentUserId) {
			const userItem = document.createElement('div');
			let userName = user.first_name + " " + user.last_name;

			userItem.className = 'user-item';
			userItem.textContent = userName;
			userItem.dataset.userId = user.id;
			userItem.addEventListener('click', () => selectUser(user.id, userName));
			userList.insertBefore(userItem, loadMore);
		}
	});
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
    let response = await fetch('/auth/logout', {
        method: 'POST',
        credentials: 'include'
    });
    if (response.ok) {
        window.location.href = '/auth';
    } else {
        console.error('Ошибка при выходе');
    }
});


loadMore.addEventListener('click', async () => {
    let response = await fetch(`/users?offset=${loaded_users_count}`);
    let newUsers = await response.json();
    if (newUsers.length === 0) {
        loadMore.classList.add('hidden');
    } else {
        addUsersToList(newUsers);

        loaded_users_count += newUsers.length;
    }
});


connectSessionWebSocket();