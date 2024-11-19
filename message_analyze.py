# マイクラのサーバーコンソールメッセージを解析するパッケージ

from enum import IntEnum
from log_manager import log_output

from log_manager import LOG_LEVEL_INFO
from log_manager import LOG_LEVEL_WARNING
from log_manager import LOG_LEVEL_ERROR
from log_manager import LOG_MSG_INFO_ANALYZE_RESULT_LOGIN
from log_manager import LOG_MSG_INFO_ANALYZE_RESULT_LOGOUT
from log_manager import LOG_MSG_INFO_ANALYZE_RESULT_UNKNOWN
from log_manager import LOG_MSG_INFO_ANALYZE_RESULT_SERVER_CHAT
from log_manager import LOG_MSG_INFO_ANALYZE_RESULT_CALL_MANAGER
from log_manager import LOG_MSG_INFO_ANALYZE_RESULT_CALL_CHAT_GPT
from log_manager import LOG_MSG_INFO_ANALYZE_RESULT_CALL_GEMINI
from log_manager import LOG_MSG_INFO_ANALYZE_RESULT_CALL_AI
from log_manager import LOG_MSG_INFO_ANALYZE_RESULT_CMD_PARAM
from log_manager import LOG_MSG_INFO_ANALYZE_RESULT_POS_INFO

class AnalyzeMsgID(IntEnum):
    ERROR = -1
    SERVER_CHAT = 0
    LOGIN = 1
    LOGOUT = 2
    CALL_MANAGER = 3
    CMD_PARAM = 4
    POS_INFO = 5
    POS_INFO_ON_MINECART = 6
    CALL_CHAT_GPT = 7
    CALL_GEMINI = 8
    CALL_AI = 9
    UNKNOWN = 255


class AnalyzeResultData:
    message_id = AnalyzeMsgID.ERROR
    message_user = ""
    message_data = ""
    message_full_data = ""


# マイクラマネージャー呼び方リスト
mainecraft_manager_name_list = [
    "m",
    "M",
    "マイクラマネージャー",
    "マネージャー",
    "マイクラ",
    "マーマネ",
    "minecraftmanager",
    "manager"
]


