# マインクラフトマネージャーのログを管理するパッケージ

import subprocess
import os
import datetime

# 定数
LOG_DIR_PATH = "./log/"
LOG_FILE_LATEST_NAME = "latest.log"
CURRENT_LOG_LEVEL = 3
LOG_LEVEL_INFO = 3
LOG_LEVEL_WARNING = 2
LOG_LEVEL_ERROR = 1
LOG_FILE_MAX_LINE = 1000

# ログメッセージ一覧
# INFO
LOG_MSG_INFO_MAIN_EVENT_LOGIN = "Change login flg True in user manage list"
LOG_MSG_INFO_MAIN_EVENT_CONFIG_USER_ADD = "Added user in config data"
LOG_MSG_INFO_MAIN_EVENT_LOGOUT = "Change login flg False in user manage list"
LOG_MSG_INFO_MAIN_USER_STATUS_CHANGE = "Change user status in user manage list"
LOG_MSG_INFO_MAIN_SEND_CMD = "Send command to minecraft"
LOG_MSG_INFO_MAIN_SEND_CHAT = "Send message to minecraft chat"
LOG_MSG_INFO_MAIN_EVENT_NOT_SPEED_MINECART_STANDBY = "current user status id is not CHECK_ON_THE_MINECART"
LOG_MSG_INFO_MAIN_TIMER_SET = "Set to timer"
LOG_MSG_INFO_MAIN_TIMER_DELETE = "Timer to be deleted hit"
LOG_MSG_INFO_MAIN_SPEED_MINECART_COOL_TIME_FLG_RESET = "Reset to speed minecart cool time flg"
LOG_MSG_INFO_MAIN_CHAT_GPT_COMPLETE_REQ = "Chat GPT Request is complete"
LOG_MSG_INFO_MAIN_WARP_COMPLETED = "User warp completed."

LOG_MSG_INFO_CREATE_LOG_DIR = "Created log directory"
LOG_MSG_INFO_CREATE_LOG_FILE = "Created log file"

LOG_MSG_INFO_LOG_ROTATE_LOG_FILE = "Execute rotate log file"

LOG_MSG_INFO_ANALYZE_RESULT_SERVER_CHAT = "Result of analyze is server chat"
LOG_MSG_INFO_ANALYZE_RESULT_LOGIN = "Result of analyze is login message"
LOG_MSG_INFO_ANALYZE_RESULT_LOGOUT = "Result of analyze is logout message"
LOG_MSG_INFO_ANALYZE_RESULT_UNKNOWN = "Result of analyze is unknown message"
LOG_MSG_INFO_ANALYZE_RESULT_CALL_MANAGER = "Result of analyze is call manager"
LOG_MSG_INFO_ANALYZE_RESULT_CALL_CHAT_GPT = "Result of analyze is call chat gpt"
LOG_MSG_INFO_ANALYZE_RESULT_CALL_GEMINI = "Result of analyze is call gemini"
LOG_MSG_INFO_ANALYZE_RESULT_CALL_AI = "Result of analyze is call ai"
LOG_MSG_INFO_ANALYZE_RESULT_CMD_PARAM = "Result of analyze is command param"
LOG_MSG_INFO_ANALYZE_RESULT_POS_INFO = "Result of analyze is pos info"

LOG_MSG_INFO_FILE_CREATED_PROGRAM_DIR = "Created programData directory"
LOG_MSG_INFO_FILE_CREATED_CONF_FILE = "Created config file. Please setting for config file (minecraft_logfile_path, tmux_session_name, tmux_window_name)"

LOG_MSG_INFO_DB_ACCESS = "Accessed the database"
LOG_MSG_INFO_DB_QUERY_EXECUTE = "Execute query"


# WARNING
LOG_MSG_WARNING_LOG_FILE_ROTATE_FUNC_RET = "Return value of function log_file_rotate is -1"
LOG_MSG_WARNING_MAIN_USER_MANAGE_SET_USER_STATUS_FAILED = "Failed to set user status, no search target user in user manage list"
LOG_MSG_WARNING_MAIN_USER_MANAGE_BACK_USER_STATUS_FAILED = "Failed to back user status, no search target user in user manage list"
LOG_MSG_WARNING_MAIN_USER_MANAGE_GET_USER_STATUS_FAILED = "Failed to get user status, no search target user in user manage list"
LOG_MSG_WARNING_MAIN_EVENT_PROCESS_SUB_FAIELD_NO_USER_STATUS = "Failed to event process sub. discard message. because Failed to get user status"
LOG_MSG_WARNING_MAIN_TIMER_SET_FAILED = "Failed to timer set, no search target user in user manage list"
LOG_MSG_WARNING_MAIN_TIMER_DELETE_FAILED = "Failed to timer delete, no search target user or target timer in user manage list"
LOG_MSG_WARNING_MAIN_CHAT_GPT_CHAT_LOG_DB_INSERT_FIALED = "Failed to insert the chat log into the database"
LOG_MSG_WARNING_MAIN_WARP_SELECT_NG_OUT_OF_RANGE = "Failed to warp command, select number is out of range."
LOG_MSG_WARNING_MAIN_WARP_SELECT_NG_CONVERT_NUMBER = "Failed to warp command, select number is failed to convert."

