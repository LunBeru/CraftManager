#!/bin/bash

# 圧縮ファイル名は、圧縮対象ファイル名と同じになる（もちろん拡張子は別）

# コマンドライン引数
# 1：圧縮対象のログファイルのデイレィクトリパス
# 2: 圧縮対象のログファイル名 拡張子は含めないこと（yyyy-mm-dd-HHMM）
# 3: 圧縮ファイルの保存先のディレクトリパス

# コマンドライン引数の数チェック
if [ $# -eq 3 ]; then

    # コマンドライン引数取得
    archive_src_dir_path=$1
    archive_src_file_name=$2
    archive_store_dir_path=$3

    # 圧縮コマンド
    tar czvf $archive_src_file_name.tgz -C $archive_src_dir_path $archive_src_file_name.log 

    # 圧縮ファイルの移動
    mv $archive_src_file_name.tgz $archive_store_dir_path

    # 圧縮元ファイルを削除
    rm $archive_src_dir_path$archive_src_file_name.log

else
    echo "Argument error. Arg = archive_src_path, archive_file_name(no extension), store path"

fi

