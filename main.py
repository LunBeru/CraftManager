# 必要モジュールのインストールを忘れないこと
# pip install google-generativeai
# pip install openai==0.28


# 環境変数の設定を忘れないこと
# $CHAT_GPT_APIKEY <chat gptのAPI KEY>
# $GEMINI_APYKEY <geminiのAPI KEY>

import queue
import google.generativeai as genai
import os
import json
import openai
import threading
import time
import subprocess
import file_manager
import log_manager
import message_analyze
from enum import IntEnum
import copy
import random
from log_manager import log_output
from log_manager import LOG_LEVEL_INFO
from log_manager import LOG_LEVEL_WARNING
from log_manager import LOG_LEVEL_ERROR


class UserStatusID(IntEnum):
    ERROR = -1
    STANDBAY = 0
    RES_WAIT_MAIN_MENEW = 1
    KILL_CMD_STANDBY = 2
    SEND_POS_STANDBY = 3
    SEND_POS = 4
    SPEED_MINECART_STANDBY = 5
    CHECK_ON_THE_MINECART = 6
    SPEED_MINECART_WAIT_ACCEPT = 7
    SPEED_MINECART_ACCEPT_OR_REJECT = 8
    SPEED_MINECART_EXECUTE = 9
    CALL_CHAT_GPT = 10
    CALL_GEMINI = 11
    CALL_AI = 12
    WARP_TO_USER = 13


class TimerEndEventID(IntEnum):
    ERROR = -1
    CALL_CMD_ONE_TIME = 0
    CALL_CMD_ENDLESS = 1
    CALL_FUNCTION = 2


class TimerEventManage:
    end_posix_time = 0
    end_event_id = TimerEndEventID.ERROR
    set_time = 0
    data_dict = {}
    delete_flg = False
    logout_delete_flg = False                       # ログアウト時、削除するかのフラグ True:ユーザーがログアウトしたら削除


class UserMnage:
    name = ""
    status_id = UserStatusID.STANDBAY
    status_id_backup = UserStatusID.STANDBAY        # 前回の状態を保持しておく必要がある場合利用
    data_dict = {}                                  # データ保持が必要になった場合の保持領域
    login = False
    timer_event_list = []
    to_chatgpt_queue = queue.Queue()                # chatgpt当てのキュー

    data_dict["speed_minecart_cool_time_flg"] = False



# グローバル変数
user_manage_list = []
tmux_session_name = ""
tmux_window_name = ""
chat_gpt_queue = queue.Queue()
gemini_queue = queue.Queue()
gemini_and_chatgpt_queue = queue.Queue()    # 使用していない関数で使用しているため、一応残す。関数整理の際に一緒に削除すること
ai_say_str_queue = queue.Queue()
chatgpt_prompt_list = [{"role":"system", "content":""}]
chatgpt_prompt_list_lock = threading.Lock()


# マイクラチャット送信関数 AIが喋る用（全ユーザー, 別スレッドで実行用）
# arg: なし
# ret: なし
def send_minecraft_chat_all_user_say_ai_thread():

    global ai_say_str_queue

    # 無限ループ
    while file_manager.check_exists_loop_flg_file() == True:

        # キューから、話すリストを取得
        send_str_list = ai_say_str_queue.get()

        # マイクラチャット送信コマンドを作成
        minecraft_chat_command_list = []

        # リストのデータにマイクラコマンドをくっつける
        for send_str_list_ite in send_str_list:
            minecraft_chat_command_list.append("say " + send_str_list_ite)

        # 送信先tmuxを抽出
        send_session_name = tmux_session_name
        send_window_name = tmux_window_name

        # コマンド送信
        for count, command in enumerate(minecraft_chat_command_list, start=1):
            command_str = "tmux send-keys -t " + send_session_name + ":" + send_window_name + " '" + command + "' Enter"
            try:
                log_output(LOG_LEVEL_INFO, log_manager.LOG_MSG_INFO_MAIN_SEND_CHAT + " command=" + command_str)
                subprocess.run(command_str, shell=True)
                # 最後と「-----」以外はディレイを設ける
                if count < len(minecraft_chat_command_list) - 1 and ("------------------------------" not in command):
                    time.sleep(len(command) * 0.1)
            
            except Exception:
                log_output(LOG_LEVEL_ERROR, log_manager.LOG_MSG_ERROR_MAIN_SEND_CHAT_FAILED + " command=" + command_str)
                

    return 0


# AIが喋る用キューに文字をputする関数
# arg: なし
# ret: なし
def send_minecraft_chat_all_user_ai_put_queue(input_str_list):

    global ai_say_str_queue

    ai_say_str_queue.put(input_str_list)


# gemini スレッド関数
# arg: 呼び出したユーザー名
# ret: 0
def gemini_thread_func(username):

    global gemini_queue

    send_str_list = []
    send_str_list.append("geminiを呼び出しました。")
    send_str_list.append("文字を入力してください。")
    send_str_list.append("終了する場合は")
    send_str_list.append("eを入力してください。(Endのe)")

    send_minecraft_chat(send_str_list, username, True)

    break_flg = False

    # gemini初期準備
    gemini_api_key = os.environ.get("GEMINI_APIKEY")
    genai.configure(api_key=gemini_api_key)
    generation_config = {
        "temperature": 0.3,  # 生成するテキストのランダム性を制御
        "top_p": 1,          # 生成に使用するトークンの累積確率を制御
        "top_k": 1,          # 生成に使用するトップkトークンを制御
        "max_output_tokens": 2048,  # 最大出力トークン数を指定
    }
    model = genai.GenerativeModel("gemini-1.5-flash", generation_config=generation_config, safety_settings={"SEXUALLY_EXPLICIT":"BLOCK_ONLY_HIGH", "HATE_SPEECH":"BLOCK_ONLY_HIGH", "HARASSMENT":"BLOCK_ONLY_HIGH"})
    model_gemini = model.start_chat(history=[])

    # 無限ループ
    while file_manager.check_exists_loop_flg_file() == True:

        # キューが空になるまで繰り返す
        while gemini_queue.empty() == False:

            # 文字列の取り出し
            input_str = gemini_queue.get()

            # eの場合は終了
            if input_str == "e":
                break_flg = True
                break

            # それ以外
            else:
                # gemini チャットの応答
                response = model_gemini.send_message(input_str)
                res_gemini_str = response.text

                res_list = res_gemini_str.splitlines()
                res_list.append("------------------------------")

                send_minecraft_chat_all_user_ai_put_queue(res_list)

        if break_flg == True:
            break

    # 終了メッセージ送信
    send_str_list.clear()
    send_str_list.append("geminiを終了しました。")
    send_str_list.append("------------------------------")
    send_minecraft_chat(send_str_list, username, True)

    #管理データをスタンバイに書き換え
    user_manage_list_change_status(username, UserStatusID.STANDBAY)

    return 0


# chatgptレスポンスを会話履歴リストに追加（履歴は一定数を保つ）
# arg: 会話履歴リスト, レスポンス文字列
# ret: 追加した状態の会話履歴リスト
def chat_gpt_add_msg_history_list(msg_list:list, response_msg:str):

    # フォーマットメモ
    # {"role": "system", "content": "あなたはとても丁寧で親しみやすいアシスタントです。"},
    # {"role": "user", "content": "こんにちは、最近の技術トレンドについて教えてくれませんか？"},
    # {"role": "assistant", "content": "こんにちは！技術トレンドについてお話ししますね。特にAI分野では..."}

    res_list = msg_list

    # データを追加
    add_dict = {"role": "assistant", "content": response_msg}
    res_list.append(add_dict)

    # 3往復のメッセージを超えていた場合は削除（systemメッセージは除く）
    if len(res_list) > (3 * 2) + 1:
        del res_list[1]
        del res_list[1]

    return res_list


# chatgptに覚えるべきメッセージか質問をする
# arg: ユーザーからのメッセージ
# ret: 0=覚える必要なし 1=覚える必要あり -1=エラー発生
def chat_gpt_check_memory_needed(user_msg:str):

    ret = -1
    global chatgpt_prompt_list
    global chatgpt_prompt_list_lock

    # chatgpt初期準備
    openai.api_key = os.environ.get("CHAT_GPT_APIKEY")

    # プロンプト設定
    system_prompt = (
        "あなたはマインクラフトjavaエディションのプレイをサポートするアシスタントです。\n"
        "あなたは、英語の小文字で'yes'か'no'のみ答えることができます。\n"
        "あなたは、情報を覚えることができます。"
    )

    # 質問準備
    question_msg = (
        "拠点の情報、サーバーの情報、重要なもの、覚えた情報の変更や削除に関係する場合は覚えてください。"
        "次の文章は、覚えるべきですか？\n"
        "'{question}'\n"
    ).format(question=user_msg)

    # プロンプト送信
    with chatgpt_prompt_list_lock:
        chatgpt_prompt_list_copy = copy.deepcopy(chatgpt_prompt_list)

    chatgpt_prompt_list_copy[0] = {"role":"system", "content":system_prompt}
    chatgpt_prompt_list_copy.append({"role":"user", "content":question_msg})

    try:
        response = openai.ChatCompletion.create(model="gpt-4o-2024-08-06", messages=chatgpt_prompt_list_copy, max_tokens=1000, temperature=0.0, top_p=1)

    # 処理に失敗
    except Exception as e:
        log_output(LOG_LEVEL_ERROR, log_manager.LOG_MSG_ERROR_MAIN_CHAT_GPT_ERROR)
        return ret

    # 回答の抽出
    res_str = response['choices'][0]['message']['content']

    # ログの出力
    log_output(LOG_LEVEL_INFO, "check chatgpt memory needed. msg='{msg}'".format(msg=question_msg))

    # 回答による分岐
    if "yes" in res_str:
        ret = 1
        log_output(LOG_LEVEL_INFO, "check result:memory needed")

    elif "no" in res_str:
        ret = 0
        log_output(LOG_LEVEL_INFO, "check result:not memory needed")

    else:
        # エラーにはしない（覚え無くて良い判定）
        ret = 0
        log_output(LOG_LEVEL_WARNING, "check result:response is unknown")

    log_output(LOG_LEVEL_INFO, "response='{res}'".format(res=res_str))

    return ret


