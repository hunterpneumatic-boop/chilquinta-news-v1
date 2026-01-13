import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import re
import datetime
import concurrent.futures
import os
import markdown
from docx import Document # 👈 V1.1 新增：用于处理 Word
from docx.shared import Pt, RGBColor # 👈 V1.1 新增：用于调整 Word 字体颜色
from io import BytesIO # 👈 V1.1 新增：用于在内存中生成文件

# ==========================================
# 0. 【网络配置】
# ==========================================
if "OS" in os.environ:
    os.environ["http_proxy"] = "http://127.0.0.1:7897"
    os.environ["https_proxy"] = "http://127.0.0.1:7897"

# ==========================================
# 1. 配置区域
# ==========================================
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except FileNotFoundError:
    st.error("❌ 未找到密钥配置！请确保本地有 .streamlit/secrets.toml 或云端已配置 Secrets。")
    st.stop()

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-flash-latest')

# ==========================================
# 2. 核心功能
# ==========================================
def extract_urls(text):
    url_pattern = r'(https?://[^\s]+)'
    return re.findall(url_pattern, text)

def scrape_one_url(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            paragraphs = soup.find_all('p')
            text = "\n".join([p.get_text() for p in paragraphs])
            if len(text) < 50: text = soup.get_text()
            return url, text[:2500] 
        return url, f"[网页错误: {response.status_code}]"
    except Exception as e:
        return url, f"[抓取出错: {str(e)}]"

# 🌟 V1.1 升级：支持多语言 Prompt
def ai_generate_daily_brief(raw_input, scraped_text_block, lang_mode):
    
    # 基础要求
    base_prompt = f"""
    你是一位 Chilquinta 能源公司的情报专家。
    请根据提供的【原始分类】和【抓取的正文】，写一份排版精美的日报。
    时间：{datetime.date.today()}
    
    【排版严格要求】：
    请对每一条新闻使用以下 Markdown 格式：
    ### 🍊 [标题]
    [正文内容]
    **🔗 Source:** [URL]
    ---
    """

    # 根据选择的语言模式，调整指令
    if lang_mode == "中文 (保留西语术语)":
        lang_instruction = """
        【语言要求】：
        1. 使用**中文**撰写摘要。
        2. **术语保留**：所有机构名、法规、项目名、人名，必须在中文后保留西语原文，例如：国家能源委员会 (CNE)。
        3. 标题使用中文。
        """
    elif lang_mode == "纯西语 (Español)":
        lang_instruction = """
        【语言要求】：
        1. 使用**专业西班牙语 (Español)** 撰写摘要。
        2. 风格要正式、商务 (Formal Business Tone)。
        3. 标题使用西语。
        """
    else: # 中文 + 西语
        lang_instruction = """
        【语言要求】：
        1. **双语对照模式**：对于每一条新闻，先写一段中文摘要，紧接着换行，写一段西班牙语摘要。
        2. 格式如下：
           [中文摘要内容...]
           
           (Español): [Resumen en español...]
        3. 标题使用：中文标题 / Título en Español
        """

    full_prompt = base_prompt + lang_instruction
    
    try:
        full_content = f"【原始消息框架】:\n{raw_input}\n\n【抓取的详细正文】:\n{scraped_text_block}"
        response = model.generate_content(full_prompt + "\n\n" + full_content)
        return response.text
    except Exception as e:
        return f"AI 思考出错: {str(e)}"

# 生成 HTML (保持不变，用于预览和网页下载)
def convert_to_html_file(markdown_text):
    html_body = markdown.markdown(markdown_text)
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.8; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; background-color: #f4f7f6; }}
            .container {{ background-color: #ffffff; padding: 40px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }}
            h2 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; margin-top: 30px; }}
            h3 {{ color: #d35400; margin-top: 25px; margin-bottom: 10px; font-size: 1.15em; font-weight: 600; }}
            p {{ margin-bottom: 15px; text-align: justify; }}
            ul {{ background-color: #f8f9fa; padding: 15px 15px 15px 35px; border-radius: 8px; border-left: 5px solid #3498db; margin-bottom: 20px; }}
            li {{ margin-bottom: 8px; font-size: 0.95em; word-break: break-all; color: #555; }}
            a {{ color: #007bff; text-decoration: none; font-weight: 500; }}
            .footer {{ margin-top: 40px; text-align: center; font-size: 0.8em; color: #aaa; }}
            @media only screen and (max-width: 600px) {{
                body {{ padding: 10px; }}
                .container {{ padding: 20px; }}
                h2 {{ font-size: 1.4em; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">{html_body}<div class="footer">⚡ Generated by Chilquinta AI Assistant • {datetime.date.today()}</div></div>
    </body>
    </html>
    """
    return html_content

# 🌟 V1.1 新增：生成 Word 文档
def generate_word_file(markdown_text):
    doc = Document()
    doc.add_heading(f'Chilquinta Daily News - {datetime.date.today()}', 0)

    # 简单的 Markdown 解析逻辑
    lines = markdown_text.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # 处理标题 (###)
        if line.startswith('### '):
            clean_line = line.replace('### ', '').replace('🍊', '').strip() # 去掉 emoji 以免 Word 乱码
            heading = doc.add_heading(clean_line, level=2)
            run = heading.runs[0]
            run.font.color.rgb = RGBColor(211, 84, 0) # 橙色
            
        # 处理列表 (*)
        elif line.startswith('* '):
            clean_line = line.replace('* ', '').strip()
            # 去掉 Markdown 链接格式 [text](url) 保留 text
            clean_line = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', clean_line) 
            doc.add_paragraph(clean_line, style='List Bullet')
            
        # 处理来源链接
        elif "Source:" in line or "来源链接" in line:
            doc.add_paragraph(line, style='Intense Quote')
            
        # 处理分割线
        elif line.startswith('---'):
            doc.add_paragraph('_' * 50)
            
        # 普通正文
        else:
            # 去掉粗体符号
            clean_line = line.replace('**', '')
            doc.add_paragraph(clean_line)

    # 保存到内存流
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# ==========================================
# 3. 界面构建
# ==========================================
st.set_page_config(page_title="Chilquinta News v1.1", page_icon="⚡", layout="wide")
st.title("⚡ Chilquinta 每日新闻 (v1.1)")
st.caption("支持多语言切换 • 支持 Word 下载")

# 输入区
raw_text = st.text_area("请粘贴群消息:", height=150)

# 🌟 V1.1 新增：语言选择器
lang_option = st.radio(
    "请选择生成语言:",
    ("中文 (保留西语术语)", "纯西语 (Español)", "中文 & 西语对照"),
    horizontal=True
)

if st.button("🚀 开始生成日报", type="primary"):
    if not raw_text or "http" not in raw_text:
        st.warning("请粘贴包含链接的内容！")
    else:
        urls = extract_urls(raw_text)
        status = st.status(f"发现 {len(urls)} 条链接，正在并发抓取...", expanded=True)
        scraped_data_str = ""
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_url = {executor.submit(scrape_one_url, url): url for url in urls}
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    _, content = future.result()
                    scraped_data_str += f"\n--- 链接 {url} 的正文 ---\n{content}\n"
                    status.write(f"✅ 已抓取: {url[:40]}...")
                except:
                    status.write(f"❌ 失败: {url[:40]}")
        
        status.write(f"🧠 AI 正在用【{lang_option}】模式撰写报告...")
        
        # 传递语言参数
        report_md = ai_generate_daily_brief(raw_text, scraped_data_str, lang_option)
        
        # 生成文件
        report_html = convert_to_html_file(report_md)
        word_file = generate_word_file(report_md) # 生成 Word
        
        status.update(label="✅ 完成！", state="complete", expanded=False)
        st.markdown("---")
        
        # 🌟 V1.1 升级：双下载按钮
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="📥 下载网页版 (.html)",
                data=report_html,
                file_name=f"Chilquinta_News_{datetime.date.today()}.html",
                mime="text/html"
            )
        with col2:
            st.download_button(
                label="📥 下载 Word 版 (.docx)",
                data=word_file,
                file_name=f"Chilquinta_News_{datetime.date.today()}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            
        st.markdown(report_md)