import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import re
import datetime
import concurrent.futures
import os
import markdown

# ==========================================
# 0. 【网络配置】(智能切换 - 修复版)
# ==========================================
# 这里我们用 try-except 来“试探”环境
# 如果在云端，st.secrets 能读取，这就不会报错
# 如果在本地，st.secrets 会报错，我们就捕获错误并开启代理
try:
    # 试图读取云端配置（不做任何实际操作，只是为了测试）
    test_key = st.secrets["GEMINI_API_KEY"]
except:
    # 报错了说明在本地 -> 开启梯子！
    os.environ["http_proxy"] = "http://127.0.0.1:7897"
    os.environ["https_proxy"] = "http://127.0.0.1:7897"

# ==========================================
# 1. 配置区域
# ==========================================
# 尝试从 Streamlit Secrets (云端) 获取 Key
try:
    # 👇【千万别动这一行！】云端用
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    # 👇【在这里填入你的真实 Key！】本地用
    GEMINI_API_KEY = "AIzaSyBp2t6IgQUk_sD4Uy92JGW_j6D12eclY3A"

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-flash-latest')

# ==========================================
# 2. 核心功能 (保持不变)
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

def ai_generate_daily_brief(raw_input, scraped_text_block):
    prompt = f"""
    你是一位 Chilquinta 能源公司的情报专家。
    请根据提供的【原始分类】和【抓取的正文】，写一份排版精美的中文日报。

    【排版严格要求】：
    请对每一条新闻使用以下 Markdown 格式：

    ### 🍊 [这里写中文标题] (这里保留西语原文术语)
    
    [这里写详细的新闻摘要，包含具体数据。注意：摘要写完后必须换行]

    **🔗 来源链接：**
    * [链接1]

    ---

    【内容要求】：
    1. **结构复刻**：保留原始消息中的分类。
    2. **深度摘要**：概括核心事实。
    3. **术语保留**：机构名、法规、项目名在中文后保留西语原文。
    
    【时间】：{datetime.date.today()}
    """
    
    try:
        full_content = f"【原始消息框架】:\n{raw_input}\n\n【抓取的详细正文】:\n{scraped_text_block}"
        response = model.generate_content(prompt + "\n\n" + full_content)
        return response.text
    except Exception as e:
        return f"AI 思考出错: {str(e)}"

#CSS 样式
def convert_to_html_file(markdown_text):
    html_body = markdown.markdown(markdown_text)
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0"> <style>
            /* --- 基础样式 (电脑端) --- */
            body {{ 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; 
                line-height: 1.8; 
                color: #333; 
                max-width: 800px; 
                margin: 0 auto; 
                padding: 20px;
                background-color: #f4f7f6; 
            }}
            .container {{ 
                background-color: #ffffff; 
                padding: 40px; 
                border-radius: 12px; 
                box-shadow: 0 4px 15px rgba(0,0,0,0.05); 
            }}
            h2 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; margin-top: 30px; }}
            h3 {{ color: #d35400; margin-top: 25px; margin-bottom: 10px; font-size: 1.15em; font-weight: 600; }}
            p {{ margin-bottom: 15px; text-align: justify; }}
            
            /* 链接样式优化 */
            ul {{ 
                background-color: #f8f9fa; 
                padding: 15px 15px 15px 35px; 
                border-radius: 8px; 
                border-left: 5px solid #3498db;
                margin-bottom: 20px;
            }}
            li {{ margin-bottom: 8px; font-size: 0.95em; word-break: break-all; color: #555; }}
            a {{ color: #007bff; text-decoration: none; font-weight: 500; }}
            a:hover {{ text-decoration: underline; }}
            
            .footer {{ margin-top: 40px; text-align: center; font-size: 0.8em; color: #aaa; }}

            /* --- 📱 手机端专属优化 (Media Query) --- */
            @media only screen and (max-width: 600px) {{
                body {{
                    padding: 10px; /* 手机上减少外边距 */
                }}
                .container {{
                    padding: 20px; /* 手机上减少内边距，让字显示更多 */
                }}
                h2 {{
                    font-size: 1.4em; /* 标题稍微调小一点点以免换行太丑 */
                }}
                h3 {{
                    font-size: 1.1em;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            {html_body}
            <div class="footer">
                ⚡ Generated by Chilquinta AI Assistant • {datetime.date.today()}
            </div>
        </div>
    </body>
    </html>
    """
    return html_content

# ==========================================
# 3. 界面构建
# ==========================================
st.set_page_config(page_title="Chilquinta News v1.0", page_icon="⚡", layout="wide")

st.title("⚡ Chilquinta 每日新闻 (v1.0)")
st.caption("粘贴群消息 -> 生成精美 HTML 日报")

raw_text = st.text_area("请粘贴群消息:", height=200)

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

        status.write("🧠 AI 正在撰写报告...")
        report_md = ai_generate_daily_brief(raw_text, scraped_data_str)
        report_html = convert_to_html_file(report_md)
        
        status.update(label="✅ 完成！", state="complete", expanded=False)
        
        st.markdown("---")
        st.markdown(report_md) 
        
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        st.download_button(
            label="📥 下载精美排版日报 (.html)",
            data=report_html,
            file_name=f"Chilquinta_Report_{date_str}.html",
            mime="text/html"
        )