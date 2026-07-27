import { blockPath } from './geometry'
import type { ArtifactRecord, BlockSpec, ModuleDescriptor } from './types'
import { specsFromDescriptor } from './catalog'

const STORAGE_KEY = 'pyblocks.artifacts.v1'

export function normalizeFolderName(name: string) {
  return name.trim().toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9._-]+/g, '-')
}

export function specsToSvg(moduleName: string, specs: BlockSpec[]) {
  const padding = 16
  const totalWidth = Math.max(420, ...specs.map(s => s.width + padding * 2))
  const totalHeight = specs.reduce((sum, s) => sum + s.height + padding, padding)
  let y = padding
  const symbols = specs.map((s, index) => {
    const path = blockPath(s)
    const item = `<g id="block-${index}" transform="translate(${padding} ${y})"><path d="${path}" fill="${s.color}" stroke="${s.stroke}" stroke-width="2"/><text x="18" y="${Math.max(26, s.height / 2 + 5)}" fill="${s.textColor}" font-family="system-ui,sans-serif" font-size="14" font-weight="650">${escapeXml(s.label)}</text></g>`
    y += s.height + padding
    return item
  }).join('')
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${totalWidth}" height="${totalHeight}" viewBox="0 0 ${totalWidth} ${totalHeight}" role="img" aria-label="Generated blocks for ${escapeXml(moduleName)}"><title>${escapeXml(moduleName)} blocks</title>${symbols}</svg>`
}

function escapeXml(value: string) {
  return value.replace(/[<>&'"]/g, c => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', "'": '&apos;', '"': '&quot;' })[c]!)
}

export function createArtifact(descriptor: ModuleDescriptor): ArtifactRecord {
  const specs = specsFromDescriptor(descriptor)
  const folderName = normalizeFolderName(descriptor.name)
  const json = JSON.stringify({
    schemaVersion: 1,
    virtualPath: `blocks/${folderName}/block-specs.json`,
    module: descriptor,
    generatedAt: new Date().toISOString(),
    deterministicKey: `${descriptor.name}@${descriptor.version}`,
    specs,
  }, null, 2)
  return {
    id: `${descriptor.name}@${descriptor.version}`,
    moduleName: descriptor.name,
    folderName,
    createdAt: new Date().toISOString(),
    descriptorVersion: descriptor.version,
    specs,
    svg: specsToSvg(descriptor.name, specs),
    json,
  }
}

export function loadArtifacts(): ArtifactRecord[] {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]')
  } catch {
    return []
  }
}

export function saveArtifacts(items: ArtifactRecord[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(items))
}

export function downloadText(filename: string, text: string, mime = 'text/plain') {
  const url = URL.createObjectURL(new Blob([text], { type: mime }))
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