# chatgpt 覚えるべきことの追加と最適化
# arg: 現在覚えていること, 新たに覚えること
# ret: dict["result"]=0 正常終了 -1 異常終了, dict["memory_data"]=最適化した覚えること(str)
def chatgpt_add_and_optimize_memory_data(memory_data:str, add_data:str):

    ret_dict = {"result": -1, "memory_data": ""}

    # chatgpt初期準備
    openai.api_key = os.environ.get("CHAT_GPT_APIKEY")

    # プロンプト設定
    system_prompt = (
        "あなたはマインクラフトjavaエディションのプレイをサポートするアシスタントです。\n"
        "覚えたことを一気に全て忘れるのは禁止です。少しずつの削除なら許可します。\n"
        "あなたの回答でそのまま上書きされます。回答に最終的な覚えたことを必ず含めてください。\n"
    )

    # 質問準備
    question_msg = (
        "次の情報を整理してください。最終行のデータは最新のデータです。\n"
        "'{memory}'\n"
        "'{add}'\n"
    ).format(memory=memory_data, add=add_data)

    # プロンプト送信
    prompt_list = []
    prompt_list.append({"role":"system", "content":system_prompt})
    prompt_list.append({"role":"user", "content":question_msg})

    try:
        response = openai.ChatCompletion.create(model="gpt-4o-2024-08-06", messages=prompt_list, max_tokens=1000, temperature=0.0, top_p=1)

    # 処理に失敗
    except Exception as e:
        log_output(LOG_LEVEL_ERROR, log_manager.LOG_MSG_ERROR_MAIN_CHAT_GPT_ERROR)
        return ret_dict
    
    # 回答の抽出
    res_str = response['choices'][0]['message']['content']

    # ログの出力
    log_output(LOG_LEVEL_INFO, "new memory data=['{memory}']".format(memory=res_str))

    # 返却の準備
    ret_dict["result"] = 0
    ret_dict["memory_data"] = res_str

    return ret_dict


# chatgptに問い合わせ実行
# arg: 呼び出したユーザー
# ret: 0
def talk_chatgpt_thread_func(username):

    global chatgpt_prompt_list

    send_str_list = []
    send_str_list.append("AI機能を呼び出しました。")
    send_str_list.append("文字を入力してください。")
    send_str_list.append("終了する場合は")
    send_str_list.append("eを入力してください。(Endのe)")

    send_minecraft_chat(send_str_list, username, True)

    # chatgpt初期準備
    openai.api_key = os.environ.get("CHAT_GPT_APIKEY")

    # ユーザーごとのキューの取得
    for user_manage_obj in user_manage_list:
        if user_manage_obj.name == username:
            user_queue = user_manage_obj.to_chatgpt_queue

    break_flg = False

    # 無限ループ
    while file_manager.check_exists_loop_flg_file() == True:
        # キューが空になるまで繰り返す
        while user_queue.empty() == False:
            # 文字列の取り出し
            input_dict = user_queue.get()
            input_str = input_dict["input_str"]
            
            # eの場合は終了
            if input_str == "e":
                break_flg = True
                break

            # それ以外
            else:
                # 覚えたことの読み込み
                memory_data_dict = file_manager.load_chat_gpt_file()
                memory_data_str = memory_data_dict["memory"]

                # 覚える必要があるかチェック
                send_minecraft_chat_all_user_ai_put_queue(["システムメッセージ：記憶の必要性を判定中"])
                is_needed = chat_gpt_check_memory_needed(input_str)

                # エラー
                if is_needed == -1:
                    send_minecraft_chat_all_user_ai_put_queue(["エラーが発生しました。もう一度お試しください。"])
                    continue

                # 覚える必要あり
                elif is_needed == 1:
                    # データの再読み込み
                    memory_data_dict_rewrite = file_manager.load_chat_gpt_file()
                    memory_data_str_rewrite = memory_data_dict_rewrite["memory"]
                    send_minecraft_chat_all_user_ai_put_queue(["システムメッセージ：記憶の実行と情報の整理中"])
                    optimize_result_dict = chatgpt_add_and_optimize_memory_data(memory_data_str_rewrite, input_str)

                    # エラーチェック
                    if optimize_result_dict["result"] == -1:
                        send_minecraft_chat_all_user_ai_put_queue(["エラーが発生しました。もう一度お試しください。"])
                        continue

                    # データの書き込み
                    memory_data_dict_rewrite["memory"] = optimize_result_dict["memory_data"]
                    file_manager.update_chat_gpt_file(memory_data_dict_rewrite)
                
                # 覚える必要なし
                # else:

                # 初期プロンプトの準備（書き換え）
                init_prompt = (
                    "あなたはマインクラフトjavaエディションのプレイをサポートするアシスタントであり、専門家です。\n"
                    "覚えたことを踏まえて完結に回答してください。\n"
                    "ハルシネーションは禁止です。\n"
                    "しりとり、クイズ、謎かけなどのゲームは禁止です。\n"
                    "あなたは情報を覚える機能があります。\n"
                    "ただし、覚えたことを一気に全て忘れるのは禁止です。少しずつの削除なら許可します。\n"
                    "覚えたことは次のとおりです。\n"
                    "'{memory}'"
                ).format(memory=memory_data_str)

                # グローバル変数をいじるためロックする
                with chatgpt_prompt_list_lock:
                    chatgpt_prompt_list[0] = {"role":"system", "content":init_prompt}

                    # 発言者の組み込み
                    question_prompt = ("発言者='{name}'さん：").format(name=username)
                    question_prompt = question_prompt + input_str

                    # 質問の実行
                    chatgpt_prompt_list.append({"role":"user", "content":question_prompt})
                    try:
                        send_minecraft_chat_all_user_ai_put_queue(["システムメッセージ：回答を生成中"])
                        response = openai.ChatCompletion.create(model="gpt-4o-2024-08-06", messages=chatgpt_prompt_list, max_tokens=1000, temperature=1.0, top_p=1)

                    # 処理に失敗
                    except Exception as e:
                        log_output(LOG_LEVEL_ERROR, log_manager.LOG_MSG_ERROR_MAIN_CHAT_GPT_ERROR)
                        send_minecraft_chat_all_user_ai_put_queue(["エラーが発生しました。もう一度お試しください。"])
                        continue
                    
                    # 回答の抽出～チャットへ送信
                    res_str = response['choices'][0]['message']['content']
                    res_list = res_str.splitlines()
                    res_list.insert(0, "------------------------------")
                    res_list.append("------------------------------")
                    send_minecraft_chat_all_user_ai_put_queue(res_list)

                    # 会話履歴を更新
                    chatgpt_prompt_list = chat_gpt_add_msg_history_list(chatgpt_prompt_list, res_str)

                    # ログに記録(トークン数)
                    total_tokens = response['usage']['total_tokens']
                    prompt_tokens = response['usage']['prompt_tokens']
                    completion_tokens = response['usage']['completion_tokens']
                    log_output(LOG_LEVEL_INFO, log_manager.LOG_MSG_INFO_MAIN_CHAT_GPT_COMPLETE_REQ + " use req token=" + str(prompt_tokens) + " server res token=" + str(completion_tokens) + " total token=" + str(total_tokens))
                    
                    # プロンプトリストを文字列化～ログ出力
                    all_prompt_str = ""
                    for prompt in chatgpt_prompt_list:
                        all_prompt_str = all_prompt_str + json.dumps(prompt, indent=4, ensure_ascii=False)

                    log_output(LOG_LEVEL_INFO, "all prompt=" + all_prompt_str)

        if break_flg == True:
            break

    # 終了メッセージ送信
    send_str_list.clear()
    send_str_list.append("AI機能を終了しました。")
    send_str_list.append("------------------------------")
    send_minecraft_chat(send_str_list, username, True)

    #管理データをスタンバイに書き換え
    user_manage_list_change_status(username, UserStatusID.STANDBAY)

    return 0


# タイマー管理スレッド関数
# arg: なし
# ret: 0
def timer_manage_thread_func():

    while file_manager.check_exists_loop_flg_file() == True:
        
        # ユーザーループ
        for user_manage_data in user_manage_list:

            # タイマーイベントリストループ
            for timer_event in user_manage_data.timer_event_list:

                # 現在のエポック秒取得
                posix_time_now = time.time()

                # タイマー満了の場合
                if timer_event.end_posix_time <= posix_time_now:

                    # イベントIDが1回コマンド呼び出しの場合
                    if timer_event.end_event_id == TimerEndEventID.CALL_CMD_ONE_TIME:

                        # コマンド発行
                        command_str = timer_event.data_dict["command_str"]
                        send_minecraft_command(command_str)

                        # 削除フラグをTrueにセット
                        timer_event.delete_flg = True

                    # イベントIDがコマンドのエンドレス呼び出しの場合
                    elif timer_event.end_event_id == TimerEndEventID.CALL_CMD_ENDLESS:

                        # コマンド発行
                        command_str = timer_event.data_dict["command_str"]
                        send_minecraft_command(command_str)

                        # タイマー値を更新
                        timer_event.end_posix_time = posix_time_now + timer_event.set_time

                    # イベントIDが指定関数の呼び出しの場合
                    elif timer_event.end_event_id == TimerEndEventID.CALL_FUNCTION:
                        # 関数呼び出し
                        func = timer_event.data_dict["call_func"]
                        func_arg_dict = timer_event.data_dict["call_func_arg_dict"]
                        func(func_arg_dict)

                        # 削除フラグをTrueにセット
                        timer_event.delete_flg = True

                # 満了していない場合
                else:
                    pass

            # 削除フラグがTrueのタイマーを省いてリスト作成
            new_timer_event_list = []
            for timer_event in user_manage_data.timer_event_list:
                if timer_event.delete_flg == False:
                    new_timer_event_list.append(timer_event)

            # ユーザー管理データのタイマーリストにセットし直す
            user_manage_data.timer_event_list = new_timer_event_list

    return 0


# タイマーセット関数
# arg: タイマーイベントID, セットするタイマー値, セットするタイマーデータ, ユーザー名
# ret: 0
def timer_set(timer_id, timer_value, timer_data_dict, logout_delete_flg, username):

    # 現在のエポック秒取得
    posix_time_now = time.time()

    edit_flg = False

    # 管理データ内を検索
    for user_manage_list_obj in user_manage_list:

        if user_manage_list_obj.name == username:

            # タイマーセット
            timer_event_manage = TimerEventManage()
            end_posix_time = posix_time_now + float(timer_value)
            timer_event_manage.end_event_id = timer_id
            timer_event_manage.end_posix_time = end_posix_time
            timer_event_manage.data_dict = timer_data_dict
            timer_event_manage.set_time = timer_value
            timer_event_manage.logout_delete_flg = logout_delete_flg

            user_manage_list_obj.timer_event_list.append(timer_event_manage)

            edit_flg = True

            log_output(LOG_LEVEL_INFO, log_manager.LOG_MSG_INFO_MAIN_TIMER_SET + "tiemr_id=" + str(timer_id) + " end_time=" + str(end_posix_time) + " timer_value=" + str(timer_value) + " logout_delete_flg=" + str(logout_delete_flg) + " user=" + username)

    # ユーザー情報が見つからなかった場合
    if edit_flg == False:

        log_output(LOG_LEVEL_WARNING, log_manager.LOG_MSG_WARNING_MAIN_TIMER_SET_FAILED + " user=" + username)

    return 0


