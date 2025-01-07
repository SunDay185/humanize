import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import requests
import re

# 加载环境变量
load_dotenv()

# 初始化Flask应用
app = Flask(__name__)
CORS(app)  # 启用跨域支持

# 配置API密钥
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
DEEPSEEK_API_BASE = os.getenv('DEEPSEEK_API_BASE')

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
def humanize_text():
    try:
        data = request.json
        text = data.get('text')
        mode = data.get('mode', 'free').lower()

        if not text:
            return jsonify({
                'success': False,
                'error': '请提供需要处理的文本'
            }), 400

        prompt = get_prompt_by_mode(mode, text)

        try:
            result = call_deepseek_api(prompt)
            return jsonify({
                'success': True,
                'result': result
            })

        except Exception as e:
            print(f"API调用错误: {str(e)}")  # 添加错误日志
            return jsonify({
                'success': False,
                'error': f'API调用失败: {str(e)}'
            }), 500

    except Exception as e:
        print(f"服务器错误: {str(e)}")  # 添加错误日志
        return jsonify({
            'success': False,
            'error': f'服务器错误: {str(e)}'
        }), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000) 