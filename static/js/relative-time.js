/**
 * 动态更新相对时间显示
 * 将静态的发布时间转换为动态的相对时间（如"5分钟前"）
 */
function updateRelativeTime() {
  const timeElements = document.querySelectorAll('.relative-time');
  
  timeElements.forEach(element => {
    const publishTime = new Date(element.dataset.publishTime);
    const now = new Date();
    const diffMs = now - publishTime;
    const diffMinutes = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    
    let timeText;
    if (diffMinutes < 1) {
      timeText = '刚刚';
    } else if (diffMinutes < 60) {
      timeText = `${diffMinutes}分钟前`;
    } else if (diffHours < 24) {
      timeText = `${diffHours}小时前`;
    } else if (diffDays < 7) {
      timeText = `${diffDays}天前`;
    } else {
      timeText = publishTime.toLocaleDateString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
      });
    }
    
    element.textContent = timeText;
  });
}

// 页面加载完成后立即更新时间
document.addEventListener('DOMContentLoaded', updateRelativeTime);

// 每分钟更新一次时间显示
setInterval(updateRelativeTime, 60000);