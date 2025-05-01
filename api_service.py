import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv
import requests
import re
import time
from datetime import datetime, timedelta
from collections import defaultdict
import json

# 加载环境变量
load_dotenv()

# 初始化Flask应用
app = Flask(__name__, static_url_path='', static_folder='./')

# 添加根路由，提供index.html
@app.route('/')
def index():
    return app.send_static_file('index.html')

# CORS配置
CORS(app, resources={
    r"/api/*": {
        "origins": [
            "http://localhost:5000",
            "http://127.0.0.1:5000",
            "https://humanizadordeia.top",
            "https://humanize-alpha.vercel.app",
            "https://humanize-sundays-projects-f9714b4b.vercel.app"
        ],
        "methods": ["POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "expose_headers": ["Content-Type"],
        "supports_credentials": True,
        "max_age": 600
    }
})

# 初始化限制器
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["100 per day", "10 per hour"],
    storage_uri="memory://"
)

# 配置API密钥
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
DEEPSEEK_API_BASE = os.getenv('DEEPSEEK_API_BASE', 'https://api.deepseek.com/v1/chat/completions')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
# 使用OpenRouter的Gemini模型
DEFAULT_MODEL = 'openrouter'

# 安全配置
MAX_TEXT_LENGTH = 5000  # 最大文本长度
MAX_REQUESTS_PER_IP = 100  # 每个IP每天的最大请求次数
RATE_LIMIT_RESET_INTERVAL = 86400  # 24小时，以秒为单位

# IP请求计数器
ip_request_count = defaultdict(int)
ip_last_reset = defaultdict(float)

def check_ip_limit():
    """检查IP请求限制"""
    ip = get_remote_address()
    current_time = time.time()
    
    # 检查是否需要重置计数器
    if current_time - ip_last_reset[ip] >= RATE_LIMIT_RESET_INTERVAL:
        ip_request_count[ip] = 0
        ip_last_reset[ip] = current_time
    
    # 检查请求次数
    if ip_request_count[ip] >= MAX_REQUESTS_PER_IP:
        remaining_time = RATE_LIMIT_RESET_INTERVAL - (current_time - ip_last_reset[ip])
        raise Exception(f"已达到每日请求限制，请在{int(remaining_time/3600)}小时后重试")
    
    ip_request_count[ip] += 1

def validate_text(text):
    """验证文本是否符合要求"""
    if len(text) > MAX_TEXT_LENGTH:
        raise Exception(f"文本长度超过限制（最大{MAX_TEXT_LENGTH}字符）")
    
    # 检查是否包含敏感内容
    sensitive_patterns = [
        r'(hack|crack|exploit)',
        r'(password|密码)\s*[=:]\s*\S+',
        r'(api[-_]?key|token)\s*[=:]\s*\S+'
    ]
    
    for pattern in sensitive_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            raise Exception("检测到敏感内容，请修改后重试")

def log_request(ip, text_length, mode, model=None):
    """记录请求信息"""
    if model is None:
        model = DEFAULT_MODEL
        
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] IP: {ip}, Length: {text_length}, Mode: {mode}, Model: {model}\n"
    
    with open("request_log.txt", "a", encoding="utf-8") as f:
        f.write(log_entry)

def detect_language(text):
    """
    检测文本语言
    优先级：西班牙语 > 英语 > 中文
    """
    # 检测西班牙语特征（包括重音符号和特殊标点）
    spanish_chars = set('áéíóúüñ¿¡àèìòùâêîôûäëïöüãõ')
    spanish_words = {'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas', 'y', 'o', 'pero', 'porque', 'cuando', 'donde', 'como'}
    
    # 将文本分割成单词
    words = set(text.lower().split())
    
    # 如果包含西班牙语特殊字符或常用词，判定为西班牙语
    if any(char in spanish_chars for char in text.lower()) or any(word in spanish_words for word in words):
        return 'es'
    
    # 检测英语特征（基本拉丁字母）
    english_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ')
    text_chars = set(text.replace(' ', ''))
    if text_chars.issubset(english_chars):
        return 'en'
    
    # 检测中文字符
    if any('\u4e00' <= char <= '\u9fff' for char in text):
        return 'zh'
    
    # 默认使用西班牙语
    return 'es'