# ユーザーによるチャットメッセージの解析
# arg: 解析対象の文字列リスト
# ret: 正常終了:解析結果 異常終了:メッセージID-1
def analyze_user_chat(analyze_str_list:list):
    analyze_result_data = AnalyzeResultData()

    # ユーザー名の抽出
    username = analyze_str_list[3].replace("<", "").replace(">", "")

    if len(analyze_str_list) >= 5:
        # キーワード抽出　改行コード削除
        keyword = analyze_str_list[4]
        keyword = keyword.replace("\n", "")

        if len(analyze_str_list) == 5:
            
            # マネージャーのコールワードが複数あるため、forでまわす
            call_manager_flg = False
            for manager_name in mainecraft_manager_name_list:
                if keyword == manager_name:
                    call_manager_flg = True

            # メッセージがマイクラマネージャー呼び出し文字列の場合
            if call_manager_flg == True:
                analyze_result_data.message_id = AnalyzeMsgID.CALL_MANAGER
                analyze_result_data.message_user = username
                log_output(LOG_LEVEL_INFO, LOG_MSG_INFO_ANALYZE_RESULT_CALL_MANAGER + " call manager from " + username)
            
            # メッセージがchatGPT呼び出し文字列の場合
            elif keyword == "c":
                analyze_result_data.message_id = AnalyzeMsgID.CALL_CHAT_GPT
                analyze_result_data.message_user = username
                log_output(LOG_LEVEL_INFO, LOG_MSG_INFO_ANALYZE_RESULT_CALL_CHAT_GPT + " call manager from " + username)

            # メッセージがdemini呼び出し文字列の場合
            elif keyword == "g":
                analyze_result_data.message_id = AnalyzeMsgID.CALL_GEMINI
                analyze_result_data.message_user = username
                log_output(LOG_LEVEL_INFO, LOG_MSG_INFO_ANALYZE_RESULT_CALL_GEMINI + " call manager from " + username)

            # メッセージがgemini and chatgptの呼び出し文字列の場合
            elif keyword == "ai":
                analyze_result_data.message_id = AnalyzeMsgID.CALL_AI
                analyze_result_data.message_user = username
                log_output(LOG_LEVEL_INFO, LOG_MSG_INFO_ANALYZE_RESULT_CALL_AI + " call manager from " + username)

            # それ以外はコマンドパラメータとして扱う
            else:
                analyze_result_data.message_id = AnalyzeMsgID.CMD_PARAM
                analyze_result_data.message_user = username
                analyze_result_data.message_data = keyword
                analyze_result_data.message_full_data = keyword
                log_output(LOG_LEVEL_INFO, LOG_MSG_INFO_ANALYZE_RESULT_CMD_PARAM + " user=" + username + " command param=" + keyword)


        # 現時点で2つ以上パラメータがあるコマンドは存在しない
        # elif len(analyze_str_list) == 6:
        #     pass

        # それ以外はコマンドパラメータとして扱う
        # TODO コマンドパラメータが半角空白で区切られていた場合は連結してまとめないとだめ
        else:
            analyze_result_data.message_id = AnalyzeMsgID.CMD_PARAM
            analyze_result_data.message_user = username
            analyze_result_data.message_data = keyword
            full_data_str = ""
            for data_str in analyze_str_list[4:]:
                full_data_str = full_data_str + data_str + " "
            analyze_result_data.message_full_data = full_data_str
            log_output(LOG_LEVEL_INFO, LOG_MSG_INFO_ANALYZE_RESULT_CMD_PARAM + " command param=" + keyword)


    return analyze_result_data


# 文字列が数値変換可能かチェックする
# arg: チェック対象の文字列
# ret: 変換可能:True 変換不可能:False
def check_comvert_number(check_str):

    try:
        float(check_str)

    except Exception:
        ret = False

    else:
        ret = True

    return ret


# data get <entity name> Posコマンドの結果メッセージの解析
# arg: 解析対象の文字列リスト
# ret: 正常終了:解析結果 異常終了:メッセージID-1
def analyze_data_command_result(analyze_str_list:list):

    analyze_result_data = AnalyzeResultData()
    analyze_result_data.message_id = AnalyzeMsgID.ERROR
    analyze_result_data.message_user = ""
    analyze_result_data.message_data = ""

    # パラメータが非常に長い場合は、data get <username> コマンドと判断
    if len(analyze_str_list) >= 30:

        # 文字列の結合
        analyze_str = "".join(analyze_str_list)

        # 乗り物に乗っている場合
        root_vehicle_index = analyze_str.find("RootVehicle")
        if root_vehicle_index > -1:
            # 次の要素の"SpawnY"まで抽出
            end_index = analyze_str.find("SpawnY")
            root_vehicle = analyze_str[root_vehicle_index:end_index]

            # トロッコに乗っている場合
            if '"minecraft:minecart"' in root_vehicle:

                # データを"on"で通知
                analyze_result_data.message_id = AnalyzeMsgID.POS_INFO_ON_MINECART
                analyze_result_data.message_user = analyze_str_list[3]
                analyze_result_data.message_data = "on"

            # トロッコ以外に乗っている場合
            else:
                # データを"out"で通知
                analyze_result_data.message_id = AnalyzeMsgID.POS_INFO_ON_MINECART
                analyze_result_data.message_user = analyze_str_list[3]
                analyze_result_data.message_data = "out"

        # 乗り物に乗っていない場合
        else:
            # データを"out"で通知
            analyze_result_data.message_id = AnalyzeMsgID.POS_INFO_ON_MINECART
            analyze_result_data.message_user = analyze_str_list[3]
            analyze_result_data.message_data = "out"

    # data get <username> Posコマンドの結果かチェック
    # 判断基準
    # メッセージのパラメータ数が11であること
    # 10, 11, 12番目のパラメータから「d」を取ると、数値に変換できること
    if len(analyze_str_list) == 12:

        param10 = analyze_str_list[9]
        param11 = analyze_str_list[10]
        param12 = analyze_str_list[11]

        # 邪魔な文字を排除
        delete_char_list = ["d", "[", "]", ","]
        for delete_char in delete_char_list:
            param10 = param10.replace(delete_char, "")
            param11 = param11.replace(delete_char, "")
            param12 = param12.replace(delete_char, "")

        log_output(LOG_LEVEL_INFO, "param10=" + param10)
        log_output(LOG_LEVEL_INFO, "param11=" + param11)
        log_output(LOG_LEVEL_INFO, "param12=" + param12)

        if check_comvert_number(param10) == True and check_comvert_number(param11) == True and check_comvert_number(param12) == True:
            # data get <username> Posのコマンド結果であると判断
            pos_x = int(float(param10))
            pos_y = int(float(param11))
            pos_z = int(float(param12))
            pos_str = " X=" + str(pos_x) + "  Y=" + str(pos_y) + "  Z=" + str(pos_z)

            analyze_result_data.message_id = AnalyzeMsgID.POS_INFO
            analyze_result_data.message_user = analyze_str_list[3]
            analyze_result_data.message_data = analyze_str_list[3] + ": " + pos_str

    return analyze_result_data


