// DOM Elements
const autoAcceptCheckbox = document.getElementById('auto-accept');
const autoBanCheckbox = document.getElementById('auto-ban');
const autoPickCheckbox = document.getElementById('auto-pick');
const connectionStatus = document.getElementById('connection-status');
const statusText = document.getElementById('status-text');
const currentPhase = document.getElementById('current-phase');
const currentRole = document.getElementById('current-role');
const logContainer = document.getElementById('log-container');
const lobbyMembers = document.getElementById('lobby-members');
const lobbyStatus = document.getElementById('lobby-status');
const lobbyQueue = document.getElementById('lobby-queue');
const lobbyUpdateTime = document.getElementById('lobby-update-time');

// Presets elements
const roleTabs = document.querySelectorAll('.role-tab');
const pickPresetList = document.getElementById('pick-preset-list');
const banPresetList = document.getElementById('ban-preset-list');
const addPickBtn = document.getElementById('add-pick-btn');
const addBanBtn = document.getElementById('add-ban-btn');
const importPresetsBtn = document.getElementById('import-presets-btn');
const championModal = document.getElementById('champion-modal');
const modalClose = document.getElementById('modal-close');
const championSearch = document.getElementById('champion-search');
const championList = document.getElementById('champion-list');

// Navigation elements
const navItems = document.querySelectorAll('.nav-item');
const pages = document.querySelectorAll('.page');

// State
let isRunning = false;
let currentPage = 'home';
let lobbyUpdateInterval = null;
let currentPresetRole = 'top';
let currentPresetType = null; // 'pick' or 'ban'
let allChampions = [];
let currentPresets = {};

// Champions table element
const championsTable = document.getElementById('champions-table');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initEventListeners();
    initNavigation();
    initPresets();
    loadPresetsForHomePage();
    startBot();
});

function initNavigation() {
    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const pageName = item.dataset.page;
            navigateTo(pageName);
        });
    });
}

function navigateTo(pageName) {
    // Update nav items
    navItems.forEach(item => {
        item.classList.toggle('active', item.dataset.page === pageName);
    });

    // Update pages
    pages.forEach(page => {
        page.classList.toggle('active', page.id === `page-${pageName}`);
    });

    currentPage = pageName;

    // Start/stop lobby updates based on current page
    if (pageName === 'lobby') {
        startLobbyUpdates();
    } else {
        stopLobbyUpdates();
    }

    // Load presets when navigating to presets page
    if (pageName === 'presets') {
        loadPresets();
        loadAllChampions();
    }
}

function startLobbyUpdates() {
    requestLobbyUpdate();
    if (lobbyUpdateInterval) {
        clearInterval(lobbyUpdateInterval);
    }
    lobbyUpdateInterval = setInterval(requestLobbyUpdate, 1000);
}

function stopLobbyUpdates() {
    if (lobbyUpdateInterval) {
        clearInterval(lobbyUpdateInterval);
        lobbyUpdateInterval = null;
    }
}

async function requestLobbyUpdate() {
    try {
        await eel.request_lobby_update()();
    } catch (error) {
        console.error('Failed to request lobby update:', error);
    }
}

function initEventListeners() {
    autoAcceptCheckbox.addEventListener('change', updateSettings);
    autoBanCheckbox.addEventListener('change', updateSettings);
    autoPickCheckbox.addEventListener('change', updateSettings);
}

// ==================== Presets Functions ====================

function initPresets() {
    // Role tabs
    roleTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            roleTabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            currentPresetRole = tab.dataset.role;
            renderPresets();
        });
    });

    // Add buttons
    addPickBtn.addEventListener('click', () => openChampionModal('pick'));
    addBanBtn.addEventListener('click', () => openChampionModal('ban'));

    // Import button
    importPresetsBtn.addEventListener('click', importPresetsFromFile);

    // Modal
    modalClose.addEventListener('click', closeChampionModal);
    championModal.addEventListener('click', (e) => {
        if (e.target === championModal) closeChampionModal();
    });

    // Search
    championSearch.addEventListener('input', filterChampions);
}

async function loadPresets() {
    try {
        const presets = await eel.get_all_presets()();
        currentPresets = presets || {};
        renderPresets();
    } catch (error) {
        console.error('Failed to load presets:', error);
    }
}

async function loadAllChampions() {
    try {
        const champions = await eel.get_all_champions()();
        allChampions = champions || [];
    } catch (error) {
        console.error('Failed to load champions:', error);
    }
}

function renderPresets() {
    const picks = currentPresets[currentPresetRole] || [];
    const bans = currentPresets[`${currentPresetRole}_ban`] || [];

    renderPresetList(pickPresetList, picks, 'pick');
    renderPresetList(banPresetList, bans, 'ban');
}

