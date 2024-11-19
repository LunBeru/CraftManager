# ファイルを管理するモジュール

# import
import os
import json
import time
import log_manager
from log_manager import log_output
from log_manager import LOG_LEVEL_INFO
from log_manager import LOG_LEVEL_WARNING
from log_manager import LOG_LEVEL_ERROR

# 定数
PROGRAM_DATA_FILE_DIR_PATH = "./programData/"
CONF_FILE_NAME = "conf.json"
LOOP_FLG_FILE = "LOOP_FLG_FILE"
CHAT_GPT_FILE = "chat_gpt.json"
GREETINGS_FILE = "greetings.json"

class LoadJsonFileResult:
    status = -1
    data = {}


# 管理ファイルの初期準備
# arg: なし
# ret: 正常終了:0 コンフィグファイル作成:1 異常終了:-1
def conf_file_init():

    ret = 0

    # ファイルチェック　なければ作成
    try:
        # プログラムデータディレクトリ
        if os.path.exists(PROGRAM_DATA_FILE_DIR_PATH) == False:
            os.mkdir(PROGRAM_DATA_FILE_DIR_PATH)
            log_output(LOG_LEVEL_INFO, log_manager.LOG_MSG_INFO_FILE_CREATED_PROGRAM_DIR)


        # コンフィグファイル（json）
        conf_file_full_path = PROGRAM_DATA_FILE_DIR_PATH + CONF_FILE_NAME
        if os.path.exists(conf_file_full_path) == False:
            with open(conf_file_full_path, mode="w", encoding="utf-8") as file_obj:
                init_dict = {}
                init_dict["minecraft_logfile_read_line_index"] = 0
                init_dict["minecraft_logfile_path"] = "../logs/latest.log"
                init_dict["minecraft_users"] = []
                init_dict["tmux_session_name"] = ""
                init_dict["tmux_window_name"] = ""

                json.dump(init_dict, file_obj, ensure_ascii=False)

            log_output(LOG_LEVEL_INFO, log_manager.LOG_MSG_INFO_FILE_CREATED_CONF_FILE)
            ret = 1

        # ループフラグファイル
        # このファイルが存在する限り、ループを続ける（プログラム終了したい場合は、消せば良い）
        loop_flg_file_full_path = PROGRAM_DATA_FILE_DIR_PATH + LOOP_FLG_FILE
        with open(loop_flg_file_full_path, mode="w", encoding="utf-8") as file_obj:
            pass

        # chatGPTファイル
        chat_fpt_file_full_path = PROGRAM_DATA_FILE_DIR_PATH + CHAT_GPT_FILE
        if os.path.exists(chat_fpt_file_full_path) == False: 
            with open(chat_fpt_file_full_path, mode="w", encoding="utf-8") as file_obj:
                # init_dict = {"data":[]}
                # init_dict = {"history":[], "memory":[], "rule":[]}
                init_dict = {"memory": ""}
                json.dump(init_dict, file_obj, ensure_ascii=False)

    except OSError:
        log_output(LOG_LEVEL_ERROR, log_manager.LOG_MSG_ERROR_FILE_CONF_FILE_CREATE_FAILED)
        ret = -1

    except Exception as e:
        log_output(LOG_LEVEL_ERROR, log_manager.LOG_MSG_ERROR_UNKNOWN + " error obj:" + str(e))
        ret = -1

    return ret


# チャットGTPファイルの読み込み
# arg: なし
# ret: データのリスト
def load_chat_gpt_file():

    chat_gpt_file_full_path = PROGRAM_DATA_FILE_DIR_PATH + CHAT_GPT_FILE

    with open(chat_gpt_file_full_path, mode="r", encoding="utf-8") as file_obj:
            result_data = json.load(file_obj)

    # return result_data["data"]
    return result_data


# チャットGTPファイルの書き込み
# arg: 書き込み文字列のリスト
# ret: 0
def update_chat_gpt_file(data_dict):

    chat_gpt_file_full_path = PROGRAM_DATA_FILE_DIR_PATH + CHAT_GPT_FILE
    # write_dict = {"data":data_list}
    write_dict = data_dict

    with open(chat_gpt_file_full_path, mode="w", encoding="utf-8") as file_obj:
        json.dump(write_dict, file_obj, ensure_ascii=False)

    return 0


