/* Kisan Sahayak voice and grounded scheme chat. */
const kisanForm = document.getElementById("kisanAskForm");
const kisanQuery = document.getElementById("kisanQuery");
const kisanMessages = document.getElementById("kisanMessages");
const kisanLanguage = document.getElementById("kisanLanguage");
const kisanSpeechLanguage = document.getElementById("kisanSpeechLanguage");
const kisanVoiceStatus = document.getElementById("kisanVoiceStatus");
const kisanAutoSpeak = document.getElementById("kisanAutoSpeak");
const kisanSpeaker = document.getElementById("kisanSpeaker");
const kisanTurnLabel = document.getElementById("kisanTurnLabel");
let kisanTurns = 0;
let kisanRecorder = null;
let kisanRecordingChunks = [];

fetch("/api/kisan/status")
  .then(response => response.json())
  .then(status => {
    const label = document.getElementById("kisanCorpusStatus");
    if (label && status.provider_ready) label.textContent = `AI provider ready · ${status.documents} scheme documents`;
    if (label && !status.provider_ready) label.textContent = `${status.documents} scheme documents · local grounded mode`;
  })
  .catch(() => {});

function addKisanMessage(role, content, citations) {
  const item = document.createElement("article");
  item.className = `kisan-message ${role}`;
  const body = document.createElement("div");
  body.className = "kisan-message-body";
  body.innerHTML = linkifyAnswer(content);
  item.appendChild(body);
  if (role === "assistant" && "speechSynthesis" in window && "SpeechSynthesisUtterance" in window) {
    const speakButton = document.createElement("button");
    speakButton.type = "button";
    speakButton.className = "btn btn-sm btn-outline-success kisan-speak-answer";
    speakButton.title = "Read this answer aloud";
    speakButton.innerHTML = '<i class="bi bi-volume-up-fill"></i>';
    speakButton.addEventListener("click", () => speakKisan(content, kisanLanguage?.value || "English"));
    item.appendChild(speakButton);
  }
  if (citations?.length) {
    const sources = document.createElement("div");
    sources.className = "kisan-sources";
    sources.innerHTML = `<details><summary><i class="bi bi-bookmark-fill"></i> Sources (${citations.length})</summary><div class="kisan-source-list">${citations.map(source => {
      const label = `${escapeHtml(source.scheme)}${source.page ? ` · p. ${source.page}` : ""}`;
      return source.url
        ? `<a href="${escapeHtml(source.url)}" target="_blank" rel="noopener noreferrer">${label} <i class="bi bi-box-arrow-up-right"></i></a>`
        : `<span>${label} · ${escapeHtml(source.source || "bundled document")}</span>`;
    }).join("")}</div></details>`;
    item.appendChild(sources);
  }
  kisanMessages.appendChild(item);
  kisanMessages.scrollTop = kisanMessages.scrollHeight;
}

