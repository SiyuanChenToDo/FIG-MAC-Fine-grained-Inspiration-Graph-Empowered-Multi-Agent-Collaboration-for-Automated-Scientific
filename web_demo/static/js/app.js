/**
 * Scientific Hypothesis Generation System - Web Demo
 * Main Application Logic
 */

const AppState = {
    currentPage: 'landing',
    workflowData: null,
    eventSource: null,
    agentStatus: {},
    phaseProgress: 0,
    finalContent: '',
    finalScores: {},
    agentContributions: {},
    agentFullOutputs: {},
    agentOutputBuffers: {},
    inspirationPaths: [],
    graphStats: {},
    isRunning: false
};

const AGENTS = [
    { name: 'Scholar Scour', icon: '📚', role: 'Literature Synthesis Specialist' },
    { name: 'Idea Igniter', icon: '💡', role: 'Creative Architect' },
    { name: 'Dr. Qwen Technical', icon: '🔬', role: 'Technical Feasibility Analyst' },
    { name: 'Dr. Qwen Practical', icon: '🛠️', role: 'Experimental Validation Analyst' },
    { name: 'Prof. Qwen Ethics', icon: '⚖️', role: 'Ethics & Impact Assessor' },
    { name: 'Dr. Qwen Leader', icon: '🎯', role: 'Principal Investigator' },
    { name: 'Critic Crucible', icon: '🔍', role: 'Peer Review Critic' },
    { name: 'Prof. Qwen Editor', icon: '✍️', role: 'Scientific Editor' }
];

function showPage(pageId) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.getElementById(pageId).classList.add('active');
    AppState.currentPage = pageId.replace('-page', '');
    window.scrollTo(0, 0);
}

function goToLanding() { showPage('landing-page'); }
function goToInput() { showPage('input-page'); checkSystemStatus(); }
function goToThink() { showPage('think-page'); }
function goToResult() { showPage('result-page'); renderResults(); }

function resetAndGoHome() {
    if (AppState.eventSource) {
        AppState.eventSource.close();
        AppState.eventSource = null;
    }
    AppState.isRunning = false;
    AppState.workflowData = null;
    AppState.agentStatus = {};
    AppState.phaseProgress = 0;
    AppState.inspirationPaths = [];
    AppState.agentFullOutputs = {};
    AppState.agentOutputBuffers = {};
    showPage('landing-page');
}

function setQuery(text) { document.getElementById('query-input').value = text; }

async function checkSystemStatus() {
    try {
        const res = await fetch('/api/status');
        const data = await res.json();
        updateIndicator('ind-graphstorm', data.graphstorm_model);
        updateIndicator('ind-faiss', data.faiss_index);
        updateIndicator('ind-agents', data.camel_agents);
        const statusEl = document.getElementById('landing-status');
        if (statusEl) {
            const ready = data.graphstorm_model && data.faiss_index;
            statusEl.innerHTML = ready
                ? '<span class="status-dot"></span><span class="status-text">All systems operational</span>'
                : '<span class="status-dot loading"></span><span class="status-text">Some components offline. Simulation mode available.</span>';
        }
    } catch (e) { console.warn('Status check failed:', e); }
}

function updateIndicator(id, ready) {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.remove('ready', 'error');
    el.classList.add(ready ? 'ready' : 'error');
}

async function startWorkflow() {
    const input = document.getElementById('query-input');
    const topic = input.value.trim();
    if (!topic) {
        input.style.borderColor = 'var(--accent-red)';
        setTimeout(() => input.style.borderColor = '', 1000);
        return;
    }
    if (AppState.isRunning) return;
    AppState.isRunning = true;

    const btn = document.getElementById('submit-btn');
    btn.disabled = true;
    btn.querySelector('.btn-text').textContent = 'Generating...';
    btn.querySelector('.btn-loading').style.display = 'inline';

    initThinkPage(topic);
    showPage('think-page');

    const isRealtime = document.getElementById('mode-toggle').checked;
    const endpoint = isRealtime ? '/api/realtime/start' : '/api/demo/start';

    try {
        const res = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ topic, speed: 1.5 })
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (AppState.isRunning) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const events = buffer.split(/\r?\n\r?\n/);
            buffer = events.pop() || '';
            for (const evt of events) {
                if (evt.trim()) handleSSEEvent(evt);
            }
        }
        if (buffer.trim()) handleSSEEvent(buffer);
    } catch (e) {
        console.error('Workflow error:', e);
        addThinkBlock('error', `Connection Error: ${e.message}`);
    } finally {
        AppState.isRunning = false;
        btn.disabled = false;
        btn.querySelector('.btn-text').textContent = 'Generate Hypothesis';
        btn.querySelector('.btn-loading').style.display = 'none';
    }
}

function handleSSEEvent(rawEvent) {
    const eventMatch = rawEvent.match(/^event:\s*(\w+)/m);
    if (!eventMatch) return;
    const eventType = eventMatch[1];

    const dataLines = [];
    const dataRegex = /^data:\s*(.*)$/gm;
    let m;
    while ((m = dataRegex.exec(rawEvent)) !== null) {
        dataLines.push(m[1]);
    }
    if (dataLines.length === 0) return;

    const dataStr = dataLines.join('\n');
    let data;
    try {
        data = JSON.parse(dataStr);
    } catch (e) {
        console.warn('Failed to parse SSE data:', dataStr.substring(0, 200));
        return;
    }

    switch (eventType) {
        case 'workflow_start': handleWorkflowStart(data); break;
        case 'phase_start': handlePhaseStart(data); break;
        case 'think': handleThink(data); break;
        case 'agent_start': handleAgentStart(data); break;
        case 'agent_think': handleAgentThink(data); break;
        case 'agent_content': handleAgentContent(data); break;
        case 'agent_complete': handleAgentComplete(data); break;
        case 'agent_full_output': handleAgentFullOutput(data); break;
        case 'inspiration_path': handleInspirationPath(data); break;
        case 'phase_end': handlePhaseEnd(data); break;
        case 'workflow_complete': handleWorkflowComplete(data); break;
        case 'error': addThinkBlock('error', data.message || 'Unknown Error'); break;
        case 'info': addThinkBlock('info', data.message || ''); break;
    }
}

function handleWorkflowStart(data) {
    AppState.workflowData = { topic: data.topic, phases: [] };
    AppState.graphStats = data.graph_stats || {};
    updateProgress(0);
    if (data.graph_stats) {
        const stats = data.graph_stats;
        const statsText = `Graph: ${stats.total_nodes?.toLocaleString() || 0} nodes, ${stats.total_edges?.toLocaleString() || 0} edges | Model: ${stats.model_metrics?.model || 'RGCN'} MRR=${stats.model_metrics?.mrr || 0}`;
        addThinkBlock('initialization', statsText, 'info');
    }
}