# マイクラマネージャー挨拶バリエーションファイル読み込み
# arg: なし
# ret: メッセージのリスト(list[str])
def load_minecraft_manager_greetings_file():

    file_name = GREETINGS_FILE

    with open(file_name, mode="r", encoding="utf-8") as file_obj:
            result_data = json.load(file_obj)
            result_list = result_data["messages"]

    return result_list


# ループフラグファイルの存在確認
# arg: なし
# ret: True: 存在した場合 False: 存在しない場合
def check_exists_loop_flg_file():

    loop_flg_file_full_path = PROGRAM_DATA_FILE_DIR_PATH + LOOP_FLG_FILE

    loop_flg = os.path.exists(loop_flg_file_full_path)

    return loop_flg


# 設定ファイルの読み込み
# arg: なし
# ret:正常終了:JSON読み込み結果オブジェクト(status=0 data=設定ファイルデータ(dict)) 異常終了:JSON読み込み結果オブジェクト(status:-1)
def load_conf_file():

    load_conf_file_result = LoadJsonFileResult()
    conf_file_full_path = PROGRAM_DATA_FILE_DIR_PATH + CONF_FILE_NAME

    try:
        with open(conf_file_full_path, mode="r", encoding="utf-8") as file_obj:
            load_conf_file_result.data = json.load(file_obj)
            load_conf_file_result.status = 0

    except OSError:
        log_output(LOG_LEVEL_ERROR, log_manager.LOG_MSG_ERROR_FILE_CONF_FILE_OPEN_FAILED)

    except json.JSONDecodeError:
        log_output(LOG_LEVEL_ERROR, log_manager.LOG_MSG_ERROR_FILE_CONF_FILE_JSON_COMVERT_FAILED)
        
    except Exception as e:
        log_output(LOG_LEVEL_ERROR, log_manager.LOG_MSG_ERROR_UNKNOWN + " error obj:" + str(e))

    return load_conf_file_result


# 設定ファイルの更新
# arg: 設定ファイルデータ(dict)
# ret: 正常終了:0 異常終了:-1
def update_conf_file(conf_dict):

    conf_file_full_path = PROGRAM_DATA_FILE_DIR_PATH + CONF_FILE_NAME
    ret = -1

    try:
        with open(conf_file_full_path, mode="w", encoding="utf-8") as file_obj:
            json.dump(conf_dict, file_obj, ensure_ascii=False)

    except OSError:
        log_output(LOG_LEVEL_ERROR, log_manager.LOG_MSG_ERROR_FILE_CONF_FILE_OPEN_FAILED)

    except TypeError:
        log_output(LOG_LEVEL_ERROR, log_manager.LOG_MSG_ERROR_FILE_CONF_FILE_JSON_DUMP_FAILED)
        
    except Exception as e:
        log_output(LOG_LEVEL_ERROR, log_manager.LOG_MSG_ERROR_UNKNOWN + " error obj:" + str(e))

    else:
        ret = 0

    return ret


# ファイルのタイムスタンプを返却
# arg: ファイルパス
# ret: 正常終了:タイムスタンプ（float) 異常終了:-1
def get_time_stamp(file_path):

    # 何度かリトライする（1000回試行→1秒スリープ を10セット）
    time_stamp = -1
    try_count = 0
    try_count2 = 0

    while time_stamp < 0 and try_count2 < 10:
        while time_stamp < 0 and try_count <= 1000:

            # ファイルの最終更新日時を取得
            try:
                time_stamp = os.path.getmtime(file_path)
            
            # ファイルのタイムスタンプ取得失敗
            except OSError:
                log_output(LOG_LEVEL_ERROR, log_manager.LOG_MSG_ERROR_FILE_TIMESTAMP_GET_FAILED + " filepath=" + file_path)
                
            # 予期せぬエラー
            except Exception as e:
                log_output(LOG_LEVEL_ERROR, log_manager.LOG_MSG_ERROR_UNKNOWN + " " + str(e))

            finally:
                try_count = try_count + 1

        if time_stamp < 0:
            try_count2 = try_count2 + 1
            try_count = 0
            time.sleep(1)

    return time_stamp