# メッセージ解析のメイン関数
# arg: 解析対象の文字列
# ret: 正常終了:解析結果 異常終了:メッセージID-1
def analyze_main(analyze_str:str):

    analyze_result_data = AnalyzeResultData()

    # 空白で区切る
    analyze_str_list = analyze_str.split(" ")
    keyword_msg = analyze_str_list[3]

    # サーバーによるチャットメッセージの場合
    if keyword_msg.count("server") == 1:
        analyze_result_data.message_id = AnalyzeMsgID.SERVER_CHAT
        analyze_result_data.message_data = analyze_str
        log_output(LOG_LEVEL_INFO, LOG_MSG_INFO_ANALYZE_RESULT_SERVER_CHAT + " message=" + analyze_str)

    # ユーザーによるチャットメッセージの場合　サーバーのメッセージは除外する
    elif keyword_msg.count("<") == 1:
        analyze_result_data = analyze_user_chat(analyze_str_list)
        

    # ログインメッセージの場合
    elif ("joined the game" in analyze_str) == True:
        username = analyze_str_list[3]
        analyze_result_data.message_id = AnalyzeMsgID.LOGIN
        analyze_result_data.message_user = username
        log_output(LOG_LEVEL_INFO, LOG_MSG_INFO_ANALYZE_RESULT_LOGIN + " username=" + username)

    # ログアウトメッセージの場合
    elif ("left the game" in analyze_str) == True:
        username = analyze_str_list[3]
        analyze_result_data.message_id = AnalyzeMsgID.LOGOUT
        analyze_result_data.message_user = username
        log_output(LOG_LEVEL_INFO, LOG_MSG_INFO_ANALYZE_RESULT_LOGOUT + " username=" + username)

    # data getコマンドの結果だった場合
    elif ("has the following entity data:" in analyze_str) == True:
        analyze_result_data = analyze_data_command_result(analyze_str_list)
        log_output(LOG_LEVEL_INFO, LOG_MSG_INFO_ANALYZE_RESULT_POS_INFO + " message_data=" + analyze_result_data.message_data)

    # 不要なメッセージ
    else:
        analyze_result_data.message_id = AnalyzeMsgID.UNKNOWN
        log_output(LOG_LEVEL_INFO, LOG_MSG_INFO_ANALYZE_RESULT_UNKNOWN + " message=" + analyze_str)

    return analyze_result_data