function addSchemeResults(result) {
  if (!result?.schemes?.length) return;
  const translations = {
    English: { eligibility: "Eligibility", benefits: "Benefits", why: "Why this matches", documents: "Required documents", source: "Official Source", apply: "Official Application", info: "Official Information", verified: "Last verified" },
    Telugu: { eligibility: "అర్హత", benefits: "ప్రయోజనాలు", why: "ఎందుకు సరిపోతుంది", documents: "అవసరమైన పత్రాలు", source: "అధికారిక మూలం", apply: "అధికారిక దరఖాస్తు", info: "అధికారిక సమాచారం", verified: "చివరిగా ధృవీకరించిన తేదీ" },
    Hindi: { eligibility: "पात्रता", benefits: "लाभ", why: "यह क्यों उपयुक्त है", documents: "आवश्यक दस्तावेज़", source: "आधिकारिक स्रोत", apply: "आधिकारिक आवेदन", info: "आधिकारिक जानकारी", verified: "अंतिम सत्यापन" },
    Tamil: { eligibility: "தகுதி", benefits: "நன்மைகள்", why: "ஏன் பொருந்துகிறது", documents: "தேவையான ஆவணங்கள்", source: "அதிகாரப்பூர்வ மூலம்", apply: "அதிகாரப்பூர்வ விண்ணப்பம்", info: "அதிகாரப்பூர்வ தகவல்", verified: "கடைசி சரிபார்ப்பு" },
    Kannada: { eligibility: "ಅರ್ಹತೆ", benefits: "ಪ್ರಯೋಜನಗಳು", why: "ಏಕೆ ಹೊಂದಿಕೆಯಾಗುತ್ತದೆ", documents: "ಅಗತ್ಯ ದಾಖಲೆಗಳು", source: "ಅಧಿಕೃತ ಮೂಲ", apply: "ಅಧಿಕೃತ ಅರ್ಜಿ", info: "ಅಧಿಕೃತ ಮಾಹಿತಿ", verified: "ಕೊನೆಯ ಪರಿಶೀಲನೆ" },
    Malayalam: { eligibility: "യോഗ്യത", benefits: "പ്രയോജനങ്ങൾ", why: "എന്തുകൊണ്ട് അനുയോജ്യം", documents: "ആവശ്യമായ രേഖകൾ", source: "ഔദ്യോഗിക ഉറവിടം", apply: "ഔദ്യോഗിക അപേക്ഷ", info: "ഔദ്യോഗിക വിവരം", verified: "അവസാന പരിശോധന" },
  };
  const labels = translations[result.language] || translations.English;
  const cards = document.createElement("div");
  cards.className = "kisan-scheme-results";
  cards.innerHTML = result.schemes.map(scheme => `<article class="kisan-scheme-card"><div class="kisan-scheme-heading"><h3>${escapeHtml(scheme.scheme_name)}</h3><span>${escapeHtml(scheme.level)} · ${escapeHtml(scheme.state)}</span></div><p>${escapeHtml(scheme.description)}</p><p><strong>${labels.eligibility}:</strong> ${escapeHtml(scheme.eligibility_status)}</p><p><strong>${labels.why}:</strong> ${escapeHtml(scheme.eligibility_reason)}</p><p><strong>${labels.benefits}:</strong></p><ul>${scheme.benefits.map(item => `<li>${escapeHtml(item)}</li>`).join("")}</ul><p><strong>${labels.documents}:</strong></p><ul>${scheme.documents.map(item => `<li>${escapeHtml(item)}</li>`).join("")}</ul><small>${labels.verified}: ${escapeHtml(scheme.last_verified)}</small><div class="kisan-scheme-links">${scheme.application_url ? `<a href="${escapeHtml(scheme.application_url)}" target="_blank" rel="noopener noreferrer">${labels.apply} <i class="bi bi-box-arrow-up-right"></i></a>` : `<span>${labels.info}</span>`}<a href="${escapeHtml(scheme.official_source_url)}" target="_blank" rel="noopener noreferrer">${labels.source} <i class="bi bi-box-arrow-up-right"></i></a></div></article>`).join("");
  kisanMessages.appendChild(cards);
  kisanMessages.scrollTop = kisanMessages.scrollHeight;
}

async function askKisan(query) {
  const language = kisanLanguage.value;
  addKisanMessage("user", query);
  const loading = document.createElement("article");
  loading.className = "kisan-message assistant kisan-loading";
  loading.textContent = "Searching official scheme documents...";
  kisanMessages.appendChild(loading);
  try {
    const response = await fetch("/api/kisan/ask", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query, language }) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Unable to answer this question.");
    loading.remove();
    addKisanMessage("assistant", data.answer, data.citations);
    addSchemeResults(data.scheme_results);
    kisanTurns += 1;
    if (kisanTurnLabel) kisanTurnLabel.textContent = `${kisanTurns} turn${kisanTurns === 1 ? "" : "s"}`;
    if (data.retrieval?.mode === "local-grounded") kisanVoiceStatus.textContent = "Add SARVAM_API_KEY or OPENAI_API_KEY in agribot/.env for generated Telugu answers.";
    if (kisanAutoSpeak?.checked && "speechSynthesis" in window) speakKisan(data.answer, kisanLanguage.value);
  } catch (error) {
    loading.remove();
    addKisanMessage("assistant", error.message);
  }
}

kisanForm?.addEventListener("submit", event => {
  event.preventDefault();
  const query = kisanQuery.value.trim();
  if (!query) return;
  kisanQuery.value = "";
  askKisan(query);
});

document.querySelectorAll(".kisan-suggestion").forEach(button => button.addEventListener("click", () => askKisan(button.dataset.query)));

