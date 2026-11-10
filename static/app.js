/**
 * Nova Voice Assistant — Frontend Engine
 * Complete Web Audio API, MediaRecorder, State Machine, and Canvas Visualizer
 */

class VoiceAssistantApp {
  constructor() {
    // Application States: 'idle' | 'listening' | 'thinking' | 'speaking'
    this.state = 'idle';

    // Settings & State Flags
    this.isVoiceEnabled = true;
    this.isAutoRecordEnabled = false;
    this.activePersona = 'friendly';
    this.activeVoice = 'en-US-AriaNeural';
    this.customPrompt = '';
    this.sessionId = 'session_' + Math.random().toString(36).substring(2, 9);

    // Audio & Media Recording
    this.audioContext = null;
    this.micStream = null;
    this.micSourceNode = null;
    this.micAnalyserNode = null;
    this.playbackSourceNode = null;
    this.playbackAnalyserNode = null;
    this.mediaRecorder = null;
    this.recordedAudioChunks = [];
    this.recordingStartTime = 0;
    this.recordingTimerInterval = null;

    // Chat History
    this.messages = [];
    this.isDrawerOpen = false;

    // Canvas Visualizer
    this.canvas = null;
    this.ctx = null;
    this.animationFrameId = null;
    this.particles = [];

    // DOM Elements Cache
    this.initElements();
    this.loadSettings();
    this.initAudioContext();
    this.initVisualizer();
    this.bindEvents();
    this.loadHistory();
    this.fetchServerStatus();
  }

  // ---------------------------------------------------------------------------
  // 1. Element Binding
  // ---------------------------------------------------------------------------
  initElements() {
    this.floatingBot = document.getElementById('floatingBot');
    this.orbCore = document.getElementById('orbCore');
    this.orbStateIcon = document.getElementById('orbStateIcon');
    this.heroStatusText = document.getElementById('heroStatusText');
    this.mainStatusBadge = document.getElementById('mainStatusBadge');
    this.statusIndicatorDot = document.getElementById('statusIndicatorDot');
    this.subStatusText = document.getElementById('subStatusText');
    this.liveSubtitleBox = document.getElementById('liveSubtitleBox');
    this.liveSubtitleText = document.getElementById('liveSubtitleText');
    this.liveFileBanner = document.getElementById('liveFileBanner');
    this.liveFileLink = document.getElementById('liveFileLink');
    this.liveFileText = document.getElementById('liveFileText');
    this.liveFileIcon = document.getElementById('liveFileIcon');
    this.liveSourcesBanner = document.getElementById('liveSourcesBanner');
    this.liveSourcesText = document.getElementById('liveSourcesText');

    this.micButton = document.getElementById('micButton');
    this.micBtnIcon = document.getElementById('micBtnIcon');
    this.recordingTimerBadge = document.getElementById('recordingTimerBadge');
    this.recordingTime = document.getElementById('recordingTime');
    this.cancelRecordBtn = document.getElementById('cancelRecordBtn');
    this.textInput = document.getElementById('textInput');
    this.sendBtn = document.getElementById('sendBtn');

    this.toggleVoiceBtn = document.getElementById('toggleVoiceBtn');
    this.voiceToggleIcon = document.getElementById('voiceToggleIcon');
    this.voiceToggleLabel = document.getElementById('voiceToggleLabel');
    this.toggleAutoRecordBtn = document.getElementById('toggleAutoRecordBtn');
    this.autoRecordIcon = document.getElementById('autoRecordIcon');

    this.personaSelect = document.getElementById('personaSelect');
    this.voiceSelect = document.getElementById('voiceSelect');

    this.toggleDrawerBtn = document.getElementById('toggleDrawerBtn');
    this.closeDrawerBtn = document.getElementById('closeDrawerBtn');
    this.chatDrawer = document.getElementById('chatDrawer');
    this.chatMessages = document.getElementById('chatMessages');
    this.emptyChatPlaceholder = document.getElementById('emptyChatPlaceholder');
    this.messageCountBadge = document.getElementById('messageCountBadge');
    this.clearChatBtn = document.getElementById('clearChatBtn');
    this.unreadBadge = document.getElementById('unreadBadge');

    this.settingsModal = document.getElementById('settingsModal');
    this.openSettingsBtn = document.getElementById('openSettingsBtn');
    this.closeSettingsBtn = document.getElementById('closeSettingsBtn');
    this.saveSettingsBtn = document.getElementById('saveSettingsBtn');
    this.resetSettingsBtn = document.getElementById('resetSettingsBtn');
    this.customPromptInput = document.getElementById('customPromptInput');
    this.personaTagline = document.getElementById('personaTagline');

    this.ttsAudioPlayer = document.getElementById('ttsAudioPlayer');
    this.canvas = document.getElementById('visualizerCanvas');
    this.ctx = this.canvas.getContext('2d');
  }

  // ---------------------------------------------------------------------------
  // 2. Audio Engine & Web Audio Setup
  // ---------------------------------------------------------------------------
  initAudioContext() {
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (AudioCtx) {
      this.audioContext = new AudioCtx();
    }
  }