# タイマー削除関数　timer_data指定
# arg: ユーザー名, タイマーセット時に渡したデータ
# ret: 0
def timer_delete(username, timer_data_dict):

    # 管理データ内を検索
    for user_manage_list_obj in user_manage_list:
        if user_manage_list_obj.name == username:

            # 削除するタイマー検索
            delete_index = -1
            count = 0
            for timer_manage in user_manage_list_obj.timer_event_list:
                # タイマーのデータが同一だった場合、削除index保持
                if timer_manage.data_dict == timer_data_dict:
                    delete_index = count
                    log_output(LOG_LEVEL_INFO, log_manager.LOG_MSG_INFO_MAIN_TIMER_DELETE + "tiemr_id=" + str(timer_manage.end_event_id) + " end_time=" + str(timer_manage.end_posix_time) + " timer_value=" + str(timer_manage.set_time) + " user=" + username)

                count = count + 1

            # タイマー削除
            del user_manage_list_obj.timer_event_list[delete_index]

    # ユーザー情報が見つからなかった場合
    if delete_index == -1:
        log_output(LOG_LEVEL_WARNING, log_manager.LOG_MSG_WARNING_MAIN_TIMER_DELETE_FAILED + " user=" + username)

    return 0


# タイマー削除関数　指定したタイマーIDのタイマー全てを削除
# arg: ユーザー名, タイマーセット時に渡したデータ
# ret: 0
def timer_delete_select_timer_id(username, timer_id):

    # 管理データ内を検索
    for user_manage_list_obj in user_manage_list:
        if user_manage_list_obj.name == username:

            # 削除するタイマー検索
            delete_index_list = []
            count = 0
            for timer_manage in user_manage_list_obj.timer_event_list:
                # タイマーのデータが同一だった場合、削除index保持
                if timer_manage.end_event_id == timer_id:
                    delete_index_list.append(count)
                    log_output(LOG_LEVEL_INFO, log_manager.LOG_MSG_INFO_MAIN_TIMER_DELETE + "tiemr_id=" + str(timer_manage.end_event_id) + " end_time=" + str(timer_manage.end_posix_time) + " timer_value=" + str(timer_manage.set_time) + " user=" + username)

                count = count + 1

            # タイマー削除
            for delete_index in delete_index_list:
                del user_manage_list_obj.timer_event_list[delete_index]

    # ユーザー情報が見つからなかった場合
    if len(delete_index_list) <= 0:
        log_output(LOG_LEVEL_WARNING, log_manager.LOG_MSG_WARNING_MAIN_TIMER_DELETE_FAILED + " user=" + username)

    return 0


# タイマーセット関数（満了時、関数呼び出しタイプ）
def timer_set_regist_function(timer_value, call_func, call_func_arg_dict, logout_delete_flg, username):

    timer_id = TimerEndEventID.CALL_FUNCTION
    data_dict = {"call_func":call_func, "call_func_arg_dict":call_func_arg_dict}

    timer_set(timer_id, timer_value, data_dict, logout_delete_flg, username)


# タイマー削除 関数満了時、関数呼び出しタイプ　call_func, call_func_arg_dict指定
# arg: ユーザー名, タイマーセット時に渡したデータ
# ret: 0
def timer_delete_regist_function(username, call_func, call_func_arg_dict):

    # 管理データ内を検索
    for user_manage_list_obj in user_manage_list:
        if user_manage_list_obj.name == username:

            # 削除するタイマー検索
            delete_index = -1
            count = 0
            for timer_manage in user_manage_list_obj.timer_event_list:
                # 関数呼び出しタイプのタイマーで、呼び出し登録関数と引数が一致した場合
                if timer_manage.end_event_id == TimerEndEventID.CALL_FUNCTION:
                    if timer_manage.data_dict["call_func"] == call_func and timer_manage.data_dict["call_func_arg_dict"] == call_func_arg_dict:
                        # 削除するインデックスを保持
                        delete_index = count
                        log_output(LOG_LEVEL_INFO, log_manager.LOG_MSG_INFO_MAIN_TIMER_DELETE + "tiemr_id=" + str(timer_manage.end_event_id) + " end_time=" + str(timer_manage.end_posix_time) + " timer_value=" + str(timer_manage.set_time) + " user=" + username)
                        break

                count = count + 1

            # タイマー削除
            del user_manage_list_obj.timer_event_list[delete_index]

    # ユーザー情報が見つからなかった場合
    if delete_index == -1:
        log_output(LOG_LEVEL_WARNING, log_manager.LOG_MSG_WARNING_MAIN_TIMER_DELETE_FAILED + " user=" + username)

    return 0



# 高速トロッコクールタイムリセット関数（タイマーから実行される想定）
# arg: ユーザー名（dict）
# ret: 0
def timer_regist_func_speed_minecart_cool_time_reset(arg_dict):

    # ユーザー名取得
    username = arg_dict["username"]

    # 管理データーからユーザーを探して、クールタイム状態リセット
    for user_manage in user_manage_list:
        if user_manage.name == username:
            user_manage.data_dict["speed_minecart_cool_time_flg"] = False

            log_output(LOG_LEVEL_INFO, log_manager.LOG_MSG_INFO_MAIN_SPEED_MINECART_COOL_TIME_FLG_RESET + " username=" + username)

    return 0


# 高速トロッコ効果時間終了の処理（タイマーから実行される想定）
# arg: ユーザー名（dict）
# ret: 0
def timer_regist_func_speed_minecart_time_up(arg_dict):

    send_data_list = []
    username = arg_dict["username"]

    # 時間加速を終了するコマンドと、メッセージを準備
    send_data_list.append("効果時間である5分が経過したため")
    send_data_list.append("高速トロッコを終了します。")
    send_command_str = "tick rate 20"

    # コマンド発行しているタイマー削除
    timer_data_dict = {"command_str":"data get entity " + username}
    timer_delete(username, timer_data_dict)

    # 時間加速を終了するコマンド送信
    send_minecraft_command(send_command_str)

    # クールタイムステータスのセット
    for user_manage_data in user_manage_list:
        if user_manage_data.name == username:
            user_manage_data.data_dict["speed_minecart_cool_time_flg"] = True

    # クールタイムリセットのタイマーをセット
    func_arg_dict = {"username":username}
    timer_set_regist_function(180.0, timer_regist_func_speed_minecart_cool_time_reset, func_arg_dict, False, username)

    # ログインユーザー全員に通知メッセージ送信
    for user_manage_data in user_manage_list:
        if user_manage_data.login == True:
            send_minecraft_chat(send_data_list, user_manage_data.name, False)

    # 申請者のステータスをスタンバイに変更
    next_user_status = UserStatusID.STANDBAY
    user_manage_list_change_status(username, next_user_status)

    return 0


# マイクラチャット送信関数（全ユーザー）
# arg: チャットに送信する文字列リスト
# ret: 0
def send_minecraft_chat_all_user(send_str_list):

    # デバッグ用
    # with open("./send_chat.txt", mode="a", encoding="utf-8") as file_obj:
    #     for i in send_str_list:
    #         file_obj.write(i + "\n")

    # マイクラチャット送信コマンドを作成
    minecraft_chat_command_list = []

    # リストのデータにマイクラコマンドをくっつける
    minecraft_chat_command_list.append("say ------------------------------")
    for send_str_list_ite in send_str_list:
        minecraft_chat_command_list.append("say " + send_str_list_ite)
    
    minecraft_chat_command_list.append("say ------------------------------")
    

    # 送信先tmuxを抽出
    send_session_name = tmux_session_name
    send_window_name = tmux_window_name

    # コマンド送信
    for command in minecraft_chat_command_list:
        command_str = "tmux send-keys -t " + send_session_name + ":" + send_window_name + " '" + command + "' Enter"
        try:
            log_output(LOG_LEVEL_INFO, log_manager.LOG_MSG_INFO_MAIN_SEND_CHAT + " command=" + command_str)
            subprocess.run(command_str, shell=True)
        
        except Exception:
            log_output(LOG_LEVEL_ERROR, log_manager.LOG_MSG_ERROR_MAIN_SEND_CHAT_FAILED + " command=" + command_str)

    return 0



# マイクラチャット送信関数
# arg: チャットに送信する文字列リスト, ターゲットのユーザー, コンフィグデータ, 区切りフラグ（False:区切りあり True:区切り無し）
# ret: 0
def send_minecraft_chat(send_str_list, username, no_line_flg):

    # デバッグ用
    # with open("./send_chat.txt", mode="a", encoding="utf-8") as file_obj:
    #     for i in send_str_list:
    #         file_obj.write(i + "\n")

    # マイクラチャット送信コマンドを作成
    minecraft_chat_command_list = []
    # 区切り行を一行入れる
    if no_line_flg == False:
        minecraft_chat_command_list.append("msg " + username + " ------------------------------")
    
    for send_str_list_ite in send_str_list:
        minecraft_chat_command_list.append("msg " + username + " " + send_str_list_ite)

    # 区切り行を一行入れる
    if no_line_flg == False:
        minecraft_chat_command_list.append("msg " + username + " ------------------------------")

    # 送信先tmuxを抽出
    send_session_name = tmux_session_name
    send_window_name = tmux_window_name

    # コマンド送信
    for command in minecraft_chat_command_list:
        command_str = "tmux send-keys -t " + send_session_name + ":" + send_window_name + " '" + command + "' Enter"
        try:
            log_output(LOG_LEVEL_INFO, log_manager.LOG_MSG_INFO_MAIN_SEND_CHAT + " command=" + command_str)
            subprocess.run(command_str, shell=True)
        
        except Exception:
            log_output(LOG_LEVEL_ERROR, log_manager.LOG_MSG_ERROR_MAIN_SEND_CHAT_FAILED + " command=" + command_str)

    return 0


