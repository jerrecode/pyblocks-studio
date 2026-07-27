export type BlockKind =
  | 'hat'
  | 'stack'
  | 'terminal'
  | 'reporter'
  | 'boolean'
  | 'container'
  | 'declaration'
  | 'import'
  | 'decorator'
  | 'comment'

export type ConnectorRole = 'input' | 'output'
export type ConnectorDirection = 'north' | 'south' | 'east' | 'west' | 'inward' | 'outward'
export type ConnectorGender = 'male' | 'female'
export type ConnectorFamily =
  | 'stack'
  | 'expression'
  | 'boolean'
  | 'name'
  | 'module'
  | 'iterable'
  | 'callable'
  | 'type'
  | 'keyword-argument'
  | 'decorator'
  | 'annotation'
  | 'body'
  | 'exception-type'
  | 'pattern'
  | 'any'

export interface ConnectorSpec {
  id: string
  role: ConnectorRole
  direction: ConnectorDirection
  gender: ConnectorGender
  family: ConnectorFamily
  acceptedTypes: string[]
  x: number
  y: number
  snapRadius: number
  multiplicity: 'one' | 'many'
  coercion: boolean
  compatibility: string
}

export interface BlockSpec {
  id: string
  namespace: string
  category: string
  label: string
  kind: BlockKind
  icon: string
  width: number
  height: number
  color?: string
  stroke?: string
  textColor?: string
  pythonTemplate: string
  connectors: ConnectorSpec[]
  fields?: Record<string, string>
  description?: string
  bodySlots?: number
  provenance?: string
}

export interface BlockInstance {
  id: string
  specId: string
  x: number
  y: number
  values: Record<string, string>
  parentId?: string
  nextId?: string
  bodyIds?: string[]
  collapsed?: boolean
  z: number
}

export interface WorkspaceGraph {
  version: 1
  blocks: BlockInstance[]
  roots: string[]
}

export interface ParameterDescriptor {
  name: string
  kind: 'positional' | 'keyword' | 'varargs' | 'kwargs'
  annotation?: string
  default?: string
  required: boolean
}

export interface CallableDescriptor {
  name: string
  qualifiedName: string
  kind: 'function' | 'method' | 'constructor'
  parameters: ParameterDescriptor[]
  returns?: string
  doc?: string
}

export interface ModuleDescriptor {
  name: string
  version: string
  summary: string
  callables: CallableDescriptor[]
  constants: Array<{ name: string; type: string; value?: string }>
  classes: Array<{ name: string; methods: CallableDescriptor[] }>
  provenance: string
}

export interface ArtifactRecord {
  id: string
  moduleName: string
  folderName: string
  createdAt: string
  descriptorVersion: string
  specs: BlockSpec[]
  svg: string
  json: string
}

export interface SnapCandidate {
  sourceBlockId: string
  sourceConnectorId: string
  targetBlockId: string
  targetConnectorId: string
  distance: number
  compatible: boolean
}