function speakKisan(text, language) {
  if (!("speechSynthesis" in window)) {
    if (kisanVoiceStatus) kisanVoiceStatus.textContent = "Read aloud is not supported in this browser.";
    return;
  }
  const speech = window.speechSynthesis;
  speech.cancel();
  speech.resume();
  const spokenText = text.split(/\n\s*Sources and application references:/i)[0].replace(/[*#]/g, "").trim();
  if (!spokenText) return;
  const utterance = new window.SpeechSynthesisUtterance(spokenText);
  const selectedLanguage = language || "English";
  const languageCode = { Telugu: "te-IN", Hindi: "hi-IN", Tamil: "ta-IN", Kannada: "kn-IN", Malayalam: "ml-IN" }[selectedLanguage] || "en-IN";
  utterance.lang = languageCode;
  const voices = speech.getVoices();
  const matchingVoice = voices.find(voice => voice.lang.toLowerCase().startsWith(languageCode.slice(0, 2)));
  if (matchingVoice) utterance.voice = matchingVoice;
  utterance.rate = 0.95;
  utterance.onerror = () => {
    if (kisanVoiceStatus) kisanVoiceStatus.textContent = "Read aloud was blocked by the browser. Click the page once and try again.";
  };
  setTimeout(() => {
    speech.resume();
    speech.speak(utterance);
  }, 50);
}

document.getElementById("kisanNewConversation")?.addEventListener("click", () => {
  kisanMessages.innerHTML = '<div class="kisan-welcome"><div class="kisan-welcome-icon"><i class="bi bi-leaf-fill"></i></div><div><h2>How can I help your farm?</h2><p>Ask about a government scheme, subsidy, eligibility rule, or application.</p></div></div>';
  kisanTurns = 0;
  if (kisanTurnLabel) kisanTurnLabel.textContent = "0 turns";
  if (kisanVoiceStatus) kisanVoiceStatus.textContent = "New conversation started.";
});

document.getElementById("kisanEmailSend")?.addEventListener("click", () => {
  const email = document.getElementById("kisanEmail")?.value.trim();
  const status = document.getElementById("kisanEmailStatus");
  if (status) status.textContent = email ? "Transcript email is ready for backend setup." : "Enter an email address first.";
});

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
const mic = document.getElementById("kisanMic");
if (navigator.mediaDevices?.getUserMedia && window.MediaRecorder && mic) {
  mic.addEventListener("click", () => {
    if (kisanRecorder?.state === "recording") {
      kisanRecorder.stop();
      mic.innerHTML = '<i class="bi bi-mic-fill"></i>';
      return;
    }
    navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
      kisanRecordingChunks = [];
      kisanRecorder = new MediaRecorder(stream);
      kisanRecorder.ondataavailable = event => { if (event.data.size) kisanRecordingChunks.push(event.data); };
      kisanRecorder.onstop = async () => {
        stream.getTracks().forEach(track => track.stop());
        kisanVoiceStatus.textContent = "Transcribing your question...";
        const language = { Hindi: "hi-IN", Telugu: "te-IN", Tamil: "ta-IN", Kannada: "kn-IN", Malayalam: "ml-IN" }[kisanLanguage.value] || "en-IN";
        const formData = new FormData();
        formData.append("audio", new Blob(kisanRecordingChunks, { type: "audio/webm" }), "kisan.webm");
        formData.append("language", language);
        try {
          const response = await fetch("/api/kisan/voice", { method: "POST", body: formData });
          const data = await response.json();
          if (!response.ok) throw new Error(data.error || "Voice transcription failed.");
          kisanQuery.value = data.text || "";
          kisanVoiceStatus.textContent = data.text ? "Voice question captured. Press send." : "No speech was detected.";
        } catch (error) {
          kisanVoiceStatus.textContent = error.message;
        }
      };
      kisanRecorder.start();
      mic.innerHTML = '<i class="bi bi-stop-fill"></i>';
      kisanVoiceStatus.textContent = "Recording... click the microphone again to stop.";
    }).catch(() => { kisanVoiceStatus.textContent = "Microphone permission was denied or unavailable."; });
  });
} else if (SpeechRecognition && mic) {
  mic.addEventListener("click", () => {
    const recognition = new SpeechRecognition();
    recognition.lang = { Hindi: "hi-IN", Telugu: "te-IN", Tamil: "ta-IN", Kannada: "kn-IN", Malayalam: "ml-IN" }[kisanLanguage.value] || "en-IN";
    recognition.interimResults = false;
    kisanVoiceStatus.textContent = "Listening...";
    recognition.onresult = event => { kisanQuery.value = event.results[0][0].transcript; kisanVoiceStatus.textContent = "Voice question captured. Press send."; };
    recognition.onerror = () => { kisanVoiceStatus.textContent = "Voice input was unavailable. You can type your question instead."; };
    recognition.onend = () => { if (kisanVoiceStatus.textContent === "Listening...") kisanVoiceStatus.textContent = ""; };
    recognition.start();
  });
} else if (mic) {
  mic.disabled = true;
  mic.title = "Voice input is not supported in this browser";
}

function escapeHtml(value) {
  const node = document.createElement("div");
  node.textContent = value == null ? "" : String(value);
  return node.innerHTML;
}

function linkifyAnswer(value) {
  return escapeHtml(value).replace(
    /(https?:\/\/[^\s<]+)/g,
    '<a href="$1" target="_blank" rel="noopener noreferrer">$1 <i class="bi bi-box-arrow-up-right"></i></a>'
  );
}
