import gradio as gr
import os
from openai import OpenAI
from run_ql import *
import time

MAX_TEMPERATURE = 1.99
MAX_TOP_P = 1.00
MIN_TEMPERATURE = 0.00
MIN_TOP_P = 0.01

# available model list
gModels = ["qwen-max", "qwen-plus", "qwen-turbo", "qwen-long", "qwen-omni-turbo", "deepseek-v3","deepseek-r1"]

# initialize openAI type API client
client = OpenAI(
    # 方式1：使用环境变量
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    # 方式2：直接填写API Key
    # api_key="sk-xxx",

    # base_url处请填写您的API供应商提供的API接口网址
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

# model parameter: temperature[0, 2.0) top_p(0, 1.0], models
gModelParas = {"temperature": 1.0, "top_p": 0.5, "model": gModels[0], "stream" : True}

with open(os.path.join(SCRIPT_DIR, "prompt_db.md"), "r", encoding="utf-8") as f:
    prompt_db = f.read()
with open(os.path.join(SCRIPT_DIR, "prompt_query.md"), "r", encoding="utf-8") as f:
    prompt_query = f.read() 
with open(os.path.join(SCRIPT_DIR, "prompt_error.md"), "r", encoding="utf-8") as f:
    prompt_error = f.read()
with open(os.path.join(SCRIPT_DIR, "prompt_result.md"), "r", encoding="utf-8") as f:
    prompt_result = f.read()
with open(os.path.join(SCRIPT_DIR, "dbconfig-lock.json"), "r", encoding="utf-8") as f:
    dbconfig = f.read()


def run_ql(name, query):
    print_message("Running CodeQL queries...", flush=True)

    db_path = os.path.join(DB_DIR, name)
    output_path = os.path.join(OUTPUTS_DIR, f'{query}_results.csv')
    query_path = os.path.join(QUERIES_DIR, name, query)

    import subprocess

    process = subprocess.Popen(
        f"codeql database analyze {db_path} {query_path} --format=csv --output={output_path} --rerun",
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8"
    )
    stdout, stderr = process.communicate()
    if process.returncode != 0:
        print("Generate Query Result Error:", stderr, flush=True)
        raise RuntimeError(f"Failed to run CodeQL queries. Error output: {stderr.strip()}")

    print_message(f"CodeQL analysis completed. Results are saved in {output_path}", flush=True)


# stream chat function
def model_chat(user_message, history):
    name = ""
    query = ""
    result = ""
    complete_response = ""
    error = ""
    i = 0
    try_times = 3
    while i < 3:
        try:
            if i == 0:
                complete_response += "正在生成所查询数据库的名称...\n"
                message = prompt_db + "\n\n以下是用户的数据库配置: \n" + dbconfig + "\n\n用户的查询需求: \n" + user_message
            elif i == 1 and error == "":
                complete_response += "\n\n正在生成CodeQL查询语句...\n"
                message = prompt_query + "\n\n用户的查询需求: \n" + user_message
            elif i == 1 and error != "":
                complete_response += "\n\n正在重新生成CodeQL查询语句...\n"
                message = prompt_error + "\n\n错误信息: \n" + error + "\n\n用户的查询需求: \n" + user_message
            else:
                complete_response += "\n\n正在分析查询结果...\n"
                message = prompt_result + "\n\n以下是查询结果的CSV内容: \n" + result + "\n\n用户的查询需求: \n" + user_message

            yield complete_response
            # 逐步处理流式响应
            history.append({"role" : "user", "content": message})

            completion = client.chat.completions.create(
                model = gModelParas["model"],
                messages = history,
                temperature = gModelParas["temperature"],
                top_p = gModelParas["top_p"],
                stream = gModelParas["stream"],
                stream_options={"include_usage": True}
            )
            partial_response = ""
            reasoning = False
            for chunk in completion:
                # 检查是否有新的文本内容
                if chunk.choices and chunk.choices[0].delta:
                    content = ""
                    if chunk.choices[0].delta.content:
                        if reasoning:
                            reasoning = False
                            content += "\n______\n"
                        content += chunk.choices[0].delta.content
                    elif hasattr(chunk.choices[0].delta, "reasoning_content") and chunk.choices[0].delta.reasoning_content:
                        if not reasoning:
                            reasoning = True
                            content += "***Reasoning***\n"
                        content += chunk.choices[0].delta.reasoning_content
                    partial_response += content
                    complete_response += content
                    yield complete_response  # 逐步返回累积的文本

                if chunk.choices and chunk.choices[0].finish_reason:
                    if i == 0:
                        name = partial_response.split("```")[1].strip() if "```" in partial_response else partial_response.strip()
                    elif i == 1:
                        if "```ql" in partial_response:
                            query = partial_response.split("```ql")[1].split("```")[0].strip()
                        elif "```" in partial_response:
                            query = partial_response.split("```")[1].strip()
                        else:
                            query = partial_response.strip()
                        
                        TimeStamp = int(time.time())
                        DB_QUERY_DIR = os.path.join(QUERIES_DIR, name)
                        if not os.path.exists(DB_QUERY_DIR):
                            os.makedirs(DB_QUERY_DIR)
                        query_file = f"custom_query_{name}_{TimeStamp}.ql"
                        query_file_path = os.path.join(DB_QUERY_DIR, query_file)
                        with open(query_file_path, "w", encoding="utf-8") as f:
                            f.write(query)

                        try:
                            run_ql(name, query=query_file)
                            with open(os.path.join(OUTPUTS_DIR, f'{query_file}_results.csv'), "r", encoding="utf-8") as f:
                                result = f.read()
                            if result.strip() == "":
                                complete_response += "\n\n查询结果为空，不存在函数调用或查询语句错误，请修改查询需求后重试。\n"
                                yield complete_response
                                return
                            else:
                                complete_response += "\n\n查询结果分析如下:\n ```csv\n" + result + "\n```\n"
                            error = ""
                        except Exception as e:
                            error = str(e)
                            if try_times > 0:
                                complete_response += f"\n\n运行CodeQL查询时出错，正在重新生成查询语句...（剩余尝试次数：{try_times}）\n"
                                yield complete_response
                                try_times -= 1
                                i -= 1  # 回到生成查询语句的步骤
                            else:
                                complete_response += f"\n\n运行CodeQL查询时失败，错误信息：{error}，请修改查询需求后重试。\n"
                                yield complete_response
                                return
                        
                    elif i == 2:
                        return  # 流式传输结束
            i += 1
        except Exception as e:
            yield f"出错了 {str(e)}"



# UI
with gr.Blocks(title="CodeQL Code Analysis with LLM") as demo:
    gr.Markdown("## CodeQL代码分析助手")

    with gr.Row(equal_height=True, variant = "panel" , max_height= 300):
        with gr.Column(scale = 2, min_width = 1):
            model_selector = gr.Dropdown(
                label = "models",
                choices = gModels,
                value = gModelParas["model"],
                interactive = True
            )
            model_selector.change(
                fn = lambda value : gModelParas.update({"model": value}) or None,
                inputs=model_selector
            )
    with gr.Row():
        gr.ChatInterface(fn=model_chat,
                         type="messages",
                         save_history=True,
                         editable=True
                        )

if __name__ == '__main__':
    create_files()
    for_each_config()
    demo.launch(share=False, server_port=7860, server_name="0.0.0.0")