function renderPresetList(container, champions, presetType) {
    if (!champions || champions.length === 0) {
        container.innerHTML = '<p class="placeholder">Нет чемпионов</p>';
        return;
    }

    let html = '';
    champions.forEach((champ, index) => {
        html += `
            <div class="preset-item" draggable="true" data-id="${champ.id}" data-index="${index}" data-type="${presetType}">
                <span class="position">${index + 1}</span>
                <span class="champion-name">${champ.name}</span>
                <button class="remove-btn" onclick="removeChampion(${champ.id}, '${presetType}')">&times;</button>
            </div>
        `;
    });

    container.innerHTML = html;

    // Add drag and drop
    initDragAndDrop(container, presetType);
}

function initDragAndDrop(container, presetType) {
    const items = container.querySelectorAll('.preset-item');

    items.forEach(item => {
        item.addEventListener('dragstart', (e) => {
            item.classList.add('dragging');
            e.dataTransfer.setData('text/plain', JSON.stringify({
                id: item.dataset.id,
                index: item.dataset.index,
                type: presetType
            }));
        });

        item.addEventListener('dragend', () => {
            item.classList.remove('dragging');
        });

        item.addEventListener('dragover', (e) => {
            e.preventDefault();
        });

        item.addEventListener('drop', async (e) => {
            e.preventDefault();
            const data = JSON.parse(e.dataTransfer.getData('text/plain'));
            const targetIndex = parseInt(item.dataset.index);
            const sourceIndex = parseInt(data.index);

            if (sourceIndex !== targetIndex && data.type === presetType) {
                try {
                    await eel.move_champion_in_preset(
                        currentPresetRole,
                        presetType,
                        parseInt(data.id),
                        targetIndex
                    )();
                    await loadPresets();
                } catch (error) {
                    console.error('Failed to move champion:', error);
                }
            }
        });
    });
}

function openChampionModal(presetType) {
    currentPresetType = presetType;
    championModal.classList.remove('hidden');
    championSearch.value = '';
    renderChampionGrid();
    championSearch.focus();
}

function closeChampionModal() {
    championModal.classList.add('hidden');
    currentPresetType = null;
}

function renderChampionGrid() {
    const searchTerm = championSearch.value.toLowerCase();
    const currentList = currentPresetType === 'pick'
        ? (currentPresets[currentPresetRole] || [])
        : (currentPresets[`${currentPresetRole}_ban`] || []);
    const currentIds = new Set(currentList.map(c => c.id));

    const filtered = allChampions.filter(champ =>
        champ.name.toLowerCase().includes(searchTerm) ||
        (champ.alias && champ.alias.toLowerCase().includes(searchTerm))
    );

    if (filtered.length === 0) {
        championList.innerHTML = '<p class="placeholder">Чемпионы не найдены</p>';
        return;
    }

    let html = '';
    filtered.forEach(champ => {
        const isSelected = currentIds.has(champ.id);
        const selectedClass = isSelected ? 'selected' : '';
        html += `
            <div class="champion-item ${selectedClass}"
                 onclick="selectChampion(${champ.id}, '${champ.name.replace(/'/g, "\\'")}', ${isSelected})">
                <span class="name">${champ.name}</span>
            </div>
        `;
    });

    championList.innerHTML = html;
}

function filterChampions() {
    renderChampionGrid();
}

async function selectChampion(championId, championName, isSelected) {
    try {
        if (isSelected) {
            await eel.remove_champion_from_preset(currentPresetRole, currentPresetType, championId)();
        } else {
            await eel.add_champion_to_preset(currentPresetRole, currentPresetType, championId, championName)();
        }
        await loadPresets();
        renderChampionGrid();
    } catch (error) {
        console.error('Failed to update preset:', error);
    }
}

async function removeChampion(championId, presetType) {
    try {
        await eel.remove_champion_from_preset(currentPresetRole, presetType, championId)();
        await loadPresets();
    } catch (error) {
        console.error('Failed to remove champion:', error);
    }
}

async function importPresetsFromFile() {
    try {
        await eel.import_presets_from_file()();
        await loadPresets();
        addLog('Presets imported from file', 'success');
    } catch (error) {
        console.error('Failed to import presets:', error);
        addLog('Failed to import presets', 'error');
    }
}

// ==================== Bot Functions ====================

async function startBot() {
    try {
        await eel.start_bot()();
        isRunning = true;
        addLog('Bot started', 'info');
    } catch (error) {
        addLog('Failed to start: ' + error, 'error');
    }
}

async function updateSettings() {
    const settings = {
        auto_accept: autoAcceptCheckbox.checked,
        auto_ban: autoBanCheckbox.checked,
        auto_pick: autoPickCheckbox.checked
    };

    try {
        await eel.update_settings(settings)();
    } catch (error) {
        console.error('Failed to update settings:', error);
    }
}

// ==================== Exposed to Python ====================

eel.expose(updateConnectionStatus);
function updateConnectionStatus(connected, text) {
    connectionStatus.className = 'status ' + (connected ? 'connected' : 'disconnected');
    statusText.textContent = text;
}

eel.expose(updatePhase);
function updatePhase(phase) {
    currentPhase.textContent = phase || '-';
}

eel.expose(updateRole);
function updateRole(role) {
    currentRole.textContent = role || '-';
}

