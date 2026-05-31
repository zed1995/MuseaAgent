const state = {
  conversations: [],
  selectedConversationId: null,
  messages: [],
  lastDebug: null,
  loadingConversationId: null,
  isSending: false,
  statusText: "",
};

const conversationListEl = document.getElementById("conversation-list");
const chatHeaderEl = document.getElementById("chat-header");
const messageListEl = document.getElementById("message-list");
const requestStatusEl = document.getElementById("request-status");
const debugOutputEl = document.getElementById("debug-output");
const composerEl = document.getElementById("composer");
const composerInputEl = document.getElementById("composer-input");
const newConversationButtonEl = document.getElementById("new-conversation-button");
const modeSelectEl = document.getElementById("mode-select");
const sendButtonEl = document.getElementById("send-button");

async function loadConversations() {
  const response = await fetch("/api/debug/conversations");
  state.conversations = await response.json();
  renderConversations();
  if (!state.selectedConversationId && state.conversations.length > 0) {
    await selectConversation(state.conversations[0].id);
  }
}

async function createConversation() {
  const response = await fetch("/api/debug/conversations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title: null }),
  });
  const conversation = await response.json();
  state.conversations.unshift(conversation);
  renderConversations();
  await selectConversation(conversation.id);
}

async function selectConversation(conversationId) {
  state.selectedConversationId = conversationId;
  state.loadingConversationId = conversationId;
  state.statusText = "Loading messages...";
  renderConversations();
  renderMessages();
  renderRequestStatus();
  const response = await fetch(`/api/debug/conversations/${conversationId}/messages`);
  if (!response.ok) {
    state.messages = [];
    state.loadingConversationId = null;
    state.statusText = "";
    debugOutputEl.textContent = `Failed to load messages for conversation ${conversationId}.`;
    renderConversations();
    renderMessages();
    renderRequestStatus();
    return;
  }
  state.messages = await response.json();
  state.loadingConversationId = null;
  state.statusText = "";
  renderConversations();
  renderMessages();
  renderRequestStatus();
}

async function respond(message, mode) {
  if (!state.selectedConversationId) {
    await createConversation();
  }

  state.isSending = true;
  state.statusText = "Sending...";
  renderComposer();
  renderRequestStatus();
  const response = await fetch(`/api/debug/conversations/${state.selectedConversationId}/respond`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, mode }),
  });
  if (!response.ok) {
    const errorText = await response.text();
    state.isSending = false;
    state.statusText = "";
    renderComposer();
    renderRequestStatus();
    debugOutputEl.textContent = `Failed to send message: ${errorText}`;
    return;
  }
  const payload = await response.json();
  state.lastDebug = payload.debug;
  await loadConversations();
  await selectConversation(state.selectedConversationId);
  state.isSending = false;
  state.statusText = "";
  renderComposer();
  renderDebug();
  renderRequestStatus();
}

function renderConversations() {
  conversationListEl.innerHTML = "";
  for (const conversation of state.conversations) {
    const item = document.createElement("button");
    item.type = "button";
    item.className =
      "conversation-item"
      + (conversation.id === state.selectedConversationId ? " active" : "")
      + (conversation.id === state.loadingConversationId ? " loading" : "");
    item.textContent = conversation.title || `Conversation ${conversation.id}`;
    item.disabled = state.isSending;
    item.addEventListener("click", () => selectConversation(conversation.id));
    conversationListEl.appendChild(item);
  }
}

function renderMessages() {
  messageListEl.innerHTML = "";
  const selected = state.conversations.find((item) => item.id === state.selectedConversationId);
  chatHeaderEl.textContent = selected ? selected.title || `Conversation ${selected.id}` : "No conversation selected";

  if (state.loadingConversationId === state.selectedConversationId) {
    const loadingState = document.createElement("div");
    loadingState.className = "empty-state";
    loadingState.innerHTML = "<strong>Loading messages...</strong><div>Fetching conversation history from the server.</div>";
    messageListEl.appendChild(loadingState);
    return;
  }

  if (state.messages.length === 0) {
    const emptyState = document.createElement("div");
    emptyState.className = "empty-state";
    emptyState.innerHTML = "<strong>No messages in this conversation yet.</strong><div>Send one below to test the next turn.</div>";
    messageListEl.appendChild(emptyState);
    return;
  }

  for (const message of state.messages) {
    const item = document.createElement("div");
    item.className = `message ${message.role}`;
    const title = document.createElement("strong");
    title.textContent = message.role;
    const body = document.createElement("div");
    body.textContent = message.content;
    item.appendChild(title);
    item.appendChild(body);
    if (message.structured_data?.agent) {
      const note = document.createElement("pre");
      note.textContent = JSON.stringify(message.structured_data.agent, null, 2);
      item.appendChild(note);
    }
    messageListEl.appendChild(item);
  }
}

function renderComposer() {
  composerInputEl.disabled = state.isSending;
  modeSelectEl.disabled = state.isSending;
  newConversationButtonEl.disabled = state.isSending;
  sendButtonEl.disabled = state.isSending;
  sendButtonEl.textContent = state.isSending ? "Sending..." : "Send";
}

function renderRequestStatus() {
  requestStatusEl.textContent = state.statusText;
}

function renderDebug() {
  debugOutputEl.textContent = state.lastDebug
    ? JSON.stringify(state.lastDebug, null, 2)
    : "No turn selected yet.";
}

composerEl.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = composerInputEl.value.trim();
  if (!message) {
    return;
  }
  composerInputEl.value = "";
  await respond(message, modeSelectEl.value);
});

newConversationButtonEl.addEventListener("click", () => {
  createConversation();
});

renderComposer();
renderRequestStatus();

loadConversations().catch((error) => {
  debugOutputEl.textContent = `Failed to load debug chat: ${error}`;
});
