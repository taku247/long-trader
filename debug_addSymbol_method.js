// addSymbolメソッドの詳細調査

console.log('=== addSymbolメソッドの調査 ===');

// 1. addSymbolメソッドの内容を確認
console.log('addSymbolメソッドの内容:');
console.log(symbolProgressManager.addSymbol.toString());

console.log('\n=== 実際にNEARでaddSymbolをテスト実行 ===');

// 2. NEARでaddSymbolを実際に実行してみる（でも最後の送信はスキップ）
try {
    // addSymbolメソッドを一時的に変更して、最後の送信部分をスキップ
    const originalAddSymbol = symbolProgressManager.addSymbol;
    
    // メソッドを一時的にオーバーライド（デバッグ用）
    symbolProgressManager.addSymbol = function(symbol) {
        console.log('addSymbol実行開始 - symbol:', symbol);
        
        // 元のメソッドのロジックを部分的に実行
        const symbolUpper = symbol.toUpperCase();
        console.log('大文字変換後:', symbolUpper);
        
        // symbolsDataでの重複チェック
        if (this.symbolsData) {
            const allSymbols = [
                ...this.symbolsData.running,
                ...this.symbolsData.completed,
                ...this.symbolsData.pending,
                ...this.symbolsData.failed
            ];
            
            const existingSymbol = allSymbols.find(s => s.symbol === symbolUpper);
            if (existingSymbol) {
                console.log('❌ 重複発見:', existingSymbol);
                return false; // 重複の場合
            } else {
                console.log('✅ 重複なし - 追加可能');
            }
        }
        
        console.log('addSymbol処理完了（実際の送信はスキップ）');
        return true;
    };
    
    // NEARでテスト実行
    const result = symbolProgressManager.addSymbol('NEAR');
    console.log('テスト実行結果:', result);
    
    // 元のメソッドに戻す
    symbolProgressManager.addSymbol = originalAddSymbol;
    
} catch (e) {
    console.log('テスト実行エラー:', e);
}

console.log('\n=== フォーム要素の確認 ===');

// 3. 実際のフォーム要素を探す
const possibleInputIds = [
    'symbolInput',
    'symbol-input', 
    'symbol_input',
    'newSymbol',
    'add-symbol-input'
];

const possibleButtonIds = [
    'addSymbolBtn',
    'add-symbol-btn',
    'add-symbol-button',
    'addSymbolButton'
];

console.log('入力フィールドを探索:');
possibleInputIds.forEach(id => {
    const element = document.getElementById(id);
    if (element) {
        console.log(`見つかりました: ${id}`, element);
    }
});

console.log('ボタンを探索:');
possibleButtonIds.forEach(id => {
    const element = document.getElementById(id);
    if (element) {
        console.log(`見つかりました: ${id}`, element);
    }
});

// 4. input要素を全て探す
console.log('\n全input要素:');
document.querySelectorAll('input').forEach((input, index) => {
    console.log(`Input[${index}]:`, {
        id: input.id,
        name: input.name,
        type: input.type,
        placeholder: input.placeholder,
        value: input.value
    });
});

// 5. formを探す
console.log('\n全form要素:');
document.querySelectorAll('form').forEach((form, index) => {
    console.log(`Form[${index}]:`, form);
});