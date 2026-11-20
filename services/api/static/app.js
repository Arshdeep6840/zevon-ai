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

// Voice Elements (Phase 2)
const micBtn = document.getElementById("mic-btn");
const voiceOverlay = document.getElementById("voice-overlay");
const closeVoiceOverlayBtn = document.getElementById("close-voice-overlay-btn");
const voiceOrb = document.getElementById("voice-orb");
const voiceStatePill = document.getElementById("voice-state-pill");
const voiceLiveTranscript = document.getElementById("voice-live-transcript");
const voiceBargeinBtn = document.getElementById("voice-bargein-btn");
const voiceSendBtn = document.getElementById("voice-send-btn");
const voiceVadIndicator = document.getElementById("voice-vad-indicator");
const voiceEnabledToggle = document.getElementById("voice-enabled-toggle");
const voiceWakePhraseInput = document.getElementById("voice-wake-phrase");
const voiceWakeSensitivityInput = document.getElementById("voice-wake-sensitivity");
const voiceTtsSelect = document.getElementById("voice-tts-select");
const voiceTtsSpeed = document.getElementById("voice-tts-speed");
const voiceSpeedVal = document.getElementById("voice-speed-val");
const voiceAutoBargeinToggle = document.getElementById("voice-auto-bargein");

// Phase 3 Elements (Tasks, Tools & MCP)
const tabChat = document.getElementById("tab-chat");
const tabTasks = document.getElementById("tab-tasks");
const tabTools = document.getElementById("tab-tools");
const viewChat = document.getElementById("view-chat");
const viewTasks = document.getElementById("view-tasks");
const viewTools = document.getElementById("view-tools");

const taskPromptInput = document.getElementById("task-prompt-input");
const runTaskBtn = document.getElementById("run-task-btn");
const tasksList = document.getElementById("tasks-list");
const refreshTasksBtn = document.getElementById("refresh-tasks-btn");
const noTaskSelected = document.getElementById("no-task-selected");
const taskDetailContent = document.getElementById("task-detail-content");
const taskDetailStatus = document.getElementById("task-detail-status");
const taskDetailTime = document.getElementById("task-detail-time");
const taskDetailPrompt = document.getElementById("task-detail-prompt");
const taskCancelBtn = document.getElementById("task-cancel-btn");
const approvalGateCard = document.getElementById("approval-gate-card");
const approvalGateDesc = document.getElementById("approval-gate-desc");
const approvalGatePayload = document.getElementById("approval-gate-payload");
const approveStepBtn = document.getElementById("approve-step-btn");
const rejectStepBtn = document.getElementById("reject-step-btn");
const taskStepsTimeline = document.getElementById("task-steps-timeline");
const taskArtifactsSection = document.getElementById("task-artifacts-section");
const taskArtifactsList = document.getElementById("task-artifacts-list");

const addMcpBtn = document.getElementById("add-mcp-btn");
const mcpModal = document.getElementById("mcp-modal");
const closeMcpModalBtn = document.getElementById("close-mcp-modal-btn");
const submitMcpBtn = document.getElementById("submit-mcp-btn");
const mcpNameInput = document.getElementById("mcp-name-input");
const mcpTransportSelect = document.getElementById("mcp-transport-select");
const mcpCommandInput = document.getElementById("mcp-command-input");
const mcpArgsInput = document.getElementById("mcp-args-input");
const mcpUrlInput = document.getElementById("mcp-url-input");
const mcpStdioFields = document.getElementById("mcp-stdio-fields");
const mcpSseFields = document.getElementById("mcp-sse-fields");
const mcpServersGrid = document.getElementById("mcp-servers-grid");
const toolsCatalogGrid = document.getElementById("tools-catalog-grid");
const toolsCatalogCount = document.getElementById("tools-catalog-count");
const refreshAuditBtn = document.getElementById("refresh-audit-btn");
const auditTableBody = document.getElementById("audit-table-body");

// Phase 3 State
let activeView = "chat";
let currentTaskId = null;
let currentPendingStepId = null;
let taskPollingTimer = null;