# マイクラのコマンドを発行する
# arg: コマンド文字列
# ret: なし
def send_minecraft_command(command):

    # 送信先tmuxを抽出
    send_session_name = tmux_session_name
    send_window_name = tmux_window_name

    # コマンド送信
    command_str = "tmux send-keys -t " + send_session_name + ":" + send_window_name + " '" + command + "' Enter"

    try:
        log_output(LOG_LEVEL_INFO, log_manager.LOG_MSG_INFO_MAIN_SEND_CMD + " command=" + command_str)
        subprocess.run(command_str, shell=True)
        
    except Exception:
        log_output(LOG_LEVEL_ERROR, log_manager.LOG_MSG_ERROR_MAIN_SEND_CMD_FAILED + " command=" + command_str)

    return 0

# 関数テーブル登録用ダミー関数
def dummy_func(analyze_result, conf_data_result):
    print("dummy_func_call")
    pass


# 挨拶文をファイルから読み取り、1つランダムで返す
# arg: ユーザー名(str)
# ret: 挨拶文(str)
def select_greeting_str(username):

    GREETING_NUM_MAX = 100
    USER_NAME_REPLACE_KEYWORD = "<username>"
    greeting_str = ""

    # ランダムでインデックスを決定
    random_index = random.randint(0, GREETING_NUM_MAX)

    # ファイルから挨拶リストを取得～特定の挨拶を取得
    greeting_list = file_manager.load_minecraft_manager_greetings_file()
    greeting_str = greeting_list[random_index]

    # ユーザー名を付与
    greeting_str = greeting_str.replace(USER_NAME_REPLACE_KEYWORD, username)

    return greeting_str


# ログイン処理
# arg: チャット解析結果データ, コンフィグデータ
# ret: コンフィグデータ更新なし:0 コンフィグデータの更新が発生:1
def event_tbl_func_login(analyze_result, conf_data_result):

    ret = 0

    # ログインユーザー抽出
    login_user_name = analyze_result.message_user

    # ログインしたユーザーの管理情報のステータスをログインに変更
    edit_flg = False
    for user_manage_list_obj in user_manage_list:
        if user_manage_list_obj.name == login_user_name:
            user_manage_list_obj.login = True
            edit_flg = True
            log_output(LOG_LEVEL_INFO, log_manager.LOG_MSG_INFO_MAIN_EVENT_LOGIN + " user=" + login_user_name)

            # 挨拶を生成して、\nで区切ってリスト化
            send_data_str = select_greeting_str(login_user_name)
            send_data_list = []
            send_data_list.append(send_data_str)

    # コンフィグ情報にユーザーが存在しない場合（edit_flgがFalseのまま）
    if edit_flg == False:
        # コンフィグ情報にユーザーを追加
        new_user_manage = UserMnage()
        new_user_manage.name = login_user_name
        new_user_manage.login = True
        new_user_manage.status_id = UserStatusID.STANDBAY
        user_manage_list.append(new_user_manage)

        # コンフィグデータにもユーザーを追加する
        conf_data_result.data["minecraft_users"].append(login_user_name)
        log_output(LOG_LEVEL_INFO, log_manager.LOG_MSG_INFO_MAIN_EVENT_CONFIG_USER_ADD + " user=" + login_user_name)
        ret = 1

        send_data_list = [
                "はじめまして！",
                "マイクラマネージャーと申します。",
                "私は、マイクラでの活動を",
                "サポートする役割を担っています。",
                "チャット欄に",
                "「m」と入力していただければ",
                "ご用件をお伺いします。",
                "「ai」でAI機能を",
                "呼び出すこともできます。",
                "お気軽にお呼びくださいね。"
        ]

        # チャットにメッセージ送信
    # send_minecraft_chat(send_data_list, login_user_name, False)
    send_minecraft_chat_all_user(send_data_list)

    return ret


# ログアウト処理
# arg: チャット解析結果データ, コンフィグデータ
# ret: 0
def event_tbl_func_logout(analyze_result, conf_data_result):

    global chat_gpt_queue
    global gemini_queue

    # ログアウトユーザー抽出
    logout_user_name = analyze_result.message_user

    # chat gptとやりとり中の場合は　chat gptスレッドを終わらせる
    for user_manage in user_manage_list:
        if user_manage.name == logout_user_name:
            # chatgptスレッドを終了させる
            if user_manage.status_id == UserStatusID.CALL_CHAT_GPT:
                chat_gpt_queue.put("e")

            # geminiスレッドを終了させる
            elif user_manage.status_id == UserStatusID.CALL_GEMINI:
                gemini_queue.put("e")

            # gemini and chatgptスレッドを終了させる
            elif user_manage.status_id == UserStatusID.CALL_AI:
                user_manage.to_chatgpt_queue.put({"input_str": "e"})

    # ユーザーステータスをリセット
    user_manage_list_change_status(logout_user_name, UserStatusID.STANDBAY)

    # ログインしたユーザーの管理情報のステータスをログアウト(False)に変更
    for user_manage_list_obj in user_manage_list:
        if user_manage_list_obj.name == logout_user_name:
            user_manage_list_obj.login = False
            log_output(LOG_LEVEL_INFO, log_manager.LOG_MSG_INFO_MAIN_EVENT_LOGOUT + " user=" + logout_user_name)

            # ログアウト時に削除して良いタイマーは削除する
            new_timer_event_list = []
            # タイマーリストループ
            for timer_manage in user_manage_list_obj.timer_event_list:
                # ログアウト時に削除しないタイマーの場合
                if timer_manage.logout_delete_flg == False:
                    # 新しいリストに保持
                    new_timer_event_list.append(timer_manage)

            # 新しいタイマーリストに上書き
            user_manage_list_obj.timer_event_list = new_timer_event_list

    return 0


# ユーザー管理データのステータスIDを変更する
# arg: ユーザー名, 設定値
# ret: 設定完了:0 未発見により設定失敗:-1
def user_manage_list_change_status(username, value):

    edit_flg = False
    ret = -1

    # 管理データ内を検索
    for user_manage_list_obj in user_manage_list:

        if user_manage_list_obj.name == username:

            # バックアップを取っておく
            user_manage_list_obj.status_id_backup = user_manage_list_obj.status_id

            # ステータス変更
            user_manage_list_obj.status_id = value
            edit_flg = True
            ret = 0

            log_output(LOG_LEVEL_INFO, log_manager.LOG_MSG_INFO_MAIN_USER_STATUS_CHANGE + " user=" + username + " value=" + str(value))

    # ユーザー情報が見つからなかった場合
    if edit_flg == False:

        log_output(LOG_LEVEL_WARNING, log_manager.LOG_MSG_WARNING_MAIN_USER_MANAGE_SET_USER_STATUS_FAILED + " user=" + username + " value=" + str(value))

    return ret


# ユーザー管理データのステータスIDをバックアップを使用して元に戻す（スタンバイの場合はもとに戻さない）
# arg: ユーザー名, 設定値
# ret: ステータス変更無し:0 ステータス変更あり:1 未発見により設定失敗:-1
def user_manage_list_back_status(username):

    hit_user_flg = False
    ret = -1

    # 管理データ内を検索
    for user_manage_list_obj in user_manage_list:

        if user_manage_list_obj.name == username:

            hit_user_flg = True
            ret = 0

            if user_manage_list_obj.status_id != UserStatusID.STANDBAY:

                user_manage_list_obj.status_id = user_manage_list_obj.status_id_backup
                log_output(LOG_LEVEL_INFO, log_manager.LOG_MSG_INFO_MAIN_USER_STATUS_CHANGE + " user=" + username + "status=" + str(user_manage_list_obj.status_id))
                ret = 1

    # ユーザー情報が見つからなかった場合
    if hit_user_flg == False:
        
        log_output(LOG_LEVEL_WARNING, log_manager.LOG_MSG_WARNING_MAIN_USER_MANAGE_BACK_USER_STATUS_FAILED + " user=" + username)

    return ret


# ユーザー管理データのステータスIDを取得する
# arg: ユーザー名
# ret: 発見:ユーザーのステータスID 発見できない:-1(status id = ERROR)
def user_manage_list_get_status(username):

    ret_status_id = UserStatusID.ERROR

    # 管理データ内を検索
    for user_manage_list_obj in user_manage_list:

        if user_manage_list_obj.name == username:

            ret_status_id = user_manage_list_obj.status_id

    # ユーザー情報が見つからなかった場合
    if ret_status_id == UserStatusID.ERROR:

        log_output(LOG_LEVEL_WARNING, log_manager.LOG_MSG_WARNING_MAIN_USER_MANAGE_GET_USER_STATUS_FAILED + " user=" + username)

    return ret_status_id


# マネージャー呼び出し処理 高速トロッコ中はコマンドの受付はしない
# arg: チャット解析結果データ, コンフィグデータ
# ret: 0
def event_tbl_func_call_manager(analyze_result, conf_data_result):

    # ユーザー名と現在のステータス取得
    username = analyze_result.message_user
    status_id = user_manage_list_get_status(username)

    # ユーザーステータスがスタンバイ状態
    if status_id == UserStatusID.STANDBAY:
        send_data_list = [
            "こんにちは！マイクラマネージャーです。",
            "ご用件を、数字で教えていただけますか？",
            "1:デスルーラしたい。",
            "2:座標を送り続けてほしい。",
            "3:高速トロッコを利用したい。",
            "4:他ユーザーの場所へワープしたい。",
            "5:どんな呼び方があるの？",
            "99:何でもない。呼んでみただけ。"
        ]

        # チャットにメッセージ送信
        send_minecraft_chat(send_data_list, analyze_result.message_user, False)

        # 管理データのステータスを変更
        user_manage_list_change_status(analyze_result.message_user, UserStatusID.RES_WAIT_MAIN_MENEW)

    # 高速トロッコ中は他コマンドを受け付けない
    elif status_id == UserStatusID.SPEED_MINECART_EXECUTE:

        send_data_list = [
            "こんにちは！マイクラマネージャーです。",
            "現在、高速トロッコ利用中のため、",
            "他機能の受付ができません。",
            "トロッコを降りて、高速トロッコを",
            "終了してから、お声がけくださいね。"
        ]

        # チャットにメッセージ送信
        send_minecraft_chat(send_data_list, analyze_result.message_user, False)

    else:
        pass

    return 0


