// 実際のイベントリスナーを調査

console.log('=== イベントリスナーの詳細調査 ===');

const symbolInput = document.getElementById('new-symbol-input');
const addButton = document.getElementById('btn-add-symbol');

// 1. jQueryイベントリスナーの確認（もしjQueryが使われている場合）
if (typeof $ !== 'undefined') {
    console.log('jQueryが利用可能');
    
    if (addButton) {
        const events = $._data(addButton, 'events');
        console.log('ボタンのjQueryイベント:', events);
    }
    
    if (symbolInput) {
        const events = $._data(symbolInput, 'events');
        console.log('入力フィールドのjQueryイベント:', events);
    }
} else {
    console.log('jQueryは利用されていません');
}

// 2. Native addEventListener で登録されたイベントリスナーを探す
console.log('\n=== Native イベントリスナー調査 ===');

// getEventListeners（Chrome DevTools専用）
if (typeof getEventListeners === 'function') {
    console.log('ボタンのイベントリスナー:', getEventListeners(addButton));
    console.log('入力フィールドのイベントリスナー:', getEventListeners(symbolInput));
} else {
    console.log('getEventListeners関数は使用できません（Chrome DevToolsでのみ利用可能）');
}

// 3. 手動でボタンクリックを監視
console.log('\n=== ボタンクリック監視の設定 ===');

if (addButton) {
    // 一時的なイベントリスナーを追加して実際の動作を確認
    const tempClickListener = function(e) {
        console.log('🔥 ボタンクリックが検出されました！');
        console.log('イベント:', e);
        console.log('ターゲット:', e.target);
        console.log('現在の入力値:', symbolInput.value);
        
        // イベントを止めて詳細を確認
        e.stopImmediatePropagation();
        e.preventDefault();
        
        console.log('実際のクリック処理を実行してみます...');
        
        // NEARを入力して処理を続行
        symbolInput.value = 'NEAR';
        
        // このリスナーを削除して、元の処理を続行
        addButton.removeEventListener('click', tempClickListener, true);
        
        // 少し待ってから実際のクリックを実行
        setTimeout(() => {
            console.log('元の処理を実行...');
            addButton.click();
        }, 1000);
        
        return false;
    };
    
    // capture: trueで最初にキャッチ
    addButton.addEventListener('click', tempClickListener, true);
    
    console.log('✅ 一時的なクリック監視を設定しました');
    console.log('NEARを入力してボタンをクリックしてください');
    
    // 入力フィールドにNEARを設定
    symbolInput.value = 'NEAR';
    console.log('NEARを入力フィールドに設定しました');
    
} else {
    console.log('❌ ボタンが見つかりません');
}

// 4. SymbolProgressManagerのbindEventsメソッドを確認
console.log('\n=== SymbolProgressManagerのイベント設定確認 ===');
if (symbolProgressManager && typeof symbolProgressManager.bindEvents === 'function') {
    console.log('bindEventsメソッドの内容:');
    console.log(symbolProgressManager.bindEvents.toString());
} else {
    console.log('bindEventsメソッドが見つかりません');
}