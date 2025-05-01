from http.server import BaseHTTPRequestHandler
import json
import os
from dotenv import load_dotenv
import requests
import re
from datetime import datetime

# 加载环境变量
load_dotenv()

# 配置API密钥
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
# 从环境变量读取默认模型设置，默认为openrouter
DEFAULT_MODEL = os.getenv('DEFAULT_MODEL', 'openrouter')

def detect_language(text):
    """检测文本语言"""
    # 检测西班牙语特征
    spanish_chars = set('áéíóúüñ¿¡àèìòùâêîôûäëïöüãõ')
    spanish_words = {'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas', 'y', 'o', 'pero', 'porque', 'cuando', 'donde', 'como'}
    
    words = set(text.lower().split())
    
    if any(char in spanish_chars for char in text.lower()) or any(word in spanish_words for word in words):
        return 'es'
    
    # 检测英语特征
    english_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ')
    text_chars = set(text.replace(' ', ''))
    if text_chars.issubset(english_chars):
        return 'en'
    
    # 检测中文字符
    if any('\u4e00' <= char <= '\u9fff' for char in text):
        return 'zh'
    
    return 'es'

def get_prompt_by_mode_and_language(mode, language, text):
    """获取提示词"""
    base_prompts = {
        'es': {
            'free': "Por favor, reescribe el siguiente texto en español para hacerlo más natural y humano:",
            'standard': "Por favor, reescribe el siguiente texto en español usando un estilo estándar y profesional:",
            'academic': "Por favor, reescribe el siguiente texto en español usando un estilo académico y formal:",
            'simple': "Por favor, simplifica el siguiente texto en español para hacerlo más fácil de entender:",
            'formal': "Por favor, reescribe el siguiente texto en español usando un estilo formal y profesional:",
            'informal': "Por favor, reescribe el siguiente texto en español usando un estilo casual y conversacional:",
            'expand': "Por favor, expande el siguiente texto en español, agregando más detalles y explicaciones:",
            'shorten': "Por favor, resume el siguiente texto en español, manteniendo los puntos principales:"
        },
        'en': {
            'free': "Please rewrite the following English text to make it more natural and human-like:",
            'standard': "Please rewrite the following English text using a standard, professional style:",
            'academic': "Please rewrite the following English text using an academic and formal style:",
            'simple': "Please simplify the following English text to make it easier to understand:",
            'formal': "Please rewrite the following English text using a formal, professional style:",
            'informal': "Please rewrite the following English text using a casual, conversational style:",
            'expand': "Please expand the following English text by adding more details and explanations:",
            'shorten': "Please summarize the following English text, keeping the main points:"
        },
        'zh': {
            'free': "请将以下中文文本改写得更加自然、人性化：",
            'standard': "请使用标准的专业风格改写以下中文文本：",
            'academic': "请使用学术和正式的风格改写以下中文文本：",
            'simple': "请简化以下中文文本，使其更容易理解：",
            'formal': "请使用正式的专业风格改写以下中文文本：",
            'informal': "请使用轻松随意的对话风格改写以下中文文本：",
            'expand': "请扩展以下中文文本，添加更多细节和解释：",
            'shorten': "请总结以下中文文本，保持主要观点："
        }
    }

    prompts = base_prompts.get(language, base_prompts['es'])
    prompt = prompts.get(mode, prompts['free'])
    return prompt + "\n\n" + text

def call_openrouter_api(prompt):
    """调用OpenRouter API"""
    try:
        print(f"[Vercel] OpenRouter API调用开始")
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
        
        print(f"[Vercel] 发送请求到OpenRouter，数据预览：{json.dumps(data, ensure_ascii=False)[:200]}...")
        
        api_url = "https://openrouter.ai/api/v1/chat/completions"
        response = requests.post(
            api_url,
            headers=headers,
            json=data,
            timeout=30,
            verify=True
        )
        
        print(f"[Vercel] OpenRouter响应状态码：{response.status_code}")
        
        if response.status_code != 200:
            error_message = f"OpenRouter API调用失败: HTTP {response.status_code}"
            try:
                error_detail = response.json()
                print(f"[Vercel] OpenRouter错误详情：{json.dumps(error_detail, ensure_ascii=False)}")
                error_message += f" - {error_detail.get('error', {}).get('message', str(error_detail))}"
            except Exception as e:
                response_text = response.text[:500]
                print(f"[Vercel] 解析OpenRouter响应失败: {str(e)}, 响应内容: {response_text}")
                error_message += f" - {response.text}"
            raise Exception(error_message)
        
        result = response.json()
        print(f"[Vercel] OpenRouter响应成功：{json.dumps(result, ensure_ascii=False)[:200]}...")
        
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
        print("[Vercel] OpenRouter API调用超时")
        raise Exception("API调用超时，请稍后重试")
    except requests.exceptions.RequestException as e:
        print(f"[Vercel] OpenRouter网络请求错误: {str(e)}")
        raise Exception(f"网络请求错误: {str(e)}")
    except Exception as e:
        print(f"[Vercel] OpenRouter API调用错误: {str(e)}")
        raise Exception(f"API调用错误: {str(e)}")

