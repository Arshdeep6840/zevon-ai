/**
 * Zevon Assistant Frontend Client
 * Handles conversations, streaming chat, profile switching, and settings.
 */

// State
let currentConversationId = null;
let currentProfile = "personal";
let currentModelId = "zevon-offline-compact";
let isGenerating = false;
let abortController = null;
let profilesData = [];
let modelsData = [];
let conversationsData = [];

// DOM Elements
const conversationListEl = document.getElementById("conversation-list");
const chatMessagesEl = document.getElementById("chat-messages");
const emptyChatEl = document.getElementById("empty-chat");
const messageInputEl = document.getElementById("message-input");
const sendBtn = document.getElementById("send-btn");
const stopBtn = document.getElementById("stop-btn");
const newChatBtn = document.getElementById("new-chat-btn");
const profileSelectEl = document.getElementById("profile-select");
const modelSelectEl = document.getElementById("model-select");
const activeTitleEl = document.getElementById("active-title");
const statusPillEl = document.getElementById("status-pill");
const hardwareTierEl = document.getElementById("hardware-tier");
const starterCardsEl = document.getElementById("starter-cards");
const exportBtn = document.getElementById("export-btn");
const settingsBtn = document.getElementById("settings-btn");
const settingsModal = document.getElementById("settings-modal");
const closeSettingsBtn = document.getElementById("close-settings-btn");
const saveSettingsBtn = document.getElementById("save-settings-btn");
const forceOfflineToggle = document.getElementById("force-offline-toggle");
const clearAllBtn = document.getElementById("clear-all-btn");

// Initialize application
async function init() {
  setupEventListeners();
  await loadProfiles();
  await loadHardware();
  await loadModels();
  await loadSettings();
  await loadConversations();

  // If no conversation selected, show welcome
  if (!currentConversationId && conversationsData.length > 0) {
    selectConversation(conversationsData[0].id);
  } else if (!currentConversationId) {
    showEmptyChat();
  }
}