function handlePhaseStart(data) {
    const phaseEl = document.createElement('div');
    phaseEl.className = 'think-phase';
    phaseEl.id = `phase-${data.phase}`;
    phaseEl.innerHTML = `
        <div class="phase-header">
            <span class="phase-icon">${data.icon}</span>
            <span class="phase-title">${data.display_name}</span>
        </div>
        <div class="phase-content"></div>
    `;
    document.getElementById('think-stream').appendChild(phaseEl);
    const stream = document.getElementById('think-content');
    stream.scrollTop = stream.scrollHeight;
    updateProgressLabel(data.phase);
}

function handleThink(data) {
    addThinkBlock(data.phase, data.content, 'think');
}

function handleAgentStart(data) {
    updateAgentStatus(data.agent, 'thinking');
    // Create real-time output panel for this agent
    ensureAgentOutputPanel(data.phase, data.agent, data.icon, data.role);
}

function handleAgentThink(data) {
    const phaseEl = document.getElementById(`phase-${data.phase}`);
    if (!phaseEl) return;
    const contentEl = phaseEl.querySelector('.phase-content');
    const block = document.createElement('div');
    block.className = 'think-block new';
    block.innerHTML = `
        <div class="think-label">${data.icon} ${data.agent}</div>
        <div class="think-content-text">${escapeHtml(data.content)}</div>
    `;
    contentEl.appendChild(block);
    setTimeout(() => block.classList.remove('new'), 300);
    const stream = document.getElementById('think-content');
    stream.scrollTop = stream.scrollHeight;
}

function handleAgentContent(data) {
    // Real-time content streaming - append to agent's output panel
    const panel = document.getElementById(`realtime-${data.agent.replace(/\s+/g, '-')}`);
    if (panel) {
        const contentEl = panel.querySelector('.realtime-content');
        if (contentEl) {
            contentEl.textContent += data.content;
            // Auto-scroll within panel
            contentEl.scrollTop = contentEl.scrollHeight;
        }
    }
    if (!AppState.agentContributions[data.agent]) {
        AppState.agentContributions[data.agent] = '';
    }
    AppState.agentContributions[data.agent] += data.content;
}

function handleAgentComplete(data) {
    updateAgentStatus(data.agent, 'completed');
    // Mark real-time panel as complete
    const panel = document.getElementById(`realtime-${data.agent.replace(/\s+/g, '-')}`);
    if (panel) {
        panel.classList.add('complete');
        const statusEl = panel.querySelector('.realtime-status');
        if (statusEl) statusEl.textContent = '✅ Output Complete';
    }
}

function handleAgentFullOutput(data) {
    // Buffer chunks and assemble full content
    if (!AppState.agentOutputBuffers[data.agent]) {
        AppState.agentOutputBuffers[data.agent] = {
            chunks: {},
            totalChunks: data.total_chunks,
            content_length: data.content_length,
            phase: data.phase,
            icon: data.icon,
            role: data.role
        };
    }
    const buf = AppState.agentOutputBuffers[data.agent];
    // Always update totalChunks in case of re-transmission or correction
    buf.totalChunks = data.total_chunks;
    buf.content_length = data.content_length;
    buf.chunks[data.chunk_index] = data.content_chunk;

    // Update real-time panel with accumulated content
    const panel = document.getElementById(`realtime-${data.agent.replace(/\s+/g, '-')}`);
    if (panel) {
        const contentEl = panel.querySelector('.realtime-content');
        if (contentEl) {
            // Assemble all chunks received so far in correct order
            let assembled = '';
            const receivedIndices = Object.keys(buf.chunks).map(Number).sort((a,b)=>a-b);
            for (const idx of receivedIndices) {
                assembled += buf.chunks[idx];
            }
            contentEl.textContent = assembled;
            contentEl.scrollTop = contentEl.scrollHeight;
        }
        // Update progress
        const progressEl = panel.querySelector('.realtime-progress');
        if (progressEl) {
            const received = Object.keys(buf.chunks).length;
            const pct = Math.round((received / buf.totalChunks) * 100);
            progressEl.textContent = `${pct}%`;
        }
    }

    // Check if all chunks received
    const receivedCount = Object.keys(buf.chunks).length;
    const missing = [];
    for (let i = 0; i < buf.totalChunks; i++) {
        if (!(i in buf.chunks)) missing.push(i);
    }

    if (missing.length === 0) {
        // All chunks received — assemble complete content
        let fullContent = '';
        for (let i = 0; i < buf.totalChunks; i++) {
            fullContent += buf.chunks[i];
        }
        AppState.agentFullOutputs[data.agent] = {
            agent: data.agent,
            icon: data.icon || AGENTS.find(a=>a.name===data.agent)?.icon || '🤖',
            role: data.role || AGENTS.find(a=>a.name===data.agent)?.role || 'Agent',
            content: fullContent,
            content_length: fullContent.length,
            complete: true
        };
        // Compute quality-based contribution score
        const quality = analyzeAgentContribution(fullContent, data.agent);
        AppState.agentContributions[data.agent] = {
            contribution: quality.score,
            breakdown: quality.breakdown,
            content_length: fullContent.length
        };
    } else {
        // Partial content — store what we have for resilience
        let partialContent = '';
        for (let i = 0; i < buf.totalChunks; i++) {
            if (buf.chunks[i]) partialContent += buf.chunks[i];
        }
        AppState.agentFullOutputs[data.agent] = {
            agent: data.agent,
            icon: data.icon || AGENTS.find(a=>a.name===data.agent)?.icon || '🤖',
            role: data.role || AGENTS.find(a=>a.name===data.agent)?.role || 'Agent',
            content: partialContent,
            content_length: partialContent.length,
            complete: false,
            missingChunks: missing
        };
        // Still compute contribution from partial content
        const quality = analyzeAgentContribution(partialContent, data.agent);
        AppState.agentContributions[data.agent] = {
            contribution: quality.score,
            breakdown: quality.breakdown,
            content_length: partialContent.length
        };
    }
}

