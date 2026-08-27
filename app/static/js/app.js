if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => navigator.serviceWorker.register('/static/sw.js').catch(() => {}));
}

document.querySelectorAll('form').forEach((form) => {
  form.addEventListener('submit', (event) => {
    const button = event.submitter;
    // 带 name/value 的按钮用于表达“同意/拒绝”等业务决策，不能禁用，否则浏览器不会提交其值。
    if (button && !button.name && !button.dataset.keepText) {
      button.dataset.originalText = button.textContent;
      button.textContent = '处理中…';
      button.disabled = true;
    }
  });
});