// Voice State
let voiceCurrentState = "idle";
let speechRecognitionInstance = null;
let currentTTSAudio = null;
let isPushToTalkActive = false;
let voiceSettingsData = {
  wake_word_enabled: true,
  wake_word_phrase: "Hey Zevon",
  wake_word_sensitivity: 0.6,
  tts_enabled: true,
  tts_voice: "en_US-lessac-medium",
  tts_speed: 1.0,
  auto_barge_in: true,
};

// Initialize application
async function init() {
  setupEventListeners();
  await loadProfiles();
  await loadHardware();
  await loadModels();
  await loadSettings();
  await loadVoiceSettings();
  initVoiceAssistant();
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

  // Voice Event Listeners (Phase 2)
  if (micBtn) micBtn.addEventListener("click", () => openVoiceOverlay());
  if (closeVoiceOverlayBtn) closeVoiceOverlayBtn.addEventListener("click", () => closeVoiceOverlay());
  if (voiceBargeinBtn) voiceBargeinBtn.addEventListener("click", () => handleVoiceBargeIn());
  if (voiceSendBtn) voiceSendBtn.addEventListener("click", () => handleVoiceSend());

  if (voiceTtsSpeed && voiceSpeedVal) {
    voiceTtsSpeed.addEventListener("input", (e) => {
      voiceSpeedVal.textContent = `${e.target.value}x`;
    });
  }

  // Push-to-Talk via Spacebar (when not typing in an input)
  window.addEventListener("keydown", (e) => {
    if (e.code === "Space" && document.activeElement !== messageInputEl && document.activeElement !== voiceLiveTranscript) {
      if (!isPushToTalkActive) {
        e.preventDefault();
        isPushToTalkActive = true;
        handlePushToTalk(true);
      }
    }
  });

  window.addEventListener("keyup", (e) => {
    if (e.code === "Space" && isPushToTalkActive) {
      e.preventDefault();
      isPushToTalkActive = false;
      handlePushToTalk(false);
    }
  });

  // Phase 3: View Switching and Event Listeners
  if (tabChat) tabChat.addEventListener("click", () => switchView("chat"));
  if (tabTasks) tabTasks.addEventListener("click", () => switchView("tasks"));
  if (tabTools) tabTools.addEventListener("click", () => switchView("tools"));

  if (runTaskBtn) runTaskBtn.addEventListener("click", runNewTask);
  if (taskPromptInput) {
    taskPromptInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        runNewTask();
      }
    });
  }

  if (refreshTasksBtn) refreshTasksBtn.addEventListener("click", loadTasks);
  if (taskCancelBtn) taskCancelBtn.addEventListener("click", handleCancelTask);
  if (approveStepBtn) approveStepBtn.addEventListener("click", () => handleApproveStep(true));
  if (rejectStepBtn) rejectStepBtn.addEventListener("click", () => handleApproveStep(false));

  if (addMcpBtn) {
    addMcpBtn.addEventListener("click", () => {
      mcpModal.classList.remove("hidden");
    });
  }
  if (closeMcpModalBtn) {
    closeMcpModalBtn.addEventListener("click", () => {
      mcpModal.classList.add("hidden");
    });
  }
  if (mcpTransportSelect) {
    mcpTransportSelect.addEventListener("change", (e) => {
      if (e.target.value === "sse") {
        mcpStdioFields.classList.add("hidden");
        mcpSseFields.classList.remove("hidden");
      } else {
        mcpStdioFields.classList.remove("hidden");
        mcpSseFields.classList.add("hidden");
      }
    });
  }
  if (submitMcpBtn) submitMcpBtn.addEventListener("click", handleCreateMcpServer);
  if (refreshAuditBtn) refreshAuditBtn.addEventListener("click", loadAuditTrail);
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

    // If Voice mode or TTS enabled, speak assistant output
    if (accumulatedText && voiceSettingsData.tts_enabled && voiceOverlay && !voiceOverlay.classList.contains("hidden")) {
      playTTSAudio(accumulatedText);
    }

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
  handleVoiceBargeIn();
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

  // Save Voice Settings (Phase 2)
  if (voiceEnabledToggle) {
    const updatedVoice = {
      wake_word_enabled: voiceEnabledToggle.checked,
      wake_word_phrase: voiceWakePhraseInput?.value?.trim() || "Hey Zevon",
      wake_word_sensitivity: parseFloat(voiceWakeSensitivityInput?.value || 0.6),
      tts_enabled: true,
      tts_voice: voiceTtsSelect?.value || "en_US-lessac-medium",
      tts_speed: parseFloat(voiceTtsSpeed?.value || 1.0),
      tts_volume: 1.0,
      tts_muted: false,
      auto_barge_in: voiceAutoBargeinToggle ? voiceAutoBargeinToggle.checked : true,
      push_to_talk_key: "Space",
    };

    await fetch("/api/v1/voice/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(updatedVoice),
    });
    voiceSettingsData = updatedVoice;
  }

  settingsModal.classList.add("hidden");
  await loadSettings();
  await loadVoiceSettings();
  await loadModels();
}