function setupEventListeners() {
  sendBtn.addEventListener("click", handleSendMessage);
  stopBtn.addEventListener("click", handleStopGeneration);
  newChatBtn.addEventListener("click", createNewConversation);

  messageInputEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  });

  // Auto-resize input
  messageInputEl.addEventListener("input", () => {
    messageInputEl.style.height = "auto";
    messageInputEl.style.height = Math.min(messageInputEl.scrollHeight, 160) + "px";
  });

  profileSelectEl.addEventListener("change", async (e) => {
    currentProfile = e.target.value;
    updateStarterCards();
    if (currentConversationId) {
      await fetch(`/api/v1/conversations/${currentConversationId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ profile: currentProfile }),
      });
    }
  });

  modelSelectEl.addEventListener("change", async (e) => {
    currentModelId = e.target.value;
    await fetch("/api/v1/models/active", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model_id: currentModelId }),
    });
    updateStatusPill();
  });

  const testOllamaBtn = document.getElementById("test-ollama-btn");
  if (testOllamaBtn) {
    testOllamaBtn.addEventListener("click", handleTestOllamaConnection);
  }

  exportBtn.addEventListener("click", handleExportConversation);

  settingsBtn.addEventListener("click", () => {
    settingsModal.classList.remove("hidden");
  });

  closeSettingsBtn.addEventListener("click", () => {
    settingsModal.classList.add("hidden");
  });

  saveSettingsBtn.addEventListener("click", handleSaveSettings);

  clearAllBtn.addEventListener("click", handleClearAllData);

  forceOfflineToggle.addEventListener("change", async (e) => {
    const forced = e.target.checked;
    await fetch("/api/v1/models/offline-toggle", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ force_offline: forced }),
    });
    await loadModels();
  });
}

// Load Profiles
async function loadProfiles() {
  try {
    const res = await fetch("/api/v1/profiles");
    profilesData = await res.json();
    profileSelectEl.innerHTML = "";
    profilesData.forEach((p) => {
      const opt = document.createElement("option");
      opt.value = p.id;
      opt.textContent = `${p.name}`;
      profileSelectEl.appendChild(opt);
    });
    profileSelectEl.value = currentProfile;
    updateStarterCards();
  } catch (err) {
    console.error("Failed to load profiles:", err);
  }
}

// Update Starter Prompt Cards for current profile
function updateStarterCards() {
  if (!starterCardsEl) return;
  starterCardsEl.innerHTML = "";
  const prof = profilesData.find((p) => p.id === currentProfile);
  if (!prof || !prof.templates) return;

  prof.templates.forEach((tmpl) => {
    const card = document.createElement("button");
    card.className =
      "text-left p-3.5 bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700/60 rounded-xl transition-all shadow-sm group";
    card.innerHTML = `
      <div class="text-xs uppercase tracking-wider font-semibold text-cyan-400 group-hover:text-cyan-300 mb-1">${escapeHtml(tmpl.category)}</div>
      <div class="text-sm font-medium text-slate-200 group-hover:text-white">${escapeHtml(tmpl.title)}</div>
    `;
    card.addEventListener("click", () => {
      messageInputEl.value = tmpl.prompt;
      messageInputEl.dispatchEvent(new Event("input"));
      handleSendMessage();
    });
    starterCardsEl.appendChild(card);
  });
}

// Load Hardware Profile
async function loadHardware() {
  try {
    const res = await fetch("/api/v1/models/hardware");
    const data = await res.json();
    if (hardwareTierEl) {
      hardwareTierEl.textContent = `${data.ram_gb} GB RAM • ${data.tier.toUpperCase()} TIER`;
      hardwareTierEl.title = `${data.cpu_cores} CPU cores; Recommended: ${data.recommended_param_size}`;
    }
  } catch (err) {
    console.error("Failed to load hardware:", err);
  }
}

// Load Models
async function loadModels() {
  try {
    const res = await fetch("/api/v1/models");
    modelsData = await res.json();
    modelSelectEl.innerHTML = "";

    modelsData.forEach((m) => {
      const opt = document.createElement("option");
      opt.value = m.id;
      const tag = m.provider === "ollama" ? "⚡ Ollama" : "📦 Embedded";
      opt.textContent = `${tag}: ${m.name} (${m.parameter_size})`;
      if (m.is_active) {
        opt.selected = true;
        currentModelId = m.id;
      }
      modelSelectEl.appendChild(opt);
    });

    updateStatusPill();
  } catch (err) {
    console.error("Failed to load models:", err);
  }
}

function updateStatusPill() {
  const activeModel = modelsData.find((m) => m.id === currentModelId);
  if (statusPillEl) {
    if (activeModel && activeModel.provider === "ollama") {
      statusPillEl.textContent = `Local: ${activeModel.name}`;
      statusPillEl.className = "px-2 py-0.5 text-xs rounded-full bg-cyan-950 text-cyan-400 border border-cyan-800 font-medium";
    } else if (activeModel && activeModel.provider === "offline-embedded") {
      statusPillEl.textContent = "Offline Mode";
      statusPillEl.className = "px-2 py-0.5 text-xs rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800 font-medium";
    } else {
      statusPillEl.textContent = "Local Connected";
      statusPillEl.className = "px-2 py-0.5 text-xs rounded-full bg-blue-950 text-blue-400 border border-blue-800 font-medium";
    }
  }
}

// Load Settings
async function loadSettings() {
  try {
    const res = await fetch("/api/v1/settings");
    const s = await res.json();
    currentProfile = s.active_profile || "personal";
    profileSelectEl.value = currentProfile;
    if (forceOfflineToggle) {
      forceOfflineToggle.checked = !!s.force_offline;
    }
    const ollamaInput = document.getElementById("setting-ollama-url");
    if (ollamaInput) ollamaInput.value = s.ollama_url || "http://localhost:11434";
  } catch (err) {
    console.error("Failed to load settings:", err);
  }
}

// Load Conversations list
async function loadConversations() {
  try {
    const res = await fetch("/api/v1/conversations");
    conversationsData = await res.json();
    renderConversationList();
  } catch (err) {
    console.error("Failed to load conversations:", err);
  }
}

function renderConversationList() {
  conversationListEl.innerHTML = "";
  if (conversationsData.length === 0) {
    conversationListEl.innerHTML = `<div class="p-4 text-xs text-slate-500 text-center">No conversations yet</div>`;
    return;
  }

  conversationsData.forEach((conv) => {
    const item = document.createElement("div");
    const isSelected = conv.id === currentConversationId;
    item.className = `group flex items-center justify-between p-2.5 rounded-lg cursor-pointer transition-colors ${
      isSelected ? "bg-slate-800 text-white font-medium" : "text-slate-400 hover:bg-slate-800/60 hover:text-slate-200"
    }`;

    item.innerHTML = `
      <div class="flex items-center space-x-2 truncate flex-1 mr-2">
        <svg class="w-4 h-4 text-slate-500 group-hover:text-cyan-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
        </svg>
        <span class="truncate text-xs">${escapeHtml(conv.title)}</span>
      </div>
      <button class="delete-btn opacity-0 group-hover:opacity-100 p-1 hover:text-red-400 transition-opacity" title="Delete conversation">
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
        </svg>
      </button>
    `;

    item.addEventListener("click", () => selectConversation(conv.id));
    const delBtn = item.querySelector(".delete-btn");
    delBtn.addEventListener("click", async (e) => {
      e.stopPropagation();
      if (confirm(`Delete "${conv.title}"?`)) {
        await deleteConversation(conv.id);
      }
    });

    conversationListEl.appendChild(item);
  });
}

// Select Conversation
async function selectConversation(id) {
  currentConversationId = id;
  renderConversationList();

  try {
    const res = await fetch(`/api/v1/conversations/${id}`);
    if (!res.ok) {
      showEmptyChat();
      return;
    }
    const data = await res.json();
    activeTitleEl.textContent = data.conversation.title;
    currentProfile = data.conversation.profile || "personal";
    profileSelectEl.value = currentProfile;
    updateStarterCards();

    chatMessagesEl.innerHTML = "";
    if (data.messages && data.messages.length > 0) {
      emptyChatEl.classList.add("hidden");
      data.messages.forEach((msg) => {
        appendMessage(msg.role, msg.content);
      });
      scrollToBottom();
    } else {
      showEmptyChat();
    }
  } catch (err) {
    console.error("Failed to load conversation details:", err);
  }
}

// Create New Conversation
function createNewConversation() {
  currentConversationId = null;
  activeTitleEl.textContent = "New Conversation";
  chatMessagesEl.innerHTML = "";
  showEmptyChat();
  renderConversationList();
  messageInputEl.focus();
}

// Delete Conversation
async function deleteConversation(id) {
  try {
    await fetch(`/api/v1/conversations/${id}`, { method: "DELETE" });
    if (currentConversationId === id) {
      currentConversationId = null;
      createNewConversation();
    }
    await loadConversations();
  } catch (err) {
    console.error("Failed to delete conversation:", err);
  }
}

function showEmptyChat() {
  emptyChatEl.classList.remove("hidden");
  updateStarterCards();
}

// Append message bubble
function appendMessage(role, content) {
  const isUser = role === "user";
  const row = document.createElement("div");
  row.className = `flex w-full mb-6 ${isUser ? "justify-end" : "justify-start"}`;

  const bubble = document.createElement("div");
  bubble.className = `max-w-[85%] md:max-w-[75%] rounded-2xl p-4 text-sm leading-relaxed ${
    isUser
      ? "bg-blue-600 text-white rounded-br-none shadow-md shadow-blue-900/20"
      : "bg-slate-800/90 text-slate-100 rounded-bl-none border border-slate-700/60 shadow-md shadow-black/30"
  }`;

  if (isUser) {
    bubble.textContent = content;
  } else {
    bubble.innerHTML = renderMarkdown(content);
    setupCodeBlockCopyButtons(bubble);
  }

  row.appendChild(bubble);
  chatMessagesEl.appendChild(row);
  return bubble;
}

// Markdown parser using window.marked or fallback
function renderMarkdown(text) {
  if (window.marked && typeof window.marked.parse === "function") {
    return window.marked.parse(text);
  }
  // Safe plain-text line-break fallback
  return escapeHtml(text).replace(/\n/g, "<br>");
}

function setupCodeBlockCopyButtons(container) {
  const preElements = container.querySelectorAll("pre");
  preElements.forEach((pre) => {
    if (pre.querySelector(".copy-btn")) return;
    const btn = document.createElement("button");
    btn.className = "copy-btn";
    btn.textContent = "Copy";
    btn.addEventListener("click", () => {
      const code = pre.querySelector("code") ? pre.querySelector("code").innerText : pre.innerText;
      navigator.clipboard.writeText(code).then(() => {
        btn.textContent = "Copied!";
        setTimeout(() => (btn.textContent = "Copy"), 2000);
      });
    });
    pre.appendChild(btn);
  });
}

function scrollToBottom() {
  const scrollContainer = chatMessagesEl.parentElement;
  if (scrollContainer) {
    scrollContainer.scrollTop = scrollContainer.scrollHeight;
  }
}

// Send Message with SSE streaming
async function handleSendMessage() {
  const text = messageInputEl.value.trim();
  if (!text || isGenerating) return;

  emptyChatEl.classList.add("hidden");
  appendMessage("user", text);
  messageInputEl.value = "";
  messageInputEl.style.height = "auto";
  scrollToBottom();

  isGenerating = true;
  sendBtn.classList.add("hidden");
  stopBtn.classList.remove("hidden");

  // Create assistant message bubble with cursor
  const assistantBubble = appendMessage("assistant", "");
  assistantBubble.innerHTML = '<span class="streaming-cursor"></span>';
  scrollToBottom();

  abortController = new AbortController();
  let accumulatedText = "";

  try {
    const payload = {
      conversation_id: currentConversationId,
      message: text,
      model_id: currentModelId,
      stream: true,
      temperature: 0.7,
    };

    const response = await fetch("/api/v1/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: abortController.signal,
    });

    if (!response.ok) {
      throw new Error(`Server returned ${response.status}: ${await response.text()}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n\n");
      buffer = lines.pop(); // keep last incomplete chunk

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          try {
            const data = JSON.parse(line.slice(6));
            if (data.conversation_id && !currentConversationId) {
              currentConversationId = data.conversation_id;
              await loadConversations();
            }
            if (data.delta) {
              accumulatedText += data.delta;
              assistantBubble.innerHTML = renderMarkdown(accumulatedText) + '<span class="streaming-cursor"></span>';
              setupCodeBlockCopyButtons(assistantBubble);
              scrollToBottom();
            }
            if (data.finish_reason === "stop") {
              break;
            }
          } catch (e) {
            console.error("Error parsing SSE JSON:", e);
          }
        }
      }
    }

    // Finalize assistant bubble
    assistantBubble.innerHTML = renderMarkdown(accumulatedText);
    setupCodeBlockCopyButtons(assistantBubble);
    scrollToBottom();
    await loadConversations();

  } catch (err) {
    if (err.name === "AbortError") {
      assistantBubble.innerHTML = renderMarkdown(accumulatedText + "\n\n*(Generation stopped)*");
    } else {
      assistantBubble.innerHTML = `<span class="text-red-400 font-medium">Error: ${escapeHtml(err.message)}</span>`;
    }
  } finally {
    isGenerating = false;
    abortController = null;
    sendBtn.classList.remove("hidden");
    stopBtn.classList.add("hidden");
  }
}