def call_deepseek_api(prompt):
    """调用DeepSeek API"""
    try:
        print(f"[Vercel] DeepSeek API调用开始")
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
        
        print(f"[Vercel] 发送请求到DeepSeek，数据预览：{json.dumps(data, ensure_ascii=False)[:200]}...")
        
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        print(f"[Vercel] DeepSeek响应状态码：{response.status_code}")
        
        if response.status_code != 200:
            error_message = f"DeepSeek API调用失败: HTTP {response.status_code}"
            try:
                error_detail = response.json()
                print(f"[Vercel] DeepSeek错误详情：{json.dumps(error_detail, ensure_ascii=False)}")
                error_message += f" - {error_detail.get('error', {}).get('message', str(error_detail))}"
            except Exception as e:
                response_text = response.text[:500]
                print(f"[Vercel] 解析DeepSeek响应失败: {str(e)}, 响应内容: {response_text}")
                error_message += f" - {response.text}"
            raise Exception(error_message)
        
        result = response.json()
        print(f"[Vercel] DeepSeek响应成功：{json.dumps(result, ensure_ascii=False)[:200]}...")
        
        content = result['choices'][0]['message']['content'].strip()
        
        if (content.startswith('"') and content.endswith('"')) or \
           (content.startswith("'") and content.endswith("'")):
            content = content[1:-1]
        
        return content
        
    except Exception as e:
        print(f"[Vercel] DeepSeek API调用错误: {str(e)}")
        raise Exception(f"API调用错误: {str(e)}")

def call_ai_api(prompt):
    """根据环境变量中配置的默认模型选择API"""
    if DEFAULT_MODEL == 'openrouter':
        return call_openrouter_api(prompt)
    else:
        return call_deepseek_api(prompt)

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            text = data.get('text')
            mode = data.get('mode', 'free').lower()
            
            if not text:
                raise Exception('请提供需要处理的文本')
            
            if len(text) > 5000:
                raise Exception('文本长度超过限制（最大5000字符）')
            
            prompt = get_prompt_by_mode_and_language(mode, detect_language(text), text)
            
            # 记录请求信息
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            client_address = self.client_address[0] if hasattr(self, 'client_address') else 'unknown'
            log_entry = f"[{timestamp}] IP: {client_address}, Length: {len(text)}, Mode: {mode}, Model: {DEFAULT_MODEL}\n"
            
            print(f"[Vercel] 接收请求: IP={client_address}, 文本长度={len(text)}, 模式={mode}, 模型={DEFAULT_MODEL}")
            
            try:
                with open("request_log.txt", "a", encoding="utf-8") as f:
                    f.write(log_entry)
            except:
                print("[Vercel] 日志写入失败")
            
            try:
                print(f"[Vercel] 开始处理文本...")
                result = call_ai_api(prompt)
                print(f"[Vercel] 文本处理成功，结果长度: {len(result)}")
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                response_data = {
                    'success': True,
                    'result': result
                }
                self.wfile.write(json.dumps(response_data).encode('utf-8'))
                
            except Exception as api_error:
                print(f"[Vercel] API调用失败: {str(api_error)}")
                # 如果主要模型失败，尝试备用模型
                if DEFAULT_MODEL == 'openrouter' and DEEPSEEK_API_KEY:
                    try:
                        print("[Vercel] 尝试使用备用模型(DeepSeek)")
                        result = call_deepseek_api(prompt)
                        print(f"[Vercel] 备用模型调用成功，结果长度: {len(result)}")
                        
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        
                        response_data = {
                            'success': True,
                            'result': result,
                            'model_used': 'deepseek (fallback)'
                        }
                        self.wfile.write(json.dumps(response_data).encode('utf-8'))
                        return
                    except Exception as fallback_error:
                        print(f"[Vercel] 备用模型调用也失败: {str(fallback_error)}")
                
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                error_response = {
                    'success': False,
                    'error': str(api_error)
                }
                self.wfile.write(json.dumps(error_response).encode('utf-8'))
            
        except Exception as e:
            print(f"[Vercel] 请求处理错误: {str(e)}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            error_response = {
                'success': False,
                'error': str(e)
            }
            self.wfile.write(json.dumps(error_response).encode('utf-8')) 