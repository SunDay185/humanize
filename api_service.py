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

# 加载环境变量
load_dotenv()

# 初始化Flask应用
app = Flask(__name__)
CORS(app)  # 启用跨域支持

# 初始化限制器
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["100 per day", "10 per hour"],
    storage_uri="memory://"
)

# 配置API密钥
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
DEEPSEEK_API_BASE = os.getenv('DEEPSEEK_API_BASE')

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

def log_request(ip, text_length, mode):
    """记录请求信息"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] IP: {ip}, Length: {text_length}, Mode: {mode}\n"
    
    with open("request_log.txt", "a", encoding="utf-8") as f:
        f.write(log_entry)

def detect_language(text):
    """检测文本语言类型"""
    # 简单的语言检测：检查是否包含中文字符
    if re.search(r'[\u4e00-\u9fff]', text):
        return 'zh'
    # 如果不包含中文字符，默认为英文
    return 'en'

def get_prompt_by_mode(mode, text):
    """根据模式和语言生成对应的提示词"""
    language = detect_language(text)
    
    if language == 'zh':
        prompts = {
            'free': f"请帮我改写以下中文文本，使其更自然、更人性化，同时确保不会被AI检测工具识别。请保持输出为中文：\n{text}",
            'academic': f"请将以下中文文本改写成学术风格，使用更专业的词汇和表达方式，同时确保内容自然且不会被AI检测工具识别。请保持输出为中文：\n{text}",
            'formal': f"请将以下中文文本改写成正式的商务风格，使用得体的措辞，同时确保自然且不会被AI检测工具识别。请保持输出为中文：\n{text}",
            'simple': f"请将以下中文文本改写成简单易懂的风格，使用日常用语，同时确保自然且不会被AI检测工具识别。请保持输出为中文：\n{text}",
            'expand': f"请扩展以下中文文本，添加更多细节和解释，使其更丰富，同时确保自然且不会被AI检测工具识别。请保持输出为中文：\n{text}",
            'shorten': f"请精简以下中文文本，保持核心意思但使用更简洁的表达，同时确保自然且不会被AI检测工具识别。请保持输出为中文：\n{text}",
        }
    else:
        prompts = {
            'free': f"Please rewrite the following English text to make it more natural and human-like, ensuring it won't be detected by AI detection tools. Keep the output in English:\n{text}",
            'academic': f"Please rewrite the following English text in an academic style, using more professional vocabulary while ensuring it sounds natural and won't be detected by AI detection tools. Keep the output in English:\n{text}",
            'formal': f"Please rewrite the following English text in a formal business style, using appropriate expressions while ensuring it sounds natural and won't be detected by AI detection tools. Keep the output in English:\n{text}",
            'simple': f"Please rewrite the following English text in a simple and easy-to-understand style, using everyday language while ensuring it won't be detected by AI detection tools. Keep the output in English:\n{text}",
            'expand': f"Please expand the following English text by adding more details and explanations while ensuring it won't be detected by AI detection tools. Keep the output in English:\n{text}",
            'shorten': f"Please shorten the following English text while maintaining the core message and ensuring it won't be detected by AI detection tools. Keep the output in English:\n{text}",
        }
    
    return prompts.get(mode, prompts['free'])

def get_system_prompt(language):
    """根据语言获取系统提示词"""
    if language == 'zh':
        return "你是一个专业的文本改写助手，善于将AI生成的文本改写得更自然、更人性化，同时确保不会被AI检测工具识别。请始终保持输出为中文。"
    else:
        return "You are a professional text rewriting assistant, skilled at making AI-generated text more natural and human-like while ensuring it won't be detected by AI detection tools. Always keep the output in English."

def call_deepseek_api(prompt):
    """调用DeepSeek API"""
    try:
        language = detect_language(prompt)
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "deepseek-chat",  # 使用正确的模型名称
            "messages": [
                {"role": "system", "content": get_system_prompt(language)},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 2000,
            "stream": False
        }
        
        api_url = "https://api.deepseek.com/v1/chat/completions"  # 使用完整的URL
        print(f"正在调用DeepSeek API")  # 添加调试日志
        print(f"API请求URL: {api_url}")  # 添加URL日志
        print(f"请求头: {headers}")  # 添加请求头日志
        print(f"请求数据: {data}")  # 添加请求数据日志
        
        response = requests.post(
            api_url,
            headers=headers,
            json=data,
            timeout=30,
            verify=True  # 启用SSL验证
        )
        
        print(f"API响应状态码: {response.status_code}")  # 添加调试日志
        print(f"API响应内容: {response.text}")  # 添加响应内容日志
        
        if response.status_code != 200:
            error_message = f"API调用失败: HTTP {response.status_code}"
            try:
                error_detail = response.json()
                error_message += f" - {error_detail.get('error', {}).get('message', str(error_detail))}"
            except:
                error_message += f" - {response.text}"
            print(error_message)  # 添加调试日志
            raise Exception(error_message)
            
        result = response.json()
        return result['choices'][0]['message']['content']
    except requests.exceptions.Timeout:
        print("API调用超时")
        raise Exception("API调用超时，请稍后重试")
    except requests.exceptions.RequestException as e:
        print(f"网络请求错误: {str(e)}")
        raise Exception(f"网络请求错误: {str(e)}")
    except Exception as e:
        print(f"DeepSeek API调用错误: {str(e)}")
        raise

@app.route('/api/humanize', methods=['POST'])
@limiter.limit("10 per minute")  # 添加每分钟请求限制
def humanize_text():
    try:
        # 检查IP限制
        check_ip_limit()
        
        data = request.json
        text = data.get('text')
        mode = data.get('mode', 'free').lower()
        
        if not text:
            return jsonify({
                'success': False,
                'error': '请提供需要处理的文本'
            }), 400
            
        # 验证文本
        validate_text(text)
        
        # 记录请求
        log_request(get_remote_address(), len(text), mode)
        
        prompt = get_prompt_by_mode(mode, text)
        
        try:
            result = call_deepseek_api(prompt)
            return jsonify({
                'success': True,
                'result': result
            })
        except Exception as e:
            print(f"API调用错误: {str(e)}")
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

@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({
        'success': False,
        'error': '请求过于频繁，请稍后重试'
    }), 429

if __name__ == '__main__':
    app.run(debug=True, port=5000) 