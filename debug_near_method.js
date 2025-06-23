// SymbolProgressManagerのメソッドを詳細調査

console.log('=== SymbolProgressManagerメソッド詳細調査 ===');

// 1. 全メソッドを確認
console.log('利用可能なメソッド:');
Object.getOwnPropertyNames(Object.getPrototypeOf(symbolProgressManager)).forEach(method => {
    if (typeof symbolProgressManager[method] === 'function') {
        console.log('- ' + method);
    }
});

// 2. checkSymbolStatusメソッドがあるかもう一度確認
if (typeof symbolProgressManager.checkSymbolStatus === 'function') {
    console.log('\ncheckSymbolStatusメソッドを実行:');
    try {
        const result = symbolProgressManager.checkSymbolStatus('NEAR');
        console.log('checkSymbolStatus("NEAR")の結果:', result);
    } catch (e) {
        console.log('checkSymbolStatusエラー:', e);
    }
} else {
    console.log('\ncheckSymbolStatusメソッドが見つかりません');
}

// 3. isSymbolAlreadyAddedのようなメソッドを探す
const possibleMethods = [
    'isSymbolAlreadyAdded',
    'isSymbolExists', 
    'hasSymbol',
    'symbolExists',
    'getSymbolStatus',
    'findSymbol',
    'isSymbolInProgress'
];

console.log('\n=== 可能性のあるメソッドをテスト ===');
possibleMethods.forEach(methodName => {
    if (typeof symbolProgressManager[methodName] === 'function') {
        console.log(`${methodName}メソッドが見つかりました`);
        try {
            const result = symbolProgressManager[methodName]('NEAR');
            console.log(`${methodName}("NEAR")の結果:`, result);
        } catch (e) {
            console.log(`${methodName}エラー:`, e.message);
        }
    }
});

// 4. 銘柄追加のフォーム処理関数を確認
console.log('\n=== フォーム関連の関数確認 ===');
if (typeof addSymbol === 'function') {
    console.log('addSymbol関数が見つかりました');
}
if (typeof validateSymbol === 'function') {
    console.log('validateSymbol関数が見つかりました');
}

// 5. NEARをテスト入力して何が起こるかシミュレート
console.log('\n=== NEAR入力シミュレーション ===');
const symbolInput = document.getElementById('symbolInput');
if (symbolInput) {
    const originalValue = symbolInput.value;
    symbolInput.value = 'NEAR';
    
    // input/changeイベントを発火
    symbolInput.dispatchEvent(new Event('input', { bubbles: true }));
    symbolInput.dispatchEvent(new Event('change', { bubbles: true }));
    
    console.log('入力フィールドにNEARを設定し、イベントを発火しました');
    
    // 元の値に戻す
    setTimeout(() => {
        symbolInput.value = originalValue;
    }, 1000);
} else {
    console.log('symbolInputが見つかりません');
}