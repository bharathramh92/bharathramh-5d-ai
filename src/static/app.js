document.addEventListener('DOMContentLoaded', () => {
    mermaid.initialize({ startOnLoad: false, theme: 'dark' });

    const analyzeBtn = document.getElementById('analyze-btn');
    const repoInput = document.getElementById('repo-path');
    const btnText = document.getElementById('btn-text');
    const btnSpinner = document.getElementById('btn-spinner');
    const pipelineTracker = document.getElementById('pipeline-tracker');
    const dashboard = document.getElementById('dashboard');

    let currentReport = null;

    // Tab Switching Logic
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetTab = btn.getAttribute('data-tab');

            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));

            btn.classList.add('active');
            document.getElementById(targetTab).classList.add('active');
        });
    });

    // Run Analysis Button Handler
    analyzeBtn.addEventListener('click', async () => {
        const repoPath = repoInput.value.trim();

        btnText.textContent = "Analyzing Codebase...";
        btnSpinner.classList.remove('hidden');
        analyzeBtn.disabled = true;
        pipelineTracker.classList.remove('hidden');

        try {
            const response = await fetch('/api/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ target_dir: repoPath || null })
            });

            if (!response.ok) {
                const err = await response.json();
                alert(`Analysis Error: ${err.detail || 'Failed to complete analysis'}`);
                return;
            }

            currentReport = await response.json();
            renderDashboard(currentReport);

        } catch (error) {
            alert(`Error running analysis: ${error.message}`);
        } finally {
            btnText.textContent = "🚀 Run Multi-Agent Analysis";
            btnSpinner.classList.add('hidden');
            analyzeBtn.disabled = false;
        }
    });

    function renderDashboard(report) {
        dashboard.classList.remove('hidden');

        // Metrics
        document.getElementById('val-loc').textContent = report.inspection_summary.total_loc.toLocaleString();
        document.getElementById('val-files').textContent = report.inspection_summary.total_files.toLocaleString();
        document.getElementById('val-routes').textContent = report.inspection_summary.api_route_count;
        document.getElementById('val-security').textContent = report.security_report.overall_rating || 'Good';

        // Languages
        const langContainer = document.getElementById('lang-list');
        langContainer.innerHTML = '';
        Object.entries(report.inspection_summary.languages || {}).forEach(([lang, count]) => {
            const tag = document.createElement('span');
            tag.className = 'tag';
            tag.textContent = `${lang}: ${count}`;
            langContainer.appendChild(tag);
        });

        // Dependencies
        const depContainer = document.getElementById('dep-list');
        depContainer.innerHTML = '';
        (report.security_report.key_risks || []).forEach(dep => {
            const tag = document.createElement('span');
            tag.className = 'tag';
            tag.textContent = dep;
            depContainer.appendChild(tag);
        });

        // Diagrams
        renderMermaid('mermaid-component', report.diagrams.component_diagram);
        renderMermaid('mermaid-sequence', report.diagrams.sequence_diagram);

        // Markdown Tabs
        document.getElementById('md-adr').innerHTML = marked.parse(report.documentation.adr_document || '');
        document.getElementById('md-security').innerHTML = marked.parse(report.security_report.summary_markdown || '');
        document.getElementById('md-onboarding').innerHTML = marked.parse(report.documentation.onboarding_guide || '');
    }

    async function renderMermaid(elementId, code) {
        const container = document.getElementById(elementId);
        container.innerHTML = '';
        try {
            const { svg } = await mermaid.render(elementId + '-svg', code);
            container.innerHTML = svg;
        } catch (e) {
            container.innerHTML = `<pre class="code-block">${code}</pre>`;
        }
    }

    // Chat Handler
    const chatInput = document.getElementById('chat-input');
    const sendChatBtn = document.getElementById('send-chat-btn');
    const chatMessages = document.getElementById('chat-messages');

    sendChatBtn.addEventListener('click', async () => {
        const question = chatInput.value.trim();
        if (!question) return;

        // Add user bubble
        appendMessage('user', question);
        chatInput.value = '';

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    question: question,
                    report_context: currentReport
                })
            });

            const data = await response.json();
            appendMessage('bot', marked.parse(data.answer || 'No response generated.'));
        } catch (err) {
            appendMessage('bot', 'Error communicating with ArchAgent assistant.');
        }
    });

    function appendMessage(sender, htmlContent) {
        const bubble = document.createElement('div');
        bubble.className = `chat-bubble ${sender}`;
        bubble.innerHTML = htmlContent;
        chatMessages.appendChild(bubble);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
});
