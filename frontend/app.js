// ===== Configuration =====
const API_BASE_URL = 'http://127.0.0.1:8000/api/v1';

// ===== State Management =====
const state = {
    tasks: [],
    currentTaskId: null,
    currentVideoId: null,
    selectedFirstFrame: null,
    selectedLastFrame: null
};

// ===== Utility Functions =====
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

function formatDuration(seconds) {
    if (!seconds) return 'N/A';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function getStatusText(status) {
    const statusMap = {
        'active': '进行中',
        'completed': '已完成',
        'pending': '待处理',
        'processing': '处理中',
        'failed': '失败'
    };
    return statusMap[status] || status;
}

// ===== Toast Notifications =====
function showToast(message, type = 'info', title = '') {
    const toastContainer = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    const icons = {
        success: '<path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" stroke="currentColor" stroke-width="2"/>',
        error: '<path d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" stroke="currentColor" stroke-width="2"/>',
        warning: '<path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" stroke="currentColor" stroke-width="2"/>',
        info: '<path d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" stroke="currentColor" stroke-width="2"/>'
    };

    toast.innerHTML = `
        <svg class="toast-icon" viewBox="0 0 24 24" fill="none">
            ${icons[type]}
        </svg>
        <div class="toast-content">
            ${title ? `<div class="toast-title">${title}</div>` : ''}
            <div class="toast-message">${message}</div>
        </div>
        <button class="toast-close">
            <svg viewBox="0 0 24 24" fill="none">
                <path d="M6 18L18 6M6 6l12 12" stroke="currentColor" stroke-width="2"/>
            </svg>
        </button>
    `;

    toastContainer.appendChild(toast);

    toast.querySelector('.toast-close').addEventListener('click', () => {
        toast.remove();
    });

    setTimeout(() => {
        toast.style.animation = 'toastSlideIn 0.3s reverse';
        setTimeout(() => toast.remove(), 300);
    }, 5000);
}

// ===== API Functions =====
async function apiRequest(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            ...options,
            headers: {
                ...options.headers,
            }
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'API request failed');
        }

        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        showToast(error.message, 'error', 'API错误');
        throw error;
    }
}

// Task API
async function createTask(taskData) {
    return await apiRequest('/task/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(taskData)
    });
}

async function getTasks(user = null, skip = 0, limit = 100) {
    const params = new URLSearchParams({ skip, limit });
    if (user) params.append('user', user);
    return await apiRequest(`/task/?${params}`);
}

async function getTaskDetail(taskId) {
    return await apiRequest(`/task/${taskId}`);
}

// Video API
async function uploadVideo(file) {
    const formData = new FormData();
    formData.append('file', file);

    return await apiRequest('/video/upload', {
        method: 'POST',
        body: formData
    });
}

async function batchUploadVideos(files) {
    const formData = new FormData();
    files.forEach(file => {
        formData.append('files', file);
    });

    return await apiRequest('/video/batch-upload', {
        method: 'POST',
        body: formData
    });
}

async function getVideoStatus(videoId) {
    return await apiRequest(`/video/status/${videoId}`);
}

// Review API
async function getReviewData(videoId) {
    return await apiRequest(`/review/${videoId}`);
}

async function submitFrameMarking(videoId, markingData) {
    return await apiRequest(`/review/${videoId}/mark`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(markingData)
    });
}

// ===== Task Management =====
async function loadTasks() {
    try {
        const tasks = await getTasks();
        state.tasks = tasks;
        renderTasks(tasks);

        // Auto-select first task if none selected
        if (tasks.length > 0 && !state.currentTaskId) {
            selectTask(tasks[0].id);
        }
    } catch (error) {
        console.error('Failed to load tasks:', error);
        document.getElementById('task-selector').innerHTML = `
            <div class="empty-state" style="padding: var(--spacing-lg); text-align: center;">
                <p style="color: var(--text-tertiary); font-size: 0.875rem;">加载任务失败</p>
            </div>
        `;
    }
}

