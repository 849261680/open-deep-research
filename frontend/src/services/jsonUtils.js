class JSONUtils {
  // 验证JSON字符串是否有效
  static isValidJSON(str) {
    if (typeof str !== 'string') return false;
    try {
      JSON.parse(str);
      return true;
    } catch (e) {
      return false;
    }
  }

  // 尝试修复不完整的JSON
  static tryFixJSON(jsonStr, onUpdate) {
    if (!jsonStr || jsonStr === '[DONE]') return;

    try {
      // 处理特殊字符
      let fixedJsonStr = jsonStr
        .replace(/\\n/g, '\\n')
        .replace(/\\'/g, "\\'")
        .replace(/\\"/g, '\\"')
        .replace(/\\&/g, '\\&')
        .replace(/\\r/g, '\\r')
        .replace(/\\t/g, '\\t')
        .replace(/\\b/g, '\\b')
        .replace(/\\f/g, '\\f');

      // 检查并修复引号
      fixedJsonStr = this._fixQuotes(fixedJsonStr);

      // 检查并修复括号
      fixedJsonStr = this._fixBrackets(fixedJsonStr);

      // 验证并解析
      if (this.isValidJSON(fixedJsonStr)) {
        const data = JSON.parse(fixedJsonStr);
        onUpdate(data);
      }
    } catch (error) {
      console.warn('修复JSON失败:', error);
    }
  }

  // 修复引号
  static _fixQuotes(str) {
    const quoteCount = (str.match(/"/g) || []).length;
    if (quoteCount % 2 !== 0) {
      return str + '"';
    }
    return str;
  }

  // 修复括号
  static _fixBrackets(str) {
    const openBraceCount = (str.match(/{/g) || []).length;
    const closeBraceCount = (str.match(/}/g) || []).length;
    const openBracketCount = (str.match(/\[/g) || []).length;
    const closeBracketCount = (str.match(/\]/g) || []).length;

    if (openBraceCount > closeBraceCount) {
      return str + '}';
    } else if (openBracketCount > closeBracketCount) {
      return str + ']';
    }
    return str;
  }

  // 安全解析JSON
  static safeParse(jsonStr, defaultValue = {}) {
    try {
      return JSON.parse(jsonStr);
    } catch (error) {
      return defaultValue;
    }
  }
}

export default JSONUtils;