// Load Voice Settings
async function loadVoiceSettings() {
  try {
    const res = await fetch("/api/v1/voice/settings");
    if (res.ok) {
      voiceSettingsData = await res.json();
      if (voiceEnabledToggle) voiceEnabledToggle.checked = voiceSettingsData.wake_word_enabled;
      if (voiceWakePhraseInput) voiceWakePhraseInput.value = voiceSettingsData.wake_word_phrase;
      if (voiceWakeSensitivityInput) voiceWakeSensitivityInput.value = voiceSettingsData.wake_word_sensitivity;
      if (voiceTtsSelect) voiceTtsSelect.value = voiceSettingsData.tts_voice;
      if (voiceTtsSpeed) voiceTtsSpeed.value = voiceSettingsData.tts_speed;
      if (voiceSpeedVal) voiceSpeedVal.textContent = `${voiceSettingsData.tts_speed}x`;
      if (voiceAutoBargeinToggle) voiceAutoBargeinToggle.checked = voiceSettingsData.auto_barge_in;
    }
  } catch (err) {
    console.error("Failed to load voice settings:", err);
  }
}

// Voice Assistant Initialization
function initVoiceAssistant() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    console.warn("SpeechRecognition API not available in browser. Using manual voice transcription fallback.");
    return;
  }

  try {
    speechRecognitionInstance = new SpeechRecognition();
    speechRecognitionInstance.continuous = true;
    speechRecognitionInstance.interimResults = true;
    speechRecognitionInstance.lang = "en-US";

    speechRecognitionInstance.onresult = (event) => {
      let interimTranscript = "";
      for (let i = event.resultIndex; i < event.results.length; ++i) {
        const item = event.results[i];
        if (item.isFinal) {
          const finalPart = item[0].transcript.trim();
          if (voiceLiveTranscript) {
            voiceLiveTranscript.value = finalPart;
          }
          checkWakeWord(finalPart);
        } else {
          interimTranscript += item[0].transcript;
        }
      }
      if (interimTranscript && voiceLiveTranscript && !voiceLiveTranscript.value) {
        voiceLiveTranscript.placeholder = interimTranscript;
      }
      // Auto barge-in if user speaks while TTS is playing
      if (currentTTSAudio && voiceSettingsData.auto_barge_in) {
        handleVoiceBargeIn();
      }
    };

    speechRecognitionInstance.onerror = (event) => {
      console.warn("SpeechRecognition error:", event.error);
      if (event.error === "not-allowed") {
        setVoiceState("mic_unavailable", "Mic Permission Denied");
      }
    };
  } catch (err) {
    console.error("Speech recognition initialization failed:", err);
  }
}

function checkWakeWord(text) {
  const phrase = (voiceSettingsData.wake_word_phrase || "Hey Zevon").toLowerCase();
  if (text.toLowerCase().includes(phrase) || text.toLowerCase().includes("zevon")) {
    setVoiceState("wake_detected", "Wake Detected: Zevon");
    setTimeout(() => {
      setVoiceState("listening", "Listening...");
    }, 800);
  }
}

