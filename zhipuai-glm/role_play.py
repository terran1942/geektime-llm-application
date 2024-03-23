import os
import itertools
from typing import Iterator, Optional
import json

import streamlit as st
from dotenv import load_dotenv
# 通过.env文件设置环境变量
# reference: https://github.com/theskumar/python-dotenv
load_dotenv()

import api
from api import generate_chat_scene_prompt, generate_role_appearance, get_characterglm_response, generate_cogview_image
from data_types import TextMsg, ImageMsg, TextMsgList, MsgList, filter_text_msg

st.set_page_config(page_title="CharacterGLM API Demo", page_icon="🤖", layout="wide")

def update_api_key(key: Optional[str] = None):
    key = key or st.session_state["API_KEY"]
    if key:
        api.API_KEY = key


# 设置API KEY
api_key = st.sidebar.text_input("API_KEY", value=os.getenv("API_KEY", ""), key="API_KEY", type="password", on_change=update_api_key)
update_api_key(api_key)


with open('santi.md', 'r', encoding='utf-8') as file:
    santi = file.read()


def resolve_role(text, role1, role2):
    instruction = f"""
        请从下列文本中，抽取人物“{role1}”、“{role2}”的描写。若文本中不包含外貌描写，请你推测人物的性别、年龄，并生成一段外貌描写。要求：
        1. 生成姓名、性别、外貌、性格、职业的描写，不要生成任何多余的内容。
        2. 尽量用短语描写，而不是完整的句子。
        3. 每个人物不要超过50字
        
        文本：
        {text}
        
        {role1}:
        {role2}：
    """
    response = api.get_chatglm_response_via_sdk(
        messages=[
            {
                "role": "user",
                "content": instruction.strip()
            }
        ]
    )
    return ''.join(response)


role_name_1 = st.sidebar.text_input(label='人物1', value='汪淼')
role_name_2 = st.sidebar.text_input(label='人物2', value='史强')

with st.sidebar:
    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            trigger_resolve_role = st.button('提取人物')

        with col2:
            trigger_generate_chat = st.button(label="生成对话")


if trigger_resolve_role:
    result = resolve_role(santi, role_name_1, role_name_2)
    role_infos=result.split('\n')
    st.session_state['人设1'] = role_info_1 = role_infos[0]
    st.session_state['人设2'] = role_info_2 = role_infos[2]
    st.text_area('人设1', role_info_1)
    st.text_area('人设2', role_info_2)
    st.session_state["history"] = {}
    st.session_state["history"][role_name_1] = []
    st.session_state["history"][role_name_2] = []


def output_stream_response(response_stream: Iterator[str], placeholder):
    content = ""
    for content in itertools.accumulate(response_stream):
        placeholder.markdown(content)
    return content


if trigger_generate_chat:
    cast_list=[{'role_name': role_name_1, 'role_info': st.session_state['人设1'], 'history': st.session_state["history"][role_name_1]},
               {'role_name': role_name_2, 'role_info': st.session_state['人设2'], 'history': st.session_state["history"][role_name_2]}]
    # 生成n次互相对话
    for n in range(5):
        for i in range(len(cast_list)):
            if i == 0:
                user = cast_list[0]
                bot = cast_list[1]
            else:
                user = cast_list[1]
                bot = cast_list[0]

            user_history = user['history']
            bot_history = bot['history']

            meta = {
                "user_name": user['role_name'],
                "user_info": user['role_info'],
                "bot_name": bot['role_name'],
                "bot_info": bot['role_info']
            }

            if len(user_history) == 0:
                greetings_stream = iter(["你好\n"])  # 创建一个迭代器模拟响应流
                output_stream_response(greetings_stream, st.empty())
                user_history.append(TextMsg({'role': 'user', 'content': '你好'}))
                bot_history.append(TextMsg({'role': 'assistant', 'content': '你好'}))

            response_stream = api.get_characterglm_response(filter_text_msg(user_history), meta)
            bot_response = output_stream_response(response_stream, st.empty())
            if not bot_response:
                user_history.pop()
            else:
                user_history.append(TextMsg({"role": "assistant", "content": bot_response}))
                bot_history.append(TextMsg({"role": "user", "content": bot_response}))

    history = json.dumps(cast_list)
    with open("chat_history.json", 'w', encoding='utf-8') as file:
        file.write(history)