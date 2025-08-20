/**
 * 下拉框更新工具函数
 * 提供稳定的选择框更新，避免用户选择丢失
 */

class DropdownUtils {
    /**
     * 安全地更新下拉框选项
     * @param {HTMLElement} selectElement - 下拉框元素
     * @param {Array} options - 选项数组 [{value: '', text: ''}]
     * @param {string} defaultText - 默认提示文本
     * @param {boolean} keepSelection - 是否保持当前选择
     */
    static updateSelect(selectElement, options, defaultText = '', keepSelection = true) {
        if (!selectElement || !Array.isArray(options)) {
            console.warn('无效的参数');
            return;
        }

        // 保存当前选中的值
        const currentValue = keepSelection ? selectElement.value : '';
        
        // 生成新的选项HTML
        let html = defaultText ? `<option value="">${defaultText}</option>` : '';
        html += options.map(option => 
            `<option value="${option.value}">${option.text}</option>`
        ).join('');
        
        // 更新选项
        selectElement.innerHTML = html;
        
        // 恢复之前的选择（如果值仍然存在）
        if (keepSelection && currentValue && options.some(opt => opt.value === currentValue)) {
            selectElement.value = currentValue;
        } else if (defaultText) {
            selectElement.value = '';
        }
    }

    /**
     * 更新线程池下拉框
     * @param {Array} pools - 线程池数组
     * @param {string} selectId - 下拉框ID
     * @param {string} defaultText - 默认提示文本
     */
    static updatePoolSelect(pools, selectId, defaultText = '请选择线程池') {
        const select = document.getElementById(selectId);
        if (!select) return;

        const options = pools.map(pool => ({
            value: pool.pool_id,
            text: pool.name
        }));

        this.updateSelect(select, options, defaultText);
    }

    /**
     * 批量更新多个下拉框
     * @param {Array} pools - 线程池数组
     * @param {Object} selectConfigs - 配置对象 {selectId: defaultText}
     */
    static updateMultiplePoolSelects(pools, selectConfigs) {
        if (!pools || !selectConfigs) {
            console.warn('无效的参数');
            return;
        }
        Object.entries(selectConfigs).forEach(([selectId, defaultText]) => {
            this.updatePoolSelect(pools, selectId, defaultText);
        });
    }

    /**
     * 加载线程池到下拉框
     */
    static loadPoolsForTaskModal() {
        fetch('/api/pools')
            .then(response => response.json())
            .then(result => {
                if (result.success && result.data) {
                    this.updatePoolSelect(result.data, 'taskPoolSelect', '请选择线程池');
                    this.updatePoolSelect(result.data, 'poolFilter', '所有线程池');
                }
            })
            .catch(error => {
                console.error('加载线程池失败:', error);
            });
    }
}

// 导出到全局作用域
if (typeof window !== 'undefined') {
    window.DropdownUtils = DropdownUtils;
}