function setVoiceState(state, label) {
  voiceCurrentState = state;
  if (voiceStatePill) {
    voiceStatePill.textContent = label || state.toUpperCase();
    const styleMap = {
      idle: "bg-slate-800 text-slate-300 border-slate-700",
      listening: "bg-cyan-950 text-cyan-300 border-cyan-700 shadow-cyan-900/50 animate-pulse",
      wake_detected: "bg-indigo-950 text-indigo-300 border-indigo-700 animate-bounce",
      transcribing: "bg-blue-950 text-blue-300 border-blue-700",
      thinking: "bg-purple-950 text-purple-300 border-purple-700 animate-pulse",
      speaking: "bg-emerald-950 text-emerald-300 border-emerald-700 shadow-emerald-900/50",
      interrupted: "bg-red-950 text-red-300 border-red-700 animate-pulse",
      mic_unavailable: "bg-red-950 text-red-400 border-red-800",
    };
    voiceStatePill.className = `px-4 py-1 rounded-full text-xs font-semibold tracking-wider uppercase mb-3 border ${styleMap[state] || styleMap.idle}`;
  }

  // Update Orb Glow
  if (voiceOrb) {
    if (state === "speaking") {
      voiceOrb.className = "w-24 h-24 rounded-full bg-gradient-to-tr from-emerald-500 via-teal-600 to-cyan-600 flex items-center justify-center shadow-2xl shadow-emerald-500/50 cursor-pointer transform hover:scale-105 transition-all";
    } else if (state === "interrupted") {
      voiceOrb.className = "w-24 h-24 rounded-full bg-gradient-to-tr from-rose-500 to-red-600 flex items-center justify-center shadow-2xl shadow-red-500/50 cursor-pointer transform hover:scale-105 transition-all";
    } else {
      voiceOrb.className = "w-24 h-24 rounded-full bg-gradient-to-tr from-cyan-500 via-blue-600 to-indigo-600 flex items-center justify-center shadow-2xl shadow-cyan-500/50 cursor-pointer transform hover:scale-105 transition-all";
    }
  }
}

function openVoiceOverlay() {
  if (voiceOverlay) voiceOverlay.classList.remove("hidden");
  setVoiceState("listening", "Listening...");
  if (voiceLiveTranscript) {
    voiceLiveTranscript.value = "";
    voiceLiveTranscript.placeholder = "Say 'Hey Zevon' or speak your request...";
  }
  if (speechRecognitionInstance) {
    try {
      speechRecognitionInstance.start();
    } catch (_) {}
  }
}

function closeVoiceOverlay() {
  if (voiceOverlay) voiceOverlay.classList.add("hidden");
  setVoiceState("idle", "Idle");
  if (speechRecognitionInstance) {
    try {
      speechRecognitionInstance.stop();
    } catch (_) {}
  }
  if (currentTTSAudio) {
    currentTTSAudio.pause();
    currentTTSAudio = null;
  }
}

function handleVoiceBargeIn() {
  if (currentTTSAudio) {
    currentTTSAudio.pause();
    currentTTSAudio = null;
  }
  if (window.speechSynthesis) {
    window.speechSynthesis.cancel();
  }
  setVoiceState("interrupted", "Interrupted (Barge-in)");
  fetch("/api/v1/voice/state", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ state: "interrupted" }),
  }).catch(() => {});

  setTimeout(() => {
    setVoiceState("listening", "Listening...");
  }, 1000);
}

function handleVoiceSend() {
  const text = (voiceLiveTranscript ? voiceLiveTranscript.value : "").trim();
  if (!text) return;
  closeVoiceOverlay();
  messageInputEl.value = text;
  messageInputEl.dispatchEvent(new Event("input"));
  handleSendMessage();
}