# geminiとchatgpt併用 呼び出し処理
# arg: チャット解析結果データ, コンフィグデータ
# ret: 0
def event_tbl_func_call_ai(analyze_result, conf_data_result):

    # ユーザー名と現在のステータス取得
    username = analyze_result.message_user
    status_id = user_manage_list_get_status(username)

    # ユーザーステータスがスタンバイ状態
    if status_id == UserStatusID.STANDBAY:

        # 管理データのステータスを変更
        user_manage_list_change_status(username, UserStatusID.CALL_AI)

        # スレッドの準備、起動
        gemini_and_chatgpt_thread = threading.Thread(target=talk_chatgpt_thread_func, args=(username,))
        gemini_and_chatgpt_thread.daemon = True
        gemini_and_chatgpt_thread.start()

    # 高速トロッコ中は他コマンドを受け付けない
    elif status_id == UserStatusID.SPEED_MINECART_EXECUTE:

        send_data_list = [
            "こんにちは！マイクラマネージャーです。",
            "現在、高速トロッコ利用中のため、",
            "他機能の受付ができません。",
            "トロッコを降りて、高速トロッコを",
            "終了してから、お声がけくださいね。"
        ]

        # チャットにメッセージ送信
        send_minecraft_chat(send_data_list, analyze_result.message_user, False)

    else:
        pass

    return 0


# gemini 呼び出し処理
# arg: チャット解析結果データ, コンフィグデータ
# ret: 0
def event_tbl_func_call_gemini(analyze_result, conf_data_result):

    # ユーザー名と現在のステータス取得
    username = analyze_result.message_user
    status_id = user_manage_list_get_status(username)

    # ユーザーステータスがスタンバイ状態
    if status_id == UserStatusID.STANDBAY:

        # 管理データのステータスを変更
        user_manage_list_change_status(username, UserStatusID.CALL_GEMINI)

        gemini_thread = threading.Thread(target=gemini_thread_func, args=(username,))
        gemini_thread.start()

    # 高速トロッコ中は他コマンドを受け付けない
    elif status_id == UserStatusID.SPEED_MINECART_EXECUTE:

        send_data_list = [
            "こんにちは！マイクラマネージャーです。",
            "現在、高速トロッコ利用中のため、",
            "他機能の受付ができません。",
            "トロッコを降りて、高速トロッコを",
            "終了してから、お声がけくださいね。"
        ]

        # チャットにメッセージ送信
        send_minecraft_chat(send_data_list, analyze_result.message_user, False)

    else:
        pass

    return 0


# chat gpt呼び出し処理
# arg: チャット解析結果データ, コンフィグデータ
# ret: 0
def event_tbl_func_call_chat_gpt_old(analyze_result, conf_data_result):

    send_data_list = [
        "こんにちは！",
        "マイクラマネージャーです。",
        "chatgptはAI機能に統合されましたので、",
        "利用したい場合は、「ai」と入力",
        "してくださいね。",
    ]

    # チャットにメッセージ送信
    send_minecraft_chat(send_data_list, analyze_result.message_user, False)

    return 0


# コマンドパラメータ処理
# arg: チャット解析結果データ, コンフィグデータ
# ret: 0
def event_tbl_func_cmd_param(analyze_result, conf_data_result):

    event_process_sub(analyze_result, conf_data_result)

    return 0


# 座標情報の処理
# arg: チャット解析結果データ, コンフィグデータ
# ret: 0
def event_tbl_func_pos_info(analyze_result, conf_data_result):

    send_data_list = []
    send_data_list.append(analyze_result.message_data)

    # チャットにメッセージ送信
    send_minecraft_chat(send_data_list, analyze_result.message_user, True)

    return 0


# 高速トロッコ　トロッコ乗車状態確認コマンドの結果受信処理
# arg: チャット解析結果データ, コンフィグデータ
# ret: 0
def event_tbl_func_pos_info_on_minecart(analyze_result, conf_data_result):

    # ユーザーとコマンドの取得
    username = analyze_result.message_user
    command = analyze_result.message_data

    # メッセージ文言の初期化
    send_data_list = []

    # 現在のステータスID取得
    user_status_id_now = UserStatusID.ERROR
    for manage_user_obj in user_manage_list:
        if manage_user_obj.name == username:
            user_status_id_now = manage_user_obj.status_id

    # 高速トロッコ準備ステータス時
    if user_status_id_now == UserStatusID.CHECK_ON_THE_MINECART:

        # on の場合（トロッコに乗っている場合）
        if command == "on":
            send_data_list.append("承認依頼を各ユーザーに送信しました。")
            send_data_list.append("承認されるまで、そのままでお待ちください。")
            send_data_list.append("本状態はトロッコを降りても")
            send_data_list.append("キャンセルされないため、注意が必要です。")
            send_data_list.append("キャンセルしたい場合は、任意の文字を")
            send_data_list.append("入力してください。")
            
            # ユーザーステータスを高速トロッコ承認待ちに変更
            next_user_status = UserStatusID.SPEED_MINECART_WAIT_ACCEPT
            user_manage_list_change_status(username, next_user_status)

            # 承認依頼送信の通知を申請者に送信
            send_minecraft_chat(send_data_list, username, False)

            # 他ユーザーに対して、高速トロッコの承認要求を飛ばす
            send_data_list = []
            send_data_list.append(username + "さんが高速トロッコを")
            send_data_list.append("利用したいようです。")
            send_data_list.append("承認する場合は、yesと入力して")
            send_data_list.append("申請を承認してください。")
            send_data_list.append("却下する場合は、")
            send_data_list.append("yes以外を入力してください。")

            # 現在ログイン中のユーザー全てに送り、ステータスを高速トロッコ承認にする
            login_user_count = 0
            for user_manage_obj in user_manage_list:
                if user_manage_obj.login == True:

                    # ログイン中の他ユーザー
                    if user_manage_obj.name != username:

                        # メッセージ送信
                        send_minecraft_chat(send_data_list, user_manage_obj.name, False)

                        # ログイン中の他ユーザーのステータスを高速トロッコ承認にする
                        # user_manage_obj.status_id_backup = user_manage_obj.status_id
                        user_manage_list_change_status(user_manage_obj.name, UserStatusID.SPEED_MINECART_ACCEPT_OR_REJECT)

                        # 承認を飛ばす先を保持する
                        user_manage_obj.data_dict["destination_username"] = username

                        # カウントインクリメント
                        login_user_count = login_user_count + 1

            # 何人の承認が必要か、自分の領域にデータを保持する　また、承認受け入れの準備をする
            for user_manage_obj in user_manage_list:
                if user_manage_obj.name == username:

                    # 何人の承認が必要か保持
                    user_manage_obj.data_dict["accept_number"] = login_user_count

                    # 承認受け入れの準備
                    user_manage_obj.data_dict["accept_count"] = 0

        # outの場合はキャンセル扱い（トロッコに乗っていない）
        else:
            send_data_list.append("トロッコへの乗車が確認できなかったため、")
            send_data_list.append("処理をキャンセルします。")
            send_data_list.append("ご用の際は、")
            send_data_list.append("またいつでも呼んでくださいね。")

            # チャットにメッセージ送信
            send_minecraft_chat(send_data_list, username, False)

            # 管理データのステータス変更
            next_user_status = UserStatusID.STANDBAY
            user_manage_list_change_status(username, next_user_status)

    # 高速トロッコ実行中ステータス dataコマンド結果受信
    elif user_status_id_now == UserStatusID.SPEED_MINECART_EXECUTE:

        # メッセージ文言の初期化
        send_data_list = []

        # トロッコに乗っている場合
        if command == "on":

            # 処理なし
            pass

        # トロッコから降りていた場合
        else:

            # コマンド発行しているタイマー削除
            timer_data_dict = {"command_str":"data get entity " + username}
            timer_delete(username, timer_data_dict)

            # 時間加速を終了するコマンドと、メッセージを準備
            send_data_list.append("高速トロッコを終了しました。")
            send_command_str = "tick rate 20"

            # 高速トロッコ効果時間のタイマー削除
            func_arg_dict = {"username":username}
            timer_delete_regist_function(username, timer_regist_func_speed_minecart_time_up, func_arg_dict)

            # 時間加速を終了するコマンド送信
            send_minecraft_command(send_command_str)

            # クールタイムステータスのセット
            for user_manage_data in user_manage_list:
                if user_manage_data.name == username:
                    user_manage_data.data_dict["speed_minecart_cool_time_flg"] = True

            # クールタイムリセットのタイマーをセット
            func_arg_dict = {"username":username}
            timer_set_regist_function(180.0, timer_regist_func_speed_minecart_cool_time_reset, func_arg_dict, False, username)

            # ログインユーザー全員に通知メッセージ送信
            for user_manage_data in user_manage_list:
                if user_manage_data.login == True:
                    send_minecraft_chat(send_data_list, user_manage_data.name, False)

            # 申請者のステータスをスタンバイに変更
            next_user_status = UserStatusID.STANDBAY
            user_manage_list_change_status(username, next_user_status)

    else:
        log_output(LOG_LEVEL_INFO, log_manager.LOG_MSG_INFO_MAIN_EVENT_NOT_SPEED_MINECART_STANDBY + " user_status=" + str(user_status_id_now))


    return 0



# 処理キャンセルメッセージ生成
# arg: ユーザー名
# ret: キャンセルメッセージ文字列のリスト
def event_cancel_message_create(username):

    send_data_list = [
        username + "さん！！！",
        "私も呼んでみました。(^_^)",
        "それでは、受付をキャンセルします。",
        "ご用の際は、またいつでもお呼びくださいね。"
    ]

    return send_data_list


# 不明なコマンド入力時のメッセージ生成
# arg: なし
# ret: メッセージ文字列のリスト
def event_unknown_command_message_create():

    send_data_list = [
        "すみません。よく分かりませんでした。",
        "処理をキャンセルします。",
        "コマンドを再度ご確認の上、",
        "指定文字列の入力をお願いします。"
    ]

    return send_data_list