def get_prompt_by_mode_and_language(mode, language, text):
    """
    根据模式和语言获取相应的提示词
    """
    base_prompts = {
        'es': {
            'free': "Por favor, reescribe el siguiente texto en español para hacerlo más natural y humano, evitando la detección de IA pero manteniendo el significado original. Asegúrate de mantener un estilo fluido y natural:",
            'standard': "Por favor, reescribe el siguiente texto en español usando un estilo estándar y profesional, manteniendo un tono equilibrado y formal:",
            'academic': "Por favor, reescribe el siguiente texto en español usando un estilo académico y formal, adecuado para publicaciones académicas y documentos científicos:",
            'simple': "Por favor, simplifica el siguiente texto en español para hacerlo más fácil de entender, usando un lenguaje claro y directo, manteniendo la esencia del mensaje:",
            'formal': "Por favor, reescribe el siguiente texto en español usando un estilo formal y profesional, adecuado para comunicaciones empresariales y documentos oficiales:",
            'informal': "Por favor, reescribe el siguiente texto en español usando un estilo casual y conversacional, manteniendo un tono amigable y cercano:",
            'expand': "Por favor, expande el siguiente texto en español, agregando más detalles, ejemplos y explicaciones mientras mantienes un estilo natural y coherente:",
            'shorten': "Por favor, resume el siguiente texto en español, manteniendo los puntos principales y la información esencial mientras reduces su longitud:"
        },
        'en': {
            'free': "Please rewrite the following English text to make it more natural and human-like, while avoiding AI detection:",
            'standard': "Please rewrite the following English text using a standard, professional style with a balanced tone:",
            'academic': "Please rewrite the following English text using an academic and formal style suitable for scholarly publications:",
            'simple': "Please simplify the following English text to make it easier to understand, using clear and direct language:",
            'formal': "Please rewrite the following English text using a formal, professional style suitable for business communications:",
            'informal': "Please rewrite the following English text using a casual, conversational style while maintaining a friendly tone:",
            'expand': "Please expand the following English text by adding more details and explanations while maintaining a natural style:",
            'shorten': "Please summarize the following English text, keeping the main points while reducing length:"
        },
        'zh': {
            'free': "请将以下中文文本改写得更加自然、人性化，同时避免AI检测：",
            'standard': "请使用标准的专业风格改写以下中文文本，保持平衡的语气：",
            'academic': "请使用学术和正式的风格改写以下中文文本，适合学术出版物：",
            'simple': "请简化以下中文文本，使用清晰直接的语言，使其更容易理解：",
            'formal': "请使用正式的专业风格改写以下中文文本，适合商务沟通：",
            'informal': "请使用轻松随意的对话风格改写以下中文文本，保持友好的语气：",
            'expand': "请扩展以下中文文本，添加更多细节和解释，同时保持自然的风格：",
            'shorten': "请总结以下中文文本，保持主要观点的同时减少长度："
        }
    }

    # 获取对应语言和模式的提示词
    prompts = base_prompts.get(language, base_prompts['es'])
    prompt = prompts.get(mode, prompts['free'])
    
    return prompt + "\n\n" + text

def get_system_prompt(language):
    """根据语言获取系统提示词"""
    if language == 'zh':
        return "你是一个专业的文本改写助手，善于将AI生成的文本改写得更自然、更人性化，同时确保不会被AI检测工具识别。请始终保持输出为中文。"
    else:
        return "You are a professional text rewriting assistant, skilled at making AI-generated text more natural and human-like while ensuring it won't be detected by AI detection tools. Always keep the output in English."