LOG_MSG_WARNING_FILE_IS_EMPTY = "read file in 1000 time. but file is empty or no file."

LOG_MSG_WARNING_LOG_OLD_LOG_FILE_COMPRESS_FAILED = "Failed to compress old log file"

LOG_MSG_WARNING_DB_INSERT_QUESTION_OVER_LENGTH = "Question string exceeds the maximum length"
LOG_MSG_WARNING_DB_INSERT_ANSWER_OVER_LENGTH = "Answer string exceeds the maximum length"

# ERROR
LOG_MSG_ERROR_MAIN_READ_TIEMSTAMP_FAILED = "Failed to read minecraft log file timestamp"
LOG_MSG_ERROR_MAIN_READ_FILE_DATA_FAILED = "Failed to read minecraft log file data"
LOG_MSG_ERROR_MAIN_SEND_CHAT_FAILED = "Failed to send chat to minecraft"
LOG_MSG_ERROR_MAIN_SEND_CMD_FAILED = "Failed to send command to minecraft"
LOG_MSG_ERROR_MAIN_CHAT_GPT_CHAT_LOG_DB_SELECT_FAILED = "Failed to retrieve the chat log data due to either a failure to connect to the database or failure to execute the SQL query"
LOG_MSG_ERROR_MAIN_CHAT_GPT_ERROR = "Failed to process request to chatgpt"

LOG_MSG_ERROR_UNKNOWN = "Unknown ERROR occurred"

LOG_MSG_ERROR_LOG_OUTPUT_FAILED = "Failed to output log"
LOG_MSG_ERROR_LOG_ROTATE_RENAME = "Failed to rename log file when rotate log file"
LOG_MSG_ERROR_LOG_ROTATE_CREATE_LOG_FILE = "Failed to create new log file when rotate log file"

LOG_MSG_ERROR_FILE_TIMESTAMP_GET_FAILED = "Failed to get file timestamp"
LOG_MSG_ERROR_FILE_FILEDATA_GET_ALL_FAILED = "Failed to get file all line"
LOG_MSG_ERROR_FILE_FILEDATA_GET_SELECT_LINE_FAILED = "Failed to get from the specified line onward"
LOG_MSG_ERROR_FILE_CONF_FILE_CREATE_FAILED = "Failed to create programu directory or create config file"
LOG_MSG_ERROR_FILE_CONF_FILE_OPEN_FAILED = "Failed to open config file"
LOG_MSG_ERROR_FILE_CONF_FILE_JSON_COMVERT_FAILED = "Failed to json convert from config file"
LOG_MSG_ERROR_FILE_CONF_FILE_JSON_DUMP_FAILED = "Failed to Json dump config dict data to file"
LOG_MSG_ERROR_FILE_COUNT_FILE_NUM_FAILED = "Failed to count file line"

LOG_MSG_ERROR_DB_QUERY_EXECUTE = "Failed to connect to the database or execute the query"
LOG_MSG_ERROR_DB_INSERT_FAILED_KEY_ERROR = "Failed to insert becouse the key was not found in the data dictionary"
LOG_MSG_ERROR_DB_INSERT_FAILED_TYPE_ERROR = "Failed to insert becouse of a type error in the data dictionary"

# ログファイルの初期準備
# arg: なし
# ret: 正常終了:0 異常終了:-1
def log_file_init():
    
    # logディレクトリの存在チェック　なければ作成
    if os.path.exists(LOG_DIR_PATH) == False:
        try:
            # logディレクトリ作成
            os.mkdir(LOG_DIR_PATH)
            print(LOG_MSG_INFO_CREATE_LOG_DIR)

        # 予期せぬエラーが発生
        except Exception as e:
            print(LOG_MSG_ERROR_UNKNOWN)
            print("error obj:" + e)
            return -1

    # logファイルの存在チェック　なければ作成
    latest_full_path = LOG_DIR_PATH + LOG_FILE_LATEST_NAME
    if os.path.exists(latest_full_path) == False:
        # logファイル（latest）作成
        try:
            with open(latest_full_path, mode="w", encoding="utf-8") as file_obj:
                pass

        # 予期せぬエラーが発生
        except Exception as e:
            print(LOG_MSG_ERROR_UNKNOWN)
            print("error obj:" + e)
            return -1
        
    # 正常終了
    return 0