function handleInspirationPath(data) {
    AppState.inspirationPaths.push(data);
    const phaseEl = document.getElementById('phase-rag_retrieval');
    if (phaseEl) {
        const contentEl = phaseEl.querySelector('.phase-content');
        const block = document.createElement('div');
        block.className = 'think-block new';
        block.style.borderLeftColor = 'var(--accent-pink)';
        block.innerHTML = `
            <div class="think-label">🔗 Inspiration Path #${data.path_id} (Confidence: ${data.confidence})</div>
            <div class="think-content-text">
                ${data.nodes.map(n => {
                    const icons = { RQ: '❓', Sol: '💡', Paper: '📄', INSPIRED: '→' };
                    return `<span style="margin-right:8px">${icons[n.type] || ''} ${n.text?.substring(0, 40) || n.title?.substring(0, 40) || n.label}</span>`;
                }).join(' ')}
            </div>
        `;
        contentEl.appendChild(block);
        setTimeout(() => block.classList.remove('new'), 300);
        const stream = document.getElementById('think-content');
        stream.scrollTop = stream.scrollHeight;
    }
}

function handlePhaseEnd(data) {
    const phaseOrder = ['initialization', 'rag_retrieval', 'literature', 'ideation', 'analysis', 'synthesis', 'review', 'polish', 'evaluation'];
    const idx = phaseOrder.indexOf(data.phase);
    if (idx >= 0) updateProgress(((idx + 1) / phaseOrder.length) * 100);

    if (data.score !== undefined) {
        const phaseEl = document.getElementById(`phase-${data.phase}`);
        if (phaseEl) {
            const block = document.createElement('div');
            block.className = 'think-block';
            block.style.borderLeftColor = 'var(--accent-green)';
            block.innerHTML = `
                <div class="think-label">📊 Phase Evaluation</div>
                <div class="think-content-text">Quality Score: ${data.score}/10 (Threshold: ${data.threshold || 8.0})</div>
            `;
            phaseEl.querySelector('.phase-content').appendChild(block);
        }
    }
}

function handleWorkflowComplete(data) {
    AppState.finalContent = data.final_content || '';
    AppState.finalScores = data.scores || {};
    AppState.inspirationPaths = data.inspiration_paths || [];
    AppState.graphStats = data.graph_stats || {};

    // Force-assemble any incomplete agent output buffers
    for (const [agentName, buf] of Object.entries(AppState.agentOutputBuffers)) {
        if (!AppState.agentFullOutputs[agentName]) {
            let partialContent = '';
            const receivedIndices = Object.keys(buf.chunks).map(Number).sort((a,b)=>a-b);
            for (const idx of receivedIndices) {
                partialContent += buf.chunks[idx];
            }
            if (partialContent.length > 0) {
                AppState.agentFullOutputs[agentName] = {
                    agent: agentName,
                    icon: AGENTS.find(a=>a.name===agentName)?.icon || '🤖',
                    role: AGENTS.find(a=>a.name===agentName)?.role || 'Agent',
                    content: partialContent,
                    content_length: partialContent.length,
                    complete: false,
                    missingChunks: []
                };
                const quality = analyzeAgentContribution(partialContent, agentName);
                AppState.agentContributions[agentName] = {
                    contribution: quality.score,
                    breakdown: quality.breakdown,
                    content_length: partialContent.length
                };
            }
        }
    }

    updateProgress(100);
    document.getElementById('view-result-btn').style.display = 'block';
    addThinkBlock('complete', '🎉 Workflow complete! Click the button below to view the final report.');
}

// ============================================
// Real-time Agent Output Panel
// ============================================
function ensureAgentOutputPanel(phase, agentName, icon, role) {
    const phaseEl = document.getElementById(`phase-${phase}`);
    if (!phaseEl) return;
    const contentEl = phaseEl.querySelector('.phase-content');
    const panelId = `realtime-${agentName.replace(/\s+/g, '-')}`;

    if (document.getElementById(panelId)) return;

    const panel = document.createElement('div');
    panel.className = 'realtime-panel';
    panel.id = panelId;
    panel.innerHTML = `
        <div class="realtime-header">
            <span class="realtime-agent">${icon} ${agentName}</span>
            <span class="realtime-status">💭 Generating...</span>
            <span class="realtime-progress"></span>
        </div>
        <div class="realtime-content"></div>
    `;
    contentEl.appendChild(panel);

    const stream = document.getElementById('think-content');
    stream.scrollTop = stream.scrollHeight;
}

// ============================================
// Think Page UI
// ============================================
function initThinkPage(topic) {
    AppState.agentStatus = {};
    AGENTS.forEach(a => AppState.agentStatus[a.name] = 'waiting');
    AppState.phaseProgress = 0;
    AppState.agentContributions = {};
    AppState.agentFullOutputs = {};
    AppState.agentOutputBuffers = {};
    AppState.inspirationPaths = [];

    document.getElementById('think-stream').innerHTML = '';
    document.getElementById('query-display').textContent = `Query: ${topic}`;
    document.getElementById('view-result-btn').style.display = 'none';

    // Build round table visualization
    const list = document.getElementById('agent-list');
    const centerX = 210, centerY = 210, radius = 150;

    // Clear existing agents but keep center hub and SVG
    const existingAgents = list.querySelectorAll('.round-table-agent');
    existingAgents.forEach(el => el.remove());

    // Create SVG lines for each agent
    const svg = document.getElementById('round-table-svg');
    svg.setAttribute('viewBox', '0 0 420 420');
    svg.innerHTML = '';

    AGENTS.forEach((agent, idx) => {
        const angle = (idx * 45 - 90) * Math.PI / 180;
        const x = centerX + radius * Math.cos(angle);
        const y = centerY + radius * Math.sin(angle);

        // Create agent node
        const node = document.createElement('div');
        node.className = 'round-table-agent waiting';
        node.id = `agent-${agent.name.replace(/\s+/g, '-')}`;
        node.dataset.agent = agent.name;
        node.style.left = (x - 36) + 'px';
        node.style.top = (y - 36) + 'px';
        node.innerHTML = `
            <div class="rt-avatar">${agent.icon}</div>
            <div class="rt-name">${agent.name}</div>
        `;
        list.appendChild(node);

        // Create SVG connection line
        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        line.setAttribute('x1', centerX);
        line.setAttribute('y1', centerY);
        line.setAttribute('x2', x);
        line.setAttribute('y2', y);
        line.setAttribute('class', 'connection-line');
        line.setAttribute('id', `line-${agent.name.replace(/\s+/g, '-')}`);
        svg.appendChild(line);
    });

    // Reset center hub
    const centerHub = document.getElementById('round-table-center');
    centerHub.classList.remove('active');
    document.getElementById('center-icon').textContent = '🤝';
    document.getElementById('center-label').textContent = 'Awaiting Collaboration';

    updateProgress(0);
    updateProgressLabel('init');
}