# 別ユーザーへのワープ受付 選択メニュー表示
# arg: チャット解析結果データ
# ret: 0
def event_sub_func_warp_to_user(analyze_result):

    global user_manage_list

    # ユーザー名とメッセージ抽出
    username = analyze_result.message_user
    message_data = analyze_result.message_full_data

    next_user_status = UserStatusID.ERROR
    
    # ログイン中のユーザーを取得
    login_user_list = get_login_user_list()

    # 自分以外のユーザーがいる場合
    if len(login_user_list) > 1:
        # 自分を省く
        for i, login_user in enumerate(login_user_list):
            if username == login_user:
                break

        del login_user_list[i]

        # ログイン中ユーザー一覧を文字列に変換
        login_user_list_str = ""
        for i, login_user in enumerate(login_user_list, start=1):
            login_user_list_str = login_user_list_str + ("{index}:{name}").format(index=i, name=login_user) + "\n"

        send_data_str = (
            "ワープ先を数字で選んでください。\n"
            "{userlist}"
        ).format(userlist=login_user_list_str)

        # ログインユーザーリストを保持
        user_data_dict = get_user_manage_data_dict(username)
        user_data_dict["warp_user_list"] = login_user_list

        # 送信文字列をリスト化（\nで）
        send_data_list = send_data_str.split("\n")
        next_user_status = UserStatusID.WARP_TO_USER

    # 自分以外のユーザーがいない場合
    else:
        send_data_str = (
            "他にログイン中ユーザーがいません。\n"
            "処理をキャンセルします。\n"
            "ご用の際は、いつでもお声がけくださいね！\n"
        )

        # 送信文字列をリスト化（\nで）
        send_data_list = send_data_str.split("\n")
        next_user_status = UserStatusID.STANDBAY

    # チャットに文字列を送信して、ユーザーステータスを変更
    send_minecraft_chat(send_data_list, username, False)
    user_manage_list_change_status(username, next_user_status)

    return 0


# メインメニュー選択結果の処理
# arg: チャット解析結果データ, コンフィグデータ
# ret: 0
def event_user_status_tbl_func_select_main_menew(analyze_result, conf_data_result):

    # ユーザーとコマンドの取得
    username = analyze_result.message_user
    command = analyze_result.message_data

    # メッセージ文言の初期化
    send_data_list = []

    # 1:デスルーラ
    if command == "1" or command == "１":
        send_data_list.append("デスルーラですね？承知しました。")
        send_data_list.append(username + "さん宛てに、")
        send_data_list.append("killコマンドを発行します。")
        send_data_list.append("心の準備はよろしいですか？")
        send_data_list.append("準備ができたら")
        send_data_list.append("yesと入力して教えてください。")
        send_data_list.append("yes以外を入力すると")
        send_data_list.append("キャンセルすることができます。")

        # 管理データのステータス変更
        next_user_status = UserStatusID.KILL_CMD_STANDBY
        user_manage_list_change_status(username, next_user_status)

        # チャットにメッセージ送信
        send_minecraft_chat(send_data_list, username, False)

    # 2:座標随時送信
    elif command == "2" or command == "２":
        send_data_list.append("承知しました。")
        send_data_list.append(username + "さん宛てに、")
        send_data_list.append("一定間隔で現在の座標を")
        send_data_list.append("送信します。")
        send_data_list.append("座標送信中、チャットに任意の文字を")
        send_data_list.append("送信するとキャンセルできます。")
        send_data_list.append("準備ができましたら、")
        send_data_list.append("yesと入力して教えてください。")

        # 管理データのステータス変更
        next_user_status = UserStatusID.SEND_POS_STANDBY
        user_manage_list_change_status(username, next_user_status)

        # チャットにメッセージ送信
        send_minecraft_chat(send_data_list, username, False)

    # 3:高速トロッコ
    elif command == "3" or command == "３":
 
        hit_flg = False
        speed_minecrat_status_id_list = [
            UserStatusID.SPEED_MINECART_STANDBY,
            UserStatusID.CHECK_ON_THE_MINECART,
            UserStatusID.SPEED_MINECART_WAIT_ACCEPT,
            UserStatusID.SPEED_MINECART_EXECUTE
        ]

        # 他に、ステータスが高速トロッコ関連のユーザーがいないかチェック
        for user_manage in user_manage_list:
            for speed_minecrat_status_id in speed_minecrat_status_id_list:

                # 自分自身を省く
                if user_manage.name != username:
                    if user_manage.status_id == speed_minecrat_status_id:
                        hit_flg = True

        # 他に高速トロッコ関連のステータスのユーザーがいない
        if hit_flg == False:
            # 高速トロッコのクールタイム中ではないかチェック
            for user_manage in user_manage_list:
                if user_manage.name == username:
                    # 高速トロッコのクールタイム中ではない
                    if user_manage.data_dict["speed_minecart_cool_time_flg"] == False:
                        send_data_list.append("承知しました。高速トロッコは")
                        send_data_list.append("時間の流れを操作して、トロッコを")
                        send_data_list.append("高速にする機能です。5分経過または")
                        send_data_list.append("トロッコを降りると解除されます。")
                        send_data_list.append("他プレイヤーにも影響するため")
                        send_data_list.append("利用には他プレイヤーの承認も")
                        send_data_list.append("必要です。トロッコに乗りましたら、")
                        send_data_list.append("yesと入力して教えてください。")
                        send_data_list.append("それ以外が入力されるとキャンセルします。")

                        # 管理データのステータス変更
                        next_user_status = UserStatusID.SPEED_MINECART_STANDBY
                        user_manage_list_change_status(username, next_user_status)

                    # 高速トロッコのクールタイム中
                    else:
                        send_data_list.append("現在高速トロッコのクールタイム中のため")
                        send_data_list.append("利用することができません。")
                        send_data_list.append("もうしばらくしてから、お試しください。")

                        # 管理データのステータス変更
                        next_user_status = UserStatusID.STANDBAY
                        user_manage_list_change_status(username, next_user_status)

        # 他に高速トロッコの準備を進めているユーザー、または高速トロッコ利用中のユーザーがいる
        else:
            send_data_list.append("他に高速トロッコ利用の準備を")
            send_data_list.append("進めているユーザーがいるため、")
            send_data_list.append("現在は利用できません。")
            send_data_list.append("受付をキャンセルいたします。")
            send_data_list.append("ご用の際は、またいつでもお呼びくださいね。")

            # 管理データのステータス変更
            next_user_status = UserStatusID.STANDBAY
            user_manage_list_change_status(username, next_user_status)

        # チャットにメッセージ送信
        send_minecraft_chat(send_data_list, username, False)

    # 4:他ユーザーの場所へワープ
    elif command == "4" or command == "４":

        # 長いので関数にまとめた
        event_sub_func_warp_to_user(analyze_result)

    # 5:呼び方一覧
    elif command == "5" or command == "５":
        send_data_list.append("これらの呼び方で反応できます。")

        for manager_name in message_analyze.mainecraft_manager_name_list:
            send_data_list.append(manager_name)

        send_data_list.append("お好きな呼び方でお呼びくださいね。")

        # 管理データのステータス変更
        next_user_status = UserStatusID.STANDBAY
        user_manage_list_change_status(username, next_user_status)

        # チャットにメッセージ送信
        send_minecraft_chat(send_data_list, username, False)

    # 99: キャンセル
    elif command == "99" or command == "９９":
        # キャンセルメッセージ生成
        send_data_list = event_cancel_message_create(username)

        # 管理データのステータス変更
        next_user_status = UserStatusID.STANDBAY
        user_manage_list_change_status(username, next_user_status)

        # チャットにメッセージ送信
        send_minecraft_chat(send_data_list, username, False)

    # 不明なコマンド
    else:
        # 不明なコマンド入力時のメッセージ生成
        send_data_list = event_unknown_command_message_create()

        # 管理データのステータス変更
        next_user_status = UserStatusID.STANDBAY
        user_manage_list_change_status(username, next_user_status)

        # チャットにメッセージ送信
        send_minecraft_chat(send_data_list, username, False)

    return 0


# killコマンドの実行確定
# arg: チャット解析結果データ, コンフィグデータ
# ret: 0
def event_user_status_tbl_func_execute_kill(analyze_result, conf_data_result):

    # ユーザーとコマンドの取得
    username = analyze_result.message_user
    command = analyze_result.message_data

    # メッセージ文言の初期化
    send_data_list = []

    # yes の場合
    if command == "yes":
        # killを実行
        send_minecraft_command("kill " + username)

    # yes以外の場合はキャンセル扱い
    else:
        send_data_list.append("yes以外の文字が入力されたため、")
        send_data_list.append("処理をキャンセルします。")
        send_data_list.append("ご用の際は、")
        send_data_list.append("またいつでも呼んでくださいね。")

        # チャットにメッセージ送信
        send_minecraft_chat(send_data_list, username, False)

    # 管理データのステータス変更
    next_user_status = UserStatusID.STANDBAY
    user_manage_list_change_status(username, next_user_status)

    return 0


# 座標送信の実行確定
# arg: チャット解析結果データ, コンフィグデータ
# ret: 0
def event_user_status_tbl_func_execute_send_pos(analyze_result, conf_data_result):

    # ユーザーとコマンドの取得
    username = analyze_result.message_user
    command = analyze_result.message_data

    # メッセージ文言の初期化
    send_data_list = []

    # yes の場合
    if command == "yes":

        # タイマーにコマンドセット
        timer_data_dict = {"command_str":"data get entity " + username + " Pos"}
        timer_set(TimerEndEventID.CALL_CMD_ENDLESS, 0.1, timer_data_dict, True, username)

        # ユーザーステータスを座標送信に変更
        next_user_status = UserStatusID.SEND_POS
        user_manage_list_change_status(username, next_user_status)

    # yes以外の場合はキャンセル扱い
    else:
        send_data_list.append("yes以外の文字が入力されたため、")
        send_data_list.append("処理をキャンセルします。")
        send_data_list.append("ご用の際は、")
        send_data_list.append("またいつでも呼んでくださいね。")

        # チャットにメッセージ送信
        send_minecraft_chat(send_data_list, username, False)

        # 管理データのステータス変更
        next_user_status = UserStatusID.STANDBAY
        user_manage_list_change_status(username, next_user_status)

    return 0


# 座標送信中のメッセージ受付　何かしらのメッセージを受けた場合、座標送信を停止する
# arg: チャット解析結果データ, コンフィグデータ
# ret: 0
def event_user_status_tbl_func_sending_pos(analyze_result, conf_data_result):

    # ユーザーとコマンドの取得
    username = analyze_result.message_user
    command = analyze_result.message_data

    # メッセージ文言の初期化
    send_data_list = []

    # チャットメッセージの準備
    send_data_list.append("座標の送信処理を中断します。")
    send_data_list.append("ご用の際は、")
    send_data_list.append("またいつでも呼んでくださいね。")

    # チャットにメッセージ送信
    send_minecraft_chat(send_data_list, username, False)

    # コマンド送信しているタイマーを削除
    timer_data_dict = timer_data_dict = {"command_str":"data get entity " + username + " Pos"}
    timer_delete(username, timer_data_dict)

    # 管理データのステータス変更
    next_user_status = UserStatusID.STANDBAY
    user_manage_list_change_status(username, next_user_status)

    return 0