function renderTasks(tasks) {
    const taskSelector = document.getElementById('task-selector');

    if (tasks.length === 0) {
        taskSelector.innerHTML = `
            <div class="empty-state" style="padding: var(--spacing-lg); text-align: center;">
                <p style="color: var(--text-tertiary); font-size: 0.875rem;">暂无任务</p>
                <p style="color: var(--text-tertiary); font-size: 0.75rem; margin-top: 4px;">点击 + 创建新任务</p>
            </div>
        `;
        return;
    }

    taskSelector.innerHTML = tasks.map(task => `
        <div class="task-item ${state.currentTaskId === task.id ? 'active' : ''}" 
             onclick="selectTask('${task.id}')">
            <div class="task-item-header">
                <div class="task-item-name">${task.name}</div>
                <span class="task-item-badge">${getStatusText(task.status)}</span>
            </div>
            <div class="task-item-stats">
                <div class="task-item-stat">
                    <svg viewBox="0 0 24 24" fill="none" style="width: 12px; height: 12px;">
                        <path d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" stroke="currentColor" stroke-width="2"/>
                    </svg>
                    ${task.total_videos} 个视频
                </div>
                <div class="task-item-stat">
                    <svg viewBox="0 0 24 24" fill="none" style="width: 12px; height: 12px;">
                        <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" stroke="currentColor" stroke-width="2"/>
                    </svg>
                    ${task.completed_videos} 已完成
                </div>
            </div>
        </div>
    `).join('');
}

async function selectTask(taskId) {
    state.currentTaskId = taskId;
    state.currentVideoId = null;

    // Update UI
    document.querySelectorAll('.task-item').forEach(item => {
        item.classList.remove('active');
    });
    event.currentTarget?.classList.add('active');

    // Load task videos
    await loadTaskVideos(taskId);

    // Clear frame display
    clearFrameDisplay();
}

async function loadTaskVideos(taskId) {
    try {
        const taskDetail = await getTaskDetail(taskId);
        renderVideos(taskDetail.videos || []);
    } catch (error) {
        console.error('Failed to load task videos:', error);
        document.getElementById('video-list').innerHTML = `
            <div class="empty-state" style="padding: var(--spacing-lg); text-align: center;">
                <p style="color: var(--text-tertiary); font-size: 0.875rem;">加载视频失败</p>
            </div>
        `;
    }
}

function renderVideos(videos) {
    const videoList = document.getElementById('video-list');

    if (videos.length === 0) {
        videoList.innerHTML = `
            <div class="empty-state" style="padding: var(--spacing-lg); text-align: center;">
                <p style="color: var(--text-tertiary); font-size: 0.875rem;">该任务暂无视频</p>
                <p style="color: var(--text-tertiary); font-size: 0.75rem; margin-top: 4px;">点击 + 上传视频</p>
            </div>
        `;
        return;
    }

    videoList.innerHTML = videos.map(video => `
        <div class="video-item ${state.currentVideoId === video.video_id ? 'active' : ''}" 
             onclick="selectVideo('${video.video_id}')">
            <div class="video-item-thumbnail">
                ${video.first_frame_url ?
            `<img src="${video.first_frame_url}" alt="${video.video_filename}">` :
            `<div class="video-item-placeholder">
                        <svg viewBox="0 0 24 24" fill="none">
                            <path d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" stroke="currentColor" stroke-width="2"/>
                        </svg>
                    </div>`
        }
            </div>
            <div class="video-item-info">
                <div class="video-item-name" title="${video.video_filename || 'Unknown'}">${video.video_filename || 'Unknown'}</div>
                <div class="video-item-meta">
                    <div class="video-item-status">
                        <span class="status-dot ${video.video_status}"></span>
                        ${getStatusText(video.video_status)}
                    </div>
                    ${video.duration ? `<div>时长: ${formatDuration(video.duration)}</div>` : ''}
                    ${video.video_width && video.video_height ? `<div>${video.video_width}x${video.video_height}</div>` : ''}
                </div>
            </div>
        </div>
    `).join('');
}

async function selectVideo(videoId) {
    state.currentVideoId = videoId;

    // Update UI
    document.querySelectorAll('.video-item').forEach(item => {
        item.classList.remove('active');
    });
    event.currentTarget?.classList.add('active');

    // Load video frames
    await loadVideoFrames(videoId);
}