function addThinkBlock(phase, content, type = 'normal') {
    const stream = document.getElementById('think-stream');
    let phaseEl = document.getElementById(`phase-${phase}`);
    if (!phaseEl) {
        phaseEl = document.createElement('div');
        phaseEl.className = 'think-phase';
        phaseEl.id = `phase-${phase}`;
        phaseEl.innerHTML = `
            <div class="phase-header">
                <span class="phase-icon">💬</span>
                <span class="phase-title">System Message</span>
            </div>
            <div class="phase-content"></div>
        `;
        stream.appendChild(phaseEl);
    }
    const contentEl = phaseEl.querySelector('.phase-content');
    const block = document.createElement('div');
    block.className = 'think-block new';

    if (type === 'error') {
        block.style.borderLeftColor = 'var(--accent-red)';
        block.innerHTML = `<div class="think-content-text" style="color:var(--accent-red)">❌ ${escapeHtml(content)}</div>`;
    } else if (type === 'info') {
        block.style.borderLeftColor = 'var(--accent-amber)';
        block.innerHTML = `<div class="think-content-text" style="color:var(--accent-amber)">ℹ️ ${escapeHtml(content)}</div>`;
    } else {
        block.innerHTML = `<div class="think-content-text">${escapeHtml(content)}</div>`;
    }
    contentEl.appendChild(block);
    setTimeout(() => block.classList.remove('new'), 300);
    const thinkContent = document.getElementById('think-content');
    thinkContent.scrollTop = thinkContent.scrollHeight;
}

function updateAgentStatus(agentName, status) {
    const el = document.getElementById(`agent-${agentName.replace(/\s+/g, '-')}`);
    if (!el) return;

    // Remove existing status classes
    el.classList.remove('waiting', 'thinking', 'completed');

    // Remove existing checkmark
    const existingCheck = el.querySelector('.rt-check');
    if (existingCheck) existingCheck.remove();

    // Update center hub
    const centerHub = document.getElementById('round-table-center');
    const centerIcon = document.getElementById('center-icon');
    const centerLabel = document.getElementById('center-label');

    // Update SVG line
    const line = document.getElementById(`line-${agentName.replace(/\s+/g, '-')}`);
    if (line) {
        line.classList.remove('active', 'completed');
    }

    switch (status) {
        case 'thinking':
            el.classList.add('thinking');
            if (line) line.classList.add('active');
            // Update center hub to show active agent
            centerHub.classList.add('active');
            const agent = AGENTS.find(a => a.name === agentName);
            if (agent) {
                centerIcon.textContent = agent.icon;
                centerLabel.textContent = 'Collaborating';
            }
            break;
        case 'completed':
            el.classList.add('completed');
            if (line) line.classList.add('completed');
            // Add checkmark badge
            const avatar = el.querySelector('.rt-avatar');
            if (avatar) {
                const check = document.createElement('div');
                check.className = 'rt-check';
                check.textContent = '✓';
                avatar.appendChild(check);
            }
            break;
        default:
            el.classList.add('waiting');
            break;
    }

    // If any agent is still thinking, keep hub active
    const anyThinking = document.querySelector('.round-table-agent.thinking');
    if (!anyThinking) {
        centerHub.classList.remove('active');
        centerIcon.textContent = '🤝';
        const completedCount = document.querySelectorAll('.round-table-agent.completed').length;
        if (completedCount === AGENTS.length) {
            centerLabel.textContent = 'All Complete';
            centerIcon.textContent = '✅';
        } else {
            centerLabel.textContent = 'Awaiting Collaboration';
        }
    }
}

function updateProgress(percent) {
    const style = document.getElementById('dynamic-progress-style');
    if (style) style.remove();
    const newStyle = document.createElement('style');
    newStyle.id = 'dynamic-progress-style';
    newStyle.textContent = `.progress-bar::after { width: ${percent}% !important; }`;
    document.head.appendChild(newStyle);
}

function updateProgressLabel(phase) {
    const labels = document.querySelectorAll('.plabel');
    labels.forEach(l => l.classList.remove('active'));
    const phaseMap = {
        'initialization': 'init', 'rag_retrieval': 'rag',
        'literature': 'agents', 'ideation': 'agents', 'analysis': 'agents',
        'synthesis': 'agents', 'review': 'iter', 'polish': 'iter', 'evaluation': 'done'
    };
    const target = phaseMap[phase];
    if (target) {
        const label = document.querySelector(`.plabel[data-phase="${target}"]`);
        if (label) label.classList.add('active');
    }
}