def call_openrouter_api(prompt):
    """调用OpenRouter API"""
    try:
        language = detect_language(prompt)
        print(f"[OpenRouter] 准备调用API，语言: {language}, 模型: google/gemini-2.0-flash-001")
        
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://humanizadordeia.top",  # 你的网站URL
            "X-Title": "Humanize AI Text"  # 应用名称
        }
        
        data = {
            "model": "google/gemini-2.0-flash-001",  # 使用OpenRouter上的Gemini模型
            "messages": [
                {"role": "system", "content": "你是一个专业的文本改写助手。请直接输出改写后的文本，不要添加任何评论、解释或其他内容。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 2000,
            # 添加数据隐私策略设置，允许OpenRouter使用数据进行训练
            "data_usage_policy": {
                "allow_prompt_training": True,
                "allow_response_training": True
            }
        }
        
        print(f"[OpenRouter] 请求数据: {json.dumps(data, ensure_ascii=False)[:200]}...")
        
        api_url = "https://openrouter.ai/api/v1/chat/completions"
        print(f"[OpenRouter] 发送请求到: {api_url}")
        
        response = requests.post(
            api_url,
            headers=headers,
            json=data,
            timeout=30,
            verify=True
        )
        
        print(f"[OpenRouter] 收到响应，状态码: {response.status_code}")
        
        if response.status_code != 200:
            error_message = f"OpenRouter API调用失败: HTTP {response.status_code}"
            try:
                error_detail = response.json()
                error_detail_str = json.dumps(error_detail, ensure_ascii=False)
                print(f"[OpenRouter] 错误详情: {error_detail_str}")
                error_message += f" - {error_detail.get('error', {}).get('message', str(error_detail))}"
            except Exception as e:
                response_text = response.text[:500]  # 限制长度，避免日志过大
                print(f"[OpenRouter] 解析响应JSON失败: {str(e)}, 响应内容: {response_text}")
                error_message += f" - {response.text}"
            raise Exception(error_message)
        
        result = response.json()
        print(f"[OpenRouter] 成功获取响应: {json.dumps(result, ensure_ascii=False)[:200]}...")
        
        # 获取API返回的文本内容
        content = result['choices'][0]['message']['content']
        content_preview = content[:100] + "..." if len(content) > 100 else content
        print(f"[OpenRouter] 响应内容预览: {content_preview}")
        
        # 清理文本，移除可能的前缀说明和后缀评论
        content = content.strip()
        # 如果内容以引号开始和结束，移除引号
        if (content.startswith('"') and content.endswith('"')) or \
           (content.startswith("'") and content.endswith("'")):
            content = content[1:-1]
        
        return content
        
    except requests.exceptions.Timeout:
        print("[OpenRouter] API调用超时")
        raise Exception("API调用超时，请稍后重试")
    except requests.exceptions.RequestException as e:
        print(f"[OpenRouter] 网络请求错误: {str(e)}")
        raise Exception(f"网络请求错误: {str(e)}")
    except Exception as e:
        print(f"[OpenRouter] 其他错误: {str(e)}")
        raise

def call_deepseek_api(prompt):
    """调用DeepSeek API"""
    try:
        language = detect_language(prompt)
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "你是一个专业的文本改写助手。请直接输出改写后的文本，不要添加任何评论、解释或其他内容。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 2000,
            "stream": False
        }
        
        response = requests.post(
            DEEPSEEK_API_BASE,
            headers=headers,
            json=data,
            timeout=30,
            verify=True
        )
        
        if response.status_code != 200:
            error_message = f"DeepSeek API调用失败: HTTP {response.status_code}"
            try:
                error_detail = response.json()
                error_message += f" - {error_detail.get('error', {}).get('message', str(error_detail))}"
            except:
                error_message += f" - {response.text}"
            raise Exception(error_message)
        
        result = response.json()
        # 获取API返回的文本内容
        content = result['choices'][0]['message']['content']
        
        # 清理文本，移除可能的前缀说明和后缀评论
        content = content.strip()
        # 如果内容以引号开始和结束，移除引号
        if (content.startswith('"') and content.endswith('"')) or \
           (content.startswith("'") and content.endswith("'")):
            content = content[1:-1]
        
        return content
        
    except requests.exceptions.Timeout:
        raise Exception("API调用超时，请稍后重试")
    except requests.exceptions.RequestException as e:
        raise Exception(f"网络请求错误: {str(e)}")
    except Exception as e:
        raise

def call_ai_api(prompt):
    """根据环境变量中配置的默认模型选择API"""
    if DEFAULT_MODEL == 'openrouter':
        return call_openrouter_api(prompt)
    else:
        return call_deepseek_api(prompt)

@app.route('/api/humanize', methods=['POST', 'OPTIONS'])
@limiter.limit("10 per minute")  # 添加每分钟请求限制
def humanize_text():
    if request.method == 'OPTIONS':
        return '', 204  # 返回成功状态码，但没有内容
    
    try:
        # 检查IP限制
        check_ip_limit()
        
        data = request.json
        text = data.get('text')
        
        # 获取并清理模式参数
        raw_mode = data.get('mode', 'free')
        # 如果模式值包含空格或非ASCII字符，只取第一部分
        mode = raw_mode.split()[0].lower() if raw_mode else 'free'
        
        # 添加模式参数的详细日志，包括原始数据内容
        print(f"[Flask] 接收到原始模式参数: '{raw_mode}', 处理后: '{mode}'")
        print(f"[Flask] 原始请求数据: {json.dumps(data, ensure_ascii=False)}")
        
        # 验证模式参数是否有效
        valid_modes = ['free', 'standard', 'academic', 'simple', 'formal', 'informal', 'expand', 'shorten']
        if mode not in valid_modes:
            print(f"[Flask] 警告: 接收到无效的模式参数 '{mode}'，使用默认值 'free'")
            mode = 'free'
        else:
            print(f"[Flask] 使用有效的模式参数: '{mode}'")
        
        if not text:
            return jsonify({
                'success': False,
                'error': '请提供需要处理的文本'
            }), 400
            
        # 验证文本
        validate_text(text)
        
        # 记录请求
        log_request(get_remote_address(), len(text), mode)
        
        prompt = get_prompt_by_mode_and_language(mode, detect_language(text), text)
        
        try:
            result = call_ai_api(prompt)
            return jsonify({
                'success': True,
                'result': result
            })
        except Exception as e:
            print(f"API调用错误: {str(e)}")
            # 如果主要模型失败，尝试备用模型
            if DEFAULT_MODEL == 'openrouter' and DEEPSEEK_API_KEY:
                try:
                    print("OpenRouter API调用失败，尝试使用DeepSeek API...")
                    result = call_deepseek_api(prompt)
                    return jsonify({
                        'success': True,
                        'result': result,
                        'model_used': 'deepseek (fallback)'
                    })
                except Exception as fallback_error:
                    print(f"备用API调用也失败: {str(fallback_error)}")
            
            return jsonify({
                'success': False,
                'error': f'API调用失败: {str(e)}'
            }), 500
            
    except Exception as e:
        print(f"服务器错误: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 429 if "限制" in str(e) else 500

@app.route('/api/models', methods=['GET'])
def get_available_models():
    """获取可用的模型列表"""
    models = [
        {
            'id': 'openrouter', 
            'name': 'DeepSeek-R1 (OpenRouter)', 
            'description': '使用OpenRouter代理的DeepSeek-R1模型', 
            'default': DEFAULT_MODEL == 'openrouter'
        }
    ]
    
    # 如果有DeepSeek API密钥，添加DeepSeek模型
    if DEEPSEEK_API_KEY:
        models.append({
            'id': 'deepseek', 
            'name': 'DeepSeek Chat', 
            'description': '使用DeepSeek官方API', 
            'default': DEFAULT_MODEL == 'deepseek'
        })
    
    return jsonify({'models': models})

@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({
        'success': False,
        'error': '请求过于频繁，请稍后重试'
    }), 429

if __name__ == '__main__':
    app.run(debug=True, port=5000) 