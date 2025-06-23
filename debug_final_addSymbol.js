// addSymbol実行時の詳細ログ（修正版）

console.log('=== addSymbol詳細ログの設定 ===');

const originalAddSymbol = symbolProgressManager.addSymbol;

symbolProgressManager.addSymbol = async function() {
    const symbolInput = document.getElementById('new-symbol-input');
    const symbol = symbolInput.value.trim().toUpperCase();
    
    console.log('🔍 addSymbol実行開始');
    console.log('入力されたsymbol:', symbol);
    console.log('現在のsymbolsData:', this.symbolsData);
    
    const allSymbols = [
        ...this.symbolsData.running,
        ...this.symbolsData.completed,
        ...this.symbolsData.pending,
        ...this.symbolsData.failed
    ];
    
    console.log('allSymbols配列の長さ:', allSymbols.length);
    console.log('running:', this.symbolsData.running.length);
    console.log('completed:', this.symbolsData.completed.length);
    console.log('pending:', this.symbolsData.pending.length);
    console.log('failed:', this.symbolsData.failed.length);
    
    // NEARが含まれているかチェック
    const nearSymbols = allSymbols.filter(s => s.symbol === symbol);
    console.log(`${symbol}のマッチング数:`, nearSymbols.length);
    
    if (nearSymbols.length > 0) {
        console.log('❌ 見つかったNEARの詳細:', nearSymbols);
        console.log('どのカテゴリにあるか:');
        console.log('- running:', this.symbolsData.running.filter(s => s.symbol === symbol));
        console.log('- completed:', this.symbolsData.completed.filter(s => s.symbol === symbol));
        console.log('- pending:', this.symbolsData.pending.filter(s => s.symbol === symbol));
        console.log('- failed:', this.symbolsData.failed.filter(s => s.symbol === symbol));
    } else {
        console.log('✅ NEARは見つかりませんでした');
    }
    
    // 元のメソッドを実行
    return originalAddSymbol.call(this);
};

console.log('✅ addSymbolメソッドにデバッグログを追加しました');
console.log('NEARを入力してボタンをクリックしてください');

// 自動でNEARを設定
const symbolInput = document.getElementById('new-symbol-input');
if (symbolInput) {
    symbolInput.value = 'NEAR';
    console.log('✅ 入力フィールドにNEARを設定しました');
}