# ファイルの全行を取得
# arg: ファイルパス
# ret: 正常終了:ファイルの内容文字列リスト 異常終了:None
def get_file_all(file_path):

    # 何度かリトライする（1000回試行→1秒スリープ を10セット）
    file_data = []
    try_count = 0
    try_count2 = 0

    while len(file_data) <= 0 and try_count2 < 10:
        while len(file_data) <= 0 and try_count < 1000:
            file_data = []
            try:
                # ファイルの全行を取得
                with open(file_path, mode="r", encoding="utf-8") as file_obj:
                    # 改行コードで分割（改行コードはリストに含めない）
                    file_data_buff = file_obj.readlines()

                    for line in file_data_buff:
                        file_data.append(line.rstrip("\n"))

            # ファイルデータ取得失敗
            except OSError:
                log_output(LOG_LEVEL_ERROR, log_manager.LOG_MSG_ERROR_FILE_FILEDATA_GET_ALL_FAILED + " filepath=" + file_path)
                file_data = []

            finally:
                try_count = try_count + 1

        if len(file_data) <= 0:
            try_count2 = try_count2 + 1
            try_count = 0
            time.sleep(1)
            
    if try_count2 >= 10:
        log_output(LOG_LEVEL_WARNING, log_manager.LOG_MSG_WARNING_FILE_IS_EMPTY + "filepath=" + file_path)

    return file_data


# ファイルの行数を数える
# arg: ファイルパス
# ret: 正常終了:ファイルの行数 異常終了:-1
def count_file_line(file_path):

    # 行数0の場合は何度かリトライする（1000回試行→1秒スリープ を10セット）
    file_line_num = -1
    line_count = 0
    try_count = 0
    try_count2 = 0

    while file_line_num <= 0 and try_count2 < 10:
        while file_line_num <= 0 and try_count < 1000:

            try:
                # ファイルオープン
                with open(file_path, mode="r", encoding="utf-8") as file_obj:
                    # ファイル行数カウントのループ
                    for line_count, file_data in enumerate(file_obj, start=1):
                        pass

                file_line_num = line_count

            # ファイル読み込み失敗
            except OSError:
                log_output(LOG_LEVEL_ERROR, log_manager.LOG_MSG_ERROR_FILE_COUNT_FILE_NUM_FAILED + " filepath=" + file_path)

            finally:
                try_count = try_count + 1

            if file_line_num <= 0:
                try_count2 = try_count2 + 1
                try_count = 0
                time.sleep(1)

    if try_count2 >= 10:
        log_output(LOG_LEVEL_WARNING, log_manager.LOG_MSG_WARNING_FILE_IS_EMPTY + "filepath=" + file_path)


    return file_line_num


# ファイルの指定行から最後まで取得
# arg: ファイルパス, 開始行番号(N指定でN行目から読み込む)
# ret: 正常終了:ファイルの内容文字列リスト 異常終了:None
def get_file_select_line_to_the_end(file_path, start_line):

    # 何度かリトライする（1000回試行→1秒スリープ を10セット）
    file_data_list = []
    try_count = 0
    try_count2 = 0

    while len(file_data_list) <= 0 and try_count2 < 10:
        while len(file_data_list) <= 0 and try_count < 1000:
            file_data_list = []
            try:
                # ファイルOPEN
                with open(file_path, mode="r", encoding="utf-8") as file_obj:

                    file_data_list_buff = []

                    # ファイル読み込みループ
                    for read_line_pos, file_data in enumerate(file_obj, start=1):

                        # 指定行までスキップ

                        # 指定行以降の場合
                        if read_line_pos >= start_line:
                            # 末尾の改行コードは取り除く
                            file_data_list.append(file_data.rstrip("\n"))

            # ファイルデータ取得失敗
            except OSError:
                log_output(LOG_LEVEL_ERROR, log_manager.LOG_MSG_ERROR_FILE_FILEDATA_GET_SELECT_LINE_FAILED + " filepath=" + file_path)
                file_data_list = []

            finally:
                try_count = try_count + 1

        if len(file_data_list) <= 0:
            try_count2 = try_count2 + 1
            try_count = 0
            time.sleep(1)
            
    if try_count2 >= 10:
        log_output(LOG_LEVEL_WARNING, log_manager.LOG_MSG_WARNING_FILE_IS_EMPTY + "filepath=" + file_path)

    return file_data_list


# マイクラマネージャーの管理ファイル取得
# arg: なし
# ret: 正常終了:status=0 data=管理データの辞書型 異常終了:status=-1
def get_conf_file():
    return


