import os
from datetime import datetime

# Files changed today
FILES_TOUCHED = [
    r"engine\voice\hybrid_asr.py",
    r"engine\voice\tts_engine.py",
    r"engine\ai\local_llm.py",
    r"engine\core\command_parser.py",
    r"engine\core\executor.py",
    r"engine\memory\memory_manager.py",
    r"engine\device\device_controller.py",
    r"engine\vision\vision_engine.py",
    r"engine\comms\comms_manager.py",
    r"scripts\download_models.py",
    r"engine\ai\email_writer.py"
]

def generate_html_report(workspace_dir: str):
    html_path = os.path.join(workspace_dir, "JK_Full_Report.html")
    
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>JK Mobile AI - Development Report</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1000px;
            margin: 0 auto;
            padding: 40px;
            background-color: #f9f9f9;
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #2980b9;
            margin-top: 40px;
        }}
        .summary-box {{
            background: #fff;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }}
        .file-section {{
            background: #fff;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }}
        pre {{
            background: #282c34;
            color: #abb2bf;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            font-size: 14px;
        }}
        .path {{
            font-family: monospace;
            background: #ecf0f1;
            padding: 3px 6px;
            border-radius: 3px;
        }}
    </style>
</head>
<body>

    <h1>JK Mobile AI - Full Development Report</h1>
    <p><strong>Generated on:</strong> {datetime.now().strftime("%B %d, %Y %H:%M:%S")}</p>

    <div class="summary-box">
        <h2>Executive Summary of Changes</h2>
        <ul>
            <li><strong>Multilingual Engine:</strong> Swapped Vosk for OpenAI Whisper to enable auto-language detection. Integrated GoogleTrans middleware to bridge non-English queries to the local LLaMA model and translate responses back dynamically.</li>
            <li><strong>Bulletproof TTS Architecture:</strong> Completely rebuilt the English Text-to-Speech system. Replaced raw Python COM objects with isolated PowerShell subprocesses running SAPI5, bypassing all PyAudio threading deadlocks. Handled non-English TTS via Google TTS (gTTS) and PyGame.</li>
            <li><strong>Memory Module:</strong> Implemented a JSON-backed rolling conversation history buffer injected into the LLaMA context, allowing JK to retain cross-turn context.</li>
            <li><strong>Device Controller:</strong> Added system hardware hooks using <code>psutil</code> and <code>screen-brightness-control</code> to report battery/CPU and manipulate monitor brightness.</li>
            <li><strong>Vision Engine:</strong> Implemented an offline MobileNet SSD OpenCV object detection pipeline. Added a model download script to fetch the necessary Caffe weights.</li>
            <li><strong>Comms Manager:</strong> Integrated with an LLM-powered EmailWriter to convert rough dictations into professional emails. Added logic for handling structured communication intents.</li>
            <li><strong>Command Parser & Executor Overhaul:</strong> Added robust fallback-clamping for LLM hallucinations, generalized regex matching, and expanded execution routes for all new modules.</li>
        </ul>
    </div>

    <h2>Source Code Modifications</h2>
"""

    for file_rel_path in FILES_TOUCHED:
        abs_path = os.path.join(workspace_dir, file_rel_path)
        html_content += f"""
    <div class="file-section">
        <h3>File: <span class="path">{file_rel_path}</span></h3>
"""
        if os.path.exists(abs_path):
            try:
                with open(abs_path, 'r', encoding='utf-8') as f:
                    code = f.read()
                # Escape HTML tags in code
                code = code.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                html_content += f"<pre><code>{code}</code></pre>"
            except Exception as e:
                html_content += f"<p><em>Error reading file: {e}</em></p>"
        else:
            html_content += f"<p><em>File not found in workspace.</em></p>"
        
        html_content += "</div>"

    html_content += """
</body>
</html>
"""

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"Report generated successfully at: {html_path}")

if __name__ == "__main__":
    import sys
    workspace = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    generate_html_report(workspace)
