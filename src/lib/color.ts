const curated: Record<string, number> = {
  flow: 18,
  data: 218,
  operators: 145,
  functions: 282,
  classes: 330,
  exceptions: 355,
  async: 188,
  imports: 42,
  files: 168,
  collections: 112,
  typing: 258,
  stdlib: 204,
  external: 300,
}

export function hashString(input: string): number {
  let h = 2166136261
  for (let i = 0; i < input.length; i += 1) {
    h ^= input.charCodeAt(i)
    h = Math.imul(h, 16777619)
  }
  return h >>> 0
}

export function blockColor(namespace: string, category: string, kind: string) {
  const base = curated[category] ?? hashString(namespace) % 360
  const variant = (hashString(`${namespace}:${kind}`) % 17) - 8
  const hue = (base + variant + 360) % 360
  const saturation = kind === 'comment' ? 36 : kind === 'boolean' ? 72 : 66
  const lightness = kind === 'decorator' ? 52 : kind === 'reporter' ? 56 : 50
  const fill = `hsl(${hue} ${saturation}% ${lightness}%)`
  const stroke = `hsl(${hue} ${Math.min(84, saturation + 8)}% ${Math.max(24, lightness - 20)}%)`
  const textColor = lightness < 60 ? '#ffffff' : '#101522'
  return { fill, stroke, textColor }
}
