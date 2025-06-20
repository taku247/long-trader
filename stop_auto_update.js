// 自動更新を停止してNEARを削除

console.log('=== 自動更新停止とNEAR削除 ===');

// 自動更新を一時停止
try {
    symbolProgressManager.stopAutoUpdate();
    console.log('✅ 自動更新を停止しました');
} catch (e) {
    console.log('自動更新停止エラー:', e.message);
}

// NEARを削除
symbolProgressManager.symbolsData.completed = symbolProgressManager.symbolsData.completed.filter(s => s.symbol !== 'NEAR');
console.log('✅ completedからNEARを削除');

// 削除結果を確認
const nearCheck = symbolProgressManager.symbolsData.completed.filter(s => s.symbol === 'NEAR');
console.log('削除後のNEAR件数:', nearCheck.length);

// 画面の表示も更新
try {
    symbolProgressManager.renderSymbols();
    console.log('✅ 画面表示を更新');
} catch (e) {
    console.log('画面更新エラー:', e.message);
}

console.log('今すぐNEARを追加してみてください');

// 入力フィールドにNEARを設定
const symbolInput = document.getElementById('new-symbol-input');
if (symbolInput) {
    symbolInput.value = 'NEAR';
    console.log('✅ 入力フィールドにNEARを設定');
}