// Конфигурация API
const API_BASE = 'http://localhost:5000/api';
const WS_URL = 'http://localhost:5000';

// WebSocket соединение
let socket = null;
let isConnected = false;

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    initWebSocket();
    loadStats();
    loadPrompts();
    loadDatasets();
    loadAlgorithmSteps();
    loadHistory();
    createConnectionStatus();
});

// ========== WebSocket инициализация ==========
function initWebSocket() {
    // Используем socket.io клиент
    socket = io(WS_URL, {
        transports: ['websocket', 'polling'],
        reconnection: true,
        reconnectionDelay: 1000,
        reconnectionDelayMax: 5000,
        reconnectionAttempts: Infinity
    });

    socket.on('connect', () => {
        console.log('✅ WebSocket connected');
        isConnected = true;
        updateConnectionStatus(true);
        
        // Подписываемся на обновления
        socket.emit('subscribe_stats');
        socket.emit('subscribe_history');
    });

    socket.on('disconnect', () => {
        console.log('❌ WebSocket disconnected');
        isConnected = false;
        updateConnectionStatus(false);
    });

    socket.on('connected', (data) => {
        console.log('Connected:', data.message);
    });

    // Обработка обновлений статистики
    socket.on('stats_update', (stats) => {
        updateStatsDisplay(stats);
    });

    socket.on('stats_updated', () => {
        loadStats(); // Перезагружаем статистику
    });

    // Обработка новых вызовов LLM
    socket.on('llm_call_logged', (data) => {
        console.log('New LLM call:', data);
        addHistoryItem(data);
        loadStats(); // Обновляем статистику
    });

    // Обработка обновлений промптов
    socket.on('prompt_created', (data) => {
        console.log('Prompt created:', data);
        loadPrompts();
        loadStats();
    });

    socket.on('prompt_updated', (data) => {
        console.log('Prompt updated:', data);
        loadPrompts();
    });

    socket.on('prompt_deleted', (data) => {
        console.log('Prompt deleted:', data);
        loadPrompts();
        loadStats();
    });
}

// ========== Connection Status ==========
function createConnectionStatus() {
    const status = document.createElement('div');
    status.id = 'connectionStatus';
    status.className = 'connection-status disconnected';
    status.innerHTML = '<span class="indicator"></span> Disconnected';
    document.body.appendChild(status);
}

function updateConnectionStatus(connected) {
    const status = document.getElementById('connectionStatus');
    if (status) {
        if (connected) {
            status.className = 'connection-status connected';
            status.innerHTML = '<span class="indicator"></span> Connected';
        } else {
            status.className = 'connection-status disconnected';
            status.innerHTML = '<span class="indicator"></span> Disconnected';
        }
    }
}

// ========== Управление вкладками ==========
function initTabs() {
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabName = btn.dataset.tab;
            
            // Убираем активный класс у всех
            tabButtons.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));
            
            // Добавляем активный класс
            btn.classList.add('active');
            document.getElementById(`${tabName}-tab`).classList.add('active');
            
            // Загружаем данные для активной вкладки
            if (tabName === 'prompts') loadPrompts();
            else if (tabName === 'datasets') loadDatasets();
            else if (tabName === 'history') loadHistory();
            else if (tabName === 'algorithm') loadAlgorithmSteps();
        });
    });
}