function handlePushToTalk(isDown) {
  if (isDown) {
    openVoiceOverlay();
    setVoiceState("listening", "Push-to-Talk (Active)");
  } else {
    setVoiceState("transcribing", "Transcribing...");
    setTimeout(() => {
      handleVoiceSend();
    }, 400);
  }
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

// --- Phase 3: View Switching ---

function switchView(viewName) {
  activeView = viewName;

  const tabs = [
    { name: "chat", el: tabChat },
    { name: "tasks", el: tabTasks },
    { name: "tools", el: tabTools },
  ];
  tabs.forEach((t) => {
    if (!t.el) return;
    if (t.name === viewName) {
      t.el.className = "px-3 py-1 rounded-lg font-medium bg-blue-600 text-white shadow-sm transition-all";
    } else {
      t.el.className = "px-3 py-1 rounded-lg font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 transition-all";
    }
  });

  if (viewChat) viewChat.classList.toggle("hidden", viewName !== "chat");
  if (viewTasks) viewTasks.classList.toggle("hidden", viewName !== "tasks");
  if (viewTools) viewTools.classList.toggle("hidden", viewName !== "tools");

  if (viewName === "tasks") {
    loadTasks();
    if (!taskPollingTimer) {
      taskPollingTimer = setInterval(loadTasks, 3000);
    }
  } else {
    if (taskPollingTimer) {
      clearInterval(taskPollingTimer);
      taskPollingTimer = null;
    }
  }

  if (viewName === "tools") {
    loadTools();
    loadMcpServers();
    loadAuditTrail();
  }
}

// --- Phase 3: Task Workspace ---

async function loadTasks() {
  try {
    const res = await fetch("/api/v1/tasks");
    if (!res.ok) return;
    const tasks = await res.json();

    const badge = document.getElementById("tasks-badge-count");
    if (badge) {
      const activeCount = tasks.filter(t => ["running", "waiting_approval", "planning"].includes(t.status)).length;
      if (activeCount > 0) {
        badge.textContent = activeCount;
        badge.classList.remove("hidden");
      } else {
        badge.classList.add("hidden");
      }
    }

    if (!tasksList) return;
    if (tasks.length === 0) {
      tasksList.innerHTML = `<div class="p-4 text-center text-slate-500 text-xs">No tasks yet.</div>`;
      return;
    }

    tasksList.innerHTML = tasks
      .map((t) => {
        const isSelected = t.id === currentTaskId;
        const statusColors = {
          pending: "bg-slate-800 text-slate-400 border-slate-700",
          planning: "bg-cyan-950 text-cyan-400 border-cyan-800",
          running: "bg-blue-950 text-blue-400 border-blue-800",
          waiting_approval: "bg-amber-950 text-amber-400 border-amber-800 animate-pulse",
          completed: "bg-emerald-950 text-emerald-400 border-emerald-800",
          failed: "bg-red-950 text-red-400 border-red-800",
          cancelled: "bg-slate-900 text-slate-500 border-slate-800",
        };
        const badgeCls = statusColors[t.status] || "bg-slate-800 text-slate-400";
        return `
          <div onclick="selectTask('${t.id}')" class="p-2.5 rounded-xl border transition-all cursor-pointer ${
            isSelected
              ? "bg-slate-800/90 border-cyan-500/80 shadow-md"
              : "bg-slate-900/60 border-slate-800 hover:border-slate-700"
          }">
            <div class="flex items-center justify-between mb-1">
              <span class="text-[10px] font-semibold px-1.5 py-0.5 rounded-full border ${badgeCls} uppercase">
                ${t.status.replace("_", " ")}
              </span>
              <span class="text-[10px] text-slate-500 font-mono">
                ${new Date(t.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            </div>
            <div class="text-xs text-slate-200 font-medium truncate">${escapeHtml(t.prompt)}</div>
            <div class="text-[10px] text-slate-400 mt-1 flex items-center justify-between">
              <span>Steps: ${t.plan ? t.plan.length : 0}</span>
              <span>Artifacts: ${t.artifacts ? t.artifacts.length : 0}</span>
            </div>
          </div>
        `;
      })
      .join("");

    if (currentTaskId) {
      const active = tasks.find(t => t.id === currentTaskId);
      if (active) renderTaskDetail(active);
    }
  } catch (err) {
    console.error("Failed to load tasks:", err);
  }
}

async function selectTask(taskId) {
  currentTaskId = taskId;
  try {
    const res = await fetch(`/api/v1/tasks/${taskId}`);
    if (res.ok) {
      const task = await res.json();
      renderTaskDetail(task);
      loadTasks();
    }
  } catch (err) {
    console.error("Error selecting task:", err);
  }
}

function renderTaskDetail(task) {
  if (!noTaskSelected || !taskDetailContent) return;
  noTaskSelected.classList.add("hidden");
  taskDetailContent.classList.remove("hidden");

  taskDetailPrompt.textContent = task.prompt;
  taskDetailTime.textContent = new Date(task.created_at).toLocaleString();

  const statusColors = {
    pending: "bg-slate-800 text-slate-300 border-slate-700",
    planning: "bg-cyan-950 text-cyan-300 border-cyan-800",
    running: "bg-blue-950 text-blue-300 border-blue-800",
    waiting_approval: "bg-amber-950 text-amber-300 border-amber-800 animate-pulse",
    completed: "bg-emerald-950 text-emerald-300 border-emerald-800",
    failed: "bg-red-950 text-red-300 border-red-800",
    cancelled: "bg-slate-900 text-slate-500 border-slate-800",
  };
  taskDetailStatus.className = `px-2.5 py-0.5 rounded-full text-xs font-semibold tracking-wide uppercase border ${
    statusColors[task.status] || "bg-slate-800 text-slate-300"
  }`;
  taskDetailStatus.textContent = task.status.replace("_", " ");

  // Approval Gate Card
  if (task.status === "waiting_approval") {
    const waitingStep = task.plan.find(s => s.status === "waiting_approval");
    if (waitingStep) {
      currentPendingStepId = waitingStep.step_id;
      approvalGateCard.classList.remove("hidden");
      approvalGateDesc.textContent = `Step ${waitingStep.step_id}: '${waitingStep.title}' is classified as Risk Level ${waitingStep.risk_level} and requires explicit approval to proceed.`;
      approvalGatePayload.textContent = JSON.stringify({
        tool: waitingStep.tool_name,
        risk_level: waitingStep.risk_level,
        arguments: waitingStep.arguments,
      }, null, 2);
    }
  } else {
    approvalGateCard.classList.add("hidden");
    currentPendingStepId = null;
  }

  // Plan Timeline
  if (!task.plan || task.plan.length === 0) {
    taskStepsTimeline.innerHTML = `<div class="text-xs text-slate-500 italic p-3">Generating execution plan...</div>`;
  } else {
    taskStepsTimeline.innerHTML = task.plan.map((s) => {
      const riskClass = `badge-${s.risk_level.toLowerCase()}`;
      const stepStatusIcons = {
        pending: "⏳",
        running: "⚡",
        waiting_approval: "⚠️",
        completed: "✅",
        failed: "❌",
        rejected: "🚫",
      };
      return `
        <div class="relative bg-slate-900/80 border border-slate-800 rounded-xl p-3.5 space-y-2">
          <div class="flex items-center justify-between">
            <div class="flex items-center space-x-2">
              <span class="text-xs font-bold text-slate-400">#${s.step_id}</span>
              <span class="text-xs font-semibold text-slate-100">${escapeHtml(s.title)}</span>
              <span class="px-2 py-0.2 text-[10px] rounded-full font-semibold font-mono ${riskClass}">
                ${s.risk_level}
              </span>
            </div>
            <div class="flex items-center space-x-1.5 text-xs font-medium text-slate-400">
              <span>${stepStatusIcons[s.status] || "●"}</span>
              <span class="capitalize">${s.status.replace("_", " ")}</span>
            </div>
          </div>
          ${s.tool_name ? `<div class="text-[11px] text-cyan-400 font-mono">tool: ${s.tool_name}</div>` : ""}
          ${s.result ? `
            <div class="bg-slate-950 p-2.5 rounded-lg border border-slate-800/80 font-mono text-[11px] text-slate-300 overflow-x-auto max-h-36">
              ${escapeHtml(s.result)}
            </div>
          ` : ""}
        </div>
      `;
    }).join("");
  }

  // Artifacts
  if (task.artifacts && task.artifacts.length > 0) {
    taskArtifactsSection.classList.remove("hidden");
    taskArtifactsList.innerHTML = task.artifacts.map(a => `
      <div class="bg-slate-900/80 border border-slate-800 rounded-xl p-3 flex items-center space-x-3">
        <div class="w-8 h-8 rounded-lg bg-cyan-950 text-cyan-400 flex items-center justify-center font-bold text-xs shrink-0">
          ${a.type === "file" ? "📄" : "📝"}
        </div>
        <div class="min-w-0 flex-1">
          <div class="text-xs font-medium text-slate-200 truncate">${escapeHtml(a.path || a.title || "Artifact")}</div>
          <div class="text-[10px] text-slate-500 font-mono">${escapeHtml(a.type || "file")} • ${escapeHtml(a.action || "created")}</div>
        </div>
      </div>
    `).join("");
  } else {
    taskArtifactsSection.classList.add("hidden");
  }
}

async function runNewTask() {
  if (!taskPromptInput) return;
  const prompt = taskPromptInput.value.trim();
  if (!prompt) return;

  try {
    const res = await fetch("/api/v1/tasks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt, conversation_id: currentConversationId || "default" }),
    });
    if (res.ok) {
      const task = await res.json();
      taskPromptInput.value = "";
      currentTaskId = task.id;
      renderTaskDetail(task);
      await loadTasks();
    }
  } catch (err) {
    console.error("Failed to run task:", err);
  }
}