async function loadVideoFrames(videoId) {
    const frameDisplay = document.getElementById('frame-display');
    const contentTitle = document.getElementById('content-title');
    const contentSubtitle = document.getElementById('content-subtitle');
    const contentActions = document.getElementById('content-actions');

    // Show loading state
    frameDisplay.innerHTML = `
        <div class="empty-state">
            <div class="loading" style="width: 48px; height: 48px; border-width: 4px;"></div>
            <h3 style="margin-top: var(--spacing-lg);">加载中...</h3>
            <p>正在获取视频帧数据</p>
        </div>
    `;

    try {
        const reviewData = await getReviewData(videoId);

        // Update header
        contentTitle.textContent = reviewData.filename;
        contentSubtitle.textContent = `总帧数: ${reviewData.total_frames} | 已提取: ${reviewData.extracted_frames}`;

        // Add review button if needed
        if (reviewData.needs_review) {
            contentActions.innerHTML = `
                <button class="btn btn-primary" onclick="openReviewMode()">
                    <svg viewBox="0 0 24 24" fill="none">
                        <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" stroke="currentColor" stroke-width="2"/>
                    </svg>
                    开始审核
                </button>
            `;
        } else {
            contentActions.innerHTML = '';
        }

        // Render frames
        renderFrames(reviewData);

    } catch (error) {
        console.error('Failed to load video frames:', error);
        frameDisplay.innerHTML = `
            <div class="empty-state">
                <svg viewBox="0 0 24 24" fill="none">
                    <path d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" stroke="currentColor" stroke-width="2"/>
                </svg>
                <h3>加载失败</h3>
                <p>无法获取视频帧数据</p>
            </div>
        `;
    }
}

function renderFrames(reviewData) {
    const frameDisplay = document.getElementById('frame-display');

    let html = '<div class="frame-sections">';

    // Marked frames section
    if (reviewData.marked_first_frame && reviewData.marked_last_frame) {
        html += `
            <div class="frame-section">
                <div class="frame-section-header">
                    <div class="frame-section-title">
                        <svg viewBox="0 0 24 24" fill="none" style="width: 24px; height: 24px;">
                            <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" stroke="currentColor" stroke-width="2"/>
                        </svg>
                        已标记的首尾帧
                    </div>
                    ${reviewData.reviewed_by ? `<div class="frame-section-info">审核人: ${reviewData.reviewed_by}</div>` : ''}
                </div>
                <div class="frame-gallery">
                    ${renderFrameCard(reviewData.marked_first_frame, '首帧')}
                    ${renderFrameCard(reviewData.marked_last_frame, '尾帧')}
                </div>
            </div>
        `;
    }

    // First frame candidates
    if (reviewData.first_candidates && reviewData.first_candidates.length > 0) {
        html += `
            <div class="frame-section">
                <div class="frame-section-header">
                    <div class="frame-section-title">
                        首帧候选
                        <span class="frame-section-badge">${reviewData.first_candidates.length} 个候选</span>
                    </div>
                </div>
                <div class="frame-gallery">
                    ${reviewData.first_candidates.map(frame => renderFrameCard(frame)).join('')}
                </div>
            </div>
        `;
    }

    // Last frame candidates
    if (reviewData.last_candidates && reviewData.last_candidates.length > 0) {
        html += `
            <div class="frame-section">
                <div class="frame-section-header">
                    <div class="frame-section-title">
                        尾帧候选
                        <span class="frame-section-badge">${reviewData.last_candidates.length} 个候选</span>
                    </div>
                </div>
                <div class="frame-gallery">
                    ${reviewData.last_candidates.map(frame => renderFrameCard(frame)).join('')}
                </div>
            </div>
        `;
    }

    // All frames
    if (reviewData.all_frames && reviewData.all_frames.length > 0) {
        html += `
            <div class="frame-section">
                <div class="frame-section-header">
                    <div class="frame-section-title">
                        所有提取的帧
                        <span class="frame-section-badge">${reviewData.all_frames.length} 帧</span>
                    </div>
                </div>
                <div class="frame-gallery">
                    ${reviewData.all_frames.map(frame => renderFrameCard(frame)).join('')}
                </div>
            </div>
        `;
    }

    html += '</div>';
    frameDisplay.innerHTML = html;
}