// ============================================
// Agent Contribution Quality Analysis
// ============================================
function analyzeAgentContribution(content, agentName) {
    if (!content) return { score: 0, breakdown: {} };

    // 1. Structural richness (headings, lists, sections)
    const headings = (content.match(/^#{1,3}\s+.+$/gm) || []).length;
    const listItems = (content.match(/^[\s]*[-*+]\s+.+$/gm) || []).length;
    const numberedItems = (content.match(/^[\s]*\d+\.\s+.+$/gm) || []).length;
    const codeBlocks = (content.match(/```[\s\S]*?```/g) || []).length;

    // 2. Depth indicators (formulas, citations, evaluations)
    const blockFormulas = (content.match(/\$\$[\s\S]*?\$\$|\\\[[\s\S]*?\\\]/g) || []).length;
    const inlineFormulas = (content.match(/\$[^$\n]+\$/g) || []).length;
    const citations = (content.match(/\[[A-Z][a-zA-Z\s,]+\d{4}[a-z]?\]|\(.*?et\s+al.*?\d{4}.*?\)/g) || []).length;
    const evaluations = (content.match(/\bscore\b|\beval\b|\bevaluation\b|\brating\b|\d+\.?\d*\s*\/\s*10/gi) || []).length;
    const jsonScores = (content.match(/"score"\s*:\s*"?\d+"?/g) || []).length;

    // 3. Content volume (word count, not character count)
    const cnChars = (content.match(/[\u4e00-\u9fa5]/g) || []).length;
    const enWords = (content.match(/[a-zA-Z]{2,}/g) || []).length;
    const totalWords = cnChars + enWords;

    // 4. Role-based base weights (reflecting importance in pipeline)
    const roleWeights = {
        'Scholar Scour': 0.95,
        'Idea Igniter': 1.05,
        'Dr. Qwen Technical': 0.90,
        'Dr. Qwen Practical': 0.90,
        'Prof. Qwen Ethics': 0.85,
        'Dr. Qwen Leader': 1.00,
        'Critic Crucible': 0.95,
        'Prof. Qwen Editor': 0.80
    };
    const weight = roleWeights[agentName] || 0.85;

    // 5. Compute dimension scores
    const structureScore = headings * 3.0 + listItems * 1.5 + numberedItems * 1.5 + codeBlocks * 2.0;
    const depthScore = blockFormulas * 5.0 + inlineFormulas * 2.0 + citations * 3.0 + evaluations * 2.0 + jsonScores * 2.5;
    const volumeScore = Math.min(totalWords / 150, 10); // Cap at 10 points for volume

    // Bonus for JSON-structured analysis outputs (Technical/Practical/Ethics)
    const isJsonOutput = content.trim().startsWith('```json') || content.trim().startsWith('{');
    const jsonBonus = isJsonOutput ? 3.0 : 0;

    // Bonus for review/critique outputs (Critic)
    const hasCritique = /\b(weakness|weaknesses|limitation|limitations|concern|issue|problem|flaw)\b/gi.test(content);
    const critiqueBonus = hasCritique ? 2.5 : 0;

    const rawScore = structureScore + depthScore + volumeScore + jsonBonus + critiqueBonus;
    const finalScore = Math.round(rawScore * weight);

    return {
        score: finalScore,
        breakdown: {
            structure: Math.round(structureScore),
            depth: Math.round(depthScore),
            volume: Math.round(volumeScore * 10) / 10,
            jsonBonus: Math.round(jsonBonus * 10) / 10,
            critiqueBonus: Math.round(critiqueBonus * 10) / 10,
            headings, listItems, blockFormulas, inlineFormulas,
            citations, evaluations, jsonScores, totalWords, weight
        }
    };
}

// ============================================
// Result Page Rendering
// ============================================
function renderResults() {
    renderGraphStats();
    renderInspirationPaths();
    renderRadarChart();

    const reportEl = document.getElementById('report-content');
    if (AppState.finalContent) {
        let processed = AppState.finalContent
            .replace(/\\\[([\s\S]*?)\\\]/g, '$$$$$1$$$$')
            .replace(/\\\(([\s\S]*?)\\\)/g, '$$$1$$');
        processed = processed.replace(/\$([^$\n]+)\$/g, (match, tex) => {
            return '$' + tex.replace(/_/g, '\\_') + '$';
        });
        processed = processed.replace(/\$\$([\s\S]*?)\$\$/g, (match, tex) => {
            return '$$' + tex.replace(/_/g, '\\_') + '$$';
        });
        reportEl.innerHTML = marked.parse(processed);
        renderMath();
    } else {
        reportEl.innerHTML = '<p style="color:var(--text-muted)">No report content available</p>';
    }

    renderContributionChart();
    renderLLMOutputs();
}

function renderGraphStats() {
    const grid = document.getElementById('graph-stats-grid');
    const stats = AppState.graphStats;
    if (!stats || !stats.total_nodes) {
        grid.innerHTML = '<p style="color:var(--text-muted)">No graph data available</p>';
        return;
    }
    const metrics = stats.model_metrics || {};
    grid.innerHTML = `
        <div class="graph-stat-item">
            <div class="graph-stat-value">${stats.total_nodes?.toLocaleString() || 0}</div>
            <div class="graph-stat-label">Total Nodes</div>
        </div>
        <div class="graph-stat-item">
            <div class="graph-stat-value">${stats.total_edges?.toLocaleString() || 0}</div>
            <div class="graph-stat-label">Total Edges</div>
        </div>
        <div class="graph-stat-item">
            <div class="graph-stat-value">${stats.node_types?.Paper?.toLocaleString() || 0}</div>
            <div class="graph-stat-label">Paper Nodes</div>
        </div>
        <div class="graph-stat-item">
            <div class="graph-stat-value">${stats.edge_types?.INSPIRED?.toLocaleString() || 0}</div>
            <div class="graph-stat-label">INSPIRED Edges</div>
        </div>
        <div class="graph-stat-item">
            <div class="graph-stat-value">${metrics.mrr || 0}</div>
            <div class="graph-stat-label">MRR Score</div>
        </div>
        <div class="graph-stat-item">
            <div class="graph-stat-value">${metrics.hidden_size || 0}</div>
            <div class="graph-stat-label">Hidden Dim</div>
        </div>
        <div class="graph-stat-item">
            <div class="graph-stat-value">${metrics.num_layers || 0}</div>
            <div class="graph-stat-label">GNN Layers</div>
        </div>
        <div class="graph-stat-item">
            <div class="graph-stat-value">${metrics.fanout || ''}</div>
            <div class="graph-stat-label">Fanout</div>
        </div>
    `;
}

function renderInspirationPaths() {
    const container = document.getElementById('inspiration-paths');
    const paths = AppState.inspirationPaths;
    if (!paths || paths.length === 0) {
        container.innerHTML = '<p style="color:var(--text-muted)">No inspiration path data</p>';
        return;
    }

    const typeMeta = {
        RQ:     { icon: '❓', label: 'Research Question', cls: 'rq' },
        Sol:    { icon: '💡', label: 'Solution', cls: 'sol' },
        Paper:  { icon: '📄', label: 'Paper', cls: 'paper' },
        INSPIRED: { icon: '✨', label: '', cls: 'edge' }
    };

    container.innerHTML = paths.map(path => {
        const nodesHtml = path.nodes.map((node, i) => {
            const meta = typeMeta[node.type] || { icon: '•', label: node.type, cls: '' };
            const isEdge = node.type === 'INSPIRED';
            const content = node.type === 'Paper'
                ? (node.title || '')
                : (node.text || node.label || '');
            const short = content.length > 40 ? content.substring(0, 40) + '...' : content;

            let html = '<div class="path-node-wrap">';
            html += `<div class="path-node ${meta.cls}">`;
            html += `<div class="path-node-icon">${meta.icon}</div>`;
            if (meta.label) {
                html += `<div class="path-node-type">${meta.label}</div>`;
            }
            if (!isEdge) {
                html += `<div class="path-node-text">${escapeHtml(short)}</div>`;
                if (content.length > 40) {
                    html += `<div class="path-node-full">${escapeHtml(content)}</div>`;
                }
            } else {
                html += `<div class="path-node-text">${escapeHtml(node.label)} ${node.predicted ? '🔮' : ''}</div>`;
            }
            html += '</div>';

            // Add connector arrow if not the last node
            if (i < path.nodes.length - 1) {
                html += '<div class="path-connector"></div>';
            }
            html += '</div>';
            return html;
        }).join('');

        return `
        <div class="inspiration-path">
            <div class="path-header">
                <span class="path-title">Inspiration Path #${path.path_id}</span>
                <span class="path-score">Score: ${path.score} | Confidence: ${path.confidence}</span>
            </div>
            <div class="path-flow">
                ${nodesHtml}
            </div>
            <div class="path-reasoning">
                <strong>Reasoning:</strong> ${escapeHtml(path.reasoning)}
            </div>
        </div>
        `;
    }).join('');
}

function renderLLMOutputs() {
    const container = document.getElementById('llm-outputs');
    const outputs = AppState.agentFullOutputs;
    const agents = AGENTS.filter(a => outputs[a.name]);

    if (agents.length === 0) {
        container.innerHTML = '<p style="color:var(--text-muted)">No LLM output data</p>';
        return;
    }

    container.innerHTML = agents.map(agent => {
        const data = outputs[agent.name];
        const contrib = AppState.agentContributions[agent.name];
        const bd = contrib?.breakdown;

        // Content completeness badge
        let completenessBadge = '';
        if (data.complete === false) {
            const missing = data.missingChunks?.length || 0;
            completenessBadge = `<span class="llm-badge warning" title="${missing} chunks missing">⚠️ Incomplete</span>`;
        } else {
            completenessBadge = `<span class="llm-badge success">✅ Complete</span>`;
        }

        // Quality stat badges
        let statBadges = '';
        if (bd) {
            const stats = [];
            if (bd.headings > 0) stats.push(`📑 ${bd.headings} Sections`);
            if (bd.blockFormulas + bd.inlineFormulas > 0) stats.push(`📐 ${bd.blockFormulas + bd.inlineFormulas} Formulas`);
            if (bd.citations > 0) stats.push(`📚 ${bd.citations} Citations`);
            if (bd.evaluations + bd.jsonScores > 0) stats.push(`📊 ${bd.evaluations + bd.jsonScores} Evaluations`);
            if (bd.totalWords > 0) stats.push(`📝 ~${bd.totalWords} words`);
            if (stats.length > 0) {
                statBadges = `<div class="llm-quality-stats">${stats.map(s => `<span class="llm-stat-badge">${s}</span>`).join('')}</div>`;
            }
        }

        // Render markdown content with KaTeX support
        let processed = (data.content || '')
            .replace(/\\\[([\s\S]*?)\\\]/g, '$$$$$1$$$$')
            .replace(/\\\(([\s\S]*?)\\\)/g, '$$$1$$');
        let htmlContent = marked.parse(processed);

        return `
            <div class="llm-output-card" id="llm-card-${agent.name.replace(/\s+/g, '-')}">
                <div class="llm-output-header" onclick="toggleLLMOutput('${agent.name.replace(/\s+/g, '-')}')">
                    <div class="llm-output-agent">
                        <span class="llm-output-avatar">${agent.icon}</span>
                        <div class="llm-output-info">
                            <div class="llm-output-name">${agent.name}</div>
                            <div class="llm-output-role">${agent.role}</div>
                        </div>
                    </div>
                    <div class="llm-output-meta">
                        ${completenessBadge}
                        <span class="llm-output-length">${(data.content_length || 0).toLocaleString()} chars</span>
                        <span class="llm-output-expand">▼</span>
                    </div>
                </div>
                <div class="llm-output-body">
                    ${statBadges}
                    <div class="llm-output-content markdown-body">${htmlContent}</div>
                </div>
            </div>
        `;
    }).join('');

    // Render math in LLM output cards
    if (typeof katex !== 'undefined') {
        container.querySelectorAll('.markdown-body').forEach(el => {
            el.innerHTML = el.innerHTML.replace(
                /\$\$([\s\S]*?)\$\$/g,
                (match, tex) => {
                    try {
                        return katex.renderToString(tex.trim(), { displayMode: true, throwOnError: false });
                    } catch (e) { return match; }
                }
            );
            el.innerHTML = el.innerHTML.replace(
                /\$([^$\n<]+)\$/g,
                (match, tex) => {
                    try {
                        return katex.renderToString(tex.trim(), { displayMode: false, throwOnError: false });
                    } catch (e) { return match; }
                }
            );
        });
    }
}

function toggleLLMOutput(id) {
    const card = document.getElementById('llm-card-' + id);
    if (card) card.classList.toggle('expanded');
}

function renderRadarChart() {
    const canvas = document.getElementById('radarChart');
    if (!canvas) return;
    const existing = Chart.getChart(canvas);
    if (existing) existing.destroy();

    const scores = AppState.finalScores;
    const defaultScores = {
        technical_feasibility: 8, methodological_consistency: 9,
        experimental_feasibility: 8, falsifiability: 8,
        scientific_significance: 8, social_impact: 7,
        innovation: 9, writing_quality: 8
    };
    const data = scores && Object.keys(scores).length > 0 ? scores : defaultScores;
    const labels = ['Technical Feasibility', 'Methodological Consistency', 'Experimental Feasibility', 'Falsifiability', 'Scientific Significance', 'Social Impact', 'Innovation', 'Writing Quality'];
    const values = [
        data.technical_feasibility || 0, data.methodological_consistency || 0,
        data.experimental_feasibility || 0, data.falsifiability || 0,
        data.scientific_significance || 0, data.social_impact || 0,
        data.innovation || 0, data.writing_quality || 0
    ];
    const threshold = 8.0;
    const thresholdValues = labels.map(() => threshold);

    // Dimension colors for axis labels
    const dimColors = ['#a78bfa', '#22d3ee', '#34d399', '#fbbf24', '#f87171', '#fb923c', '#e879f9', '#38bdf8'];

    // Compute average score for center display
    const avgScore = (values.reduce((a, b) => a + b, 0) / values.length).toFixed(1);

    const chart = new Chart(canvas, {
        type: 'radar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Quality Threshold',
                    data: thresholdValues,
                    backgroundColor: 'transparent',
                    borderColor: 'rgba(148, 163, 184, 0.2)',
                    borderWidth: 1.5,
                    borderDash: [6, 4],
                    pointRadius: 0,
                    pointHoverRadius: 0,
                    fill: false,
                    order: 2
                },
                {
                    label: 'Composite Score',
                    data: values,
                    backgroundColor: (context) => {
                        const chart = context.chart;
                        const { ctx, chartArea } = chart;
                        if (!chartArea) return 'rgba(139, 92, 246, 0.15)';
                        const cx = (chartArea.left + chartArea.right) / 2;
                        const cy = (chartArea.top + chartArea.bottom) / 2;
                        const r = Math.min(chartArea.right - chartArea.left, chartArea.bottom - chartArea.top) / 2 * 0.85;
                        const gradient = ctx.createRadialGradient(cx, cy, 0, cx, cy, r);
                        gradient.addColorStop(0, 'rgba(6, 182, 212, 0.35)');
                        gradient.addColorStop(0.4, 'rgba(139, 92, 246, 0.2)');
                        gradient.addColorStop(0.75, 'rgba(168, 85, 247, 0.1)');
                        gradient.addColorStop(1, 'rgba(168, 85, 247, 0.02)');
                        return gradient;
                    },
                    borderColor: (context) => {
                        const chart = context.chart;
                        const { ctx, chartArea } = chart;
                        if (!chartArea) return 'rgba(139, 92, 246, 0.9)';
                        const cx = (chartArea.left + chartArea.right) / 2;
                        const cy = (chartArea.top + chartArea.bottom) / 2;
                        const angle = Math.atan2(chartArea.bottom - cy, chartArea.right - cx);
                        const gradient = ctx.createLinearGradient(
                            cx - Math.cos(angle) * 100, cy - Math.sin(angle) * 100,
                            cx + Math.cos(angle) * 100, cy + Math.sin(angle) * 100
                        );
                        gradient.addColorStop(0, 'rgba(6, 182, 212, 0.9)');
                        gradient.addColorStop(0.5, 'rgba(139, 92, 246, 0.95)');
                        gradient.addColorStop(1, 'rgba(236, 72, 153, 0.9)');
                        return gradient;
                    },
                    borderWidth: 2.5,
                    pointStyle: 'circle',
                    pointBackgroundColor: (context) => {
                        const val = context.raw;
                        return val >= 8 ? '#34d399' : val >= 6 ? '#fbbf24' : '#f87171';
                    },
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2.5,
                    pointRadius: 6,
                    pointHoverRadius: 10,
                    pointHoverBackgroundColor: '#22d3ee',
                    pointHoverBorderColor: '#ffffff',
                    pointHoverBorderWidth: 3,
                    tension: 0.15,
                    order: 1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: {
                duration: 1400,
                easing: 'easeOutQuart'
            },
            layout: {
                padding: { top: 10, bottom: 10, left: 10, right: 10 }
            },
            scales: {
                r: {
                    beginAtZero: true,
                    max: 10,
                    min: 0,
                    ticks: {
                        stepSize: 2,
                        color: 'rgba(148, 163, 184, 0.5)',
                        backdropColor: 'transparent',
                        font: { size: 9, family: "'Inter', system-ui, sans-serif" },
                        showLabelBackdrop: false,
                        z: 1
                    },
                    grid: {
                        color: (ctx) => {
                            if (ctx.index === 0) return 'transparent';
                            return ctx.index % 2 === 0
                                ? 'rgba(148, 163, 184, 0.06)'
                                : 'rgba(148, 163, 184, 0.14)';
                        },
                        circular: true,
                        lineWidth: 1
                    },
                    angleLines: {
                        color: 'rgba(148, 163, 184, 0.1)',
                        lineWidth: 1
                    },
                    pointLabels: {
                        color: (ctx) => dimColors[ctx.index % dimColors.length],
                        font: {
                            size: 12,
                            weight: '700',
                            family: "'Inter', system-ui, sans-serif"
                        },
                        backdropColor: 'rgba(15, 23, 42, 0.6)',
                        backdropPadding: { top: 4, bottom: 4, left: 6, right: 6 },
                        borderRadius: 6,
                        padding: 18
                    }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    enabled: true,
                    backgroundColor: 'rgba(15, 23, 42, 0.92)',
                    titleColor: '#e2e8f0',
                    titleFont: { size: 13, weight: '600' },
                    bodyColor: '#94a3b8',
                    bodyFont: { size: 12 },
                    borderColor: 'rgba(139, 92, 246, 0.35)',
                    borderWidth: 1,
                    cornerRadius: 10,
                    padding: 14,
                    displayColors: true,
                    boxPadding: 6,
                    usePointStyle: true,
                    callbacks: {
                        title: (items) => items[0].label,
                        label: (context) => {
                            const val = context.raw;
                            const fullStars = Math.round(val / 2);
                            const emptyStars = 5 - fullStars;
                            const stars = '★'.repeat(fullStars) + '☆'.repeat(emptyStars);
                            const status = val >= 8 ? 'Excellent' : val >= 6 ? 'Good' : 'Needs Improvement';
                            return [`Score: ${val} / 10  (${status})`, `Rating: ${stars}`];
                        }
                    }
                }
            }
        },
        plugins: [
            {
                id: 'radarGlow',
                beforeDatasetsDraw: (chart) => {
                    const { ctx } = chart;
                    ctx.save();
                    ctx.shadowColor = 'rgba(139, 92, 246, 0.25)';
                    ctx.shadowBlur = 25;
                    ctx.shadowOffsetX = 0;
                    ctx.shadowOffsetY = 0;
                },
                afterDatasetsDraw: (chart) => {
                    chart.ctx.restore();
                }
            },
            {
                id: 'scoreLabels',
                afterDatasetsDraw: (chart) => {
                    const { ctx, data } = chart;
                    const dataset = data.datasets[1];
                    const meta = chart.getDatasetMeta(1);
                    if (!meta || !meta.data) return;

                    ctx.save();
                    ctx.font = "bold 11px 'Inter', system-ui, sans-serif";
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'bottom';

                    meta.data.forEach((point, index) => {
                        const value = dataset.data[index];
                        const x = point.x;
                        const y = point.y;
                        const text = value.toString();

                        // Determine color by score
                        const color = value >= 8 ? '#34d399' : value >= 6 ? '#fbbf24' : '#f87171';

                        // Draw text with subtle shadow for readability
                        ctx.shadowColor = 'rgba(0,0,0,0.7)';
                        ctx.shadowBlur = 4;
                        ctx.fillStyle = color;
                        ctx.fillText(text, x, y - 14);
                        ctx.shadowBlur = 0;

                        // Draw small indicator ring
                        ctx.beginPath();
                        ctx.arc(x, y, 3.5, 0, Math.PI * 2);
                        ctx.fillStyle = color;
                        ctx.fill();
                        ctx.beginPath();
                        ctx.arc(x, y, 6, 0, Math.PI * 2);
                        ctx.strokeStyle = color + '40';
                        ctx.lineWidth = 1;
                        ctx.stroke();
                    });

                    ctx.restore();
                }
            },
            {
                id: 'centerScore',
                afterDraw: (chart) => {
                    const { ctx, chartArea } = chart;
                    if (!chartArea) return;
                    const cx = (chartArea.left + chartArea.right) / 2;
                    const cy = (chartArea.top + chartArea.bottom) / 2;

                    ctx.save();

                    // Outer glow ring
                    ctx.beginPath();
                    ctx.arc(cx, cy, 28, 0, Math.PI * 2);
                    ctx.strokeStyle = 'rgba(139, 92, 246, 0.15)';
                    ctx.lineWidth = 1;
                    ctx.stroke();

                    // Inner circle background
                    ctx.beginPath();
                    ctx.arc(cx, cy, 22, 0, Math.PI * 2);
                    ctx.fillStyle = 'rgba(15, 23, 42, 0.85)';
                    ctx.fill();
                    ctx.strokeStyle = 'rgba(139, 92, 246, 0.3)';
                    ctx.lineWidth = 1.5;
                    ctx.stroke();

                    // Average score text
                    ctx.font = "bold 15px 'Inter', system-ui, sans-serif";
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    const avgColor = parseFloat(avgScore) >= 8 ? '#34d399' : parseFloat(avgScore) >= 6 ? '#fbbf24' : '#f87171';
                    ctx.fillStyle = avgColor;
                    ctx.fillText(avgScore, cx, cy - 1);

                    // Label below
                    ctx.font = "9px 'Inter', system-ui, sans-serif";
                    ctx.fillStyle = 'rgba(148, 163, 184, 0.7)';
                    ctx.fillText('Mean Score', cx, cy + 13);

                    ctx.restore();
                }
            }
        ]
    });
}

function renderContributionChart() {
    const ctx = document.getElementById('contributionChart');
    if (!ctx) return;
    const existing = Chart.getChart(ctx);
    if (existing) existing.destroy();

    // Build contribution data using quality-based scores
    const contributions = {};
    AGENTS.forEach(a => {
        const data = AppState.agentContributions[a.name];
        if (data && typeof data === 'object' && typeof data.contribution === 'number') {
            contributions[a.name] = data.contribution;
        } else {
            // Fallback: compute from full output if available
            const fullOut = AppState.agentFullOutputs[a.name];
            if (fullOut && fullOut.content) {
                const quality = analyzeAgentContribution(fullOut.content, a.name);
                contributions[a.name] = quality.score;
                AppState.agentContributions[a.name] = {
                    contribution: quality.score,
                    breakdown: quality.breakdown,
                    content_length: fullOut.content.length
                };
            } else {
                contributions[a.name] = 0;
            }
        }
    });

    const values = AGENTS.map(a => contributions[a.name] || 0);
    const maxVal = Math.max(...values, 1);

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: AGENTS.map(a => `${a.icon} ${a.name}`),
            datasets: [{
                label: 'Composite Contribution',
                data: values,
                backgroundColor: AGENTS.map(a => {
                    const pct = (contributions[a.name] || 0) / maxVal;
                    const alpha = 0.4 + pct * 0.5;
                    const colors = {
                        'Scholar Scour': `rgba(168,85,247,${alpha})`,
                        'Idea Igniter': `rgba(6,182,212,${alpha})`,
                        'Dr. Qwen Technical': `rgba(34,197,94,${alpha})`,
                        'Dr. Qwen Practical': `rgba(245,158,11,${alpha})`,
                        'Prof. Qwen Ethics': `rgba(239,68,68,${alpha})`,
                        'Dr. Qwen Leader': `rgba(236,72,153,${alpha})`,
                        'Critic Crucible': `rgba(249,115,22,${alpha})`,
                        'Prof. Qwen Editor': `rgba(20,184,166,${alpha})`
                    };
                    return colors[a.name] || `rgba(148,163,184,${alpha})`;
                }),
                borderColor: AGENTS.map(a => {
                    const colors = {
                        'Scholar Scour': 'rgba(168,85,247,1)',
                        'Idea Igniter': 'rgba(6,182,212,1)',
                        'Dr. Qwen Technical': 'rgba(34,197,94,1)',
                        'Dr. Qwen Practical': 'rgba(245,158,11,1)',
                        'Prof. Qwen Ethics': 'rgba(239,68,68,1)',
                        'Dr. Qwen Leader': 'rgba(236,72,153,1)',
                        'Critic Crucible': 'rgba(249,115,22,1)',
                        'Prof. Qwen Editor': 'rgba(20,184,166,1)'
                    };
                    return colors[a.name] || 'rgba(148,163,184,1)';
                }),
                borderWidth: 1,
                borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            indexAxis: 'y',
            scales: {
                x: {
                    beginAtZero: true,
                    ticks: { color: '#64748b', font: { size: 10 } },
                    grid: { color: 'rgba(148,163,184,0.1)' },
                    title: { display: true, text: 'Composite Contribution Score', color: '#94a3b8', font: { size: 10 } }
                },
                y: {
                    ticks: { color: '#94a3b8', font: { size: 10 } },
                    grid: { display: false }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const agentName = AGENTS[context.dataIndex]?.name;
                            const contrib = AppState.agentContributions[agentName];
                            if (contrib && contrib.breakdown) {
                                const b = contrib.breakdown;
                                return [
                                    `Composite Contribution: ${context.parsed.x}`,
                                    `  Structural Richness: ${b.structure} (Headings ${b.headings} Lists ${b.listItems})`,
                                    `  Depth Metrics: ${b.depth} (Formulas ${b.blockFormulas+b.inlineFormulas} Citations ${b.citations} Evaluations ${b.evaluations})`,
                                    `  Content Volume: ${b.volume} (~${b.totalWords} words)`,
                                    `  Char Count: ${(contrib.content_length || 0).toLocaleString()} chars`
                                ];
                            }
                            return `Composite Contribution: ${context.parsed.x}`;
                        }
                    }
                }
            }
        }
    });
}