// Stop generation
function handleStopGeneration() {
  if (abortController) {
    abortController.abort();
  }
}

// Export conversation
async function handleExportConversation() {
  if (!currentConversationId) {
    alert("Select a conversation to export");
    return;
  }
  try {
    const res = await fetch(`/api/v1/conversations/${currentConversationId}/export?format=markdown`);
    const data = await res.json();
    const blob = new Blob([data.markdown], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `zevon-conversation-${currentConversationId.slice(0, 8)}.md`;
    a.click();
    URL.revokeObjectURL(url);
  } catch (err) {
    console.error("Failed to export conversation:", err);
  }
}

// Test Ollama Connection
async function handleTestOllamaConnection() {
  const btn = document.getElementById("test-ollama-btn");
  const resultEl = document.getElementById("ollama-test-result");
  const inputEl = document.getElementById("setting-ollama-url");
  const targetUrl = (inputEl ? inputEl.value : "").trim() || "http://localhost:11434";

  if (!resultEl) return;
  resultEl.classList.remove("hidden");
  resultEl.className = "text-xs mt-1.5 text-slate-400";
  resultEl.textContent = "Connecting to Ollama...";

  if (btn) btn.disabled = true;

  try {
    // Send update temporarily to check target
    await fetch("/api/v1/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ settings: { ollama_url: targetUrl } }),
    });

    const res = await fetch("/api/v1/health");
    const data = await res.json();
    const ollamaOk = data?.model_runtime?.providers?.ollama;

    if (ollamaOk) {
      await loadModels();
      const count = modelsData.filter((m) => m.provider === "ollama").length;
      resultEl.className = "text-xs mt-1.5 text-emerald-400 font-medium";
      resultEl.textContent = `✓ Connected! Found ${count} local Ollama model(s).`;
    } else {
      resultEl.className = "text-xs mt-1.5 text-rose-400 font-medium";
      resultEl.textContent = `✗ Could not connect to Ollama at ${targetUrl}. Is 'ollama serve' running?`;
    }
  } catch (err) {
    resultEl.className = "text-xs mt-1.5 text-rose-400 font-medium";
    resultEl.textContent = `✗ Connection error: ${err.message}`;
  } finally {
    if (btn) btn.disabled = false;
  }
}

// Save Settings
async function handleSaveSettings() {
  const ollamaUrl = document.getElementById("setting-ollama-url")?.value?.trim();
  const defProfile = document.getElementById("setting-default-profile")?.value;
  const isForceOffline = forceOfflineToggle ? forceOfflineToggle.checked : false;

  const newSettings = {};
  if (defProfile) newSettings.active_profile = defProfile;
  if (ollamaUrl) newSettings.ollama_url = ollamaUrl;
  newSettings.force_offline = isForceOffline ? "true" : "false";

  await fetch("/api/v1/settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ settings: newSettings }),
  });

  settingsModal.classList.add("hidden");
  await loadSettings();
  await loadModels();
}

// Clear all data
async function handleClearAllData() {
  if (confirm("Are you sure you want to delete ALL conversations and message history? This cannot be undone.")) {
    await fetch("/api/v1/conversations", { method: "DELETE" });
    currentConversationId = null;
    settingsModal.classList.add("hidden");
    createNewConversation();
    await loadConversations();
  }
}

function escapeHtml(str) {
  if (!str) return "";
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// Start app on DOMContentLoaded
document.addEventListener("DOMContentLoaded", init);