function renderFrameCard(frame, label = null) {
    return `
        <div class="frame-item" data-frame-id="${frame.id}">
            <img src="${frame.url}" alt="Frame ${frame.frame_number}" loading="lazy">
            <div class="frame-info">
                ${label ? `<strong>${label}</strong><br>` : ''}
                帧 #${frame.frame_number}<br>
                ${frame.timestamp.toFixed(2)}s
                ${frame.confidence_score ? `<br>置信度: ${(frame.confidence_score * 100).toFixed(1)}%` : ''}
            </div>
        </div>
    `;
}

function clearFrameDisplay() {
    const frameDisplay = document.getElementById('frame-display');
    const contentTitle = document.getElementById('content-title');
    const contentSubtitle = document.getElementById('content-subtitle');
    const contentActions = document.getElementById('content-actions');

    contentTitle.textContent = '选择视频查看帧数据';
    contentSubtitle.textContent = '从左侧选择任务和视频';
    contentActions.innerHTML = '';

    frameDisplay.innerHTML = `
        <div class="empty-state">
            <svg viewBox="0 0 24 24" fill="none">
                <path d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" stroke="currentColor" stroke-width="2"/>
            </svg>
            <h3>暂无帧数据</h3>
            <p>请从左侧选择一个视频来查看其帧数据</p>
        </div>
    `;
}

// ===== Review Mode =====
function openReviewMode() {
    const modal = document.getElementById('review-modal');
    modal.classList.add('active');

    // Enable frame selection
    document.querySelectorAll('.frame-item').forEach(item => {
        item.style.cursor = 'pointer';
        item.addEventListener('click', handleFrameSelection);
    });
}

function handleFrameSelection(event) {
    const frameItem = event.currentTarget;
    const frameId = frameItem.dataset.frameId;
    const section = frameItem.closest('.frame-section');
    const sectionTitle = section.querySelector('.frame-section-title').textContent;

    if (sectionTitle.includes('首帧')) {
        state.selectedFirstFrame = frameId;
        section.querySelectorAll('.frame-item').forEach(item => item.classList.remove('selected'));
        frameItem.classList.add('selected');
    } else if (sectionTitle.includes('尾帧')) {
        state.selectedLastFrame = frameId;
        section.querySelectorAll('.frame-item').forEach(item => item.classList.remove('selected'));
        frameItem.classList.add('selected');
    }
}

async function submitReview() {
    const reviewerName = document.getElementById('reviewer-name').value;
    const reviewNotes = document.getElementById('review-notes').value;

    if (!reviewerName) {
        showToast('请输入审核人名称', 'warning');
        return;
    }

    if (!state.selectedFirstFrame || !state.selectedLastFrame) {
        showToast('请选择首帧和尾帧', 'warning');
        return;
    }

    try {
        await submitFrameMarking(state.currentVideoId, {
            first_frame_id: state.selectedFirstFrame,
            last_frame_id: state.selectedLastFrame,
            reviewer: reviewerName,
            review_notes: reviewNotes || null
        });

        showToast('审核提交成功', 'success');
        closeModal('review-modal');

        // Reload video frames
        await loadVideoFrames(state.currentVideoId);

        // Reset selection
        state.selectedFirstFrame = null;
        state.selectedLastFrame = null;
    } catch (error) {
        console.error('Failed to submit review:', error);
    }
}

// ===== Modal Functions =====
function openCreateTaskModal() {
    document.getElementById('create-task-modal').classList.add('active');
}

function openUploadVideoModal() {
    document.getElementById('upload-video-modal').classList.add('active');
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
}

// ===== File Upload Handling =====
let selectedFiles = [];