// ========== Загрузка статистики ==========
async function loadStats() {
    try {
        const response = await fetch(`${API_BASE}/stats`);
        const stats = await response.json();
        updateStatsDisplay(stats);
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

function updateStatsDisplay(stats) {
    if (stats.prompts) {
        document.getElementById('promptsCount').textContent = 
            `${stats.prompts.active}/${stats.prompts.total}`;
    }
    if (stats.llm_calls) {
        document.getElementById('llmCallsCount').textContent = 
            stats.llm_calls.total.toLocaleString();
    }
    if (stats.datasets) {
        document.getElementById('datasetsCount').textContent = 
            stats.datasets.total;
    }
}

// ========== Управление промптами ==========
let allPrompts = [];
let filteredPrompts = [];

async function loadPrompts() {
    try {
        const grid = document.getElementById('promptsGrid');
        grid.innerHTML = '<div class="loading-state">Загрузка промптов...</div>';
        
        const response = await fetch(`${API_BASE}/prompts`);
        allPrompts = await response.json();
        filteredPrompts = [...allPrompts];
        
        grid.innerHTML = '';
        
        if (allPrompts.length === 0) {
            grid.innerHTML = '<div class="empty-state"><p>Нет промптов. Создайте первый промпт.</p></div>';
            return;
        }
        
        // Загружаем фильтры шагов алгоритма
        loadPromptFilters();
        
        // Отображаем отфильтрованные промпты
        renderPrompts();
    } catch (error) {
        console.error('Error loading prompts:', error);
        document.getElementById('promptsGrid').innerHTML = 
            '<div class="empty-state"><p>Ошибка загрузки промптов</p></div>';
        showToast('Ошибка загрузки промптов', 'error');
    }
}

function loadPromptFilters() {
    const steps = [...new Set(allPrompts.map(p => p.algorithm_step).filter(Boolean))];
    const stepSelect = document.getElementById('promptsFilterStep');
    if (stepSelect) {
        const currentValue = stepSelect.value;
        stepSelect.innerHTML = '<option value="">Все шаги</option>';
        steps.forEach(step => {
            const option = document.createElement('option');
            option.value = step;
            option.textContent = step;
            stepSelect.appendChild(option);
        });
        stepSelect.value = currentValue;
    }
}

function filterPrompts() {
    const searchTerm = (document.getElementById('promptsSearch')?.value || '').toLowerCase();
    const statusFilter = document.getElementById('promptsFilterStatus')?.value || '';
    const stepFilter = document.getElementById('promptsFilterStep')?.value || '';
    
    filteredPrompts = allPrompts.filter(prompt => {
        const matchesSearch = !searchTerm || 
            prompt.name.toLowerCase().includes(searchTerm) ||
            (prompt.description || '').toLowerCase().includes(searchTerm) ||
            (prompt.algorithm_step || '').toLowerCase().includes(searchTerm);
        
        const matchesStatus = !statusFilter || 
            (statusFilter === 'active' && prompt.is_active) ||
            (statusFilter === 'inactive' && !prompt.is_active);
        
        const matchesStep = !stepFilter || prompt.algorithm_step === stepFilter;
        
        return matchesSearch && matchesStatus && matchesStep;
    });
    
    renderPrompts();
}

function renderPrompts() {
    const grid = document.getElementById('promptsGrid');
    grid.innerHTML = '';
    
    if (filteredPrompts.length === 0) {
        grid.innerHTML = '<div class="empty-state"><p>Промпты не найдены</p></div>';
        return;
    }
    
    filteredPrompts.forEach(prompt => {
        const card = createPromptCard(prompt);
        grid.appendChild(card);
    });
}

function createPromptCard(prompt) {
    const card = document.createElement('div');
    card.className = `prompt-card ${prompt.is_active ? 'active' : ''}`;
    
    card.innerHTML = `
        <div class="prompt-header">
            <div>
                <div class="prompt-name">${escapeHtml(prompt.name)}</div>
                <span class="prompt-badge ${prompt.is_active ? 'badge-active' : 'badge-inactive'}">
                    ${prompt.is_active ? 'Активен' : 'Неактивен'}
                </span>
                ${prompt.algorithm_step ? `<span class="prompt-badge badge-step">${escapeHtml(prompt.algorithm_step)}</span>` : ''}
            </div>
        </div>
        <div class="prompt-description">${escapeHtml(prompt.description || 'Без описания')}</div>
        <div class="prompt-meta">
            <span>Temperature: ${prompt.temperature}</span>
            <span>Max Tokens: ${prompt.max_tokens === -1 ? '∞' : prompt.max_tokens}</span>
        </div>
        <div class="prompt-actions">
            <button class="btn btn-primary btn-sm" onclick="editPrompt(${prompt.id})">Редактировать</button>
            <button class="btn btn-secondary btn-sm" onclick="duplicatePrompt(${prompt.id})" title="Дублировать">📋</button>
            <button class="btn btn-danger btn-sm" onclick="deletePrompt(${prompt.id})">Удалить</button>
        </div>
    `;
    
    return card;
}

function showCreatePromptModal() {
    document.getElementById('promptId').value = '';
    document.getElementById('promptForm').reset();
    document.getElementById('promptModalTitle').textContent = 'Создать промпт';
    document.getElementById('promptModal').classList.add('active');
}

function editPrompt(promptId) {
    fetch(`${API_BASE}/prompts/${promptId}`)
        .then(res => res.json())
        .then(prompt => {
            document.getElementById('promptId').value = prompt.id;
            document.getElementById('promptName').value = prompt.name;
            document.getElementById('promptDescription').value = prompt.description || '';
            document.getElementById('promptAlgorithmStep').value = prompt.algorithm_step || '';
            document.getElementById('promptSystem').value = prompt.system_prompt || '';
            document.getElementById('promptUserTemplate').value = prompt.user_prompt_template || '';
            document.getElementById('promptTemperature').value = prompt.temperature;
            document.getElementById('promptMaxTokens').value = prompt.max_tokens;
            document.getElementById('promptIsActive').checked = prompt.is_active;
            
            document.getElementById('promptModalTitle').textContent = 'Редактировать промпт';
            document.getElementById('promptModal').classList.add('active');
        })
        .catch(error => {
            console.error('Error loading prompt:', error);
            showToast('Ошибка загрузки промпта', 'error');
        });
}

function closePromptModal() {
    document.getElementById('promptModal').classList.remove('active');
}

document.getElementById('promptForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const promptId = document.getElementById('promptId').value;
    const data = {
        name: document.getElementById('promptName').value,
        description: document.getElementById('promptDescription').value,
        algorithm_step: document.getElementById('promptAlgorithmStep').value,
        system_prompt: document.getElementById('promptSystem').value,
        user_prompt_template: document.getElementById('promptUserTemplate').value,
        temperature: parseFloat(document.getElementById('promptTemperature').value),
        max_tokens: parseInt(document.getElementById('promptMaxTokens').value),
        is_active: document.getElementById('promptIsActive').checked
    };
    
    try {
        const url = promptId ? `${API_BASE}/prompts/${promptId}` : `${API_BASE}/prompts`;
        const method = promptId ? 'PUT' : 'POST';
        
        const response = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        if (response.ok) {
            closePromptModal();
            showToast('Промпт успешно сохранен', 'success');
            loadPrompts();
            loadStats();
        } else {
            const error = await response.json();
            showToast(error.error || 'Неизвестная ошибка', 'error');
        }
    } catch (error) {
        console.error('Error saving prompt:', error);
        showToast('Ошибка сохранения промпта', 'error');
    }
});

async function duplicatePrompt(promptId) {
    try {
        const response = await fetch(`${API_BASE}/prompts/${promptId}`);
        const prompt = await response.json();
        
        const data = {
            name: `${prompt.name} (копия)`,
            description: prompt.description || '',
            algorithm_step: prompt.algorithm_step || '',
            system_prompt: prompt.system_prompt || '',
            user_prompt_template: prompt.user_prompt_template || '',
            temperature: prompt.temperature,
            max_tokens: prompt.max_tokens,
            is_active: false // Копия создается неактивной
        };
        
        const createResponse = await fetch(`${API_BASE}/prompts`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        if (createResponse.ok) {
            showToast('Промпт успешно скопирован', 'success');
            loadPrompts();
            loadStats();
        } else {
            const error = await createResponse.json();
            showToast(error.error || 'Ошибка копирования промпта', 'error');
        }
    } catch (error) {
        console.error('Error duplicating prompt:', error);
        showToast('Ошибка копирования промпта', 'error');
    }
}

async function deletePrompt(promptId) {
    const prompt = allPrompts.find(p => p.id === promptId);
    const promptName = prompt ? prompt.name : 'этот промпт';
    
    if (!confirm(`Вы уверены, что хотите удалить промпт "${promptName}"?`)) return;
    
    try {
        const response = await fetch(`${API_BASE}/prompts/${promptId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            showToast('Промпт успешно удален', 'success');
            loadPrompts();
            loadStats();
        } else {
            showToast('Ошибка удаления промпта', 'error');
        }
    } catch (error) {
        console.error('Error deleting prompt:', error);
        showToast('Ошибка удаления промпта', 'error');
    }
}

// ========== Управление датасетами ==========
async function loadDatasets() {
    try {
        const list = document.getElementById('datasetsList');
        list.innerHTML = '<div class="loading-state">Загрузка датасетов...</div>';
        
        const response = await fetch(`${API_BASE}/datasets`);
        const datasets = await response.json();
        
        list.innerHTML = '';
        
        if (datasets.length === 0) {
            list.innerHTML = '<div class="empty-state"><p>Нет датасетов. Создайте первый датасет.</p></div>';
            return;
        }
        
        datasets.forEach(dataset => {
            const card = createDatasetCard(dataset);
            list.appendChild(card);
        });
    } catch (error) {
        console.error('Error loading datasets:', error);
        showToast('Ошибка загрузки датасетов', 'error');
    }
}

function createDatasetCard(dataset) {
    const card = document.createElement('div');
    card.className = 'dataset-card';
    
    const metadata = dataset.metadata ? JSON.parse(dataset.metadata) : {};
    
    card.innerHTML = `
        <div class="dataset-info">
            <h3>${escapeHtml(dataset.name)}</h3>
            <p>${escapeHtml(dataset.description || 'Без описания')}</p>
            <div class="dataset-stats">
                <span>Версия: ${dataset.version}</span>
                <span>Образцов: ${dataset.total_samples}</span>
                <span>Обработано: ${dataset.processed_samples || 0}</span>
                <span>Статус: ${dataset.status}</span>
            </div>
        </div>
    `;
    
    return card;
}

function showCreateDatasetModal() {
    document.getElementById('datasetId').value = '';
    document.getElementById('datasetForm').reset();
    document.getElementById('datasetVersion').value = '1.0';
    document.getElementById('datasetModalTitle').textContent = 'Создать датасет';
    document.getElementById('datasetModal').classList.add('active');
}

function closeDatasetModal() {
    document.getElementById('datasetModal').classList.remove('active');
}

document.getElementById('datasetForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const datasetId = document.getElementById('datasetId').value;
    const data = {
        name: document.getElementById('datasetName').value,
        description: document.getElementById('datasetDescription').value,
        version: document.getElementById('datasetVersion').value || '1.0'
    };
    
    // Валидация
    if (!data.name.trim()) {
        showToast('Название датасета обязательно', 'error');
        return;
    }
    
    try {
        const url = `${API_BASE}/datasets`;
        const method = 'POST';
        
        const response = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        if (response.ok) {
            closeDatasetModal();
            showToast('Датасет успешно создан', 'success');
            loadDatasets();
            loadStats();
        } else {
            const error = await response.json();
            showToast(error.error || 'Ошибка создания датасета', 'error');
        }
    } catch (error) {
        console.error('Error saving dataset:', error);
        showToast('Ошибка создания датасета', 'error');
    }
});

// ========== История обработки ==========
let historyItems = new Map(); // Храним загруженные элементы для избежания дубликатов

async function loadHistory() {
    const step = document.getElementById('historyFilterStep').value;
    const promptId = document.getElementById('historyFilterPrompt').value;
    const limit = document.getElementById('historyLimit').value;
    
    const list = document.getElementById('historyList');
    list.innerHTML = '<div class="loading-state">Загрузка истории...</div>';
    
    let url = `${API_BASE}/llm-history?limit=${limit}`;
    if (step) url += `&algorithm_step=${step}`;
    if (promptId) url += `&prompt_id=${promptId}`;
    
    try {
        const response = await fetch(url);
        const history = await response.json();
        
        list.innerHTML = '';
        historyItems.clear();
        
        if (history.length === 0) {
            list.innerHTML = '<div class="empty-state"><p>История пуста</p></div>';
            return;
        }
        
        history.forEach(item => {
            historyItems.set(item.id, item);
            const card = createHistoryCard(item);
            list.appendChild(card);
        });
        
        // Загружаем фильтры
        loadHistoryFilters();
    } catch (error) {
        console.error('Error loading history:', error);
        showToast('Ошибка загрузки истории', 'error');
    }
}

// Добавление нового элемента истории в realtime
function addHistoryItem(item) {
    // Проверяем, не добавлен ли уже этот элемент
    if (historyItems.has(item.id)) {
        return;
    }
    
    // Проверяем фильтры
    const step = document.getElementById('historyFilterStep').value;
    const promptId = document.getElementById('historyFilterPrompt').value;
    
    if (step && item.algorithm_step !== step) {
        return;
    }
    if (promptId && item.prompt_id != promptId) {
        return;
    }
    
    const list = document.getElementById('historyList');
    
    // Убираем empty state если есть
    const emptyState = list.querySelector('.empty-state');
    if (emptyState) {
        emptyState.remove();
    }
    
    // Добавляем новый элемент в начало списка
    const card = createHistoryCard(item);
    list.insertBefore(card, list.firstChild);
    historyItems.set(item.id, item);
    
    // Ограничиваем количество элементов (удаляем последний если превышен лимит)
    const limit = parseInt(document.getElementById('historyLimit').value) || 50;
    const items = list.querySelectorAll('.history-item');
    if (items.length > limit) {
        const lastItem = items[items.length - 1];
        const lastItemId = parseInt(lastItem.dataset.id);
        historyItems.delete(lastItemId);
        lastItem.remove();
    }
    
    // Добавляем анимацию появления
    card.style.opacity = '0';
    card.style.transform = 'translateY(-10px)';
    setTimeout(() => {
        card.style.transition = 'all 0.3s ease';
        card.style.opacity = '1';
        card.style.transform = 'translateY(0)';
    }, 10);
}

function createHistoryCard(item) {
    const card = document.createElement('div');
    card.className = `history-item ${item.success ? 'success' : 'error'}`;
    card.dataset.id = item.id;
    card.onclick = () => showHistoryDetails(item.id);
    
    const date = new Date(item.created_at);
    
    card.innerHTML = `
        <div class="history-header">
            <div>
                <div class="history-step">${escapeHtml(item.algorithm_step || 'Неизвестно')}</div>
                <div class="history-prompt">Промпт: ${escapeHtml(item.prompt_name || 'Не указан')}</div>
            </div>
            <div class="history-time">${date.toLocaleString('ru-RU')}</div>
        </div>
        <div class="history-stats">
            <span>Модель: ${escapeHtml(item.model || 'N/A')}</span>
            <span>Время: ${item.response_time_ms}ms</span>
            <span>Токены: ${item.tokens_used || 0}</span>
            <span>Temperature: ${item.temperature}</span>
            ${!item.success ? `<span style="color: #e74c3c;">Ошибка: ${escapeHtml(item.error_message || 'Неизвестная ошибка')}</span>` : ''}
        </div>
    `;
    
    return card;
}

async function loadHistoryFilters() {
    // Загружаем шаги алгоритма
    const stepsResponse = await fetch(`${API_BASE}/algorithm-steps`);
    const steps = await stepsResponse.json();
    
    const stepSelect = document.getElementById('historyFilterStep');
    const currentValue = stepSelect.value;
    stepSelect.innerHTML = '<option value="">Все шаги алгоритма</option>';
    steps.forEach(step => {
        const option = document.createElement('option');
        option.value = step.algorithm_step;
        option.textContent = `${step.algorithm_step} (${step.call_count} вызовов)`;
        stepSelect.appendChild(option);
    });
    stepSelect.value = currentValue;
    
    // Загружаем промпты
    const promptsResponse = await fetch(`${API_BASE}/prompts`);
    const prompts = await promptsResponse.json();
    
    const promptSelect = document.getElementById('historyFilterPrompt');
    const currentPromptValue = promptSelect.value;
    promptSelect.innerHTML = '<option value="">Все промпты</option>';
    prompts.forEach(prompt => {
        const option = document.createElement('option');
        option.value = prompt.id;
        option.textContent = prompt.name;
        promptSelect.appendChild(option);
    });
    promptSelect.value = currentPromptValue;
}

async function showHistoryDetails(historyId) {
    try {
        const response = await fetch(`${API_BASE}/llm-history/${historyId}`);
        const item = await response.json();
        
        const details = document.getElementById('historyDetails');
        
        // Создаем основную структуру
        details.innerHTML = `
            <div class="history-detail-section">
                <h3>Общая информация</h3>
                <p><strong>Шаг алгоритма:</strong> ${escapeHtml(item.algorithm_step || 'N/A')}</p>
                <p><strong>Промпт:</strong> ${escapeHtml(item.prompt_name || 'N/A')}</p>
                <p><strong>Модель:</strong> ${escapeHtml(item.model || 'N/A')}</p>
                <p><strong>Время:</strong> ${new Date(item.created_at).toLocaleString('ru-RU')}</p>
                <p><strong>Статус:</strong> ${item.success ? '✅ Успешно' : '❌ Ошибка'}</p>
            </div>
            
            ${item.system_prompt ? `
            <div class="history-detail-section">
                <h3>Системный промпт</h3>
                <pre>${escapeHtml(item.system_prompt)}</pre>
            </div>
            ` : ''}
            
            ${item.user_prompt_template ? `
            <div class="history-detail-section">
                <h3>Шаблон пользовательского промпта</h3>
                <pre>${escapeHtml(item.user_prompt_template)}</pre>
            </div>
            ` : ''}
            
            <div class="history-detail-section">
                <h3>Входные данные</h3>
                <div id="inputDataViewer"></div>
            </div>
            
            <div class="history-detail-section">
                <h3>Выходные данные</h3>
                <div id="outputDataViewer"></div>
            </div>
            
            ${item.metadata ? `
            <div class="history-detail-section">
                <h3>Метаданные</h3>
                <div id="metadataViewer"></div>
            </div>
            ` : ''}
            
            ${item.error_message ? `
            <div class="history-detail-section">
                <h3>Ошибка</h3>
                <pre style="color: #e74c3c;">${escapeHtml(item.error_message)}</pre>
            </div>
            ` : ''}
            
            <div class="history-detail-section">
                <h3>Параметры</h3>
                <p><strong>Temperature:</strong> ${item.temperature}</p>
                <p><strong>Токенов использовано:</strong> ${item.tokens_used || 0}</p>
                <p><strong>Время ответа:</strong> ${item.response_time_ms}ms</p>
            </div>
        `;
        
        // Добавляем JSON viewers
        const inputViewer = createJSONViewer(item.input_data || '{}');
        document.getElementById('inputDataViewer').appendChild(inputViewer);
        
        const outputViewer = createJSONViewer(item.output_data || '{}');
        document.getElementById('outputDataViewer').appendChild(outputViewer);
        
        if (item.metadata) {
            const metadataViewer = createJSONViewer(item.metadata || '{}');
            document.getElementById('metadataViewer').appendChild(metadataViewer);
        }
        
        document.getElementById('historyModal').classList.add('active');
    } catch (error) {
        console.error('Error loading history details:', error);
        showToast('Ошибка загрузки деталей', 'error');
    }
}

function closeHistoryModal() {
    document.getElementById('historyModal').classList.remove('active');
}

// ========== Визуализация алгоритма ==========
async function loadAlgorithmSteps() {
    try {
        const response = await fetch(`${API_BASE}/algorithm-steps`);
        const steps = await response.json();
        
        const flow = document.getElementById('algorithmFlow');
        flow.innerHTML = '';
        
        if (steps.length === 0) {
            flow.innerHTML = '<div class="empty-state"><p>Нет данных об алгоритме</p></div>';
            return;
        }
        
        // Загружаем промпты для каждого шага
        const promptsResponse = await fetch(`${API_BASE}/prompts`);
        const prompts = await promptsResponse.json();
        
        steps.forEach(step => {
            const stepPrompts = prompts.filter(p => p.algorithm_step === step.algorithm_step);
            const card = createAlgorithmStepCard(step, stepPrompts);
            flow.appendChild(card);
        });
    } catch (error) {
        console.error('Error loading algorithm steps:', error);
    }
}

function createAlgorithmStepCard(step, prompts) {
    const card = document.createElement('div');
    card.className = 'algorithm-step has-llm';
    
    card.innerHTML = `
        <div class="step-header">
            <div class="step-name">${escapeHtml(step.algorithm_step)}</div>
            <span class="step-badge">LLM обработка</span>
        </div>
        <div class="step-stats">
            <span>Вызовов: ${step.call_count}</span>
            <span>Промптов: ${step.prompt_count}</span>
        </div>
        ${prompts.length > 0 ? `
        <div class="step-prompts">
            <strong>Используемые промпты:</strong>
            ${prompts.map(p => `<span class="prompt-mini">${escapeHtml(p.name)}</span>`).join('')}
        </div>
        ` : ''}
    `;
    
    return card;
}

// ========== Утилиты ==========
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ========== Toast Notifications ==========
function showToast(message, type = 'info', title = '') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const icons = {
        success: '✅',
        error: '❌',
        warning: '⚠️',
        info: 'ℹ️'
    };
    
    toast.innerHTML = `
        <span class="toast-icon">${icons[type] || icons.info}</span>
        <div class="toast-content">
            ${title ? `<div class="toast-title">${escapeHtml(title)}</div>` : ''}
            <div class="toast-message">${escapeHtml(message)}</div>
        </div>
        <button class="toast-close" onclick="this.parentElement.remove()">&times;</button>
    `;
    
    container.appendChild(toast);
    
    // Автоматическое удаление через 5 секунд
    setTimeout(() => {
        if (toast.parentElement) {
            toast.style.animation = 'slideInRight 0.3s ease reverse';
            setTimeout(() => toast.remove(), 300);
        }
    }, 5000);
}

// ========== JSON Viewer ==========
function formatJSON(jsonString) {
    try {
        const obj = typeof jsonString === 'string' ? JSON.parse(jsonString) : jsonString;
        return JSON.stringify(obj, null, 2);
    } catch (e) {
        return jsonString;
    }
}

function highlightJSON(jsonString) {
    const formatted = formatJSON(jsonString);
    return formatted
        .replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, (match) => {
            let cls = 'json-number';
            if (/^"/.test(match)) {
                if (/:$/.test(match)) {
                    cls = 'json-key';
                } else {
                    cls = 'json-string';
                }
            } else if (/true|false/.test(match)) {
                cls = 'json-boolean';
            } else if (/null/.test(match)) {
                cls = 'json-null';
            }
            return `<span class="${cls}">${escapeHtml(match)}</span>`;
        });
}

function createJSONViewer(jsonString, title = '') {
    const viewer = document.createElement('div');
    viewer.className = 'json-viewer';
    viewer.style.position = 'relative';
    
    const copyBtn = document.createElement('button');
    copyBtn.className = 'json-copy-btn';
    copyBtn.textContent = 'Копировать';
    copyBtn.onclick = () => {
        navigator.clipboard.writeText(formatJSON(jsonString)).then(() => {
            showToast('JSON скопирован в буфер обмена', 'success');
        });
    };
    
    const pre = document.createElement('pre');
    pre.innerHTML = highlightJSON(jsonString);
    
    viewer.appendChild(copyBtn);
    viewer.appendChild(pre);
    
    return viewer;
}

// Закрытие модальных окон по клику вне их
window.onclick = function(event) {
    const promptModal = document.getElementById('promptModal');
    const historyModal = document.getElementById('historyModal');
    const datasetModal = document.getElementById('datasetModal');
    
    if (event.target === promptModal) {
        closePromptModal();
    }
    if (event.target === historyModal) {
        closeHistoryModal();
    }
    if (event.target === datasetModal) {
        closeDatasetModal();
    }
}

// ========== Клавиатурные сокращения ==========
document.addEventListener('keydown', (e) => {
    // Ctrl+K или Cmd+K - поиск
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        const searchInput = document.getElementById('promptsSearch');
        if (searchInput && document.getElementById('prompts-tab').classList.contains('active')) {
            searchInput.focus();
        }
    }
    
    // Ctrl+N или Cmd+N - создать промпт
    if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
        e.preventDefault();
        if (document.getElementById('prompts-tab').classList.contains('active')) {
            showCreatePromptModal();
        }
    }
    
    // Esc - закрыть модальные окна
    if (e.key === 'Escape') {
        closePromptModal();
        closeHistoryModal();
        closeDatasetModal();
    }
});

// ========== Валидация форм ==========
function validatePromptForm() {
    const name = document.getElementById('promptName').value.trim();
    const algorithmStep = document.getElementById('promptAlgorithmStep').value;
    
    let isValid = true;
    
    // Очистка предыдущих ошибок
    document.querySelectorAll('.form-error').forEach(el => el.remove());
    document.querySelectorAll('.form-group.error').forEach(el => el.classList.remove('error'));
    
    if (!name) {
        showFieldError('promptName', 'Название обязательно');
        isValid = false;
    }
    
    if (!algorithmStep) {
        showFieldError('promptAlgorithmStep', 'Шаг алгоритма обязателен');
        isValid = false;
    }
    
    return isValid;
}

function showFieldError(fieldId, message) {
    const field = document.getElementById(fieldId);
    if (field) {
        const formGroup = field.closest('.form-group');
        if (formGroup) {
            formGroup.classList.add('error');
            const errorDiv = document.createElement('div');
            errorDiv.className = 'form-error';
            errorDiv.textContent = message;
            formGroup.appendChild(errorDiv);
        }
    }
}

// Добавляем валидацию к форме промпта
document.getElementById('promptForm').addEventListener('submit', (e) => {
    if (!validatePromptForm()) {
        e.preventDefault();
        showToast('Пожалуйста, исправьте ошибки в форме', 'error');
    }
});

