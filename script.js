document.addEventListener('DOMContentLoaded', () => {
    // 获取DOM元素
    const modeButtons = document.querySelectorAll('.mode-btn');
    const inputTextarea = document.querySelector('.text-area-container:first-child textarea');
    const outputTextarea = document.querySelector('.text-area-container:last-child textarea');
    const clearBtn = document.getElementById('clear-btn');
    const pasteBtn = document.getElementById('paste-btn');
    const humanizeBtn = document.getElementById('humanize-btn');
    const copyBtn = document.querySelector('.copy-btn');
    const wordCounts = document.querySelectorAll('.word-count');
    const loadingOverlay = document.querySelector('.loading-overlay');

    // 复制文本的通用函数
    async function copyText(text, button) {
        try {
            await navigator.clipboard.writeText(text);
            button.classList.add('copied');
            const prevHtml = button.innerHTML;
            button.innerHTML = `
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="20 6 9 17 4 12"></polyline>
                </svg>
                <span>已复制</span>
            `;
            setTimeout(() => {
                button.classList.remove('copied');
                button.innerHTML = prevHtml;
            }, 2000);
        } catch (err) {
            alert('无法复制到剪贴板，请手动复制。');
        }
    }

    // 更新字数统计
    function updateWordCount(textarea, countElement) {
        const text = textarea.value;
        const wordCount = text.trim() ? text.trim().split(/\s+/).length : 0;
        countElement.textContent = `${wordCount} words`;
    }

    // 计算预计等待时间
    function calculateWaitTime(text) {
        // 基础处理时间（秒）
        const baseTime = 5;
        // 根据文本长度增加时间
        const wordsCount = text.trim().split(/\s+/).length;
        const lengthTime = Math.ceil(wordsCount / 100) * 2; // 每100字增加2秒
        // 总时间
        const totalTime = baseTime + lengthTime;
        return Math.min(totalTime, 30); // 最长显示30秒
    }

    // 更新等待时间显示
    function updateWaitingTime(seconds) {
        const loadingTime = document.querySelector('.loading-time');
        loadingTime.textContent = `预计等待时间：${seconds} 秒`;
    }

    // 显示加载动画
    function showLoading(waitTime) {
        loadingOverlay.classList.add('active');
        outputTextarea.value = '';  // 清空输出框
        updateWaitingTime(waitTime);
        
        // 倒计时更新
        let timeLeft = waitTime;
        const countdownInterval = setInterval(() => {
            timeLeft--;
            if (timeLeft > 0) {
                updateWaitingTime(timeLeft);
            } else {
                clearInterval(countdownInterval);
            }
        }, 1000);
    }

    // 隐藏加载动画
    function hideLoading() {
        loadingOverlay.classList.remove('active');
    }

    // 监听输入框变化
    inputTextarea.addEventListener('input', () => {
        updateWordCount(inputTextarea, wordCounts[0]);
    });

    // 监听输出框变化
    outputTextarea.addEventListener('input', () => {
        updateWordCount(outputTextarea, wordCounts[1]);
    });

    // 模式选择功能
    modeButtons.forEach(button => {
        button.addEventListener('click', () => {
            modeButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
        });
    });

    // 清空功能
    clearBtn.addEventListener('click', () => {
        inputTextarea.value = '';
        updateWordCount(inputTextarea, wordCounts[0]);
    });

    // 粘贴功能
    pasteBtn.addEventListener('click', async () => {
        try {
            const text = await navigator.clipboard.readText();
            inputTextarea.value = text;
            updateWordCount(inputTextarea, wordCounts[0]);
        } catch (err) {
            alert('无法访问剪贴板，请手动粘贴文本。');
        }
    });

    // 复制功能
    copyBtn.addEventListener('click', () => {
        copyText(outputTextarea.value, copyBtn);
    });

    // 显示错误消息
    function showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="8" x2="12" y2="12"></line>
                <line x1="12" y1="16" x2="12.01" y2="16"></line>
            </svg>
            <span>${message}</span>
        `;
        document.body.appendChild(errorDiv);
        
        // 3秒后自动消失
        setTimeout(() => {
            errorDiv.classList.add('fade-out');
            setTimeout(() => errorDiv.remove(), 300);
        }, 3000);
    }

    // 检查文本长度
    function validateText(text) {
        const MAX_LENGTH = 5000;
        if (text.length > MAX_LENGTH) {
            throw new Error(`文本长度超过限制（最大${MAX_LENGTH}字符）`);
        }
        return true;
    }

    // 人性化处理功能
    humanizeBtn.addEventListener('click', async () => {
        const text = inputTextarea.value;
        if (!text.trim()) {
            showError('请先输入或粘贴需要处理的文本');
            return;
        }

        try {
            // 验证文本长度
            validateText(text);
            
            // 计算等待时间并显示加载状态
            const waitTime = calculateWaitTime(text);
            humanizeBtn.disabled = true;
            humanizeBtn.innerHTML = `
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="loading-icon">
                    <line x1="12" y1="2" x2="12" y2="6"></line>
                    <line x1="12" y1="18" x2="12" y2="22"></line>
                    <line x1="4.93" y1="4.93" x2="7.76" y2="7.76"></line>
                    <line x1="16.24" y1="16.24" x2="19.07" y2="19.07"></line>
                    <line x1="2" y1="12" x2="6" y2="12"></line>
                    <line x1="18" y1="12" x2="22" y2="12"></line>
                    <line x1="4.93" y1="19.07" x2="7.76" y2="16.24"></line>
                    <line x1="16.24" y1="7.76" x2="19.07" y2="4.93"></line>
                </svg>
                <span>处理中...</span>
            `;
            showLoading(waitTime);
            
            const processedText = await humanizeText(text);
            outputTextarea.value = processedText;
            updateWordCount(outputTextarea, wordCounts[1]);
        } catch (error) {
            showError(error.message || '处理文本时出现错误，请稍后重试');
            console.error('处理错误:', error);
        } finally {
            hideLoading();
            humanizeBtn.disabled = false;
            humanizeBtn.innerHTML = `
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M20.24 12.24a6 6 0 0 0-8.49-8.49L5 10.5V19h8.5z"></path>
                    <line x1="16" y1="8" x2="2" y2="22"></line>
                    <line x1="17.5" y1="15" x2="9" y2="15"></line>
                </svg>
                <span>开始转换</span>
            `;
        }
    });
});

// 文本处理函数
async function humanizeText(text) {
    const mode = document.querySelector('.mode-btn.active').textContent.toLowerCase();
    
    try {
        const response = await fetch('http://localhost:5000/api/humanize', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({
                text,
                mode
            })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || '服务器响应错误');
        }
        
        if (!data.success) {
            throw new Error(data.error || '处理失败');
        }
        
        return data.result;
    } catch (error) {
        console.error('API调用错误:', error);
        throw new Error(error.message || '处理文本时出现错误，请稍后重试');
    }
} 