eel.expose(addLog);
function addLog(message, type = 'info') {
    const entry = document.createElement('div');
    entry.className = 'log-entry ' + type;

    const time = new Date().toLocaleTimeString('ru-RU');
    entry.textContent = `[${time}] ${message}`;

    logContainer.appendChild(entry);
    logContainer.scrollTop = logContainer.scrollHeight;

    while (logContainer.children.length > 100) {
        logContainer.removeChild(logContainer.firstChild);
    }
}

eel.expose(updateChampionsTable);
function updateChampionsTable(data) {
    if (!championsTable) return;

    if (!data || Object.keys(data).length === 0) {
        championsTable.innerHTML = '<p class="placeholder">Нет пресетов</p>';
        return;
    }

    const roles = [
        { key: 'top', name: 'Топ' },
        { key: 'jungle', name: 'Лес' },
        { key: 'middle', name: 'Мид' },
        { key: 'bottom', name: 'Бот' },
        { key: 'utility', name: 'Саппорт' }
    ];

    let html = '<div class="presets-overview">';

    roles.forEach(role => {
        const picks = data[role.key] || [];
        const bans = data[`${role.key}_ban`] || [];

        html += `
            <div class="role-presets-row">
                <div class="role-name">${role.name}</div>
                <div class="role-picks">
                    <span class="label">Пики:</span>
                    <span class="champions-list">${picks.length > 0 ? picks.map(c => c.name).join(', ') : '-'}</span>
                </div>
                <div class="role-bans">
                    <span class="label">Баны:</span>
                    <span class="champions-list">${bans.length > 0 ? bans.map(c => c.name).join(', ') : '-'}</span>
                </div>
            </div>
        `;
    });

    html += '</div>';
    championsTable.innerHTML = html;
}

async function loadPresetsForHomePage() {
    try {
        const presets = await eel.get_all_presets()();
        updateChampionsTable(presets);
    } catch (error) {
        console.error('Failed to load presets for home page:', error);
        if (championsTable) {
            championsTable.innerHTML = '<p class="placeholder">Ошибка загрузки пресетов</p>';
        }
    }
}

eel.expose(updateLobbyFull);
function updateLobbyFull(data) {
    const now = new Date().toLocaleTimeString('ru-RU');
    lobbyUpdateTime.textContent = `Обновлено: ${now}`;

    if (!data || !data.members || data.members.length === 0) {
        lobbyStatus.className = 'lobby-status';
        lobbyStatus.innerHTML = '<p class="placeholder">Лобби не найдено</p>';
        lobbyQueue.textContent = '-';
        lobbyMembers.innerHTML = `
            <div class="no-lobby-message">
                <div class="icon">&#128101;</div>
                <p>Нет данных о лобби</p>
                <p style="font-size: 0.85rem; margin-top: 10px;">Создайте или присоединитесь к лобби в клиенте игры</p>
            </div>
        `;
        return;
    }

    let statusClass = 'lobby-status';
    let lobbyStatusText = 'В лобби';

    if (data.phase === 'Matchmaking') {
        statusClass += ' searching';
        lobbyStatusText = 'Поиск матча...';
    } else if (data.phase === 'ChampSelect') {
        statusClass += ' in-game';
        lobbyStatusText = 'Выбор чемпионов';
    } else if (data.phase === 'InProgress') {
        statusClass += ' in-game';
        lobbyStatusText = 'В игре';
    } else {
        statusClass += ' in-lobby';
    }

    lobbyStatus.className = statusClass;
    lobbyStatus.innerHTML = `<span>${lobbyStatusText}</span>`;
    lobbyQueue.textContent = data.queueName || 'Не выбран';

    if (data.members.length === 0) {
        lobbyMembers.innerHTML = '<p class="placeholder">Нет участников</p>';
        return;
    }

    let html = '';
    data.members.forEach((member, index) => {
        const isLeader = member.isLeader;
        const leaderBadge = isLeader ? '<span class="leader-badge">&#128081;</span>' : '';
        const readyIcon = member.ready ? '&#10004;' : '&#9203;';
        const memberClass = isLeader ? 'lobby-member leader' : 'lobby-member';

        html += `
            <div class="${memberClass}">
                <div class="member-index">${index + 1}</div>
                <div class="member-info">
                    <div class="member-name">${leaderBadge}${member.name}</div>
                    <div class="member-ranks">
                        <span class="rank-item">
                            <span class="rank-label">Solo:</span>
                            <span>${member.soloRank || 'Unranked'}</span>
                        </span>
                        <span class="rank-item">
                            <span class="rank-label">Flex:</span>
                            <span>${member.flexRank || 'Unranked'}</span>
                        </span>
                    </div>
                </div>
                <div class="member-status">${readyIcon}</div>
            </div>
        `;
    });

    lobbyMembers.innerHTML = html;
}

eel.expose(updateLobby);
function updateLobby(members) {
    updateLobbyFull({ members: members, phase: null, queueName: null });
}

eel.expose(setButtonsState);
function setButtonsState(running) {
    isRunning = running;
}
