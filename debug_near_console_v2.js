// ブラウザのコンソールで実行してください

// 1. 現在のsymbolProgressManagerを確認
console.log('=== Current symbolProgressManager ===');
if (typeof symbolProgressManager !== 'undefined') {
    console.log('symbolProgressManager found:', symbolProgressManager);
    
    // symbolsDataプロパティを探す
    if (symbolProgressManager.symbolsData) {
        const allSymbols = [
            ...symbolProgressManager.symbolsData.running,
            ...symbolProgressManager.symbolsData.completed,
            ...symbolProgressManager.symbolsData.pending,
            ...symbolProgressManager.symbolsData.failed
        ];
        
        const nearSymbols = allSymbols.filter(s => s.symbol === 'NEAR');
        console.log('Total symbols:', allSymbols.length);
        console.log('NEAR found:', nearSymbols.length);
        
        if (nearSymbols.length > 0) {
            console.log('NEAR details:', nearSymbols);
        }
    } else {
        console.log('symbolsData not found in symbolProgressManager');
        console.log('Available properties:', Object.keys(symbolProgressManager));
    }
    
    // 内部状態を確認
    if (symbolProgressManager.symbols) {
        console.log('symbolProgressManager.symbols:', symbolProgressManager.symbols);
        const nearInSymbols = symbolProgressManager.symbols.find(s => s === 'NEAR' || s.symbol === 'NEAR');
        if (nearInSymbols) {
            console.log('NEAR found in symbols array:', nearInSymbols);
        }
    }
    
    // checkSymbolStatusメソッドを確認
    if (typeof symbolProgressManager.checkSymbolStatus === 'function') {
        console.log('Calling checkSymbolStatus("NEAR")...');
        const nearStatus = symbolProgressManager.checkSymbolStatus('NEAR');
        console.log('NEAR status from checkSymbolStatus:', nearStatus);
    }
    
} else {
    console.log('symbolProgressManager not found');
}

// 2. グローバル変数を全て確認
console.log('\n=== All global variables containing "symbol" ===');
for (let key in window) {
    if (key.toLowerCase().includes('symbol')) {
        console.log(key, ':', typeof window[key]);
    }
}

// 3. APIから直接取得
console.log('\n=== Fetching fresh API data ===');
fetch('/api/symbols/status')
    .then(r => r.json())
    .then(data => {
        console.log('API Response:', data);
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
        } else {
            console.log('✅ API shows NEAR is NOT in the system (can be added)');
        }
    })
    .catch(err => console.error('API Error:', err));

// 4. LocalStorageをチェック
console.log('\n=== LocalStorage ===');
for (let key in localStorage) {
    if (key.toLowerCase().includes('near') || key.toLowerCase().includes('symbol')) {
        console.log(key, ':', localStorage[key]);
    }
}

// 5. 強制的にNEARをクリア（symbolProgressManagerから）
console.log('\n=== Attempting to clear NEAR from frontend ===');
if (typeof symbolProgressManager !== 'undefined') {
    // symbolsDataがある場合
    if (symbolProgressManager.symbolsData) {
        ['running', 'completed', 'pending', 'failed'].forEach(category => {
            if (symbolProgressManager.symbolsData[category]) {
                const originalLength = symbolProgressManager.symbolsData[category].length;
                symbolProgressManager.symbolsData[category] = symbolProgressManager.symbolsData[category].filter(s => s.symbol !== 'NEAR');
                const newLength = symbolProgressManager.symbolsData[category].length;
                if (originalLength !== newLength) {
                    console.log(`Removed NEAR from ${category} (${originalLength} -> ${newLength})`);
                }
            }
        });
    }
    
    // symbols配列がある場合
    if (symbolProgressManager.symbols && Array.isArray(symbolProgressManager.symbols)) {
        const originalLength = symbolProgressManager.symbols.length;
        symbolProgressManager.symbols = symbolProgressManager.symbols.filter(s => {
            return s !== 'NEAR' && (!s.symbol || s.symbol !== 'NEAR');
        });
        const newLength = symbolProgressManager.symbols.length;
        if (originalLength !== newLength) {
            console.log(`Removed NEAR from symbols array (${originalLength} -> ${newLength})`);
        }
    }
    
    // 内部キャッシュやマップがある場合
    if (symbolProgressManager._symbolCache) {
        delete symbolProgressManager._symbolCache.NEAR;
        console.log('Removed NEAR from _symbolCache');
    }
    
    if (symbolProgressManager.symbolStatusMap) {
        delete symbolProgressManager.symbolStatusMap.NEAR;
        console.log('Removed NEAR from symbolStatusMap');
    }
    
    console.log('✅ Attempted to clear NEAR from all known locations');
    console.log('Try adding NEAR again now.');
} else {
    console.log('❌ Cannot clear - symbolProgressManager not found');
}