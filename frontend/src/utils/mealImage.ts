/** Max edge after client resize (matches backend). */
const MAX_EDGE = 1280
/** Target upload size soft cap. */
const MAX_BYTES = 4.5 * 1024 * 1024

/**
 * Decode any browser-supported image (incl. iPhone HEIC in Safari) to a JPEG File.
 * Avoids server 400 on HEIC / oversized camera shots.
 */
export async function normalizeMealImage(file: File): Promise<File> {
  if (!file || file.size === 0) {
    throw new Error('空文件')
  }

  let bitmap: ImageBitmap
  try {
    bitmap = await createImageBitmap(file)
  } catch {
    throw new Error('无法读取这张图，请改用相册里的 JPG/PNG，或先用系统「照片」导出后再传')
  }

  try {
    const scale = Math.min(1, MAX_EDGE / Math.max(bitmap.width, bitmap.height))
    const w = Math.max(1, Math.round(bitmap.width * scale))
    const h = Math.max(1, Math.round(bitmap.height * scale))
    const canvas = document.createElement('canvas')
    canvas.width = w
    canvas.height = h
    const ctx = canvas.getContext('2d')
    if (!ctx) throw new Error('浏览器无法处理图片')
    ctx.drawImage(bitmap, 0, 0, w, h)

    let quality = 0.85
    let blob: Blob | null = await canvasToJpeg(canvas, quality)
    while (blob && blob.size > MAX_BYTES && quality > 0.5) {
      quality -= 0.1
      blob = await canvasToJpeg(canvas, quality)
    }
    if (!blob) throw new Error('图片压缩失败')

    const base = (file.name || 'meal').replace(/\.[^.]+$/, '') || 'meal'
    return new File([blob], `${base}.jpg`, { type: 'image/jpeg', lastModified: Date.now() })
  } finally {
    bitmap.close()
  }
}

function canvasToJpeg(canvas: HTMLCanvasElement, quality: number): Promise<Blob | null> {
  return new Promise((resolve) => {
    canvas.toBlob((b) => resolve(b), 'image/jpeg', quality)
  })
}