# ログファイルのローテート（命名：YY-mm-dd-HHMMSS_log.txt）
# arg: なし
# ret: 正常終了:0 異常終了:-1
def log_file_rotate():

    # 現在日時の取得
    datetime_now_obj = datetime.datetime.now()
    datetime_now_str = datetime_now_obj.strftime("%Y-%m-%d-%H%M%S")

    # ログファイル名変更
    rename_full_path = LOG_DIR_PATH + LOG_FILE_LATEST_NAME
    old_full_path = LOG_DIR_PATH + datetime_now_str + ".log"
    datetime_now_log_str = datetime_now_obj.strftime("%Y%m%d-%H:%M:%S")
    try:
        os.rename(rename_full_path, old_full_path)

    except OSError:
        with open(rename_full_path, mode="a", encoding="utf-8") as file_obj:
            file_obj.write(datetime_now_log_str + "-WARNING:" + LOG_MSG_ERROR_LOG_ROTATE_RENAME + "\n")
            return -1

    # 予期せぬエラー
    except Exception as e:
        with open(rename_full_path, mode="a", encoding="utf-8") as file_obj:
            file_obj.write(datetime_now_log_str + "-ERROR:" + LOG_MSG_ERROR_UNKNOWN + "\n")
            file_obj.write("error obj:")
            file_obj.write(e)
            return -1
        
    # ログファイル作成
    ret = log_file_init()

    # ログファイル作成に失敗
    if ret == -1:
        print(LOG_MSG_ERROR_LOG_ROTATE_CREATE_LOG_FILE + "\n")
        print("error obj:")
        print(e)
        return -1
    
    log_output(LOG_LEVEL_INFO, LOG_MSG_INFO_LOG_ROTATE_LOG_FILE + "rotate file=" + datetime_now_str + ".log")
        
    # 古いログファイルを圧縮（tgz）
    try:
        subprocess.run("pwd")
        subprocess.run("./log_archive.sh " + LOG_DIR_PATH + " " + datetime_now_str + " " + LOG_DIR_PATH, shell=True)

    except Exception as e:
        print(e)
        log_output(LOG_LEVEL_WARNING, LOG_MSG_WARNING_LOG_OLD_LOG_FILE_COMPRESS_FAILED + "oldLogFileName=" + old_full_path)

    return 0


# ログの出力（[YYYY/mm/dd-HH:MM:ss]-<LogLevel>:<logMessage>\n）
# arg: ログレベル, ログメッセージ
# ret: 正常終了:0 異常終了:-1
def log_output(log_level, log_msg):

    try:
        # 現在日時の取得
        datetime_now_obj = datetime.datetime.now()
        datetime_now_str = datetime_now_obj.strftime("[%Y%m%d-%H:%M:%S]")

        # ログファイル行数チェック
        latest_full_path = LOG_DIR_PATH + LOG_FILE_LATEST_NAME
        with open(latest_full_path, mode="r", encoding="utf-8") as file_obj:
            log_file_data = file_obj.readlines()
            log_file_line = len(log_file_data)

        # 行数が最大を迎えた場合は、ローテート
        if log_file_line >= LOG_FILE_MAX_LINE:
            res = log_file_rotate()

            # ログローテートに失敗した場合
            if res == -1:
                with open(latest_full_path, mode="a", encoding="utf-8") as file_obj:
                    file_obj.write(datetime_now_str + "-WARNING:" + LOG_MSG_WARNING_LOG_FILE_ROTATE_FUNC_RET + "\n")

        # 記録する必要のあるログ
        if log_level <= CURRENT_LOG_LEVEL:
            # 現在のログレベルがINFO
            if log_level == LOG_LEVEL_INFO:
                with open(latest_full_path, mode="a", encoding="utf-8") as file_obj:
                    file_obj.write(datetime_now_str + "-INFO:" + log_msg + "\n")

            # 現在のログレベルがWARNING
            if log_level == LOG_LEVEL_WARNING:
                with open(latest_full_path, mode="a", encoding="utf-8") as file_obj:
                    file_obj.write(datetime_now_str + "-WARNING:" + log_msg + "\n")

            # 現在のログレベルがERROR
            if log_level == LOG_LEVEL_ERROR:
                with open(latest_full_path, mode="a", encoding="utf-8") as file_obj:
                    file_obj.write(datetime_now_str + "-ERROR:" + log_msg + "\n")

    except Exception as e:
        print(LOG_MSG_ERROR_LOG_OUTPUT_FAILED + " error obj:")
        print(e)
        return -1

    return 0