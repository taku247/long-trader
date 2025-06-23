// ブラウザのコンソールで実行してください

// 1. 現在のsymbolProgressManagerを確認
console.log('=== symbolProgressManagerの状態確認 ===');
if (typeof symbolProgressManager !== 'undefined') {
    console.log('symbolProgressManagerが見つかりました:', symbolProgressManager);
    
    // symbolsDataプロパティを探す
    if (symbolProgressManager.symbolsData) {
        const allSymbols = [
            ...symbolProgressManager.symbolsData.running,
            ...symbolProgressManager.symbolsData.completed,
            ...symbolProgressManager.symbolsData.pending,
            ...symbolProgressManager.symbolsData.failed
        ];
        
        const nearSymbols = allSymbols.filter(s => s.symbol === 'NEAR');
        console.log('総銘柄数:', allSymbols.length);
        console.log('NEAR検出数:', nearSymbols.length);
        
        if (nearSymbols.length > 0) {
            console.log('NEARの詳細:', nearSymbols);
        }
    } else {
        console.log('symbolProgressManagerにsymbolsDataが見つかりません');
        console.log('利用可能なプロパティ:', Object.keys(symbolProgressManager));
    }
    
    // 内部状態を確認
    if (symbolProgressManager.symbols) {
        console.log('symbolProgressManager.symbols:', symbolProgressManager.symbols);
        const nearInSymbols = symbolProgressManager.symbols.find(s => s === 'NEAR' || s.symbol === 'NEAR');
        if (nearInSymbols) {
            console.log('symbols配列でNEARを発見:', nearInSymbols);
        }
    }
    
    // checkSymbolStatusメソッドを確認
    if (typeof symbolProgressManager.checkSymbolStatus === 'function') {
        console.log('checkSymbolStatus("NEAR")を実行中...');
        const nearStatus = symbolProgressManager.checkSymbolStatus('NEAR');
        console.log('checkSymbolStatusからのNEARステータス:', nearStatus);
    }
    
} else {
    console.log('symbolProgressManagerが見つかりません');
}

// 2. グローバル変数を全て確認
console.log('\n=== "symbol"を含むグローバル変数の確認 ===');
for (let key in window) {
    if (key.toLowerCase().includes('symbol')) {
        console.log(key, ':', typeof window[key]);
    }
}

// 3. APIから直接取得
console.log('\n=== API最新データ取得 ===');
fetch('/api/symbols/status')
    .then(r => r.json())
    .then(data => {
        console.log('APIレスポンス:', data);
        const allSymbols = [
            ...data.running,
            ...data.completed,
            ...data.pending,
            ...data.failed
        ];
        
        const nearSymbols = allSymbols.filter(s => s.symbol === 'NEAR');
        console.log('API - 総銘柄数:', allSymbols.length);
        console.log('API - NEAR検出数:', nearSymbols.length);
        
        if (nearSymbols.length > 0) {
            console.log('API - NEARの詳細:', nearSymbols);
        } else {
            console.log('✅ APIではNEARがシステムに存在しない（追加可能）');
        }
    })
    .catch(err => console.error('APIエラー:', err));

// 4. LocalStorageをチェック
console.log('\n=== LocalStorage確認 ===');
for (let key in localStorage) {
    if (key.toLowerCase().includes('near') || key.toLowerCase().includes('symbol')) {
        console.log(key, ':', localStorage[key]);
    }
}

// 5. 強制的にNEARをフロントエンドからクリア
console.log('\n=== フロントエンドからNEARを強制削除 ===');
if (typeof symbolProgressManager !== 'undefined') {
    // symbolsDataがある場合
    if (symbolProgressManager.symbolsData) {
        ['running', 'completed', 'pending', 'failed'].forEach(category => {
            if (symbolProgressManager.symbolsData[category]) {
                const originalLength = symbolProgressManager.symbolsData[category].length;
                symbolProgressManager.symbolsData[category] = symbolProgressManager.symbolsData[category].filter(s => s.symbol !== 'NEAR');
                const newLength = symbolProgressManager.symbolsData[category].length;
                if (originalLength !== newLength) {
                    console.log(`${category}からNEARを削除 (${originalLength} -> ${newLength})`);
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
            console.log(`symbols配列からNEARを削除 (${originalLength} -> ${newLength})`);
        }
    }
    
    // 内部キャッシュやマップがある場合
    if (symbolProgressManager._symbolCache) {
        delete symbolProgressManager._symbolCache.NEAR;
        console.log('_symbolCacheからNEARを削除');
    }
    
    if (symbolProgressManager.symbolStatusMap) {
        delete symbolProgressManager.symbolStatusMap.NEAR;
        console.log('symbolStatusMapからNEARを削除');
    }
    
    console.log('✅ 全ての既知の場所からNEARを削除しました');
    console.log('今すぐNEARの追加を試してください。');
} else {
    console.log('❌ クリアできません - symbolProgressManagerが見つかりません');
}