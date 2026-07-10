/* AgriBot – Chat Page JS */

const chatMessages = document.getElementById("chatMessages");
const chatInput    = document.getElementById("chatInput");
const sendBtn      = document.getElementById("sendBtn");
const clearChatBtn = document.getElementById("clearChatBtn");
const modelBadge   = document.getElementById("modelBadge");

// Load model badge
fetch("/health").then(r => r.json()).then(d => {
  if (modelBadge) modelBadge.textContent = d.model || "unknown";
}).catch(() => {});

// Load history on page load
async function loadHistory() {
  try {
    const data = await apiFetch("/api/chat/history");
    data.forEach(msg => appendMessage(msg.role, msg.content, false));
    scrollToBottom();
  } catch (_) {}
}
loadHistory();

function appendMessage(role, content, animate = true) {
  const isUser    = role === "user";
  const avatarIcon = isUser ? "person-fill" : "robot";
  const avatarClass = isUser ? "user-msg" : "";

  const wrapper = document.createElement("div");
  wrapper.className = `chat-message ${avatarClass}`;

  const renderedContent = isUser ? escapeHtml(content) : renderMarkdown(content);

  wrapper.innerHTML = `
    <div class="chat-avatar"><i class="bi bi-${avatarIcon}"></i></div>
    <div>
      <div class="chat-bubble ${animate && !isUser ? 'typing-anim' : ''}">
        ${renderedContent}
        ${!isUser ? `<div class="chat-bubble-actions">
          <button class="btn btn-xs btn-outline-secondary" onclick="copyText(this)" title="Copy">
            <i class="bi bi-clipboard"></i>
          </button>
        </div>` : ""}
      </div>
      <small class="text-muted d-block mt-1 px-1" style="font-size:.7rem;">${new Date().toLocaleTimeString()}</small>
    </div>`;

  chatMessages.appendChild(wrapper);
  scrollToBottom();
}

function appendTyping() {
  const el = document.createElement("div");
  el.className = "chat-message";
  el.id = "typingIndicator";
  el.innerHTML = `
    <div class="chat-avatar"><i class="bi bi-robot"></i></div>
    <div class="chat-bubble">
      <div class="typing-dots"><span></span><span></span><span></span></div>
    </div>`;
  chatMessages.appendChild(el);
  scrollToBottom();
}

function removeTyping() {
  const el = document.getElementById("typingIndicator");
  if (el) el.remove();
}

async function sendMessage(text) {
  const msg = (text || chatInput.value).trim();
  if (!msg) return;

  chatInput.value = "";
  chatInput.style.height = "auto";
  sendBtn.disabled = true;
  document.getElementById("suggestedRow").style.display = "none";

  appendMessage("user", msg);
  appendTyping();

  try {
    const data = await apiFetch("/api/chat/message", {
      method: "POST",
      body: JSON.stringify({ message: msg }),
    });
    removeTyping();
    appendMessage("assistant", data.reply);
  } catch (err) {
    removeTyping();
    appendMessage("assistant", `⚠️ Error: ${err.message}`);
  } finally {
    sendBtn.disabled = false;
  }
}

// Events
sendBtn.addEventListener("click", () => sendMessage());
chatInput.addEventListener("keydown", e => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
});
chatInput.addEventListener("input", function () {
  this.style.height = "auto";
  this.style.height = Math.min(this.scrollHeight, 140) + "px";
});
clearChatBtn.addEventListener("click", async () => {
  await apiFetch("/api/chat/clear", { method: "POST" });
  chatMessages.innerHTML = "";
  document.getElementById("suggestedRow").style.display = "";
});

function sendSuggested(el) { sendMessage(el.textContent); }

function copyText(btn) {
  const bubble = btn.closest(".chat-bubble");
  const text   = bubble.innerText.replace("Copy", "").trim();
  navigator.clipboard.writeText(text).then(() => {
    btn.innerHTML = '<i class="bi bi-check2"></i>';
    setTimeout(() => { btn.innerHTML = '<i class="bi bi-clipboard"></i>'; }, 1500);
  });
}

function scrollToBottom() {
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function escapeHtml(t) {
  return t.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}
