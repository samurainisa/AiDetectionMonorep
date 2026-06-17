export const displayDocumentName = (value?: string | null, fileType?: string | null): string => {
  const normalizedType = (fileType || '').toLowerCase()
  const normalizedValue = (value || '').trim()

  if (normalizedType === 'text' || normalizedValue === 'direct_text_input') return 'Ввод текста'
  if (!normalizedValue) return 'Без имени'

  return normalizedValue
}