# 高速トロッコ準備処理　利用決定処理
# arg: チャット解析結果データ, コンフィグデータ
# ret: 0
def event_user_status_tbl_func_standby_speed_minecart(analyze_result, conf_data_result):

    # ユーザーとコマンドの取得
    username = analyze_result.message_user
    command = analyze_result.message_data

    # メッセージ文言の初期化
    send_data_list = []

    # yes の場合
    if command == "yes":
        # ユーザーステータスをトロッコ乗車確認に変更
        next_user_status = UserStatusID.CHECK_ON_THE_MINECART
        user_manage_list_change_status(username, next_user_status)

        # トロッコに乗っているか確認コマンドを送信
        send_command_str = "data get entity " + username
        send_minecraft_command(send_command_str)

    # yes以外の場合はキャンセル扱い
    else:
        send_data_list.append("yes以外の文字が入力されたため、")
        send_data_list.append("処理をキャンセルします。")
        send_data_list.append("ご用の際は、")
        send_data_list.append("またいつでも呼んでくださいね。")

        # チャットにメッセージ送信
        send_minecraft_chat(send_data_list, username, False)

        # 管理データのステータス変更
        next_user_status = UserStatusID.STANDBAY
        user_manage_list_change_status(username, next_user_status)

    return 0


# 高速トロッコ　承認待ち状態に申請者からメッセージ受信
# arg: チャット解析結果データ, コンフィグデータ
# ret: 0
def event_user_status_tbl_func_wait_accept_speed_minecart(analyze_result, conf_data_result):

    # ユーザーとコマンドの取得
    username = analyze_result.message_user
    command = analyze_result.message_data

    # メッセージ文言の初期化
    send_data_list = []
    all_user_send_data_list = []

    # 処理キャンセルのメッセージ
    send_data_list.append("入力を確認しましたので、")
    send_data_list.append("申請を取り下げ、処理をキャンセルします。")
    send_data_list.append("ご用の際は、またいつでもお呼びくださいね。")
    send_minecraft_chat(send_data_list, username, False)

    # 高速トロッコ承認 却下状態のユーザーステータスを元に戻す
    for user_manage_obj in user_manage_list:
        if user_manage_obj.status_id == UserStatusID.SPEED_MINECART_ACCEPT_OR_REJECT:
            user_manage_list_back_status(user_manage_obj.name)

    # ログイン中のユーザー全員に、高速トロッコ申請の取り下げを通知
    all_user_send_data_list.append("高速トロッコの申請が取り下げられました。")
    for user_manage_obj in user_manage_list:
        if user_manage_obj.login == True:
            send_minecraft_chat(all_user_send_data_list, user_manage_obj.name, False)

    # 管理データのステータス変更
    next_user_status = UserStatusID.STANDBAY
    user_manage_list_change_status(username, next_user_status)

    return 0


# 高速トロッコ　承認 or 拒否処理
# arg: チャット解析結果データ, コンフィグデータ
# ret: 0
def event_user_status_tbl_func_accept_speed_minecart(analyze_result, conf_data_result):

    # ユーザーとコマンドの取得
    username = analyze_result.message_user
    command = analyze_result.message_data

    # メッセージ文言の初期化
    send_data_list = []

    # 承認した場合
    if command == "yes":

        # 承認を飛ばす先を確認
        for user_manage_obj in user_manage_list:
            if user_manage_obj.name == username:
                destination_username = user_manage_obj.data_dict["destination_username"]

        # 承認を飛ばす
        for user_manage_obj in user_manage_list:
            if user_manage_obj.name == destination_username:
                user_manage_obj.data_dict["accept_count"] = user_manage_obj.data_dict["accept_count"] + 1

        # 承認送信を承認した人に通知
        send_data_list.append("承認を送信しました。")
        send_minecraft_chat(send_data_list, username, False)

        # 承認者のステータスを元に戻す
        user_manage_list_back_status(username)

    # 却下した場合
    else:

        # 却下を飛ばす先を確認
        for user_manage_obj in user_manage_list:
            if user_manage_obj.name == username:
                destination_username = user_manage_obj.data_dict["destination_username"]

        # 却下をセット
        for user_manage_obj in user_manage_list:
            if user_manage_obj.name == destination_username:
                user_manage_obj.data_dict["accept_count"] = -1

        # 管理データのステータスは、拒否受信処理で、全員一括変更する

    return 0


# AI機能実行中にユーザーの入力を受信
# arg: チャット解析結果データ, コンフィグデータ
# ret: 0
def event_user_status_tbl_func_ai_param(analyze_result, conf_data_result):

    # ユーザー名とメッセージ抽出
    username = analyze_result.message_user
    message_data = analyze_result.message_full_data

    put_dict = {"input_str":message_data, "question_user":username}
    
    # ユーザー管理データリストから対象ユーザーをサーチ～対象ユーザーのキューにぷっと
    for user_manage_obj in user_manage_list:
        if user_manage_obj.name == username:
            user_manage_obj.to_chatgpt_queue.put(put_dict)

    return 0


# Gemini実行中にユーザーの入力を受信
# arg: チャット解析結果データ, コンフィグデータ
# ret: 0
def event_user_status_tbl_func_gemini_param(analyze_result, conf_data_result):

    # メッセージをキューに入れる
    global gemini_queue
    gemini_queue.put(analyze_result.message_full_data)

    return 0


# チャットGPT実行中にユーザーの入力を受信
# arg: チャット解析結果データ, コンフィグデータ
# ret: 0
def event_user_status_tbl_func_chat_gpt_param(analyze_result, conf_data_result):

    # メッセージをキューに入れる
    global chat_gpt_queue
    chat_gpt_queue.put(analyze_result.message_full_data)

    return 0


# ログイン中のユーザーリストを返却する
# arg: なし
# ret: ログイン中のユーザーリスト(list[str])
def get_login_user_list():

    login_user_list = []

    for user_manage_obj in user_manage_list:
        if user_manage_obj.login == True:
            login_user_list.append(user_manage_obj.name)

    return login_user_list


# ユーザー管理リストのユーザーごとの保持データを取得
# arg: ユーザー名
# ret: 対象ユーザーの保持データ(dict)
def get_user_manage_data_dict(username):

    global user_manage_list

    data_dict = {}

    # 特定ユーザー名でサーチ
    for user_manage_obj in user_manage_list:
        if username == user_manage_obj.name:
            data_dict = user_manage_obj.data_dict

    return data_dict


# ワープ先ユーザーを決定し、ワープ実行
# arg: チャット解析結果データ, コンフィグデータ
# ret: 0
def event_user_status_tbl_func_warp_to_user(analyze_result, conf_data_result):

    # ユーザー名とメッセージ抽出
    username = analyze_result.message_user
    message_data = analyze_result.message_full_data

    next_user_status = UserStatusID.ERROR
    send_data_list = []

    # ユーザー管理情報に保持しているデータを取得
    user_data_dict = get_user_manage_data_dict(username)
    login_user_list = user_data_dict["warp_user_list"]

    # 入力データが整数変換可能の場合
    if message_data.isdigit() == True:
        # 数値に変換し、範囲内かチェック
        select_num = int(message_data)
        if select_num > 0 and len(login_user_list) >= select_num:
            # ワープコマンド形成
            warp_target_name = login_user_list[select_num-1]
            warp_source_name = username
            warp_command_str = ("tp {source} {target}").format(source=warp_source_name, target=warp_target_name)

            # 送信メッセージ形成
            send_data_str = (
                "{source}さんを\n"
                "{target}さんの場所へ\n"
                "テレポートさせました。\n"
            ).format(source=warp_source_name, target=warp_target_name)
            send_data_list = send_data_str.split("\n")

            # コマンド実行
            send_minecraft_command(warp_command_str)
            log_output(LOG_LEVEL_INFO, log_manager.LOG_MSG_INFO_MAIN_WARP_COMPLETED + ("select number='{number}' source='{source}' target='{target}'").format(number=str(select_num), source=warp_source_name, target=warp_target_name))

        # ログインユーザーリストの範囲外だった場合
        else:
            # 送信メッセージ形成
            send_data_str = (
                "対象外の数字が入力されました。\n"
                "処理をキャンセルします。\n"
                "ご用の際は、いつでもお声がけくださいね！\n"
            )
            send_data_list = send_data_str.split("\n")
            log_output(LOG_LEVEL_WARNING, log_manager.LOG_MSG_WARNING_MAIN_WARP_SELECT_NG_OUT_OF_RANGE + "select number=" + str(select_num))

    # 整数に変換できない場合
    else:
        # 送信メッセージ形成
        send_data_str = (
            "整数への変換に失敗しました。\n"
            "処理をキャンセルします。\n"
            "ご用の際は、いつでもお声がけくださいね！\n"
        )
        send_data_list = send_data_str.split("\n")
        log_output(LOG_LEVEL_WARNING, log_manager.LOG_MSG_WARNING_MAIN_WARP_SELECT_NG_CONVERT_NUMBER + "receive str=" + message_data)

    # 使用が終わったため、保持データを削除
    del user_data_dict["warp_user_list"]

    # チャットに文字列を送信して、ユーザーステータスを変更
    send_minecraft_chat(send_data_list, username, False)
    next_user_status = UserStatusID.STANDBAY
    user_manage_list_change_status(username, next_user_status)

    return 0

# 関数テーブル
# 基本とメインメニューの関数テーブル
# アナライズのメッセージIDで分岐
event_process_func_tbl = [
    dummy_func,                             # SEVER_CHAT
    event_tbl_func_login,                   # LOGIN
    event_tbl_func_logout,                  # LOGOUT
    event_tbl_func_call_manager,            # CALL_MANAGER
    event_tbl_func_cmd_param,               # CMD_PARAM
    event_tbl_func_pos_info,                # POS_INFO
    event_tbl_func_pos_info_on_minecart,    # POS_INFO_ON_MINECART
    event_tbl_func_call_chat_gpt_old,       # CALL_CHAT_GPT
    event_tbl_func_call_gemini,             # CALL_GEMINI
    event_tbl_func_call_ai                  # CALL_AI

]

