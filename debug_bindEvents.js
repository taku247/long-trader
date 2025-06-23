// bindEventsメソッドとイベントリスナーの詳細確認

console.log('=== bindEventsメソッドの詳細確認 ===');

if (symbolProgressManager && typeof symbolProgressManager.bindEvents === 'function') {
    console.log('bindEventsメソッドの内容:');
    console.log(symbolProgressManager.bindEvents.toString());
} else {
    console.log('bindEventsメソッドが見つかりません');
}

console.log('\n=== Chrome DevToolsのgetEventListeners使用 ===');
console.log('Chrome DevToolsのコンソールで以下を実行してください:');
console.log('getEventListeners(document.getElementById("btn-add-symbol"))');
console.log('getEventListeners(document.getElementById("new-symbol-input"))');

console.log('\n=== 手動でイベント確認 ===');

const symbolInput = document.getElementById('new-symbol-input');
const addButton = document.getElementById('btn-add-symbol');

// jQueryイベントの安全な確認
if (typeof $ !== 'undefined' && addButton) {
    try {
        // jQueryの新しいバージョンではgetData関数を使用
        if ($.hasData && $.hasData(addButton)) {
            console.log('ボタンにjQueryデータがあります');
        }
        
        // onメソッドで登録されたイベントを確認
        const events = $(addButton).data('events');
        if (events) {
            console.log('jQueryイベント:', events);
        }
    } catch (e) {
        console.log('jQueryイベント確認エラー:', e.message);
    }
}

console.log('\n=== 実際のDOMイベント確認 ===');

// DOMに直接設定されているイベントハンドラーを確認
if (addButton) {
    console.log('ボタンのonclick:', addButton.onclick);
    console.log('ボタンのaddEventListener履歴を確認するため、一時的に監視します');
    
    // 元のaddEventListenerをオーバーライドして監視
    const originalAddEventListener = addButton.addEventListener;
    addButton.addEventListener = function(type, listener, options) {
        console.log(`イベントリスナー追加: ${type}`, listener);
        return originalAddEventListener.call(this, type, listener, options);
    };
}

console.log('\n=== 現在設定済みの監視状況 ===');
console.log('✅ ボタンクリック監視が設定されています');
console.log('👉 画面でNEARを入力してボタンをクリックしてください');
console.log('👉 コンソールに詳細なログが出力されます');

// 自動でNEARを設定（念のため）
if (symbolInput) {
    symbolInput.value = 'NEAR';
    symbolInput.focus();
    console.log('✅ 入力フィールドに NEAR を設定しました');
}