function renderMath() {
    const reportEl = document.getElementById('report-content');
    if (!reportEl || typeof katex === 'undefined') return;

    reportEl.innerHTML = reportEl.innerHTML.replace(
        /\$\$([\s\S]*?)\$\$/g,
        (match, tex) => {
            try {
                return katex.renderToString(tex.trim(), { displayMode: true, throwOnError: false });
            } catch (e) { return match; }
        }
    );
    reportEl.innerHTML = reportEl.innerHTML.replace(
        /\$([^$\n<]+)\$/g,
        (match, tex) => {
            try {
                return katex.renderToString(tex.trim(), { displayMode: false, throwOnError: false });
            } catch (e) { return match; }
        }
    );
}

function exportMarkdown() {
    const content = AppState.finalContent;
    if (!content) return;
    const blob = new Blob([content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `hypothesis_report_${Date.now()}.md`;
    a.click();
    URL.revokeObjectURL(url);
}

function exportJSON() {
    const data = {
        topic: AppState.workflowData?.topic || '',
        timestamp: new Date().toISOString(),
        scores: AppState.finalScores,
        agent_contributions: AppState.agentContributions,
        inspiration_paths: AppState.inspirationPaths,
        graph_stats: AppState.graphStats,
        final_content: AppState.finalContent
    };
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `hypothesis_data_${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

document.addEventListener('DOMContentLoaded', () => {
    checkSystemStatus();
});