function handleFiles(files) {
    const uploadMode = document.querySelector('input[name="upload-mode"]:checked').value;
    const fileList = document.getElementById('file-list');

    if (uploadMode === 'single') {
        selectedFiles = [files[0]];
    } else {
        selectedFiles = Array.from(files);
    }

    if (selectedFiles.length > 0) {
        fileList.classList.add('has-files');
        fileList.innerHTML = selectedFiles.map((file, index) => `
            <div class="file-item">
                <div class="file-item-info">
                    <div class="file-item-icon">
                        <svg viewBox="0 0 24 24" fill="none">
                            <path d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" stroke="currentColor" stroke-width="2"/>
                        </svg>
                    </div>
                    <div class="file-item-details">
                        <h4>${file.name}</h4>
                        <p>${formatFileSize(file.size)}</p>
                    </div>
                </div>
                <button type="button" class="file-item-remove" onclick="removeFile(${index})">
                    <svg viewBox="0 0 24 24" fill="none">
                        <path d="M6 18L18 6M6 6l12 12" stroke="currentColor" stroke-width="2"/>
                    </svg>
                </button>
            </div>
        `).join('');
    }
}

function removeFile(index) {
    selectedFiles.splice(index, 1);
    handleFiles(selectedFiles);

    if (selectedFiles.length === 0) {
        document.getElementById('file-list').classList.remove('has-files');
    }
}

// ===== Initialization =====
document.addEventListener('DOMContentLoaded', () => {
    // Remove old navigation
    const navBtns = document.querySelectorAll('.nav-btn');
    navBtns.forEach(btn => btn.style.display = 'none');

    // Modal close buttons
    document.querySelectorAll('.modal-close, .modal-overlay').forEach(el => {
        el.addEventListener('click', (e) => {
            if (e.target === el) {
                el.closest('.modal').classList.remove('active');
            }
        });
    });

    // Create Task Form
    document.getElementById('create-task-form').addEventListener('submit', async (e) => {
        e.preventDefault();

        const taskData = {
            name: document.getElementById('task-name').value,
            description: document.getElementById('task-description').value || null,
            created_by: document.getElementById('task-creator').value
        };

        try {
            await createTask(taskData);
            showToast('任务创建成功', 'success');
            closeModal('create-task-modal');
            e.target.reset();
            loadTasks();
        } catch (error) {
            console.error('Failed to create task:', error);
        }
    });

    // Upload Video Form
    const uploadForm = document.getElementById('upload-video-form');
    const fileInput = document.getElementById('video-files');
    const fileUploadArea = document.getElementById('file-upload-area');
    const fileList = document.getElementById('file-list');

    uploadForm.querySelectorAll('input[name="upload-mode"]').forEach(radio => {
        radio.addEventListener('change', (e) => {
            fileInput.multiple = e.target.value === 'batch';
            selectedFiles = [];
            fileList.innerHTML = '';
            fileList.classList.remove('has-files');
        });
    });

    fileUploadArea.addEventListener('click', () => {
        fileInput.click();
    });

    fileInput.addEventListener('change', (e) => {
        handleFiles(e.target.files);
    });

    fileUploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        fileUploadArea.classList.add('drag-over');
    });

    fileUploadArea.addEventListener('dragleave', () => {
        fileUploadArea.classList.remove('drag-over');
    });

    fileUploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        fileUploadArea.classList.remove('drag-over');
        handleFiles(e.dataTransfer.files);
    });

    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        if (selectedFiles.length === 0) {
            showToast('请选择要上传的视频文件', 'warning');
            return;
        }

        const uploadMode = uploadForm.querySelector('input[name="upload-mode"]:checked').value;
        const submitBtn = document.getElementById('upload-submit-btn');

        submitBtn.disabled = true;
        submitBtn.innerHTML = '<div class="loading"></div> 上传中...';

        try {
            if (uploadMode === 'single') {
                await uploadVideo(selectedFiles[0]);
                showToast('视频上传成功', 'success');
            } else {
                await batchUploadVideos(selectedFiles);
                showToast(`成功上传 ${selectedFiles.length} 个视频`, 'success');
            }

            closeModal('upload-video-modal');
            uploadForm.reset();
            selectedFiles = [];
            fileList.innerHTML = '';
            fileList.classList.remove('has-files');

            // Reload current task videos
            if (state.currentTaskId) {
                await loadTaskVideos(state.currentTaskId);
            }
        } catch (error) {
            console.error('Failed to upload videos:', error);
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '开始上传';
        }
    });

    // Create task button
    document.getElementById('create-task-btn').addEventListener('click', openCreateTaskModal);

    // Upload video button
    document.getElementById('upload-video-btn').addEventListener('click', openUploadVideoModal);

    // Initial load
    loadTasks();
});
