document.addEventListener('DOMContentLoaded', () => {
    const modeButtons = document.querySelectorAll('.mode-btn');
    const inputTextarea = document.querySelector('.text-area-container:first-child textarea');
    const outputTextarea = document.querySelector('.output-container textarea');
    const humanizeBtn = document.getElementById('humanize-btn');
    const copyBtn = document.querySelector('.copy-btn');
    const clearBtn = document.getElementById('clear-btn');
    const pasteBtn = document.getElementById('paste-btn');
    const wordCounts = document.querySelectorAll('.word-count');

    // API URL配置
    const getApiUrl = () => {
        // 检查是否是本地文件系统
        if (window.location.protocol === 'file:') {
            return 'http://localhost:5000/api/humanize';
        }
        // 检查是否是本地开发服务器
        if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
            return 'http://localhost:5000/api/humanize';
        }
        // 生产环境使用相对路径，这样会自动使用当前域名
        return `${window.location.origin}/api/humanize`;
    };

    const API_URL = getApiUrl();

    // 显示开发环境提示
    if (window.location.protocol === 'file:' || window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        const warningDiv = document.createElement('div');
        warningDiv.className = 'warning-message';
        warningDiv.style.cssText = 'background-color: #fff3cd; color: #856404; padding: 10px; margin: 10px; border-radius: 4px; text-align: center;';
        warningDiv.innerHTML = `
            <strong>开发环境提示：</strong><br>
            请确保本地API服务器正在运行 (http://localhost:5000)<br>
            ${window.location.protocol === 'file:' ? '建议使用本地服务器打开页面，而不是直接打开文件。' : ''}
        `;
        document.body.insertBefore(warningDiv, document.body.firstChild);
    }

    // Mapeo de modos para la API
    const modeMapping = {
        'Gratuito': 'free',
        'Estándar': 'standard',
        'Académico': 'academic',
        'Sencillo': 'simple',
        'Formal': 'formal',
        'Informal': 'informal',
        'Expandir': 'expand',
        'Reducir': 'shorten'
    };



    
    // Mostrar mensaje de error
    function showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.textContent = message;
        document.querySelector('.editor-container').appendChild(errorDiv);
        
        setTimeout(() => {
            errorDiv.remove();
        }, 3000);
    }

    // Mostrar estado de carga
    function showLoading(waitTime) {
        const loadingOverlay = document.querySelector('.loading-overlay');
        const loadingText = document.querySelector('.loading-text');
        const loadingTime = document.querySelector('.loading-time');
        
        loadingOverlay.style.display = 'flex';
        loadingText.textContent = 'La IA está procesando y optimizando su texto...';
        
        if (waitTime) {
            let timeLeft = Math.ceil(waitTime);
            loadingTime.textContent = `Tiempo estimado de espera: ${timeLeft} segundos`;
            
            // Actualizar el tiempo restante cada segundo
            const countdownInterval = setInterval(() => {
                timeLeft--;
                if (timeLeft > 0) {
                    loadingTime.textContent = `Tiempo estimado de espera: ${timeLeft} segundos`;
                } else {
                    clearInterval(countdownInterval);
                }
            }, 1000);
        } else {
            loadingTime.textContent = 'Tiempo estimado de espera: calculando...';
        }
    }

    // Ocultar estado de carga
    function hideLoading() {
        const loadingOverlay = document.querySelector('.loading-overlay');
        loadingOverlay.style.display = 'none';
    }

    // Actualizar contador de palabras
    function updateWordCount(textarea, countElement) {
        const text = textarea.value;
        const wordCount = text.trim() ? text.trim().split(/\s+/).length : 0;
        countElement.textContent = `${wordCount} palabras`;
    }

    // Calcular tiempo de espera
    function calculateWaitTime(text) {
        const baseTime = 5; // Tiempo base en segundos
        const wordsCount = text.trim().split(/\s+/).length;
        const lengthTime = Math.ceil(wordsCount / 100) * 2; // 2 segundos adicionales por cada 100 palabras
        const totalTime = baseTime + lengthTime;
        return Math.min(totalTime, 30); // Máximo 30 segundos
    }

    // Validar longitud del texto
    function validateText(text) {
        const MAX_LENGTH = 5000;
        if (text.length > MAX_LENGTH) {
            throw new Error(`El texto excede el límite (máximo ${MAX_LENGTH} caracteres)`);
        }
        return true;
    }

    // Función de procesamiento de texto
    async function humanizeText(text) {
        const displayMode = document.querySelector('.mode-btn.active').textContent;
        const mode = modeMapping[displayMode] || 'free';
        
        try {
            const response = await fetch(API_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({
                    text: text,
                    mode: mode
                })
            });
            
            if (!response.ok) {
                if (response.status === 404) {
                    throw new Error('API服务器未找到，请确保后端服务正在运行');
                }
                const errorText = await response.text();
                let errorMessage;
                try {
                    const errorData = JSON.parse(errorText);
                    errorMessage = errorData.error || '服务器返回了一个错误';
                } catch {
                    errorMessage = `服务器错误 (${response.status}): ${errorText}`;
                }
                throw new Error(errorMessage);
            }
            
            const data = await response.json();
            if (!data.success) {
                throw new Error(data.error || '处理文本时发生错误');
            }
            
            return data.result;
        } catch (error) {
            console.error('API调用错误:', error);
            // 如果是网络错误，提供更友好的错误信息
            if (error.name === 'TypeError' && error.message === 'Failed to fetch') {
                throw new Error('无法连接到API服务器，请检查网络连接或联系管理员');
            }
            throw new Error(error.message || '处理文本时发生错误，请稍后重试');
        }
    }

    // Copiar texto
    copyBtn.addEventListener('click', () => {
        const text = outputTextarea.value;
        if (!text) {
            showError('No hay texto para copiar');
            return;
        }

        navigator.clipboard.writeText(text).then(() => {
            const originalContent = copyBtn.innerHTML;
            copyBtn.innerHTML = `
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="20 6 9 17 4 12"></polyline>
                </svg>
                <span>Copiado</span>
            `;
            
            setTimeout(() => {
                copyBtn.innerHTML = originalContent;
            }, 2000);
        }).catch(() => {
            showError('Error al copiar el texto');
        });
    });

    // Pegar texto
    pasteBtn.addEventListener('click', async () => {
        try {
            const text = await navigator.clipboard.readText();
            inputTextarea.value = text;
            updateWordCount(inputTextarea, wordCounts[0]);
        } catch (error) {
            showError('Error al pegar el texto. Por favor, pegue manualmente');
        }
    });

    // Limpiar texto
    clearBtn.addEventListener('click', () => {
        inputTextarea.value = '';
        outputTextarea.value = '';
        updateWordCount(inputTextarea, wordCounts[0]);
        updateWordCount(outputTextarea, wordCounts[1]);
    });

    // Selección de modo
    modeButtons.forEach(button => {
        button.addEventListener('click', () => {
            modeButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
        });
    });

    // Escuchar cambios en la entrada
    inputTextarea.addEventListener('input', () => {
        updateWordCount(inputTextarea, wordCounts[0]);
    });

    outputTextarea.addEventListener('input', () => {
        updateWordCount(outputTextarea, wordCounts[1]);
    });

    // Procesar texto
    humanizeBtn.addEventListener('click', async () => {
        const text = inputTextarea.value;
        if (!text.trim()) {
            showError('Por favor, ingrese o pegue el texto que desea procesar');
            return;
        }

        try {
            validateText(text);
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
                <span>Procesando...</span>
            `;
            showLoading(waitTime);
            
            const processedText = await humanizeText(text);
            outputTextarea.value = processedText;
            updateWordCount(outputTextarea, wordCounts[1]);
        } catch (error) {
            showError(error.message || 'Error al procesar el texto, por favor intente nuevamente');
            console.error('Error de procesamiento:', error);
        } finally {
            hideLoading();
            humanizeBtn.disabled = false;
            humanizeBtn.innerHTML = `
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M20.24 12.24a6 6 0 0 0-8.49-8.49L5 10.5V19h8.5z"></path>
                    <line x1="16" y1="8" x2="2" y2="22"></line>
                    <line x1="17.5" y1="15" x2="9" y2="15"></line>
                </svg>
                <span>Convertir</span>
            `;
        }
    });
}); 