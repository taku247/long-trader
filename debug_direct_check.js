// 直接的な確認とbindEventsの強制表示

console.log('=== bindEventsメソッドの強制確認 ===');

// bindEventsメソッドを強制的に確認
try {
    if (symbolProgressManager) {
        const proto = Object.getPrototypeOf(symbolProgressManager);
        const bindEvents = proto.bindEvents;
        if (bindEvents) {
            console.log('bindEventsメソッドが見つかりました:');
            console.log(bindEvents.toString());
        } else {
            console.log('bindEventsメソッドがプロトタイプに見つかりません');
            
            // 直接確認
            if (symbolProgressManager.bindEvents) {
                console.log('インスタンスにbindEventsがあります:');
                console.log(symbolProgressManager.bindEvents.toString());
            }
        }
    }
} catch (e) {
    console.log('bindEvents確認エラー:', e);
}

console.log('\n=== 実際のボタンHTML確認 ===');
const addButton = document.getElementById('btn-add-symbol');
if (addButton) {
    console.log('ボタンのouterHTML:', addButton.outerHTML);
    console.log('ボタンの親要素:', addButton.parentElement.outerHTML);
}

console.log('\n=== フォーム全体の構造確認 ===');
const symbolInput = document.getElementById('new-symbol-input');
if (symbolInput) {
    const form = symbolInput.closest('form') || symbolInput.parentElement;
    console.log('フォーム/親要素のHTML:', form.outerHTML);
}

console.log('\n=== スクリプトタグの確認 ===');
const scripts = document.querySelectorAll('script');
scripts.forEach((script, index) => {
    if (script.textContent.includes('addSymbol') || script.textContent.includes('btn-add-symbol')) {
        console.log(`関連スクリプト[${index}]:`, script.textContent.substring(0, 500) + '...');
    }
});

console.log('\n=== イベント委譲の確認 ===');
// document や body レベルでのイベント委譲を確認
console.log('documentのクリックリスナーを確認中...');

// 一時的にdocumentのクリックを監視
const tempDocumentListener = function(e) {
    if (e.target.id === 'btn-add-symbol' || e.target.closest('#btn-add-symbol')) {
        console.log('🎯 document レベルでボタンクリックを検出!');
        console.log('イベント:', e);
        console.log('ターゲット:', e.target);
        
        // この監視を削除
        document.removeEventListener('click', tempDocumentListener, true);
    }
};

document.addEventListener('click', tempDocumentListener, true);
console.log('✅ documentレベルのクリック監視を設定しました');

console.log('\n=== 今すぐテストしてください ===');
console.log('1. 画面でNEARを入力');
console.log('2. ボタンをクリック');
console.log('3. コンソールの出力を確認');