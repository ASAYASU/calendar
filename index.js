//予定はホームページアクセス時と予定追加時に再取得・表示されるので関数化する
async function loadEvents(){ //async関数（awaitというfetch結果が返るまで待てる構文を使える）
    //GETリクエストを"/get_events"に送り、サーバー側での処理が終わり通信結果であるJSON型文字列の予定データが返ったら、constの再代入不可の定数に初期化（GETは省略可）
    const response = await fetch("/get_events");

    //通信結果のステータスコードが200番台以外なら、通信エラーのアラートを表示して処理を終える
    if (!response.ok) {
        alert("通信エラー");
        return;
    }

    //JSON型文字列を完全なJSONに変換してJavaScriptで扱えるようにする
    const events = await response.json();

    //予定データを表示するためのulリストのidを取得・定数に初期化、documentはJSで一つのHTMLページ全体を指す
    const list = document.getElementById("event_list");

    //ulリスト初期化（予定データを更新するたびに前の予定データを消すため）
    list.innerHTML = "";

    //for文でJSON形式の予定データを1件ずつ取り出して、新規作成したliリストににテキストを追加し、そのliをulリストに追加していく
    for(const event of events){
        const li = document.createElement("li");
        
        //event[0]が予定ID、event[1]が予定タイトル、event[2]が予定日時
        li.textContent =
            event[2] + " : " + event[1] + "     予定ID: " +event[0];

        list.appendChild(li);
    }
}

//予定追加ボタンがクリックされたときの処理を、"click"の後の関数で定義（async関数でawait構文も使える）
document.getElementById("add_button").addEventListener("click", async () => {
    //HTMLから予定タイトルと予定日時を取得して定数に初期化
    const title = document.getElementById("schedule_title").value;
    const datetime = document.getElementById("schedule_datetime").value;

    //POSTリクエストを"/add_event"に送り、サーバー側での処理が終わり通信結果であるJSON型文字列の予定追加の成否が返ったら、constの再代入不可の定数に初期化
    const response = await fetch("/add_event", {
        method: "POST",

        //リクエストの内容がJSONであることをサーバー側に伝えるためのヘッダー
        headers:{ "Content-Type": "application/json" },

        //リクエストの内容を、{下記のキー:上記の値}で、JSON型文字列に変換して送る
        body: JSON.stringify({
            schedule_title: title,
            schedule_datetime: datetime
        })
    });
    
    if (!response.ok) {
        alert("通信エラー");
        return;
    }

    //JSON型文字列の通信結果を完全なJSONに変換してJavaScriptで扱えるようにする
    const result = await response.json();

    //通信結果のstatusのキーの値が"ok"と型含め完全一致したら、予定の名前と日時の入力欄を初期化
    if(result.status === "ok") {
        document.getElementById("schedule_title").value = "";
        document.getElementById("schedule_datetime").value = "";

        //予定データを更新して表示
        loadEvents();
    }
    //"ok"以外なら、"message"のキーの値の、 "入力データがありません" か "予定の名前と日時の両方を入力してください" か "入力は100文字以内でお願いします" というエラーメッセージをトップページに表示
    else {
        alert(result.message);
    }
});

//予定削除ボタンがクリックされたときの処理を、"click"の後の関数で定義
document.getElementById("delete_button").addEventListener("click", async () => {
    //HTMLから削除対象IDを取得して定数に初期化
    const deleteId = document.getElementById("delete_id").value;

    //POSTリクエストを"/delete_event"に送り、サーバー側での処理が終わり通信結果であるJSON型文字列の予定削除の成否が返ったら、constの再代入不可の定数に初期化
    const response = await fetch("/delete_event", {
        method: "POST",

        headers:{ "Content-Type": "application/json" },

        //リクエストの内容を、{下記のキー:上記の値}で、JSON型文字列に変換して送る
        body: JSON.stringify({
            delete_id: deleteId
        })
    });

    if (!response.ok) {
        alert("通信エラー");
        return;
    }

    //JSON型文字列の通信結果を完全なJSONに変換してJavaScriptで扱えるようにする
    const result = await response.json();

    //通信結果のstatusのキーの値が"ok"と型含め完全一致したら、予定の名前と日時の入力欄を初期化・予定データを更新して表示
    if(result.status === "ok") {
        document.getElementById("delete_id").value = "";
        loadEvents();
    }
    //エラーメッセージ
    else {
        alert(result.message);
    }
});

//ログイン成功時にトップページが読み込まれた際、最初にユーザーの予定データを表示するための関数
loadEvents();