  ensureAudioContextRunning() {
    if (this.audioContext && this.audioContext.state === 'suspended') {
      this.audioContext.resume();
    }
  }

  setupPlaybackAudioNode() {
    if (!this.audioContext || this.playbackSourceNode) return;
    try {
      this.playbackSourceNode = this.audioContext.createMediaElementSource(this.ttsAudioPlayer);
      this.playbackAnalyserNode = this.audioContext.createAnalyser();
      this.playbackAnalyserNode.fftSize = 256;
      this.playbackAnalyserNode.smoothingTimeConstant = 0.8;

      this.playbackSourceNode.connect(this.playbackAnalyserNode);
      this.playbackAnalyserNode.connect(this.audioContext.destination);
    } catch (e) {
      console.warn("Could not bind MediaElementSource to audio player:", e);
    }
  }

  // ---------------------------------------------------------------------------
  // 3. State Machine Controller
  // ---------------------------------------------------------------------------
  setState(newState) {
    if (this.state === newState) return;
    this.state = newState;

    // Reset bot classes
    this.floatingBot.classList.remove('bot-idle', 'bot-listening', 'bot-thinking', 'bot-speaking');
    this.floatingBot.classList.add(`bot-${newState}`);

    switch (newState) {
      case 'idle':
        this.orbStateIcon.className = 'fa-solid fa-microphone text-2xl text-white/90 drop-shadow-md';
        this.heroStatusText.innerText = 'Click Orb or Press Spacebar to Talk';
        this.mainStatusBadge.innerText = 'Agent Idle';
        this.statusIndicatorDot.className = 'w-2 h-2 rounded-full bg-emerald-400 shadow-sm shadow-emerald-400';
        this.micButton.className = 'flex-shrink-0 w-11 h-11 rounded-xl bg-gradient-to-tr from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white flex items-center justify-center transition-all duration-300 shadow-lg shadow-purple-600/30';
        this.micBtnIcon.className = 'fa-solid fa-microphone text-base';
        this.recordingTimerBadge.classList.add('hidden');
        this.recordingTimerBadge.classList.remove('flex');
        this.stopRecordingTimer();
        break;

      case 'listening':
        this.orbStateIcon.className = 'fa-solid fa-waveform-lines text-2xl text-white drop-shadow-md animate-pulse';
        this.heroStatusText.innerText = 'Listening to you... Click to Send';
        this.mainStatusBadge.innerText = 'Listening...';
        this.statusIndicatorDot.className = 'w-2 h-2 rounded-full bg-cyan-400 shadow-sm shadow-cyan-400 animate-ping';
        this.micButton.className = 'flex-shrink-0 w-11 h-11 rounded-xl bg-gradient-to-tr from-cyan-500 to-emerald-500 text-white flex items-center justify-center transition-all duration-300 shadow-lg shadow-cyan-500/40 animate-pulse';
        this.micBtnIcon.className = 'fa-solid fa-stop text-base';
        this.recordingTimerBadge.classList.remove('hidden');
        this.recordingTimerBadge.classList.add('flex');
        this.startRecordingTimer();
        break;

      case 'thinking':
        this.orbStateIcon.className = 'fa-solid fa-spinner-third text-2xl text-white drop-shadow-md animate-spin';
        this.heroStatusText.innerText = 'Synthesizing response with Groq Llama 3.3...';
        this.mainStatusBadge.innerText = 'Thinking...';
        this.statusIndicatorDot.className = 'w-2 h-2 rounded-full bg-pink-400 shadow-sm shadow-pink-400 animate-pulse';
        this.micButton.className = 'flex-shrink-0 w-11 h-11 rounded-xl bg-purple-900/60 text-slate-400 flex items-center justify-center cursor-not-allowed';
        this.micBtnIcon.className = 'fa-solid fa-brain text-base animate-pulse';
        this.recordingTimerBadge.classList.add('hidden');
        this.recordingTimerBadge.classList.remove('flex');
        this.stopRecordingTimer();
        break;

      case 'speaking':
        this.orbStateIcon.className = 'fa-solid fa-volume-high text-2xl text-white drop-shadow-md animate-bounce';
        this.heroStatusText.innerText = 'Nova is speaking...';
        this.mainStatusBadge.innerText = 'Speaking...';
        this.statusIndicatorDot.className = 'w-2 h-2 rounded-full bg-purple-400 shadow-sm shadow-purple-400 animate-ping';
        this.micButton.className = 'flex-shrink-0 w-11 h-11 rounded-xl bg-gradient-to-tr from-purple-600 to-pink-600 text-white flex items-center justify-center transition-all duration-300 shadow-lg shadow-purple-600/30';
        this.micBtnIcon.className = 'fa-solid fa-volume-high text-base';
        this.recordingTimerBadge.classList.add('hidden');
        this.recordingTimerBadge.classList.remove('flex');
        this.stopRecordingTimer();
        break;
    }
  }

