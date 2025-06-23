// ブラウザのコンソールで実行してください

// 1. 現在のsymbolsDataを確認
console.log('=== Current symbolsData ===');
if (typeof symbolManager !== 'undefined' && symbolManager.symbolsData) {
    const allSymbols = [
        ...symbolManager.symbolsData.running,
        ...symbolManager.symbolsData.completed,
        ...symbolManager.symbolsData.pending,
        ...symbolManager.symbolsData.failed
    ];
    
    const nearSymbols = allSymbols.filter(s => s.symbol === 'NEAR');
    console.log('Total symbols:', allSymbols.length);
    console.log('NEAR found:', nearSymbols.length);
    
    if (nearSymbols.length > 0) {
        console.log('NEAR details:', nearSymbols);
    }
} else {
    console.log('symbolManager not found');
}

// 2. APIから直接取得
fetch('/api/symbols/status')
    .then(r => r.json())
    .then(data => {
        console.log('=== Fresh API Data ===');
        const allSymbols = [
            ...data.running,
            ...data.completed,
            ...data.pending,
            ...data.failed
        ];
        
        const nearSymbols = allSymbols.filter(s => s.symbol === 'NEAR');
        console.log('API - Total symbols:', allSymbols.length);
        console.log('API - NEAR found:', nearSymbols.length);
        
        if (nearSymbols.length > 0) {
            console.log('API - NEAR details:', nearSymbols);
        }
    });

// 3. LocalStorageをチェック
console.log('=== LocalStorage ===');
for (let key in localStorage) {
    if (key.toLowerCase().includes('near') || key.toLowerCase().includes('symbol')) {
        console.log(key, ':', localStorage[key]);
    }
}

// 4. 強制的にsymbolsDataをクリア（NEARのみ）
if (typeof symbolManager !== 'undefined' && symbolManager.symbolsData) {
    ['running', 'completed', 'pending', 'failed'].forEach(category => {
        symbolManager.symbolsData[category] = symbolManager.symbolsData[category].filter(s => s.symbol !== 'NEAR');
    });
    console.log('✅ NEAR cleared from symbolManager.symbolsData');
    console.log('Try adding NEAR again now.');
}