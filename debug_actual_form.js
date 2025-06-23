// 実際のフォームでNEAR入力をテスト

console.log('=== 実際のフォーム要素でのテスト ===');

// 1. 入力フィールドとボタンを取得
const symbolInput = document.getElementById('new-symbol-input');
const addButton = document.querySelector('button[onclick*="addSymbol"], button[type="submit"], .btn-primary');

console.log('入力フィールド:', symbolInput);
console.log('追加ボタン:', addButton);

// 2. 入力フィールドにNEARを設定
if (symbolInput) {
    const originalValue = symbolInput.value;
    
    console.log('NEARを入力フィールドに設定...');
    symbolInput.value = 'NEAR';
    symbolInput.focus();
    
    // 各種イベントを発火
    symbolInput.dispatchEvent(new Event('input', { bubbles: true }));
    symbolInput.dispatchEvent(new Event('change', { bubbles: true }));
    symbolInput.dispatchEvent(new Event('keyup', { bubbles: true }));
    
    console.log('入力フィールドの値:', symbolInput.value);
    
    // 3. フォームやボタンのイベントリスナーを確認
    console.log('\n=== イベントリスナー確認 ===');
    
    // 入力フィールドのイベントリスナー確認
    if (symbolInput._listeners) {
        console.log('入力フィールドのリスナー:', symbolInput._listeners);
    }
    
    // 4. 実際にボタンをクリックしてみる（ただしpreventDefaultで止める）
    if (addButton) {
        console.log('\n=== ボタンクリックのシミュレーション ===');
        
        // 元のクリックハンドラーを一時的に保存
        const originalOnClick = addButton.onclick;
        
        // テスト用のクリックハンドラー
        addButton.onclick = function(e) {
            console.log('ボタンクリックイベント発生');
            e.preventDefault(); // 実際の送信を防ぐ
            
            // 元のハンドラーがある場合は、安全に呼び出し
            if (originalOnClick) {
                try {
                    console.log('元のクリックハンドラーを実行...');
                    const result = originalOnClick.call(this, e);
                    console.log('クリックハンドラー結果:', result);
                } catch (error) {
                    console.log('クリックハンドラーエラー:', error);
                }
            }
            
            return false; // 送信を防ぐ
        };
        
        console.log('ボタンをクリック...');
        addButton.click();
        
        // 元のハンドラーに戻す
        addButton.onclick = originalOnClick;
    }
    
    // 5. フォーム送信のテスト
    const form = symbolInput.closest('form');
    if (form) {
        console.log('\n=== フォーム送信のシミュレーション ===');
        
        const originalOnSubmit = form.onsubmit;
        
        form.onsubmit = function(e) {
            console.log('フォーム送信イベント発生');
            e.preventDefault();
            
            if (originalOnSubmit) {
                try {
                    console.log('元の送信ハンドラーを実行...');
                    const result = originalOnSubmit.call(this, e);
                    console.log('送信ハンドラー結果:', result);
                } catch (error) {
                    console.log('送信ハンドラーエラー:', error);
                }
            }
            
            return false;
        };
        
        // フォーム送信をトリガー
        const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
        form.dispatchEvent(submitEvent);
        
        // 元のハンドラーに戻す
        form.onsubmit = originalOnSubmit;
    }
    
    // 6. 入力フィールドの値を元に戻す
    setTimeout(() => {
        symbolInput.value = originalValue;
        console.log('\n入力フィールドを元の値に戻しました');
    }, 2000);
    
} else {
    console.log('❌ 入力フィールドが見つかりません');
}

// 7. グローバル関数の確認
console.log('\n=== グローバル関数の確認 ===');
['addSymbol', 'validateSymbol', 'submitSymbol', 'onAddSymbol'].forEach(funcName => {
    if (typeof window[funcName] === 'function') {
        console.log(`${funcName}関数が見つかりました:`, window[funcName].toString().substring(0, 200) + '...');
    }
});