async function handleApproveStep(approved) {
  if (!currentTaskId || !currentPendingStepId) return;
  try {
    const res = await fetch(`/api/v1/tasks/${currentTaskId}/approve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        task_id: currentTaskId,
        step_id: currentPendingStepId,
        approved,
      }),
    });
    if (res.ok) {
      const updated = await res.json();
      renderTaskDetail(updated);
      await loadTasks();
    }
  } catch (err) {
    console.error("Failed to submit approval:", err);
  }
}

async function handleCancelTask() {
  if (!currentTaskId) return;
  try {
    const res = await fetch(`/api/v1/tasks/${currentTaskId}/cancel`, { method: "POST" });
    if (res.ok) {
      const updated = await res.json();
      renderTaskDetail(updated);
      await loadTasks();
    }
  } catch (err) {
    console.error("Failed to cancel task:", err);
  }
}

// --- Phase 3: Tools & MCP Management ---

async function loadTools() {
  try {
    const res = await fetch("/api/v1/tools");
    if (!res.ok) return;
    const tools = await res.json();

    if (toolsCatalogCount) {
      toolsCatalogCount.textContent = `${tools.length} tools registered`;
    }

    if (!toolsCatalogGrid) return;
    toolsCatalogGrid.innerHTML = tools.map(t => {
      const riskClass = `badge-${t.risk_level.toLowerCase()}`;
      return `
        <div class="bg-slate-900/80 border border-slate-800 rounded-xl p-4 flex flex-col justify-between space-y-3">
          <div>
            <div class="flex items-center justify-between mb-1.5">
              <span class="font-bold text-xs text-white font-mono">${escapeHtml(t.name)}</span>
              <span class="px-2 py-0.2 rounded-full text-[10px] font-semibold font-mono ${riskClass}">
                ${t.risk_level}
              </span>
            </div>
            <p class="text-xs text-slate-400 line-clamp-2">${escapeHtml(t.description)}</p>
          </div>
          <div class="text-[10px] text-slate-500 font-mono truncate">
            args: ${Object.keys(t.parameters?.properties || {}).join(", ") || "none"}
          </div>
        </div>
      `;
    }).join("");
  } catch (err) {
    console.error("Failed to load tools:", err);
  }
}

async function loadMcpServers() {
  try {
    const res = await fetch("/api/v1/mcp/servers");
    if (!res.ok) return;
    const servers = await res.json();

    if (!mcpServersGrid) return;
    if (servers.length === 0) {
      mcpServersGrid.innerHTML = `
        <div class="col-span-full p-4 bg-slate-950/60 border border-slate-800/80 rounded-xl text-center text-xs text-slate-500">
          No external MCP servers configured. Click 'Connect MCP Server' to bridge community servers.
        </div>
      `;
      return;
    }

    mcpServersGrid.innerHTML = servers.map(s => `
      <div class="bg-slate-900 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
        <div>
          <div class="flex items-center space-x-2">
            <span class="w-2 h-2 rounded-full ${s.connected ? 'bg-emerald-400' : 'bg-slate-600'}"></span>
            <span class="text-xs font-bold text-white">${escapeHtml(s.name)}</span>
            <span class="text-[10px] px-1.5 py-0.2 rounded bg-slate-800 text-slate-400 font-mono uppercase">${s.transport}</span>
          </div>
          <div class="text-[11px] text-slate-500 font-mono mt-1">
            ${escapeHtml(s.command ? `${s.command} ${(s.args || []).join(' ')}` : s.url || '')}
          </div>
        </div>
        <div class="flex items-center space-x-2">
          ${s.connected ? `
            <button onclick="handleDisconnectMcpServer('${s.id}')" class="text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 px-2.5 py-1 rounded-lg transition-colors">
              Disconnect
            </button>
          ` : `
            <button onclick="handleConnectMcpServer('${s.id}')" class="text-xs bg-blue-600 hover:bg-blue-500 text-white px-2.5 py-1 rounded-lg transition-colors">
              Connect
            </button>
          `}
          <button onclick="handleDeleteMcpServer('${s.id}')" class="text-xs text-red-400 hover:text-red-300 p-1" title="Delete server">
            ✕
          </button>
        </div>
      </div>
    `).join("");
  } catch (err) {
    console.error("Failed to load MCP servers:", err);
  }
}

async function handleCreateMcpServer() {
  const name = mcpNameInput.value.trim();
  const transport = mcpTransportSelect.value;
  if (!name) return;

  const payload = {
    name,
    transport,
    auto_connect: true,
  };

  if (transport === "stdio") {
    payload.command = mcpCommandInput.value.trim();
    const argsRaw = mcpArgsInput.value.trim();
    if (argsRaw) {
      try {
        payload.args = JSON.parse(argsRaw);
      } catch {
        payload.args = argsRaw.split(" ").filter(Boolean);
      }
    }
  } else {
    payload.url = mcpUrlInput.value.trim();
  }

  try {
    const res = await fetch("/api/v1/mcp/servers", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (res.ok) {
      mcpModal.classList.add("hidden");
      mcpNameInput.value = "";
      mcpCommandInput.value = "";
      mcpArgsInput.value = "";
      mcpUrlInput.value = "";
      await loadMcpServers();
      await loadTools();
    }
  } catch (err) {
    console.error("Failed to add MCP server:", err);
  }
}

async function handleConnectMcpServer(id) {
  await fetch(`/api/v1/mcp/servers/${id}/connect`, { method: "POST" });
  await loadMcpServers();
  await loadTools();
}

async function handleDisconnectMcpServer(id) {
  await fetch(`/api/v1/mcp/servers/${id}/disconnect`, { method: "POST" });
  await loadMcpServers();
  await loadTools();
}

async function handleDeleteMcpServer(id) {
  if (confirm("Remove this MCP server?")) {
    await fetch(`/api/v1/mcp/servers/${id}`, { method: "DELETE" });
    await loadMcpServers();
    await loadTools();
  }
}

async function loadAuditTrail() {
  try {
    const res = await fetch("/api/v1/tools/audit");
    if (!res.ok) return;
    const records = await res.json();

    if (!auditTableBody) return;
    if (records.length === 0) {
      auditTableBody.innerHTML = `<tr><td colspan="5" class="p-4 text-center text-slate-500">No tool actions recorded in audit log yet.</td></tr>`;
      return;
    }

    auditTableBody.innerHTML = records.slice(-50).reverse().map(r => {
      const riskClass = `badge-${r.risk_level.toLowerCase()}`;
      return `
        <tr class="hover:bg-slate-800/40 transition-colors">
          <td class="p-2.5 text-slate-400 whitespace-nowrap">${new Date(r.timestamp).toLocaleTimeString()}</td>
          <td class="p-2.5 font-bold text-cyan-300">${escapeHtml(r.tool_name)}</td>
          <td class="p-2.5">
            <span class="px-1.5 py-0.2 rounded font-semibold ${riskClass}">${r.risk_level}</span>
          </td>
          <td class="p-2.5">
            <span class="${r.is_error ? 'text-red-400' : 'text-emerald-400'}">
              ${r.is_error ? 'ERROR' : (r.approved ? 'APPROVED' : 'BLOCKED')}
            </span>
          </td>
          <td class="p-2.5 text-slate-300 truncate max-w-xs font-mono text-[10px]">
            ${escapeHtml(r.result || JSON.stringify(r.arguments))}
          </td>
        </tr>
      `;
    }).join("");
  } catch (err) {
    console.error("Failed to load audit trail:", err);
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
