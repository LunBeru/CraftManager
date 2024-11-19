# Craft Manager
Craft Manager は、Minecraft Java Edition の快適なプレイを推進するためのツールです。
本プログラムはマイクラサーバープログラムを実行しているコンピューターで実行することを想定しています。主な機能には、座標送信、他ユーザーへのテレポート、AIチャット機能等があります。

## 主な機能
### メインメニューの機能
- デスルーラ
- 座標送信
- 高速トロッコ
- 他ユーザーの位置へテレポート

### 他機能
- AIチャット機能

## 機能詳細
### メインメニュー
チャット欄に「m」と送信すると呼び出すことができます。
メインメニューからいくつかの機能を呼び出すことができます。

### デスルーラ
メインメニューから呼び出すことができます。本機能は機能利用者本人に向け、killコマンドを発行します。（アイテム保持の機能はないため、保持するには別途サーバー設定を変更してください。）

### 座標送信
メインメニューから呼び出すことができます。java EditionはF3キーのデバッグ表示にて、現在の座標が確認できるが画面を占領するため少々不便です。本機能は、短い間隔でチャット欄に座標が送られる機能です。チャット欄に表示されるため、デバッグ表示よりも画面を占領せずに済みます。終了するには、任意の文字をチャットへ送信してください。

### 高速トロッコ
メインメニューから呼び出すことができます。トロッコの速度を上げるコマンドは現時点で存在しないため、マイクラ内全体の時間の流れの速度を操作しトロッコの速度を速めます。マイクラ内全体の時間の流れが高速になるため、戦闘中の他プレイヤーがいる場合は注意が必要です。
全プレイヤーに影響があるため、他プレイヤーの承認が必要な機能です。
強力な機能なため、ゲームの体験を維持する目的で以下の制限があります。
1. トロッコ乗車中のみ使用可能であり、下車と同時に速度が元に戻る
2. 1度使用すると、3分間のクールタイムに入り、クールタイム中は使用不可となる
3. 効果の継続時間は最大で5分間

### 他プレイヤーの場所へテレポート
メインメニューから呼び出すことができます。他プレイヤーの位置に、テレポートすることができます。

### AIチャット機能
使用するには、マイクラのチャットへ「ai」と入力することで、AIチャット機能モードに切り替わります。本モード中は、チャットに入力したほぼ全ての文字（例外は※1参照）がAI（chatgpt）へ送信され、AIが返答を返します。AIチャット機能モードは、「e」を入力することで、終了します。
本機能は物事を記憶する機能も持っており、「覚えて」などのキーワードをメッセージに組み込むと、AIに記憶させることができます。記憶機能は、拠点の座標などの記録に便利です。
なお、「ai」ではなく、「g」を入力することでGoogleのgeminiも動作します。geminiには記憶機能を持たせておらず、応答するのみとなっています。

※1 メインメニューを呼び出す「m」などは無視されます。

## 動作確認環境
- centos stream 9
- python 3.9.20
- pythonパッケージ openai(ver.0.28) google-generativeai(0.7.2)
- tmux(ver.3.2a)
- Minecraft javaEdition(ver.1.21.3)

## 環境構築方法

### 前提
Minecraft JavaEditionが動作する環境を想定しています。Minecraft JavaEditionのための環境構築は、別サイトをご参照の上構築願います。

### 1. tmuxのインストール
本プログラムは、tmux上のセッション上で動作することを想定しているため、tmuxのインストールが必須です。tmuxがインストール済みの場合は、この手順をスキップしてください。

### 2. pythonのインストール
本プログラムを動作させるため、pythonをインストールします。
pythonは3系をインストールしてください。（2系での動作は保証できかねます。）

### 3. pythonの必要パッケージをインストール
pipを利用し、必要パッケージをインストールしてください。

### 4. tmuxのセッション上でマイクラサーバープログラムを起動する
tmuxのセッションを任意の名前で起動し、作成したセション上でマイクラのサーバープログラムを実行します。この時のセッション名とウィンドウ名は後ほど使用するため、どこかに控えておくことをおすすめします。また、ウィンドウの分割はしないようにしてください。本プログラムが正常に動作しないことがあります。

### 5. 本プログラムを実行する（初回実行）
マイクラサーバーを起動しているセッションとは別のセッションをtmuxで起動し、起動したセッション上で、本プログラムのメインファイル（main.py）を実行してください。初回実行時、必要なファイルが作成され、プログラムはすぐに終了します。

### 6. 設定ファイルの編集
手順5で作成された設定ファイルを編集します。設定ファイルはmain.pyと同階層の「programData」内の「conf.json」です。
「conf.json」内の「tmux_session_name」と「tmux_window_name」をそれぞれ設定してください。ここに設定するのは、マイクラサーバープログラムが動いているセッション名とウィンドウ名です。

### 7. 環境変数の設定
本プログラムは、chatgptとgeminiを利用するため、APIキーが必要になります。それぞれ各サービスの公式サイトなどを参考に用意してください。
APIキーを環境変数へ登録します。必要に応じて、bash_profileに記載することをおすすめします。bash_profileに記載する場合は以下のように記載します。

```bash
export CHAT_GPT_APIKEY="<ご自身のAPIキー(chatgpt)>"
export GEMINI_APIKEY="<ご自身のAPIキー(gemini)>"
```

### 7. 本プログラムを実行する
Minecraft Managerを実行するためのセッションに戻り、再びmain.pyを実行してください。環境構築は以上です。マイクラのサーバーにログインして、動作確認を行ってください。

## 免責事項と権利
- このプロジェクトは、MojangやMicrosoftとは一切関係がありません。また、これらの企業からの承認やサポートを受けていません。「Minecraft」はMojang ABの商標です。

- 本ツールの使用により生じたいかなる損害（データの損失、サーバーの不具合、その他予期せぬ問題を含む）についても、作成者は一切の責任を負いません。本ツールの使用は、全て自己責任で行ってください。