  // ---------------------------------------------------------------------------
  // 4. Voice Recording & MediaStream
  // ---------------------------------------------------------------------------
  async toggleVoiceRecording() {
    this.ensureAudioContextRunning();

    if (this.state === 'listening') {
      this.stopVoiceRecording(true);
    } else if (this.state === 'idle') {
      await this.startVoiceRecording();
    } else if (this.state === 'speaking') {
      // If AI is currently speaking, user click interrupts and starts recording
      this.stopAudioPlayback();
      await this.startVoiceRecording();
    }
  }

  async startVoiceRecording() {
    try {
      this.recordedAudioChunks = [];
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });
      this.micStream = stream;

      // Connect mic stream to analyser for visualizer
      if (this.audioContext) {
        this.micSourceNode = this.audioContext.createMediaStreamSource(stream);
        this.micAnalyserNode = this.audioContext.createAnalyser();
        this.micAnalyserNode.fftSize = 256;
        this.micAnalyserNode.smoothingTimeConstant = 0.7;
        this.micSourceNode.connect(this.micAnalyserNode);
      }

      // Determine supported mimeType
      const mimeTypes = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/ogg'];
      let chosenMime = mimeTypes.find(type => MediaRecorder.isTypeSupported(type)) || '';

      this.mediaRecorder = new MediaRecorder(stream, chosenMime ? { mimeType: chosenMime } : undefined);

      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          this.recordedAudioChunks.push(event.data);
        }
      };

      this.mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(this.recordedAudioChunks, { type: chosenMime || 'audio/webm' });
        this.cleanupMicStream();

        if (audioBlob.size > 200 && this.state !== 'idle') {
          await this.sendVoicePayload(audioBlob);
        } else {
          this.setState('idle');
        }
      };

      this.mediaRecorder.start(100);
      this.setState('listening');
      this.showLiveSubtitle("Listening to your voice...");
    } catch (err) {
      console.error("Microphone access error:", err);
      alert("Microphone permission was denied or not found. Please allow microphone access in your browser settings.");
      this.setState('idle');
    }
  }

  stopVoiceRecording(shouldProcess = true) {
    if (!this.mediaRecorder || this.mediaRecorder.state === 'inactive') return;

    if (!shouldProcess) {
      this.recordedAudioChunks = [];
    }

    try {
      this.mediaRecorder.stop();
    } catch (e) {
      console.warn("Error stopping mediaRecorder:", e);
    }
  }

  cleanupMicStream() {
    if (this.micStream) {
      this.micStream.getTracks().forEach(track => track.stop());
      this.micStream = null;
    }
    if (this.micSourceNode) {
      try { this.micSourceNode.disconnect(); } catch (e) {}
      this.micSourceNode = null;
    }
    this.micAnalyserNode = null;
  }

  startRecordingTimer() {
    this.recordingStartTime = Date.now();
    this.recordingTime.innerText = '00:00';
    clearInterval(this.recordingTimerInterval);
    this.recordingTimerInterval = setInterval(() => {
      const elapsed = Math.floor((Date.now() - this.recordingStartTime) / 1000);
      const mins = String(Math.floor(elapsed / 60)).padStart(2, '0');
      const secs = String(elapsed % 60).padStart(2, '0');
      this.recordingTime.innerText = `${mins}:${secs}`;
    }, 500);
  }

  stopRecordingTimer() {
    clearInterval(this.recordingTimerInterval);
    this.recordingTimerInterval = null;
  }

  // ---------------------------------------------------------------------------
  // 5. Backend Communication Pipeline
  // ---------------------------------------------------------------------------
  async sendVoicePayload(audioBlob) {
    this.setState('thinking');
    this.showLiveSubtitle("Sending audio to Groq Whisper...");

    const formData = new FormData();
    formData.append('file', audioBlob, 'user_voice.webm');
    formData.append('voice_enabled', this.isVoiceEnabled);
    formData.append('session_id', this.sessionId);
    formData.append('persona', this.activePersona);
    formData.append('voice', this.activeVoice);
    if (this.customPrompt) {
      formData.append('custom_prompt', this.customPrompt);
    }
    formData.append('history_json', JSON.stringify(this.getRecentHistory(8)));

    try {
      const response = await fetch('/api/voice-agent', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Server returned ${response.status}`);
      }

      const result = await response.json();
      this.handleAssistantResponse(result);
    } catch (err) {
      console.error("Voice Agent error:", err);
      this.showLiveSubtitle(`Error: ${err.message}`);
      this.addMessageToChat('assistant', `⚠️ Sorry, an error occurred: ${err.message}`);
      this.setState('idle');
    }
  }

  async sendTextMessage() {
    const text = this.textInput.value.trim();
    if (!text || this.state === 'thinking') return;

    this.ensureAudioContextRunning();
    this.textInput.value = '';
    this.autoResizeTextarea();

    // Append user message immediately
    this.addMessageToChat('user', text);
    this.setState('thinking');
    this.showLiveSubtitle(`Thinking: "${text.substring(0, 40)}..."`);

    try {
      const payload = {
        text: text,
        voice_enabled: this.isVoiceEnabled,
        session_id: this.sessionId,
        persona: this.activePersona,
        voice: this.activeVoice,
        custom_prompt: this.customPrompt || null,
        history: this.getRecentHistory(8)
      };

      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Server returned ${response.status}`);
      }

      const result = await response.json();
      this.handleAssistantResponse(result, false);
    } catch (err) {
      console.error("Chat error:", err);
      this.showLiveSubtitle(`Error: ${err.message}`);
      this.addMessageToChat('assistant', `⚠️ Error: ${err.message}`);
      this.setState('idle');
    }
  }

  handleAssistantResponse(result, includeTranscribedUser = true) {
    // 1. If voice audio was transcribed and not already displayed
    if (includeTranscribedUser && result.transcribed_text) {
      this.addMessageToChat('user', result.transcribed_text);
    }

    // 2. Extract file generation metadata
    const fileData = result.file_url ? {
      file_url: result.file_url,
      file_name: result.file_name || 'document',
      file_type: result.file_type || 'pdf',
      file_size: result.file_size || 'File'
    } : null;

    // 3. Update Hero Live File Banner if generated
    if (fileData && this.liveFileBanner) {
      this.liveFileLink.href = fileData.file_url;
      this.liveFileLink.setAttribute('download', fileData.file_name);
      this.liveFileText.innerText = `${fileData.file_name} (${fileData.file_size})`;
      const iconMap = {
        pdf: 'fa-solid fa-file-pdf text-red-400',
        pptx: 'fa-solid fa-file-powerpoint text-orange-400',
        docx: 'fa-solid fa-file-word text-blue-400',
        xlsx: 'fa-solid fa-file-excel text-emerald-400',
        csv: 'fa-solid fa-file-csv text-cyan-400'
      };
      this.liveFileIcon.className = iconMap[fileData.file_type] || 'fa-solid fa-file-arrow-down text-emerald-400';
      this.liveFileBanner.classList.remove('hidden');
    }

    // 4. Update Hero Live Web Sources Banner if sources retrieved
    if (result.sources && result.sources.length > 0 && this.liveSourcesBanner) {
      this.liveSourcesText.innerText = `Verified ${result.sources.length} live web sources`;
      this.liveSourcesBanner.classList.remove('hidden');
    } else if (this.liveSourcesBanner) {
      this.liveSourcesBanner.classList.add('hidden');
    }

    // 5. Append Assistant text response, File Card, and Source Citations
    const msgId = this.addMessageToChat('assistant', result.text_response, result.audio_base64, fileData, result.sources);

    // 6. Update Subtitle Preview
    this.showLiveSubtitle(result.text_response);

    // 6. Play Audio if available and Voice Enabled
    if (this.isVoiceEnabled) {
      const onEnded = () => {
        this.setState('idle');
        if (this.isAutoRecordEnabled) {
          setTimeout(() => {
            if (this.state === 'idle') {
              this.startVoiceRecording();
            }
          }, 400);
        }
      };

      if (result.audio_base64) {
        this.playBase64Audio(result.audio_base64, onEnded);
      } else {
        // Fallback to local browser Web Speech API synthesis
        this.speakClientTTS(result.text_response, onEnded);
      }
    } else {
      this.setState('idle');
    }
  }

  // ---------------------------------------------------------------------------
  // 6. Audio Playback Engine
  // ---------------------------------------------------------------------------
  speakClientTTS(text, onEndedCallback = null) {
    if (!('speechSynthesis' in window)) {
      if (onEndedCallback) onEndedCallback();
      this.setState('idle');
      return;
    }
    try {
      window.speechSynthesis.cancel();
      // Clean markdown tags for local speech
      const clean = text.replace(/[*_#`[\]()]/g, ' ').substring(0, 500);
      const utterance = new SpeechSynthesisUtterance(clean);
      utterance.rate = 1.0;
      utterance.pitch = 1.0;
      this.setState('speaking');

      utterance.onend = () => {
        this.setState('idle');
        if (onEndedCallback) onEndedCallback();
      };
      utterance.onerror = (err) => {
        console.warn("SpeechSynthesis error:", err);
        this.setState('idle');
        if (onEndedCallback) onEndedCallback();
      };
      window.speechSynthesis.speak(utterance);
    } catch (e) {
      console.warn("speechSynthesis error:", e);
      this.setState('idle');
      if (onEndedCallback) onEndedCallback();
    }
  }

  playBase64Audio(base64Data, onEndedCallback = null) {
    this.ensureAudioContextRunning();
    this.setupPlaybackAudioNode();

    this.ttsAudioPlayer.src = base64Data;
    this.setState('speaking');

    this.ttsAudioPlayer.onended = () => {
      if (onEndedCallback) onEndedCallback();
    };

    this.ttsAudioPlayer.onerror = (e) => {
      console.warn("Audio playback error:", e);
      this.setState('idle');
    };

    this.ttsAudioPlayer.play().catch(err => {
      console.warn("Autoplay was blocked or failed:", err);
      this.setState('idle');
    });
  }

  stopAudioPlayback() {
    if (this.ttsAudioPlayer) {
      this.ttsAudioPlayer.pause();
      this.ttsAudioPlayer.currentTime = 0;
    }
  }

  async replayAudio(messageId) {
    const msg = this.messages.find(m => m.id === messageId);
    if (!msg) return;

    if (msg.audioBase64) {
      this.playBase64Audio(msg.audioBase64, () => this.setState('idle'));
      return;
    }

    // Generate audio on-demand if missing
    try {
      this.setState('thinking');
      const response = await fetch('/api/tts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: msg.text, voice: this.activeVoice })
      });
      if (response.ok) {
        const data = await response.json();
        msg.audioBase64 = data.audio_base64;
        this.saveHistory();
        this.playBase64Audio(data.audio_base64, () => this.setState('idle'));
      }
    } catch (e) {
      console.error("Replay TTS error:", e);
      this.setState('idle');
    }
  }

  // ---------------------------------------------------------------------------
  // 7. Chat Timeline & LocalStorage
  // ---------------------------------------------------------------------------
  addMessageToChat(role, text, audioBase64 = null, fileData = null, sources = null) {
    const id = 'msg_' + Date.now() + '_' + Math.random().toString(36).substring(2, 6);
    const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    const messageObj = { id, role, text, audioBase64, fileData, sources, timestamp };
    this.messages.push(messageObj);
    this.saveHistory();

    this.renderMessage(messageObj);
    this.updateMessageBadge();

    // If drawer is closed and it's an assistant message, light up unread badge
    if (!this.isDrawerOpen && role === 'assistant') {
      this.unreadBadge.classList.remove('hidden');
    }

    return id;
  }

  renderMessage(msg) {
    if (this.emptyChatPlaceholder) {
      this.emptyChatPlaceholder.classList.add('hidden');
    }

    const isUrdu = /[\u0600-\u06FF]/.test(msg.text);
    const bubbleWrapper = document.createElement('div');
    bubbleWrapper.className = `flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'} message-bubble`;
    bubbleWrapper.id = msg.id;

    const formattedContent = msg.role === 'assistant' && window.marked 
      ? marked.parse(msg.text)
      : `<p class="whitespace-pre-wrap">${this.escapeHtml(msg.text)}</p>`;

    // Build File Download Card HTML if fileData exists
    let fileCardHtml = '';
    if (msg.fileData && msg.fileData.file_url) {
      const type = (msg.fileData.file_type || 'pdf').toLowerCase();
      const iconMap = {
        pdf: 'fa-solid fa-file-pdf',
        pptx: 'fa-solid fa-file-powerpoint',
        docx: 'fa-solid fa-file-word',
        xlsx: 'fa-solid fa-file-excel',
        csv: 'fa-solid fa-file-csv'
      };
      const iconClass = iconMap[type] || 'fa-solid fa-file-arrow-down';

      fileCardHtml = `
        <div class="file-download-card file-card-${type}">
          <div class="file-icon-box">
            <i class="${iconClass}"></i>
          </div>
          <div class="flex-1 min-w-0 pr-2">
            <h4 class="text-xs font-bold text-white truncate" title="${this.escapeHtml(msg.fileData.file_name)}">${this.escapeHtml(msg.fileData.file_name)}</h4>
            <p class="text-[10px] text-slate-400 font-mono">${type.toUpperCase()} &bull; ${msg.fileData.file_size || 'Ready'}</p>
          </div>
          <a href="${msg.fileData.file_url}" download="${this.escapeHtml(msg.fileData.file_name)}" class="download-action-btn" title="Download ${type.toUpperCase()}">
            <span>Download</span>
            <i class="fa-solid fa-arrow-down-to-line text-[10px]"></i>
          </a>
        </div>
      `;
    }

    // Build Web Source Citations HTML if sources exist
    let sourcesHtml = '';
    if (msg.sources && msg.sources.length > 0) {
      sourcesHtml = `
        <div class="source-citations-container">
          <div class="flex items-center space-x-1.5 text-[10px] text-cyan-400 font-semibold mb-1.5">
            <i class="fa-solid fa-globe"></i>
            <span>Verified Sources (${msg.sources.length}):</span>
          </div>
          <div class="flex flex-wrap gap-1.5">
            ${msg.sources.map(src => {
              let domain = '';
              try { domain = new URL(src.url).hostname.replace('www.', ''); } catch(e) {}
              return `
                <a href="${this.escapeHtml(src.url)}" target="_blank" rel="noopener noreferrer" class="source-chip" title="${this.escapeHtml(src.title)} - ${this.escapeHtml(src.snippet)}">
                  <i class="fa-solid fa-link text-[9px] text-cyan-400"></i>
                  <span class="truncate max-w-[170px]">${this.escapeHtml(src.title)}</span>
                  ${domain ? `<span class="text-[9px] opacity-60">(${domain})</span>` : ''}
                  <i class="fa-solid fa-arrow-up-right-from-square text-[8px] text-slate-400"></i>
                </a>
              `;
            }).join('')}
          </div>
        </div>
      `;
    }

    bubbleWrapper.innerHTML = `
      <div class="max-w-[85%] rounded-2xl px-4 py-3 text-xs leading-relaxed ${
        msg.role === 'user' 
          ? 'user-bubble text-white rounded-br-none' 
          : 'ai-bubble text-slate-200 rounded-bl-none prose-ai'
      } ${isUrdu ? 'urdu-text' : ''}">
        ${formattedContent}
        ${fileCardHtml}
        ${sourcesHtml}
      </div>
      <div class="flex items-center space-x-2 mt-1 px-1 text-[10px] text-slate-400">
        <span>${msg.timestamp}</span>
        ${
          msg.role === 'assistant' 
            ? `
              <span>•</span>
              <button onclick="window.app.replayAudio('${msg.id}')" class="hover:text-purple-400 flex items-center space-x-1 transition" title="Replay Audio">
                <i class="fa-solid fa-play text-[9px]"></i>
                <span>Listen</span>
              </button>
              <span>•</span>
              <button onclick="window.app.copyMessageText('${msg.id}')" class="hover:text-cyan-400 transition" title="Copy Text">
                <i class="fa-solid fa-copy text-[9px]"></i>
              </button>
            `
            : ''
        }
      </div>
    `;

    this.chatMessages.appendChild(bubbleWrapper);
    this.scrollChatToBottom();
  }

  copyMessageText(id) {
    const msg = this.messages.find(m => m.id === id);
    if (!msg) return;
    navigator.clipboard.writeText(msg.text).then(() => {
      this.showLiveSubtitle("Copied to clipboard!");
    });
  }

  scrollChatToBottom() {
    this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
  }

  updateMessageBadge() {
    this.messageCountBadge.innerText = this.messages.length;
  }

  saveHistory() {
    try {
      localStorage.setItem('nova_messages', JSON.stringify(this.messages.slice(-50)));
    } catch (e) {
      console.warn("LocalStorage save error:", e);
    }
  }

  loadHistory() {
    try {
      const saved = localStorage.getItem('nova_messages');
      if (saved) {
        this.messages = JSON.parse(saved);
        if (this.messages.length > 0) {
          this.emptyChatPlaceholder.classList.add('hidden');
          this.messages.forEach(msg => this.renderMessage(msg));
          this.updateMessageBadge();
        }
      }
    } catch (e) {
      console.warn("LocalStorage load error:", e);
    }
  }

  clearHistory() {
    if (confirm("Clear all conversation history?")) {
      this.messages = [];
      localStorage.removeItem('nova_messages');
      this.chatMessages.innerHTML = '';
      if (this.emptyChatPlaceholder) {
        this.emptyChatPlaceholder.classList.remove('hidden');
        this.chatMessages.appendChild(this.emptyChatPlaceholder);
      }
      this.updateMessageBadge();
      this.showLiveSubtitle("Conversation cleared.");
    }
  }

  getRecentHistory(count = 6) {
    return this.messages.slice(-count).map(m => ({
      role: m.role,
      content: m.text
    }));
  }

  // ---------------------------------------------------------------------------
  // 8. Settings & Preferences LocalStorage
  // ---------------------------------------------------------------------------
  saveSettings() {
    const settings = {
      isVoiceEnabled: this.isVoiceEnabled,
      isAutoRecordEnabled: this.isAutoRecordEnabled,
      activePersona: this.activePersona,
      activeVoice: this.activeVoice,
      customPrompt: this.customPrompt
    };
    localStorage.setItem('nova_settings', JSON.stringify(settings));
  }

  loadSettings() {
    try {
      const saved = localStorage.getItem('nova_settings');
      if (saved) {
        const s = JSON.parse(saved);
        this.isVoiceEnabled = s.isVoiceEnabled !== undefined ? s.isVoiceEnabled : true;
        this.isAutoRecordEnabled = s.isAutoRecordEnabled || false;
        this.activePersona = s.activePersona || 'friendly';
        this.activeVoice = s.activeVoice || 'en-US-AriaNeural';
        this.customPrompt = s.customPrompt || '';

        // Apply to UI controls
        this.updateVoiceToggleUI();
        this.updateAutoRecordUI();
        this.personaSelect.value = this.activePersona;
        if (this.voiceSelect) this.voiceSelect.value = this.activeVoice;
        this.customPromptInput.value = this.customPrompt;
      }
    } catch (e) {
      console.warn("Settings load error:", e);
    }
  }

  updateVoiceToggleUI() {
    if (this.isVoiceEnabled) {
      this.voiceToggleIcon.className = 'fa-solid fa-volume-high text-cyan-400';
      this.voiceToggleLabel.innerText = 'Voice On';
      this.toggleVoiceBtn.classList.remove('opacity-60');
    } else {
      this.voiceToggleIcon.className = 'fa-solid fa-volume-xmark text-slate-400';
      this.voiceToggleLabel.innerText = 'Muted';
      this.toggleVoiceBtn.classList.add('opacity-60');
    }
  }

  updateAutoRecordUI() {
    if (this.isAutoRecordEnabled) {
      this.autoRecordIcon.className = 'fa-solid fa-repeat text-purple-400 animate-spin';
      this.toggleAutoRecordBtn.classList.add('bg-purple-600/20', 'border-purple-500/40', 'text-white');
    } else {
      this.autoRecordIcon.className = 'fa-solid fa-repeat text-slate-400';
      this.toggleAutoRecordBtn.classList.remove('bg-purple-600/20', 'border-purple-500/40', 'text-white');
    }
  }

  // ---------------------------------------------------------------------------
  // 9. Canvas Wave Visualizer & Particle Ring Engine
  // ---------------------------------------------------------------------------
  initVisualizer() {
    if (!this.canvas) return;

    // Create background orbit particles
    this.particles = [];
    for (let i = 0; i < 40; i++) {
      this.particles.push({
        angle: Math.random() * Math.PI * 2,
        radius: 120 + Math.random() * 80,
        speed: 0.003 + Math.random() * 0.006,
        size: 1 + Math.random() * 2,
        alpha: 0.2 + Math.random() * 0.5
      });
    }

    this.renderVisualizer();
  }

  renderVisualizer() {
    const width = this.canvas.width;
    const height = this.canvas.height;
    const centerX = width / 2;
    const centerY = height / 2;

    this.ctx.clearRect(0, 0, width, height);

    // Get live frequency data depending on state
    let freqData = null;
    if (this.state === 'listening' && this.micAnalyserNode) {
      freqData = new Uint8Array(this.micAnalyserNode.frequencyBinCount);
      this.micAnalyserNode.getByteFrequencyData(freqData);
    } else if (this.state === 'speaking' && this.playbackAnalyserNode) {
      freqData = new Uint8Array(this.playbackAnalyserNode.frequencyBinCount);
      this.playbackAnalyserNode.getByteFrequencyData(freqData);
    }

    // 1. Draw Orbiting Cosmic Particles
    this.particles.forEach(p => {
      p.angle += p.speed;
      const x = centerX + Math.cos(p.angle) * p.radius;
      const y = centerY + Math.sin(p.angle) * p.radius;

      this.ctx.beginPath();
      this.ctx.arc(x, y, p.size, 0, Math.PI * 2);
      this.ctx.fillStyle = `rgba(168, 85, 247, ${p.alpha})`;
      this.ctx.fill();
    });

    // 2. Draw Reactive Sound Waves / Frequency Halo
    const baseRadius = 96;
    const barCount = 48;
    const angleStep = (Math.PI * 2) / barCount;

    for (let i = 0; i < barCount; i++) {
      const angle = i * angleStep;
      let amplitude = 0;

      if (freqData) {
        const binIndex = Math.floor((i / barCount) * (freqData.length / 2));
        amplitude = (freqData[binIndex] / 255) * 45;
      } else if (this.state === 'idle') {
        amplitude = Math.sin(Date.now() * 0.003 + i * 0.3) * 4;
      } else if (this.state === 'thinking') {
        amplitude = Math.sin(Date.now() * 0.01 + i * 0.5) * 8 + 4;
      }

      const r1 = baseRadius;
      const r2 = baseRadius + Math.max(3, amplitude);

      const x1 = centerX + Math.cos(angle) * r1;
      const y1 = centerY + Math.sin(angle) * r1;
      const x2 = centerX + Math.cos(angle) * r2;
      const y2 = centerY + Math.sin(angle) * r2;

      this.ctx.beginPath();
      this.ctx.moveTo(x1, y1);
      this.ctx.lineTo(x2, y2);

      if (this.state === 'listening') {
        this.ctx.strokeStyle = `rgba(6, 182, 212, ${0.4 + (amplitude / 45) * 0.6})`;
        this.ctx.lineWidth = 2.5;
      } else if (this.state === 'speaking') {
        this.ctx.strokeStyle = `rgba(168, 85, 247, ${0.4 + (amplitude / 45) * 0.6})`;
        this.ctx.lineWidth = 2.5;
      } else if (this.state === 'thinking') {
        this.ctx.strokeStyle = 'rgba(236, 72, 153, 0.4)';
        this.ctx.lineWidth = 1.5;
      } else {
        this.ctx.strokeStyle = 'rgba(139, 92, 246, 0.2)';
        this.ctx.lineWidth = 1;
      }

      this.ctx.lineCap = 'round';
      this.ctx.stroke();
    }

    this.animationFrameId = requestAnimationFrame(() => this.renderVisualizer());
  }

  // ---------------------------------------------------------------------------
  // 10. Live Subtitle & Health Helpers
  // ---------------------------------------------------------------------------
  showLiveSubtitle(text) {
    if (!text) {
      this.liveSubtitleBox.classList.add('hidden');
      return;
    }
    this.liveSubtitleText.innerText = text;
    this.liveSubtitleBox.classList.remove('hidden');
  }

  async fetchServerStatus() {
    try {
      const res = await fetch('/api/health');
      if (res.ok) {
        const data = await res.json();
        if (data.groq_configured) {
          this.subStatusText.innerText = `Online • ${data.groq_model}`;
        }
      }
    } catch (e) {
      console.warn("Health check error:", e);
    }
  }

  autoResizeTextarea() {
    this.textInput.style.height = 'auto';
    this.textInput.style.height = Math.min(this.textInput.scrollHeight, 120) + 'px';
  }

  escapeHtml(str) {
    return str.replace(/[&<>'"]/g, tag => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      "'": '&#39;',
      '"': '&quot;'
    }[tag] || tag));
  }

  triggerQuickPrompt(promptText) {
    if (!promptText) return;
    this.textInput.value = promptText;
    this.autoResizeTextarea();
    this.sendTextMessage();
  }

  // ---------------------------------------------------------------------------
  // 11. Event Listeners & Keyboard Shortcuts
  // ---------------------------------------------------------------------------
  bindEvents() {
    // 1. Floating Bot Click
    this.floatingBot.addEventListener('click', () => {
      this.toggleVoiceRecording();
    });

    // 2. Microphone Bottom Button
    this.micButton.addEventListener('click', () => {
      this.toggleVoiceRecording();
    });

    // 3. Cancel Recording
    this.cancelRecordBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      this.stopVoiceRecording(false);
      this.setState('idle');
      this.showLiveSubtitle("Recording canceled.");
    });

    // 4. Send Message via Text Input
    this.sendBtn.addEventListener('click', () => {
      this.sendTextMessage();
    });

    this.textInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this.sendTextMessage();
      }
    });

    this.textInput.addEventListener('input', () => {
      this.autoResizeTextarea();
    });

    // 5. Global Spacebar Shortcut (Starts/Stops Voice)
    window.addEventListener('keydown', (e) => {
      const activeTag = document.activeElement ? document.activeElement.tagName.toLowerCase() : '';
      if (e.code === 'Space' && activeTag !== 'textarea' && activeTag !== 'input') {
        e.preventDefault();
        this.toggleVoiceRecording();
      }
      if (e.key === 'Escape') {
        this.closeDrawer();
        this.settingsModal.classList.add('hidden');
      }
    });

    // 6. Voice Mute/Unmute Toggle
    this.toggleVoiceBtn.addEventListener('click', () => {
      this.isVoiceEnabled = !this.isVoiceEnabled;
      if (!this.isVoiceEnabled) {
        this.stopAudioPlayback();
      }
      this.updateVoiceToggleUI();
      this.saveSettings();
    });

    // 7. Auto-Record Hands-Free Mode Toggle
    this.toggleAutoRecordBtn.addEventListener('click', () => {
      this.isAutoRecordEnabled = !this.isAutoRecordEnabled;
      this.updateAutoRecordUI();
      this.saveSettings();
      this.showLiveSubtitle(this.isAutoRecordEnabled ? "Hands-Free Auto-Talk activated" : "Hands-Free mode turned off");
    });

    // 8. Persona Select
    this.personaSelect.addEventListener('change', (e) => {
      this.activePersona = e.target.value;
      this.saveSettings();
      this.showLiveSubtitle(`Persona switched to: ${e.target.options[e.target.selectedIndex].text}`);
    });

    // 9. Voice Select
    if (this.voiceSelect) {
      this.voiceSelect.addEventListener('change', (e) => {
        this.activeVoice = e.target.value;
        this.saveSettings();
      });
    }

    // 10. Drawer Controls
    this.toggleDrawerBtn.addEventListener('click', () => {
      this.toggleDrawer();
    });

    this.closeDrawerBtn.addEventListener('click', () => {
      this.closeDrawer();
    });

    this.clearChatBtn.addEventListener('click', () => {
      this.clearHistory();
    });

    // 11. Settings Modal Controls
    this.openSettingsBtn.addEventListener('click', () => {
      this.settingsModal.classList.remove('hidden');
    });

    this.closeSettingsBtn.addEventListener('click', () => {
      this.settingsModal.classList.add('hidden');
    });

    this.saveSettingsBtn.addEventListener('click', () => {
      this.customPrompt = this.customPromptInput.value.trim();
      this.saveSettings();
      this.settingsModal.classList.add('hidden');
      this.showLiveSubtitle("Settings saved.");
    });

    this.resetSettingsBtn.addEventListener('click', () => {
      this.customPromptInput.value = '';
      this.customPrompt = '';
      this.saveSettings();
      this.settingsModal.classList.add('hidden');
      this.showLiveSubtitle("System instructions reset.");
    });

    // Dismiss modal on background click
    this.settingsModal.addEventListener('click', (e) => {
      if (e.target === this.settingsModal) {
        this.settingsModal.classList.add('hidden');
      }
    });
  }

  toggleDrawer() {
    this.isDrawerOpen = !this.isDrawerOpen;
    if (this.isDrawerOpen) {
      this.chatDrawer.classList.remove('drawer-closed');
      this.chatDrawer.classList.add('drawer-open');
      this.unreadBadge.classList.add('hidden');
      this.scrollChatToBottom();
    } else {
      this.closeDrawer();
    }
  }

  closeDrawer() {
    this.isDrawerOpen = false;
    this.chatDrawer.classList.remove('drawer-open');
    this.chatDrawer.classList.add('drawer-closed');
  }
}

// -----------------------------------------------------------------------------
// Application Initialization
// -----------------------------------------------------------------------------
document.addEventListener('DOMContentLoaded', () => {
  window.app = new VoiceAssistantApp();
});