# メインメニュー以降の関数テーブル（ユーザーのステータスにより実行funcを分岐）
# ユーザーのステータスで分岐
event_process_user_status_func_tbl = [
    dummy_func,                                                         # STANDBY
    event_user_status_tbl_func_select_main_menew,                       # RES_WAIT_MAIN_MENEW
    event_user_status_tbl_func_execute_kill,                            # KILL_CMD_STANDBY
    event_user_status_tbl_func_execute_send_pos,                        # SEND_POS_STANDBY
    event_user_status_tbl_func_sending_pos,                             # SEND_POS
    event_user_status_tbl_func_standby_speed_minecart,                  # SPEED_MINECART_STANDBY
    dummy_func,                                                         # CHECK_ON_THE_MINECART
    event_user_status_tbl_func_wait_accept_speed_minecart,              # SPEED_MINECART_WAIT_ACCEPT
    event_user_status_tbl_func_accept_speed_minecart,                   # SPEED_MINECART_ACCEPT_OR_REJECT
    dummy_func,                                                         # SPEED_MINECART_EXECUTE
    event_user_status_tbl_func_chat_gpt_param,                          # CALL_CHAT_GPT
    event_user_status_tbl_func_gemini_param,                            # CALL_GEMINI
    event_user_status_tbl_func_ai_param,                                # CALL_AI
    event_user_status_tbl_func_warp_to_user                             # WARP_TO_USER
]



# マイクラチャットに基づいたイベント処理
# arg: チャット解析結果データ, コンフィグデータ
# ret: コンフィグデータ更新なし:0 コンフィグデータの更新が発生:1
def event_process(analyze_result, conf_data_result):

    ret = 0

    # テーブルのインデックスを超えないように（255 WANTEDが超える）
    if len(event_process_func_tbl)-1 >= analyze_result.message_id:
        function = event_process_func_tbl[analyze_result.message_id]
        ret = function(analyze_result, conf_data_result)

    return ret


# マイクラチャットに基づいたイベント処理のサブ(メインメニュー以降の処理)
# arg: チャット解析結果データ, コンフィグデータ
# ret: コンフィグデータ更新なし:0 コンフィグデータの更新が発生:1
def event_process_sub(analyze_result, conf_data_result):

    # 管理データから、ユーザー情報取得
    username = analyze_result.message_user
    user_status_id = user_manage_list_get_status(username)

    # ステータスIDが取得出来なかった場合
    if user_status_id == UserStatusID.ERROR:
        # 処理を中止する(メッセージを破棄)
        log_info_str = "user=" + username + " message_id=" + str(analyze_result.message_id) + " message_data" + analyze_result.message_data
        log_output(LOG_LEVEL_WARNING, log_manager.LOG_MSG_WARNING_MAIN_EVENT_PROCESS_SUB_FAIELD_NO_USER_STATUS + " " + log_info_str)
        return 0

    function = event_process_user_status_func_tbl[user_status_id]
    ret = function(analyze_result, conf_data_result)

    return ret


# ユーザーステータスをチェックし、常時実行する処理がある場合は実行する（タイマー処理や、座標送信など）
# arg: なし
# ret: 0
def check_user_status_execute_process():

    # 全員のユーザーステータスを確認していく
    for user_manage_data in user_manage_list:

        # # 座標送信中のステータス
        # if user_manage_data.status_id == UserStatusID.SEND_POS:
        #     # 対象ユーザーの座標確認コマンド発行
        #     command_str = "data get entity " + user_manage_data.name + " Pos"
        #     send_minecraft_command(command_str)

        # 高速トロッコ承認待ちのステータス
        if user_manage_data.status_id == UserStatusID.SPEED_MINECART_WAIT_ACCEPT:

            # 却下が発行された場合
            if user_manage_data.data_dict["accept_count"] < 0:

                # 却下メッセージログインユーザー全員に送信
                send_data_list = []
                send_data_list.append("高速トロッコ利用の申請が却下されました。")

                for user_manage_data2 in user_manage_list:
                    if user_manage_data2.login == True:
                        send_minecraft_chat(send_data_list, user_manage_data2.name, False)

                # 申請者のステータスを、STANDBYに変更
                user_manage_list_change_status(user_manage_data.name, UserStatusID.STANDBAY)

                # 他の全員のステータスをバックアップで戻す（STANDBYの場合はそのまま）
                for user_manage_data2 in user_manage_list:
                    user_manage_list_back_status(user_manage_data2.name)

            # 承認が必要数（全員）に達した場合
            elif user_manage_data.data_dict["accept_count"] == user_manage_data.data_dict["accept_number"]:

                # 時間加速コマンド発行準備 & 通知メッセージ準備
                command_str = "tick rate 200"
                send_data_list = [
                    "高速トロッコの承認が",
                    "必要数に達しました。",
                    "時間加速を開始します。"
                ]

                # ログインユーザー全員に通知メッセージ送信
                for user_manage_data2 in user_manage_list:
                    if user_manage_data2.login == True:
                        send_minecraft_chat(send_data_list, user_manage_data2.name, False)

                # 申請者のステータス変更
                next_user_status = UserStatusID.SPEED_MINECART_EXECUTE
                user_manage_list_change_status(user_manage_data.name, next_user_status)

                # 時間加速コマンド送信
                send_minecraft_command(command_str)

                # 高速トロッコ効果時間のタイマーセット
                func_arg_dict = {"username":user_manage_data.name}
                timer_set_regist_function(300.0, timer_regist_func_speed_minecart_time_up, func_arg_dict, False, user_manage_data.name)

                # トロッコに乗っているかの確認目的で、dataコマンド発行
                timer_data_dict = {"command_str":"data get entity " + user_manage_data.name}
                timer_set(TimerEndEventID.CALL_CMD_ENDLESS, 0.1, timer_data_dict, True, user_manage_data.name)

    return 0


def main():

    global tmux_session_name
    global tmux_window_name

    # 初期準備
    ret = log_manager.log_file_init()
    if ret == -1:
        print("Fatal Error!!! can't execute program")
        return -1

    ret = file_manager.conf_file_init()
    if ret == -1:
        print("Fatal Error!!! can't execute program")
        return -1
    
    # コンフィグファイル作成のため終了　設定を促す
    elif ret == 1:
        print(log_manager.LOG_MSG_INFO_FILE_CREATED_CONF_FILE)
        print("Try again after setting")
        return 0

    # 設定ファイルの読み込み
    conf_data_result = file_manager.load_conf_file()

    if conf_data_result.status == -1:
        print("Fatal Error!!! can't execute program")
        return -1
    
    # ユーザーを管理データに追加
    for conf_user_name in conf_data_result.data["minecraft_users"]:
        user_manage_data = UserMnage()
        user_manage_data.name = conf_user_name
        user_manage_data.login = False
        user_manage_list.append(user_manage_data)

    # tmuxの情報をグローバル変数にセット
    tmux_session_name = conf_data_result.data["tmux_session_name"]
    tmux_window_name = conf_data_result.data["tmux_window_name"]

    # マイクラログファイルの読み取り、過去のメッセージは読み飛ばす
    read_data_list = file_manager.get_file_all(conf_data_result.data["minecraft_logfile_path"])
    conf_data_result.data["minecraft_logfile_read_line_index"] = len(read_data_list)

    # 読み飛ばした後のindexをファイルに反映
    file_manager.update_conf_file(conf_data_result.data)

    # タイマー管理スレッド開始
    timer_manage_thread = threading.Thread(target=timer_manage_thread_func)
    timer_manage_thread.daemon = True
    timer_manage_thread.start()

    # AIが喋るようスレッド開始
    ai_say_thread = threading.Thread(target=send_minecraft_chat_all_user_say_ai_thread)
    ai_say_thread.daemon = True
    ai_say_thread.start()

    # メインループ開始
    timestamp_buff = 0
    print("---Start of main program loop---")
    log_output(LOG_LEVEL_INFO, "---Start of main program loop---")
    while file_manager.check_exists_loop_flg_file() == True:

        # ユーザー関連で、常時実行する処理がある場合実行する（タイマー処理や、座標送信など）
        check_user_status_execute_process()

        # マイクラログファイルのタイムスタンプ読み取り
        timestamp = file_manager.get_time_stamp(conf_data_result.data["minecraft_logfile_path"])

        # タイムスタンプ読み取り失敗
        if timestamp == -1:
            log_output(LOG_LEVEL_ERROR, log_manager.LOG_MSG_ERROR_MAIN_READ_TIEMSTAMP_FAILED)
            return -1

        # コンフィグデータ変更フラグ（主に読み取り位置更新のサインに使う）
        config_file_index_edit_flg = False

        # ファイルが更新されていた場合
        if timestamp > timestamp_buff:
            # タイムスタンプアップデート
            timestamp_buff = timestamp
            
            next_load_index = conf_data_result.data["minecraft_logfile_read_line_index"]
            minecraft_log_file_path = conf_data_result.data["minecraft_logfile_path"]

            # マイクラログファイルのトータル行数取得
            minecraft_log_file_total_line = file_manager.count_file_line(minecraft_log_file_path)

            data_list = []

            # ログファイルがローテートしてない場合
            # if next_load_index < len(read_data_list):
            if next_load_index < minecraft_log_file_total_line:
                # 新規に追加された行を抽出
                # 途中行から最後までファイルの内容を取得
                data_list = file_manager.get_file_select_line_to_the_end(minecraft_log_file_path ,next_load_index+1)

                # ファイルの読み取りに失敗
                if data_list == None:
                    log_output(LOG_LEVEL_ERROR, log_manager.LOG_MSG_ERROR_MAIN_READ_FILE_DATA_FAILED)
                    return -1
                
                config_file_index_edit_flg = True

            # 更新がない場合
            elif next_load_index == minecraft_log_file_total_line:
                # 何もしない
                pass

            # ログファイルがローテートで新しくなった場合
            else:   # next_load_index > len(read_data_list)
                # 初期化してから読み取る
                next_load_index = 0
                conf_data_result.data["minecraft_logfile_read_line_index"] = 0

                # 全て新規のため、まるごと読み込む
                data_list = file_manager.get_file_all(minecraft_log_file_path)

                # ファイルの読み取りに失敗
                if data_list == None:
                    log_output(LOG_LEVEL_ERROR, log_manager.LOG_MSG_ERROR_MAIN_READ_FILE_DATA_FAILED)
                    return -1
                
                config_file_index_edit_flg = True
                
            count = next_load_index

            # 取得した行をループ（新規行）
            # for data_line in new_data_list:
            for data_line in data_list:
                analyze_result = message_analyze.analyze_main(data_line)

                # イベント処理
                result = event_process(analyze_result, conf_data_result)
                count = count + 1

        # confのindexに更新があった場合（新規行が追加されていた場合）
        if config_file_index_edit_flg == True:
            
            # confファイルのアップデート
            conf_data_result.data["minecraft_logfile_read_line_index"] = count
            file_manager.update_conf_file(conf_data_result.data)

    return 0


if __name__ == "__main__":
    main()