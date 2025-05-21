export const formatText = (text: string, maxLength: number = 90) => {
    if (!text) return '';
    return text.length > maxLength ? `${text.substring(0, maxLength)}...` : text;
};