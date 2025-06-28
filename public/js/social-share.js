/**
 * 社交分享功能
 * 处理微信分享二维码生成
 */

// 显示微信分享二维码
function showWeixinQR() {
    const currentUrl = window.location.href;
    const title = document.title;
    
    // 创建二维码容器
    const modal = document.createElement('div');
    modal.className = 'weixin-qr-modal';
    modal.innerHTML = `
        <div class="weixin-qr-content">
            <div class="weixin-qr-header">
                <h3>微信扫码分享</h3>
                <button class="weixin-qr-close" onclick="closeWeixinQR()">&times;</button>
            </div>
            <div class="weixin-qr-body">
                <div id="weixin-qrcode"></div>
                <p>使用微信扫描二维码分享到朋友圈</p>
                <div class="weixin-qr-url">
                    <input type="text" value="${currentUrl}" readonly>
                    <button onclick="copyToClipboard('${currentUrl}')">复制链接</button>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // 生成二维码
    generateQRCode(currentUrl);
    
    // 显示模态框
    modal.style.display = 'flex';
}

// 关闭微信二维码模态框
function closeWeixinQR() {
    const modal = document.querySelector('.weixin-qr-modal');
    if (modal) {
        modal.remove();
    }
}

// 生成二维码
function generateQRCode(url) {
    const qrContainer = document.getElementById('weixin-qrcode');
    if (!qrContainer) return;
    
    // 使用在线二维码生成服务
    const qrUrl = `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(url)}`;
    
    const img = document.createElement('img');
    img.src = qrUrl;
    img.alt = '微信分享二维码';
    img.style.width = '200px';
    img.style.height = '200px';
    
    qrContainer.appendChild(img);
}

// 复制到剪贴板
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        alert('链接已复制到剪贴板');
    }).catch(() => {
        // 降级方案
        const textArea = document.createElement('textarea');
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        alert('链接已复制到剪贴板');
    });
}

// 点击模态框外部关闭
document.addEventListener('click', function(event) {
    const modal = document.querySelector('.weixin-qr-modal');
    if (modal && event.target === modal) {
        closeWeixinQR();
    }
});

// ESC键关闭模态框
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        closeWeixinQR();
    }
});